// TradesTab.jsx
import React, { useState, useMemo } from 'react';
import { THEME, gainLossColor } from '../theme';
import { hitRatio } from './portfolioMetrics';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;

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
