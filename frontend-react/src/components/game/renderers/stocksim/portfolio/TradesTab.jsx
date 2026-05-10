// TradesTab.jsx
import React, { useState, useMemo } from 'react';
import { THEME, gainLossColor } from '../theme';
import { hitRatio } from './portfolioMetrics';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;

/**
 * Trades tab of the portfolio dashboard. Renders a filterable, searchable
 * log of executed trades plus an aggregate hit-rate footer.
 *
 * Caller contract:
 *  - `trades` must be an array of trade records shaped like
 *    `{ tick: number, dayLabel?: string, symbol: string, side: 'buy'|'sell',
 *       qty: number, price: number, charges?: number, realized_pnl?: number }`.
 *    `symbol`, `price`, and `qty` are required to be a non-empty string and
 *    finite numbers respectively — `symbol.toLowerCase()` is called during
 *    search filtering, and `price` flows through `Math.round` in `fmt`.
 *    Passing `null`/`undefined` for these fields will throw or render `NaN`.
 *  - `charges` and `realized_pnl` are optional. `realized_pnl` distinguishes
 *    `null`/`undefined` (renders `'—'`) from `0` (renders `₹0`).
 *  - `dayLabel` is optional but must be a string when present; only trades
 *    with truthy `dayLabel` populate the day-filter chips.
 *
 * Filter chips: side (`all/buy/sell`) and day (`all` + dynamic per-trade
 * day labels) are independent groups. Both groups intentionally include an
 * `id="all"` chip; this produces two `data-testid="trades-filter-all"`
 * elements in the DOM. This is per-spec — tests should target the unique
 * side or day testids (e.g. `trades-filter-buy`, `trades-filter-Tue`)
 * rather than `trades-filter-all`. The `group` prop on the inner `Chip`
 * component is reserved for a future testid-namespacing refactor and is
 * intentionally unused today.
 *
 * Footer: `hitRatio([])` is safe and returns zeros, so the empty-trades
 * state renders `0 trade(s) · 0 closed · Win rate 0% · Avg win ₹0 · Avg
 * loss ₹0`.
 */
export default function TradesTab({ trades = [] }) {
  const [side, setSide] = useState('all');
  const [day, setDay] = useState('all');
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    return trades.filter((t) => {
      if (side !== 'all' && t.side !== side) return false;
      if (day !== 'all' && t.dayLabel !== day) return false;
      if (query && !t.symbol.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [trades, side, day, query]);

  const allDays = useMemo(() => Array.from(new Set(trades.map((t) => t.dayLabel).filter(Boolean))), [trades]);
  const stats = hitRatio(trades);

  const Chip = ({ id, group, label, current, setter }) => (
    <button
      data-testid={`trades-filter-${id}`}
      onClick={() => setter(id)}
      style={{
        padding: '3px 8px', borderRadius: 999, border: `1px solid ${THEME.borderTile}`,
        background: current === id ? THEME.accentWarm : '#fff',
        color: current === id ? '#fff' : THEME.textPrimary,
        cursor: 'pointer', fontSize: 11, marginRight: 4,
      }}
    >{label}</button>
  );

  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8, alignItems: 'center' }}>
        <Chip id="all"  label="All sides" current={side} setter={setSide} />
        <Chip id="buy"  label="Buy"        current={side} setter={setSide} />
        <Chip id="sell" label="Sell"       current={side} setter={setSide} />
        <span style={{ width: 8 }} />
        <Chip id="all" label="All days" current={day} setter={setDay} />
        {allDays.map((d) => (
          <Chip key={d} id={d} label={d} current={day} setter={setDay} />
        ))}
        <input
          data-testid="trades-search"
          placeholder="Symbol…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginLeft: 'auto', padding: '3px 6px', border: `1px solid ${THEME.borderTile}`, borderRadius: 6, fontSize: 11 }}
        />
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: THEME.bgTile, color: THEME.textMuted }}>
            {['Tick', 'Day', 'Symbol', 'Side', 'Qty', 'Price', 'Charges', 'Realized'].map((h) => (
              <th key={h} style={{ padding: 6, textAlign: 'left' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filtered.map((t, i) => (
            <tr key={i} data-testid={`trade-row-${i}`} style={{ borderBottom: `1px solid ${THEME.borderTile}` }}>
              <td style={{ padding: 6 }}>{t.tick}</td>
              <td style={{ padding: 6 }}>{t.dayLabel ?? ''}</td>
              <td style={{ padding: 6, fontWeight: 700 }}>{t.symbol}</td>
              <td style={{ padding: 6, color: t.side === 'buy' ? THEME.gain : THEME.loss }}>{t.side}</td>
              <td style={{ padding: 6 }}>{t.qty}</td>
              <td style={{ padding: 6 }}>{fmt(t.price)}</td>
              <td style={{ padding: 6 }}>{fmt(t.charges ?? 0)}</td>
              <td style={{ padding: 6, color: gainLossColor(t.realized_pnl ?? 0) }}>
                {t.realized_pnl != null ? fmt(t.realized_pnl) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div data-testid="trades-summary" style={{ marginTop: 10, fontSize: 12, color: THEME.textMuted }}>
        {trades.length} trade(s) · {stats.totalClosed} closed · Win rate {(stats.winRate * 100).toFixed(0)}% ·
        Avg win {fmt(stats.avgWin)} · Avg loss {fmt(stats.avgLoss)}
      </div>
    </div>
  );
}
