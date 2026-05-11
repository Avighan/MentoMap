/**
 * OrderTicket — Tier-2 trade form for the realtime stock-market simulator.
 *
 * Tabs: Market / Limit / Stop / SIP. Quantity stepper with 1/25%/50%/Max
 * shortcuts. Limit price field appears for limit & stop orders. SIP shows
 * an amount + schedule_tick field. Buy (green) and Sell (red) submit
 * buttons. Estimated charges (brokerage + STT + GST) are previewed
 * client-side; the server is authoritative.
 *
 * Props:
 *   stocks          Array<{ symbol, name, sector, starting_price, volatility }>
 *   selectedSymbol  string
 *   onSelectSymbol  (symbol: string) => void
 *   currentQuote    { mid, bid, ask, volume }
 *   cashAvailable   number
 *   holdings        { [symbol]: { qty, avg_price } }
 *   onSubmit        (payload) => void
 *   disabled        boolean
 */
import React, { useMemo, useState, useEffect } from 'react';
import { useNpc } from './NpcLayer';
import { brokerOnTrade } from './npcDialog';
import { THEME } from './theme';

const TABS = [
  { id: 'market', label: 'Market' },
  { id: 'limit', label: 'Limit' },
  { id: 'stop', label: 'Stop' },
  { id: 'sip', label: 'SIP' },
];

function estimateCharges(notional, side) {
  // Rough Indian-broker preview: 0.03% brokerage, 0.1% STT on sell, 18% GST on brokerage.
  const brokerage = notional * 0.0003;
  const stt = side === 'sell' ? notional * 0.001 : 0;
  const gst = brokerage * 0.18;
  return Math.round((brokerage + stt + gst) * 100) / 100;
}

