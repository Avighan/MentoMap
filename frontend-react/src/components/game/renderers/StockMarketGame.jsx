/**
 * StockMarketGame — Tier-2 (Zerodha/Groww-style) realtime stock-market
 * simulator. The server (backend stocksim engine) is authoritative for
 * prices, fills, P&L, and end-of-game scoring. This renderer:
 *   - Calls POST /stocksim/start on mount.
 *   - Polls GET /stocksim/state every config.tick_interval_ms.
 *   - Between polls, uses priceFromSeed(seed, symbol, tick, stockCfg)
 *     for chart smoothing only (server snaps it back on the next poll).
 *   - Sends trades through POST /stocksim/trade and surfaces filled /
 *     queued / rejected outcomes inline.
 *   - On final tick or manual complete, calls POST /stocksim/complete
 *     and renders the recap with backend-returned dimensions and P&L.
 *
 * Existing visual theme (#F0F4FF bg, sticky header, progress bar, blue/green/red
 * trade buttons, framer-motion banners), OnboardingFlow, FloatingDeltaLayer,
 * StreakBanner, and useEngagementSystem hook are all preserved.
 */
import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
} from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import useEngagementSystem from '../../../hooks/useEngagementSystem';
import { FloatingDeltaLayer, StreakBanner } from '../BoardGameExtras';
import OnboardingFlow from '../onboarding/OnboardingFlow';
import PostGameInsights from '../PostGameInsights';
import {
  startStocksim,
  getStocksimState,
  placeStocksimTrade,
  cancelStocksimOrder,
  completeStocksim,
} from '../../../api/stocksim';
import { priceFromSeed } from '../../../utils/stocksimPricing';
import OrderTicket from './stocksim/OrderTicket';
import DepthLadder from './stocksim/DepthLadder';
import NewsTickerStrip from './stocksim/NewsTickerStrip';
import PortfolioPanel from './stocksim/PortfolioPanel';
import EventOverlay from './stocksim/EventOverlay';
import MarketBriefing from './stocksim/MarketBriefing';
import { useOrg } from '../../../contexts/OrgContext';

const CHART_HEIGHT = 160;
const CHART_WIDTH_PER_TICK = 28;
const DEFAULT_POLL_MS = 8000;

/* Mini sparkline-style SVG chart (chart-only smoothing — not authoritative). */
const PriceChart = ({ history, color, height = CHART_HEIGHT }) => {
  if (!history || history.length < 2) return null;
  const width = Math.max(history.length * CHART_WIDTH_PER_TICK, 200);
  const min = Math.min(...history) * 0.95;
  const max = Math.max(...history) * 1.05;
  const range = max - min || 1;

  const points = history
    .map((p, i) => {
      const x = (i / (history.length - 1)) * (width - 20) + 10;
      const y = height - 10 - ((p - min) / range) * (height - 20);
      return `${x},${y}`;
    })
    .join(' ');

  const lastY =
    height - 10 - ((history[history.length - 1] - min) / range) * (height - 20);
  const fillPoints = `10,${height - 10} ${points} ${width - 10},${height - 10}`;
  const gradId = `grad-${(color || '#3b82f6').replace('#', '')}`;

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="rounded-lg"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={fillPoints} fill={`url(#${gradId})`} />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx={width - 10}
        cy={lastY}
        r="4"
        fill={color}
        stroke="white"
        strokeWidth="2"
      />
    </svg>
  );
};

const SECTOR_COLORS = {
  IT: '#3b82f6',
  Banking: '#10b981',
  Pharma: '#a855f7',
  Auto: '#f59e0b',
  Energy: '#ef4444',
  FMCG: '#06b6d4',
  Metals: '#6b7280',
};

const colorForStock = (s) =>
  s.color || SECTOR_COLORS[s.sector] || '#3b82f6';

