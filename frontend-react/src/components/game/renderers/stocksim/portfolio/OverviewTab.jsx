import React from 'react';
import Sparkline from './Sparkline';
import AllocationPie from './AllocationPie';
import { THEME, gainLossColor } from '../theme';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;
const pct = (n) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;

/**
 * Overview tab of the portfolio dashboard. Renders a snapshot of net worth,
 * today's P&L, allocation, and best/worst positions.
 *
 * Caller contract:
 *  - All numeric props (`netWorth`, `startingCash`, `todayPnL`, `cash`,
 *    `holdingsValue`, `realizedPnL`, `unrealizedPnL`) must be finite numbers
 *    when supplied; defaults to 0 if omitted.
 *  - `netWorthSeries` must be an array of finite numbers.
 *  - `allocation` must be an array of `{ label: string, value: number }` —
 *    `value` is a percentage (0–100) and is required to be numeric. The
 *    legend calls `value.toFixed(1)` directly; non-numeric values will
 *    throw. Pass `0` rather than `null`/`undefined` for unknown values.
 *  - `bestToday` / `worstToday` are optional; when omitted, position cards
 *    render a "—" sentinel.
 *  - `onAllocationClick(label)` is forwarded to `AllocationPie` as
 *    `onSliceClick` and fires when a pie slice is clicked.
 *
 * Total-return percent guards `startingCash === 0` and falls back to `0`
 * (rendered as `+0.00%`) rather than producing `Infinity` or `NaN`.
 */
export default function OverviewTab({
  netWorth = 0,
  startingCash = 0,
  todayPnL = 0,
  cash = 0,
  holdingsValue = 0,
  realizedPnL = 0,
  unrealizedPnL = 0,
  netWorthSeries = [],
  allocation = [],
  bestToday,
  worstToday,
  onAllocationClick,
}) {
  const totalReturnPct = startingCash ? ((netWorth - startingCash) / startingCash) * 100 : 0;
  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <div style={{ fontSize: 12, color: THEME.textMuted }}>Net worth</div>
          <div data-testid="overview-networth" style={{ fontSize: 28, fontWeight: 800, color: THEME.textPrimary }}>{fmt(netWorth)}</div>
          <div style={{ color: gainLossColor(todayPnL), fontWeight: 700 }}>
            {todayPnL >= 0 ? '▲' : '▼'} {fmt(Math.abs(todayPnL))} today
          </div>
        </div>
        <div data-testid="overview-total-return" style={{ color: gainLossColor(totalReturnPct), fontWeight: 700 }}>
          {pct(totalReturnPct)}
        </div>
      </div>

      <div style={{ marginTop: 8 }}>
        <Sparkline values={netWorthSeries} width={520} height={48} />
      </div>

      <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        <Stat label="Cash" value={fmt(cash)} />
        <Stat label="Holdings" value={fmt(holdingsValue)} />
        <Stat label="Today's P&L" value={fmt(todayPnL)} color={gainLossColor(todayPnL)} />
        <Stat label="Realized" value={fmt(realizedPnL)} color={gainLossColor(realizedPnL)} />
        <Stat label="Unrealized" value={fmt(unrealizedPnL)} color={gainLossColor(unrealizedPnL)} />
        <Stat label="Total return" value={pct(totalReturnPct)} color={gainLossColor(totalReturnPct)} />
      </div>

      <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '120px 1fr', gap: 12, alignItems: 'center' }}>
        <AllocationPie slices={allocation} size={120} onSliceClick={onAllocationClick} />
        <div>
          {allocation.map((s) => (
            <div key={s.label} style={{ fontSize: 12, color: THEME.textPrimary }}>
              {s.label}: {s.value.toFixed(1)}%
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <PositionCard testId="overview-best" label="Best today" position={bestToday} />
        <PositionCard testId="overview-worst" label="Worst today" position={worstToday} />
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{ background: THEME.bgTile, padding: 8, borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted }}>{label}</div>
      <div style={{ fontWeight: 700, color: color ?? THEME.textPrimary }}>{value}</div>
    </div>
  );
}

function PositionCard({ testId, label, position }) {
  if (!position) {
    return <div data-testid={testId} style={{ background: THEME.bgTile, padding: 8, borderRadius: 6, color: THEME.textMuted, fontSize: 12 }}>{label}: —</div>;
  }
  return (
    <div data-testid={testId} style={{ background: THEME.bgTile, padding: 8, borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted }}>{label}</div>
      <div style={{ fontWeight: 700 }}>{position.symbol}</div>
      <div style={{ color: gainLossColor(position.delta) }}>{fmt(position.delta)}</div>
    </div>
  );
}
