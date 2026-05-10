// PortfolioModal.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { THEME } from './theme';
import OverviewTab from './portfolio/OverviewTab';
import HoldingsTab from './portfolio/HoldingsTab';
import TradesTab from './portfolio/TradesTab';
import PerformanceTab from './portfolio/PerformanceTab';
import { netWorthSeries } from './portfolio/netWorthSeries';
import {
  maxDrawdown, concentration, hitRatio, sectorExposureSeries, benchmarkSeries, dayPnL,
} from './portfolio/portfolioMetrics';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'holdings', label: 'Holdings' },
  { id: 'trades', label: 'Trades' },
  { id: 'performance', label: 'Performance' },
];

export default function PortfolioModal({
  open, onClose,
  cash = 0, startingCash = 0, netWorth = 0, todayPnL = 0, pnl = { realized: 0, unrealized: 0 },
  holdings = {}, quotes = {}, transactions = [], priceHistory = {},
  currentTick = 0, stocks = [], days = [],
  onOpenSymbol,
}) {
  const [tab, setTab] = useState('overview');
  const [sectorFilter, setSectorFilter] = useState(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const sectorBySymbol = useMemo(() => {
    const m = {};
    for (const s of stocks) m[s.symbol] = s.sector;
    return m;
  }, [stocks]);

  const nwSeries = useMemo(
    () => netWorthSeries(transactions, priceHistory, startingCash || (cash + Object.values(holdings).reduce((s, h) => s, 0)), currentTick),
    [transactions, priceHistory, startingCash, cash, holdings, currentTick]
  );

  const livePrices = useMemo(() => {
    const p = {};
    for (const sym of Object.keys(quotes)) p[sym] = quotes[sym]?.mid ?? 0;
    return p;
  }, [quotes]);

  const allocation = useMemo(() => {
    const sectorTotals = {};
    let total = 0;
    for (const sym of Object.keys(holdings)) {
      const qty = holdings[sym]?.qty ?? 0;
      if (!qty) continue;
      const px = livePrices[sym] ?? 0;
      const mv = qty * px;
      total += mv;
      const sec = sectorBySymbol[sym] ?? 'Other';
      sectorTotals[sec] = (sectorTotals[sec] ?? 0) + mv;
    }
    return Object.entries(sectorTotals).map(([label, mv]) => ({
      label, value: total > 0 ? (mv / total) * 100 : 0,
    }));
  }, [holdings, livePrices, sectorBySymbol]);

  const holdingsRows = useMemo(() => Object.keys(holdings).map((sym) => {
    const h = holdings[sym] || {};
    const px = livePrices[sym] ?? 0;
    const avg = h.avg_price ?? 0;
    const qty = h.qty ?? 0;
    const pnlAbs = (px - avg) * qty;
    const pnlPct = avg > 0 ? ((px - avg) / avg) * 100 : 0;
    const ph = priceHistory[sym] ?? [];
    const dayDelta = ph.length >= 2 ? (ph[ph.length - 1] - ph[Math.max(0, ph.length - 2)]) * qty : 0;
    return {
      symbol: sym, sector: sectorBySymbol[sym] ?? 'Other', qty,
      avgCost: avg, ltp: px, pnlAbs, pnlPct, dayDelta,
    };
  }).filter((r) => r.qty), [holdings, livePrices, priceHistory, sectorBySymbol]);

  const tradesEnriched = useMemo(() => {
    if (!days.length) return transactions.map((t) => ({ ...t, dayLabel: '' }));
    const ranges = [];
    let acc = 0;
    for (const d of days) { ranges.push({ id: d.id, label: d.label, start: acc, end: acc + d.ticks }); acc += d.ticks; }
    return transactions.map((t) => {
      const r = ranges.find((rr) => (t.tick ?? 0) >= rr.start && (t.tick ?? 0) < rr.end);
      return { ...t, dayLabel: r?.label ?? '' };
    });
  }, [transactions, days]);

  const perfDayPnL  = useMemo(() => dayPnL(transactions, days), [transactions, days]);
  const benchmark   = useMemo(() => benchmarkSeries(priceHistory, currentTick), [priceHistory, currentTick]);
  const portfolioPctSeries = useMemo(() => {
    if (!nwSeries.length) return [];
    const start = nwSeries[0] || 1;
    return nwSeries.map((v) => ((v - start) / start) * 100);
  }, [nwSeries]);
  const topConc     = useMemo(() => concentration(holdings, livePrices), [holdings, livePrices]);
  const hr          = useMemo(() => hitRatio(transactions), [transactions]);

  if (!open) return null;

  return (
    <div
      data-testid="portfolio-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(60,40,10,0.4)',
        zIndex: 110, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 12, maxWidth: 720, width: '100%',
          maxHeight: '90vh', overflow: 'hidden', border: `1px solid ${THEME.borderTile}`,
          display: 'flex', flexDirection: 'column',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 12, borderBottom: `1px solid ${THEME.borderTile}` }}>
          <div style={{ fontWeight: 800, color: THEME.textPrimary }}>📊 My Portfolio</div>
          <button onClick={onClose} aria-label="close" style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: THEME.textMuted }}>✕</button>
        </div>
        <div style={{ display: 'flex', gap: 4, padding: '0 12px', borderBottom: `1px solid ${THEME.borderTile}`, background: THEME.bgTile }}>
          {TABS.map((t) => (
            <button
              key={t.id}
              data-testid={`portfolio-tab-${t.id}`}
              data-active={tab === t.id ? 'true' : 'false'}
              onClick={() => setTab(t.id)}
              style={{
                padding: '8px 12px', border: 'none', cursor: 'pointer',
                background: tab === t.id ? '#fff' : 'transparent',
                color: tab === t.id ? THEME.accentWarm : THEME.textMuted,
                fontWeight: tab === t.id ? 700 : 500,
                borderBottom: tab === t.id ? `2px solid ${THEME.accentWarm}` : '2px solid transparent',
              }}
            >{t.label}</button>
          ))}
        </div>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {tab === 'overview' && (
            <OverviewTab
              netWorth={netWorth}
              startingCash={startingCash}
              todayPnL={todayPnL}
              cash={cash}
              holdingsValue={netWorth - cash}
              realizedPnL={pnl.realized || 0}
              unrealizedPnL={pnl.unrealized || 0}
              netWorthSeries={nwSeries}
              allocation={allocation}
              bestToday={holdingsRows.slice().sort((a, b) => b.dayDelta - a.dayDelta)[0]}
              worstToday={holdingsRows.slice().sort((a, b) => a.dayDelta - b.dayDelta)[0]}
              onAllocationClick={(label) => { setSectorFilter(label); setTab('holdings'); }}
            />
          )}
          {tab === 'holdings' && (
            <HoldingsTab
              rows={holdingsRows}
              onOpenSymbol={(s) => { onClose?.(); onOpenSymbol?.(s); }}
              sectorFilter={sectorFilter}
              onClearSectorFilter={() => setSectorFilter(null)}
            />
          )}
          {tab === 'trades' && <TradesTab trades={tradesEnriched} />}
          {tab === 'performance' && (
            <PerformanceTab
              dayPnL={perfDayPnL}
              portfolioReturnSeries={portfolioPctSeries}
              benchmarkReturnSeries={benchmark}
              maxDD={maxDrawdown(nwSeries)}
              topConcentration={topConc}
              hitRatio={hr}
            />
          )}
        </div>
      </div>
    </div>
  );
}