const OrderTicket = ({
  stocks = [],
  selectedSymbol,
  onSelectSymbol,
  currentQuote,
  cashAvailable = 0,
  holdings = {},
  onSubmit,
  disabled = false,
}) => {
  const [orderType, setOrderType] = useState('market');
  const [qty, setQty] = useState(1);
  const [limitPrice, setLimitPrice] = useState('');
  const [stopPrice, setStopPrice] = useState('');
  const [sipAmount, setSipAmount] = useState(1000);
  const [scheduleTick, setScheduleTick] = useState(1);
  const [targetOn, setTargetOn] = useState(false);
  const [stopOn, setStopOn] = useState(false);
  const npc = useNpc();

  const stock = stocks.find((s) => s.symbol === selectedSymbol);
  const mid = currentQuote?.mid ?? stock?.starting_price ?? 0;
  const bid = currentQuote?.bid ?? mid;
  const ask = currentQuote?.ask ?? mid;
  const held = holdings?.[selectedSymbol]?.qty || 0;

  // Position sizer (uses existing ask local).
  const totalCost = (Number(qty) || 0) * (ask || 0);
  const riskPct = cashAvailable > 0 ? (totalCost / cashAvailable) * 100 : 0;
  const fivePctMove = totalCost * 0.05;

  // When stock changes, reset limit/stop defaults to mid.
  useEffect(() => {
    if (mid && !limitPrice) setLimitPrice(String(mid.toFixed(2)));
    if (mid && !stopPrice) setStopPrice(String(mid.toFixed(2)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSymbol]);

  const maxBuyQty = useMemo(() => {
    if (!ask || ask <= 0) return 0;
    return Math.max(0, Math.floor(cashAvailable / ask));
  }, [cashAvailable, ask]);

  const notional = useMemo(() => {
    const px =
      orderType === 'limit'
        ? parseFloat(limitPrice) || mid
        : orderType === 'stop'
        ? parseFloat(stopPrice) || mid
        : mid;
    return px * qty;
  }, [orderType, limitPrice, stopPrice, mid, qty]);

  const buyCharges = estimateCharges(notional, 'buy');
  const sellCharges = estimateCharges(notional, 'sell');

  const submit = (side) => {
    if (disabled || !selectedSymbol) return;
    if (orderType === 'limit') {
      const lp = parseFloat(limitPrice);
      if (!lp || lp <= 0) return;
    }
    if (orderType === 'stop' || orderType === 'stop_loss') {
      const sp = parseFloat(stopPrice);
      if (!sp || sp <= 0) return;
    }
    if (orderType === 'sip') {
      onSubmit?.({
        symbol: selectedSymbol,
        side,
        qty: 0,
        order_type: 'sip',
        amount: Number(sipAmount) || 0,
        schedule_tick: Number(scheduleTick) || 1,
      });
      return;
    }
    const payload = {
      symbol: selectedSymbol,
      side,
      qty: Number(qty) || 0,
      order_type: orderType,
    };
    if (orderType === 'limit') payload.limit_price = parseFloat(limitPrice) || mid;
    if (orderType === 'stop') payload.stop_price = parseFloat(stopPrice) || mid;
    if (orderType !== 'sip') {
      if (targetOn) payload.target_pct = 5;
      if (stopOn) payload.stop_pct = -3;
      const line = brokerOnTrade(payload, riskPct);
      if (line) npc.say('broker', line);
    }
    onSubmit?.(payload);
  };

  return (
    <div
      data-testid="stocksim-order-ticket"
      className="bg-gray-50 rounded-xl p-4 flex flex-col gap-3"
    >
      {/* Symbol selector */}
      <div>
        <label className="block text-[10px] uppercase tracking-wider text-gray-400 mb-1">
          Instrument
        </label>
        <select
          value={selectedSymbol || ''}
          onChange={(e) => onSelectSymbol?.(e.target.value)}
          className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-bold text-gray-800"
        >
          {stocks.map((s) => (
            <option key={s.symbol} value={s.symbol}>
              {s.symbol} — {s.name}
            </option>
          ))}
        </select>
      </div>

      {/* Order type tabs */}
      <div className="flex gap-1 bg-white rounded-lg p-1 border border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setOrderType(t.id)}
            className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-colors ${
              orderType === t.id
                ? 'bg-blue-500 text-white'
                : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Quote summary */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-white rounded-md py-1.5 border border-gray-100">
          <div className="text-[9px] uppercase text-gray-400">Bid</div>
          <div className="text-xs font-bold text-green-600">₹{bid?.toFixed?.(2) ?? '-'}</div>
        </div>
        <div className="bg-white rounded-md py-1.5 border border-gray-100">
          <div className="text-[9px] uppercase text-gray-400">Mid</div>
          <div className="text-xs font-bold text-gray-800">₹{mid?.toFixed?.(2) ?? '-'}</div>
        </div>
        <div className="bg-white rounded-md py-1.5 border border-gray-100">
          <div className="text-[9px] uppercase text-gray-400">Ask</div>
          <div className="text-xs font-bold text-red-600">₹{ask?.toFixed?.(2) ?? '-'}</div>
        </div>
      </div>

      {/* SIP fields */}
      {orderType === 'sip' && (
        <>
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-gray-400 mb-1">
              Amount (₹)
            </label>
            <input
              type="number"
              min="100"
              value={sipAmount}
              onChange={(e) => setSipAmount(parseInt(e.target.value, 10) || 0)}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-bold text-gray-800"
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-gray-400 mb-1">
              Schedule (tick)
            </label>
            <input
              type="number"
              min="1"
              value={scheduleTick}
              onChange={(e) => setScheduleTick(parseInt(e.target.value, 10) || 1)}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-bold text-gray-800"
            />
          </div>
        </>
      )}

      {/* Quantity stepper (non-SIP) */}
      {orderType !== 'sip' && (
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-gray-400 mb-1">
            Quantity
          </label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setQty((q) => Math.max(1, q - 1))}
              className="w-8 h-8 bg-gray-200 rounded-lg flex items-center justify-center text-gray-600 hover:bg-gray-300"
            >
              -
            </button>
            <input
              type="number"
              data-testid="order-qty"
              value={qty}
              min="1"
              onChange={(e) => setQty(Math.max(1, parseInt(e.target.value, 10) || 1))}
              className="flex-1 text-center px-3 py-2 bg-white text-gray-900 border border-gray-200 rounded-lg text-sm font-bold"
            />
            <button
              type="button"
              onClick={() => setQty((q) => q + 1)}
              className="w-8 h-8 bg-gray-200 rounded-lg flex items-center justify-center text-gray-600 hover:bg-gray-300"
            >
              +
            </button>
          </div>
          <div className="flex justify-between mt-1">
            <button
              type="button"
              onClick={() => setQty(1)}
              className="text-[10px] text-blue-500 hover:underline"
            >
              1
            </button>
            <button
              type="button"
              onClick={() => setQty(Math.max(1, Math.floor(maxBuyQty * 0.25)))}
              className="text-[10px] text-blue-500 hover:underline"
            >
              25%
            </button>
            <button
              type="button"
              onClick={() => setQty(Math.max(1, Math.floor(maxBuyQty * 0.5)))}
              className="text-[10px] text-blue-500 hover:underline"
            >
              50%
            </button>
            <button
              type="button"
              onClick={() => setQty(Math.max(1, maxBuyQty))}
              className="text-[10px] text-blue-500 hover:underline"
            >
              Max
            </button>
          </div>
          <div data-testid="order-sizer" style={{ fontSize: 10, color: THEME.textMuted, marginTop: 4 }}>
            @ qty={qty || 0} → ₹{totalCost.toLocaleString('en-IN')} ({riskPct.toFixed(1)}% of cash) ·
            +5% = +₹{fivePctMove.toFixed(2)} / −3% = −₹{(totalCost * 0.03).toFixed(2)}
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
            <button
              data-testid="chip-target"
              data-active={targetOn ? 'true' : 'false'}
              onClick={() => setTargetOn(v => !v)}
              style={{
                background: targetOn ? THEME.gain : THEME.bgTile,
                color: targetOn ? '#fff' : THEME.textPrimary,
                border: `1px solid ${THEME.borderTile}`, borderRadius: 12, padding: '2px 8px',
                fontSize: 10, cursor: 'pointer',
              }}
            >Target +5%</button>
            <button
              data-testid="chip-stop"
              data-active={stopOn ? 'true' : 'false'}
              onClick={() => setStopOn(v => !v)}
              style={{
                background: stopOn ? THEME.loss : THEME.bgTile,
                color: stopOn ? '#fff' : THEME.textPrimary,
                border: `1px solid ${THEME.borderTile}`, borderRadius: 12, padding: '2px 8px',
                fontSize: 10, cursor: 'pointer',
              }}
            >Stop −3%</button>
          </div>
        </div>
      )}

      {/* Limit / Stop fields */}
      {orderType === 'limit' && (
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-gray-400 mb-1">
            Limit Price (₹)
          </label>
          <input
            type="number"
            step="0.05"
            value={limitPrice}
            onChange={(e) => setLimitPrice(e.target.value)}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-bold text-gray-800"
          />
        </div>
      )}
      {orderType === 'stop' && (
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-gray-400 mb-1">
            Stop Price (₹)
          </label>
          <input
            type="number"
            step="0.05"
            value={stopPrice}
            onChange={(e) => setStopPrice(e.target.value)}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-bold text-gray-800"
          />
        </div>
      )}

      {/* Cost preview */}
      {orderType !== 'sip' && (
        <div className="text-[11px] text-gray-500 leading-snug">
          <div>
            Notional: <b>₹{notional.toFixed(0)}</b> · Held: <b>{held}</b> · Cash:{' '}
            <b>₹{Math.round(cashAvailable).toLocaleString()}</b>
          </div>
          <div className="text-gray-400">
            Est. charges — buy ₹{buyCharges.toFixed(2)} · sell ₹{sellCharges.toFixed(2)}
          </div>
        </div>
      )}

      {/* Buy / Sell */}
      <div className="flex gap-2">
        <button
          type="button"
          data-testid="stocksim-buy-btn"
          onClick={() => submit('buy')}
          disabled={disabled}
          className="flex-1 py-2.5 bg-green-500 text-white font-bold rounded-lg hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed text-sm"
        >
          Buy
        </button>
        <button
          type="button"
          data-testid="stocksim-sell-btn"
          onClick={() => submit('sell')}
          disabled={disabled || (orderType !== 'sip' && held <= 0)}
          className="flex-1 py-2.5 bg-red-500 text-white font-bold rounded-lg hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed text-sm"
        >
          Sell
        </button>
      </div>
    </div>
  );
};

export default OrderTicket;