const StockMarketGame = ({
  config = {},
  gameData,
  runId,
  onComplete,
  allowEarlyExit = false,
}) => {
  const showEarlyExit = allowEarlyExit || config?.allow_early_exit || false;
  const navigate = useNavigate();
  const engagement = useEngagementSystem();
  const [onboardingPhase, setOnboardingPhase] = useState('story');

  // Server-authoritative session
  const [sessionConfig, setSessionConfig] = useState(null); // backend config
  const [seed, setSeed] = useState(null);
  const [profile] = useState(config.profile || 'day_trader');
  const [serverState, setServerState] = useState(null); // { cash, holdings, ... }
  const [quotes, setQuotes] = useState({}); // { symbol: { mid, bid, ask, volume } }
  const [pnl, setPnl] = useState({ total: 0, realized: 0, unrealized: 0 });
  const [haltedSymbols, setHaltedSymbols] = useState({});
  const [activeEvent, setActiveEvent] = useState(null);
  const [newsStrip, setNewsStrip] = useState([]);

  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [priceHistory, setPriceHistory] = useState({});
  const [tradeMessage, setTradeMessage] = useState(null); // { type, text }
  const [recap, setRecap] = useState(null);
  const [completing, setCompleting] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const { org } = useOrg();
  const v2Enabled = !!org?.flags?.stocksim_v2_ui;
  const cfg = gameData?.minigame_config?.stock_market_config || {};
  const briefing = cfg.briefing;
  const [phase, setPhase] = useState(v2Enabled && briefing ? 'briefing' : 'playing');

  const pollTimerRef = useRef(null);
  const smoothingTimerRef = useRef(null);
  const completedSentRef = useRef(false);
  const tradeMessageTimerRef = useRef(null);
  const pnlRef = useRef({ total: 0, realized: 0, unrealized: 0 });
  const currentTickRef = useRef(0);

  // Cleanup trade-message timer on unmount.
  useEffect(() => () => {
    if (tradeMessageTimerRef.current) clearTimeout(tradeMessageTimerRef.current);
  }, []);

  // ── Bootstrap session ───────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    if (!runId) return undefined;
    (async () => {
      try {
        const data = await startStocksim(runId, { profile });
        if (cancelled) return;
        setSeed(data.seed);
        setSessionConfig(data.config || {});
        setServerState(data.state || {});
        setNewsStrip(data.news_strip || []);
        const stocks = data.config?.stocks || [];
        const firstSym = stocks[0]?.symbol || null;
        setSelectedSymbol(firstSym);
        // Seed price history with starting prices (tick 0).
        const hist = {};
        stocks.forEach((s) => {
          hist[s.symbol] = [s.starting_price];
        });
        setPriceHistory(hist);
      } catch (err) {
        if (!cancelled) {
          // eslint-disable-next-line no-console
          console.error('stocksim start failed', err);
          setLoadError(err?.message || 'Failed to start stocksim');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId, profile]);

  // ── Authoritative state poll ────────────────────────────────────────
  const pollState = useCallback(async () => {
    if (!runId) return;
    try {
      const data = await getStocksimState(runId);
      if (!data) return;
      setServerState(data.state || {});
      currentTickRef.current = data.state?.current_tick ?? 0;
      setQuotes(data.quotes || {});
      const nextPnl = data.pnl || { total: 0, realized: 0, unrealized: 0 };
      setPnl(nextPnl);
      pnlRef.current = nextPnl;
      setHaltedSymbols(data.halted_symbols || {});
      if (data.event) setActiveEvent(data.event);
      // Append authoritative mid to price history at the new tick.
      const tick = data.state?.current_tick ?? 0;
      setPriceHistory((prev) => {
        const next = { ...prev };
        Object.entries(data.quotes || {}).forEach(([sym, q]) => {
          const hist = next[sym] || [];
          // Pad to length tick+1 (so index aligns with tick number).
          while (hist.length < tick) {
            hist.push(hist[hist.length - 1] ?? q.mid);
          }
          if (hist.length === tick) hist.push(q.mid);
          else hist[tick] = q.mid;
          next[sym] = hist.slice(-80); // cap chart length
        });
        return next;
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('stocksim poll error', err);
    }
  }, [runId]);

  useEffect(() => {
    if (!sessionConfig) return undefined;
    const intervalMs = sessionConfig.tick_interval_ms || DEFAULT_POLL_MS;
    // Kick once immediately so the UI has authoritative data quickly.
    pollState();
    pollTimerRef.current = setInterval(pollState, intervalMs);
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [sessionConfig, pollState]);

  // ── Chart smoothing between polls ───────────────────────────────────
  // Uses priceFromSeed for visual smoothing only. Does not touch fills/P&L.
  useEffect(() => {
    if (!sessionConfig || seed == null) return undefined;
    const stocks = sessionConfig.stocks || [];
    const intervalMs = Math.max(
      500,
      Math.floor((sessionConfig.tick_interval_ms || DEFAULT_POLL_MS) / 4),
    );
    smoothingTimerRef.current = setInterval(() => {
      const tick = currentTickRef.current ?? 0;
      // Pull "next tick" preview just so the line nudges visually.
      setPriceHistory((prev) => {
        const next = { ...prev };
        stocks.forEach((s) => {
          try {
            const q = priceFromSeed(seed, s.symbol, tick + 1, s);
            const hist = next[s.symbol] || [];
            // Replace the trailing preview slot only; never beyond tick+1.
            const target = tick + 1;
            const clone = hist.slice();
            while (clone.length < target) {
              clone.push(clone[clone.length - 1] ?? q.mid);
            }
            clone[target] = q.mid;
            next[s.symbol] = clone.slice(-80);
          } catch (e) {
            /* ignore */
          }
        });
        return next;
      });
    }, intervalMs);
    return () => {
      if (smoothingTimerRef.current) clearInterval(smoothingTimerRef.current);
    };
  }, [sessionConfig, seed]);

  // ── Auto-complete when reaching final tick ──────────────────────────
  const finishGame = useCallback(async () => {
    if (!runId || completedSentRef.current) return;
    completedSentRef.current = true;
    setCompleting(true);
    try {
      const data = await completeStocksim(runId);
      setRecap(data);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('stocksim complete failed', err);
      setRecap({
        pnl: pnlRef.current,
        dimensions: {},
        recap_messages: ['Could not load recap from server.'],
        xp_awarded: 0,
        completed: true,
      });
    } finally {
      setCompleting(false);
    }
  }, [runId]);

  useEffect(() => {
    const tickCount = sessionConfig?.tick_count;
    const cur = serverState?.current_tick;
    if (
      sessionConfig &&
      typeof tickCount === 'number' &&
      typeof cur === 'number' &&
      cur >= tickCount - 1 &&
      !recap &&
      !completedSentRef.current
    ) {
      finishGame();
    }
    if (serverState?.completed && !recap && !completedSentRef.current) {
      finishGame();
    }
  }, [serverState, sessionConfig, recap, finishGame]);

  // ── Trade submission ────────────────────────────────────────────────
  const handleTradeSubmit = useCallback(
    async (payload) => {
      if (!runId) return;
      const tick = serverState?.current_tick ?? 0;
      try {
        const res = await placeStocksimTrade(runId, { ...payload, tick });
        if (res.status === 'rejected') {
          setTradeMessage({
            type: 'error',
            text: res.message || 'Order rejected',
          });
          engagement.recordChoice?.(-1);
        } else if (res.status === 'queued') {
          setTradeMessage({
            type: 'queued',
            text: 'Order queued for next tick',
          });
          engagement.recordChoice?.(1);
        } else if (res.status === 'filled') {
          setTradeMessage({
            type: 'success',
            text: `${payload.side === 'buy' ? 'Bought' : 'Sold'} ${
              res.fill?.qty ?? payload.qty
            } ${payload.symbol} @ ₹${res.fill?.price?.toFixed?.(2) ?? '-'}`,
          });
          // Optimistic update from response.
          setServerState((prev) => ({
            ...(prev || {}),
            cash: res.new_cash ?? prev?.cash,
            holdings: res.new_holdings ?? prev?.holdings,
          }));
          engagement.recordChoice?.(payload.side === 'buy' ? 2 : 3);
        } else {
          setTradeMessage({ type: 'info', text: res.message || 'Submitted' });
        }
        // Always re-sync after a trade.
        pollState();
      } catch (err) {
        setTradeMessage({
          type: 'error',
          text: err?.message || 'Network error placing trade',
        });
      }
      // Auto-clear the message after 3.5s (cleared on unmount via effect).
      if (tradeMessageTimerRef.current) clearTimeout(tradeMessageTimerRef.current);
      tradeMessageTimerRef.current = setTimeout(() => setTradeMessage(null), 3500);
    },
    [runId, serverState?.current_tick, engagement, pollState],
  );

  const handleDismissEvent = useCallback(() => setActiveEvent(null), []);

  const handleCancelOrder = useCallback(
    async (orderId) => {
      if (!runId || !orderId) return;
      try {
        await cancelStocksimOrder(runId, orderId);
        pollState();
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('cancel order failed', err);
      }
    },
    [runId, pollState],
  );

  // ── Derived values for the existing visual theme ────────────────────
  const stocks = sessionConfig?.stocks || [];
  const tickCount = sessionConfig?.tick_count || 22;
  const startingCapital = sessionConfig?.starting_capital || 100000;
  const cash = serverState?.cash ?? startingCapital;
  const holdings = serverState?.holdings || {};
  const currentTick = serverState?.current_tick ?? 0;
  const transactions = serverState?.trade_log || [];

  const portfolioValue = useMemo(() => {
    let v = 0;
    Object.entries(holdings).forEach(([sym, h]) => {
      const q = quotes[sym];
      v += (h?.qty || 0) * (q?.mid ?? h?.avg_price ?? 0);
    });
    return v;
  }, [holdings, quotes]);

  const totalValue = (cash || 0) + portfolioValue;
  const profitAbs = totalValue - startingCapital;
  const profitPct =
    startingCapital > 0 ? (profitAbs / startingCapital) * 100 : 0;

  const selectedStockInfo = stocks.find((s) => s.symbol === selectedSymbol);
  const selectedQuote = selectedSymbol ? quotes[selectedSymbol] : null;

  // ── Loading / error states ──────────────────────────────────────────
  if (loadError) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ backgroundColor: '#F0F4FF' }}
      >
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md text-center">
          <div className="text-5xl mb-3">⚠️</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">
            Could not start session
          </h2>
          <p className="text-sm text-gray-500 mb-4">{loadError}</p>
          <button
            onClick={() => navigate('/games')}
            className="px-5 py-2.5 bg-blue-500 text-white font-bold rounded-xl shadow-lg hover:bg-blue-600"
          >
            Back to Games
          </button>
        </div>
      </div>
    );
  }

  if (!sessionConfig) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ backgroundColor: '#F0F4FF' }}
      >
        <div className="text-gray-500 animate-pulse">Loading market…</div>
      </div>
    );
  }

  // ── Recap (game over) ───────────────────────────────────────────────
  if (recap) {
    const totalPnL = recap.pnl?.total ?? profitAbs;
    const dims = recap.dimensions || {};
    const messages = recap.recap_messages || [];
    const emoji =
      totalPnL >= startingCapital * 0.3
        ? '🏆'
        : totalPnL >= 0
        ? '📈'
        : '📉';
    return (
      <div
        className="min-h-screen flex items-center justify-center p-4"
        style={{ backgroundColor: '#F0F4FF' }}
      >
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="bg-white text-gray-900 rounded-2xl shadow-2xl p-10 max-w-xl w-full text-center"
        >
          <div className="text-7xl mb-4">{emoji}</div>
          <h2 className="text-3xl font-bold text-gray-800 mb-2">
            Market Closed!
          </h2>
          <p className="text-gray-500 mb-1">Total P&L</p>
          <p
            className={`text-4xl font-bold mb-4 ${
              totalPnL >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {totalPnL >= 0 ? '+' : ''}₹{Math.round(totalPnL).toLocaleString()}
          </p>

          {Object.keys(dims).length > 0 && (
            <div className="grid grid-cols-2 gap-3 mb-5 text-left">
              {Object.entries(dims).map(([k, v]) => (
                <div
                  key={k}
                  className="bg-gray-50 rounded-lg p-3 border border-gray-100"
                >
                  <div className="text-[10px] uppercase tracking-wider text-gray-400">
                    {k.replace(/_/g, ' ')}
                  </div>
                  <div className="text-lg font-bold text-gray-800">
                    {Math.round(Number(v))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {messages.length > 0 && (
            <ul className="text-sm text-gray-600 mb-5 space-y-1 text-left list-disc list-inside">
              {messages.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          )}

          {recap.xp_awarded ? (
            <div className="text-xs text-blue-500 mb-3">
              +{recap.xp_awarded} XP awarded
            </div>
          ) : null}

          <PostGameInsights
            summary={null}
            state={{
              score: Math.round(totalPnL),
              transactions_count: transactions?.length || 0,
            }}
            gameType="minigame"
            won={totalPnL >= 0}
            runId={runId}
          />

          <div className="flex gap-3 justify-center mt-4">
            <button
              onClick={() => {
                if (onComplete) onComplete({ completed: true, ...recap });
                else navigate('/games');
              }}
              className="px-5 py-2.5 bg-blue-500 text-white font-bold rounded-xl shadow-lg hover:bg-blue-600"
            >
              View Report &amp; Rewards
            </button>
            <button
              onClick={() => navigate('/games')}
              className="px-5 py-2.5 bg-gray-100 text-gray-600 rounded-xl hover:bg-gray-200"
            >
              Back to Games
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // ── v2 Market Briefing screen ────────────────────────────────────────
  if (v2Enabled && phase === 'briefing') {
    return <MarketBriefing briefing={briefing} stocks={cfg.stocks || []} onBegin={() => setPhase('playing')} />;
  }

  // ── Main UI ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen" style={{ backgroundColor: '#F0F4FF' }}>
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b shadow-sm px-6 py-3 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/games')}
            className="text-gray-400 hover:text-gray-600"
          >
            ← Back
          </button>
          <h1 className="text-xl font-bold text-gray-800">
            {gameData?.title || 'Stock Market'}
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            Tick{' '}
            <b data-testid="stocksim-tick" className="text-gray-800">
              {currentTick}
            </b>{' '}
            / {tickCount}
          </span>
          <span
            className={`text-sm font-bold ${
              profitPct >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {profitPct >= 0 ? '▲' : '▼'} {profitPct.toFixed(1)}%
          </span>
        </div>
      </header>

      {/* Progress bar */}
      <div className="h-1.5 bg-gray-100">
        <motion.div
          className="h-full bg-blue-400"
          animate={{ width: `${(currentTick / Math.max(1, tickCount)) * 100}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* News strip */}
      <NewsTickerStrip newsStrip={newsStrip} currentTick={currentTick} />

      {/* Event overlay */}
      <EventOverlay event={activeEvent} onDismiss={handleDismissEvent} />

      {/* Trade message banner */}
      {tradeMessage && (
        <div
          className={`mx-6 mt-3 rounded-lg p-3 text-sm font-medium ${
            tradeMessage.type === 'error'
              ? 'bg-red-50 text-red-700 border border-red-200'
              : tradeMessage.type === 'queued'
              ? 'bg-amber-50 text-amber-800 border border-amber-200'
              : 'bg-green-50 text-green-700 border border-green-200'
          }`}
        >
          {tradeMessage.text}
        </div>
      )}

      <div className="flex h-[calc(100vh-56px)]">
        {/* Main area */}
        <div className="flex-1 p-5 overflow-y-auto">
          {/* Portfolio summary */}
          <div className="grid grid-cols-3 gap-4 mb-5">
            <div className="bg-white text-gray-900 rounded-xl p-4 shadow-sm border border-gray-100">
              <p className="text-xs text-gray-400 uppercase tracking-wide">
                Cash
              </p>
              <p
                data-testid="stocksim-cash"
                className="text-2xl font-bold text-gray-800"
              >
                ₹
                {Math.round(cash).toLocaleString(undefined, {
                  maximumFractionDigits: 0,
                })}
              </p>
            </div>
            <div className="bg-white text-gray-900 rounded-xl p-4 shadow-sm border border-gray-100">
              <p className="text-xs text-gray-400 uppercase tracking-wide">
                Portfolio Value
              </p>
              <p className="text-2xl font-bold text-gray-800">
                ₹
                {Math.round(portfolioValue).toLocaleString(undefined, {
                  maximumFractionDigits: 0,
                })}
              </p>
            </div>
            <div
              className={`rounded-xl p-4 shadow-sm border ${
                profitPct >= 0
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <p className="text-xs text-gray-400 uppercase tracking-wide">
                Total P&L
              </p>
              <p
                className={`text-2xl font-bold ${
                  profitPct >= 0 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {profitAbs >= 0 ? '+' : ''}₹{Math.round(profitAbs)}
              </p>
            </div>
          </div>

          {/* Selected stock chart */}
          {selectedStockInfo && (
            <div className="bg-white text-gray-900 rounded-xl shadow-sm border border-gray-100 p-4 mb-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: colorForStock(selectedStockInfo) }}
                  />
                  <span className="font-bold text-gray-800">
                    {selectedStockInfo.name}
                  </span>
                  <span className="text-sm text-gray-400">
                    {selectedStockInfo.symbol}
                  </span>
                  {haltedSymbols?.[selectedSymbol] && (
                    <span className="ml-2 text-[10px] uppercase bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                      Halted
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <span className="text-lg font-bold text-gray-800">
                    ₹
                    {(selectedQuote?.mid ?? selectedStockInfo.starting_price ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>
              <PriceChart
                history={priceHistory[selectedSymbol] || []}
                color={colorForStock(selectedStockInfo)}
              />
            </div>
          )}

          {/* Stock cards */}
          <div className="grid grid-cols-2 gap-3">
            {stocks.map((s) => {
              const q = quotes[s.symbol] || {};
              const px = q.mid ?? s.starting_price;
              const h = priceHistory[s.symbol] || [];
              const changePct =
                h.length >= 2 ? ((h[h.length - 1] - h[0]) / h[0]) * 100 : 0;
              const isSelected = selectedSymbol === s.symbol;
              const shareCount = holdings?.[s.symbol]?.qty || 0;
              return (
                <motion.button
                  key={s.symbol}
                  data-testid={`stocksim-stock-${s.symbol}`}
                  onClick={() => setSelectedSymbol(s.symbol)}
                  className={`text-left p-4 rounded-xl border-2 transition-all shadow-sm ${
                    isSelected
                      ? 'border-blue-400 bg-blue-50 shadow-md'
                      : 'border-gray-100 bg-white hover:border-gray-300'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: colorForStock(s) }}
                      />
                      <span className="font-bold text-gray-800 text-sm">
                        {s.symbol}
                      </span>
                    </div>
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                        changePct >= 0
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {changePct >= 0 ? '+' : ''}
                      {changePct.toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mb-1">{s.name}</p>
                  <p className="text-lg font-bold text-gray-800">
                    ₹{Number(px || 0).toFixed(2)}
                  </p>
                  {shareCount > 0 && (
                    <p className="text-xs text-blue-600 mt-1">
                      {shareCount} shares held
                    </p>
                  )}
                </motion.button>
              );
            })}
          </div>
        </div>

        {/* Sidebar */}
        <aside className="w-96 border-l bg-white/90 backdrop-blur-sm p-5 flex flex-col gap-4 overflow-y-auto">
          <div className="flex gap-3">
            <div className="flex-1">
              <OrderTicket
                stocks={stocks}
                selectedSymbol={selectedSymbol}
                onSelectSymbol={setSelectedSymbol}
                currentQuote={selectedQuote}
                cashAvailable={cash}
                holdings={holdings}
                onSubmit={handleTradeSubmit}
                disabled={completing || !!haltedSymbols?.[selectedSymbol]}
              />
            </div>
            <DepthLadder
              bid={selectedQuote?.bid}
              ask={selectedQuote?.ask}
              mid={selectedQuote?.mid}
              volume={selectedQuote?.volume}
            />
          </div>

          {/* Pending orders */}
          {Array.isArray(serverState?.pending_orders) &&
            serverState.pending_orders.length > 0 && (
              <div className="bg-gray-50 rounded-xl p-4">
                <h4 className="text-xs uppercase tracking-wider text-gray-400 font-semibold mb-2">
                  Pending Orders
                </h4>
                <div className="space-y-1">
                  {serverState.pending_orders.map((o) => (
                    <div
                      key={o.id || o.order_id}
                      className="flex items-center justify-between text-xs"
                    >
                      <span
                        className={
                          o.side === 'buy' ? 'text-green-600' : 'text-red-600'
                        }
                      >
                        {o.side === 'buy' ? '▲' : '▼'} {o.qty}× {o.symbol}{' '}
                        {o.order_type}
                      </span>
                      <button
                        onClick={() => handleCancelOrder(o.id || o.order_id)}
                        className="text-blue-500 hover:underline"
                      >
                        Cancel
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

          <PortfolioPanel
            holdings={holdings}
            quotes={quotes}
            transactions={transactions}
            cash={cash}
            totalValue={totalValue}
            pnl={pnl}
          />

          {/* Manual complete escape hatch (e.g. for teachers/tests). */}
          {showEarlyExit && (
            <button
              onClick={finishGame}
              disabled={completing}
              className="w-full py-2 text-xs text-gray-500 hover:text-gray-700 underline"
            >
              {completing ? 'Completing…' : 'End session early'}
            </button>
          )}
        </aside>
      </div>
      <OnboardingFlow
        gameData={gameData}
        phase={onboardingPhase}
        setPhase={setOnboardingPhase}
      />
      <FloatingDeltaLayer floatingDeltas={engagement.floatingDeltas} />
      <StreakBanner
        streakCount={engagement.streakCount}
        streakMultiplier={engagement.streakMultiplier}
      />
    </div>
  );
};

export default StockMarketGame;
