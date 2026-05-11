// HoldingsTab.jsx
import React, { useState, useMemo } from 'react';
import { THEME, gainLossColor } from '../theme';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;

/**
 * Holdings tab of the portfolio dashboard. Renders a sortable, filterable
 * table of open positions with click-through to a per-symbol drilldown.
 *
 * Caller contract:
 *  - `rows` must be an array of objects shaped like
 *    `{ symbol: string, sector: string, qty: number, avgCost: number,
 *       ltp: number, pnlAbs: number, pnlPct: number, dayDelta: number }`.
 *    All numeric fields must be finite numbers — `pnlPct.toFixed(2)` is
 *    called directly at render time, so passing `null`/`undefined` will
 *    throw. Pass `0` for unknown values.
 *  - `onOpenSymbol(symbol)` is optional; row clicks no-op when it is absent.
 *  - `sectorFilter` is an optional sector name; when set, only rows with
 *    matching `sector` are shown and a "× Sector: …" chip appears.
 *  - `onClearSectorFilter()` is the callback for the sector-clear chip.
 *
 * Internal sort: rows are always sorted by `pnlPct` descending. The
 * `setSortKey` setter is reserved for a future column-header sort feature
 * (TODO: wire setSortKey to column header clicks) and is intentionally
 * unused today. Do not delete it.
 *
 * Internal filter chips: `all | profit | loss` are mutually exclusive and
 * apply before `sectorFilter`.
 */
export default function HoldingsTab({ rows = [], onOpenSymbol, sectorFilter = null, onClearSectorFilter }) {
  const [filter, setFilter] = useState('all');  // all | profit | loss
  const [sortKey, setSortKey] = useState('pnlPct');

  const filtered = useMemo(() => {
    let r = rows;
    if (filter === 'profit') r = r.filter((x) => x.pnlAbs > 0);
    if (filter === 'loss') r = r.filter((x) => x.pnlAbs < 0);
    if (sectorFilter) r = r.filter((x) => x.sector === sectorFilter);
    return [...r].sort((a, b) => (b[sortKey] ?? 0) - (a[sortKey] ?? 0));
  }, [rows, filter, sortKey, sectorFilter]);

  const Chip = ({ id, label }) => (
    <button
      data-testid={`holdings-filter-${id}`}
      onClick={() => setFilter(id)}
      style={{
        padding: '4px 10px', borderRadius: 999, border: `1px solid ${THEME.borderTile}`,
        background: filter === id ? THEME.accentWarm : '#fff',
        color: filter === id ? '#fff' : THEME.textPrimary,
        cursor: 'pointer', fontSize: 12,
      }}
    >{label}</button>
  );

  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 8, alignItems: 'center' }}>
        <Chip id="all" label="All" />
        <Chip id="profit" label="Profit" />
        <Chip id="loss" label="Loss" />
        {sectorFilter && (
          <button
            onClick={onClearSectorFilter}
            data-testid="holdings-clear-sector"
            style={{ marginLeft: 'auto', fontSize: 12, color: THEME.textMuted, background: 'none', border: 'none', cursor: 'pointer' }}
          >× Sector: {sectorFilter}</button>
        )}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: THEME.bgTile, color: THEME.textMuted }}>
            {['Symbol', 'Sector', 'Qty', 'Avg', 'LTP', 'MV', 'P&L ₹', 'P&L %', 'Day Δ'].map((h) => (
              <th key={h} style={{ padding: 6, textAlign: 'left' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <tr
              key={r.symbol}
              data-testid={`holding-row-${r.symbol}`}
              onClick={() => onOpenSymbol?.(r.symbol)}
              style={{ cursor: 'pointer', borderBottom: `1px solid ${THEME.borderTile}` }}
            >
              <td style={{ padding: 6, fontWeight: 700 }}>{r.symbol}</td>
              <td style={{ padding: 6 }}>{r.sector}</td>
              <td style={{ padding: 6 }}>{r.qty}</td>
              <td style={{ padding: 6 }}>{fmt(r.avgCost)}</td>
              <td style={{ padding: 6 }}>{fmt(r.ltp)}</td>
              <td style={{ padding: 6 }}>{fmt(r.qty * r.ltp)}</td>
              <td style={{ padding: 6, color: gainLossColor(r.pnlAbs) }}>{fmt(r.pnlAbs)}</td>
              <td style={{ padding: 6, color: gainLossColor(r.pnlPct) }}>{r.pnlPct.toFixed(2)}%</td>
              <td style={{ padding: 6, color: gainLossColor(r.dayDelta) }}>{fmt(r.dayDelta)}</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan={9} style={{ padding: 16, textAlign: 'center', color: THEME.textMuted }}>No holdings match.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
