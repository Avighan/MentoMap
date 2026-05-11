// PerformanceTab.jsx
import React from 'react';
import { THEME, gainLossColor } from '../theme';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;

/**
 * Performance tab of the portfolio dashboard. Renders a day-by-day P&L bar
 * chart, portfolio-vs-benchmark return lines, and three key risk metrics.
 *
 * Caller contract:
 *  - `dayPnL` must be an array of `{ dayId: string, label: string, pnl: number }`.
 *    All `dayId` values must be unique within the array — they are used as
 *    React keys and `data-testid` suffixes. All `pnl` values must be finite
 *    numbers; missing or non-numeric `pnl` causes silent bar corruption and
 *    renders `₹NaN` in the label.
 *  - `portfolioReturnSeries` and `benchmarkReturnSeries` must be arrays of
 *    finite numbers; both empty renders nothing (ReturnLines returns null).
 *  - `maxDD` must be a finite number; defaults to 0 when omitted. Non-numeric
 *    values will throw at `maxDD.toFixed(1)`.
 *  - `topConcentration` is optional. When present, both `symbol` (string) and
 *    `pct` (number) must be defined; `pct.toFixed(0)` is called directly.
 *    Pass the whole object as `undefined`/`null` rather than partial.
 *  - `hitRatio` is optional. When present, `winRate` (number 0–1) and
 *    `totalClosed` (integer) must be defined. `winRate * 100` and
 *    `totalClosed` are interpolated directly into the rendered string.
 */
export default function PerformanceTab({
  dayPnL = [],
  portfolioReturnSeries = [],
  benchmarkReturnSeries = [],
  maxDD = 0,
  topConcentration,
  hitRatio,
}) {
  const maxAbs = Math.max(1, ...dayPnL.map((d) => Math.abs(d.pnl)));
  return (
    <div style={{ padding: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 6, color: THEME.textPrimary }}>P&L by day</div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 100, borderBottom: `1px solid ${THEME.borderTile}`, padding: '0 4px 4px' }}>
        {dayPnL.map((d) => {
          const h = (Math.abs(d.pnl) / maxAbs) * 80;
          return (
            <div key={d.dayId} data-testid={`perf-day-${d.dayId}`} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 36 }}>
              <div style={{ fontSize: 10, color: gainLossColor(d.pnl) }}>{fmt(d.pnl)}</div>
              <div style={{ width: 24, height: h, background: gainLossColor(d.pnl), borderRadius: 3, marginTop: 4 }} />
              <div style={{ fontSize: 10, color: THEME.textMuted, marginTop: 4 }}>{d.label}</div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 12, fontWeight: 700, color: THEME.textPrimary }}>Return vs benchmark</div>
      <ReturnLines portfolio={portfolioReturnSeries} benchmark={benchmarkReturnSeries} />

      <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        <Stat data-testid="perf-max-dd" label="Max drawdown" value={`${maxDD.toFixed(1)}%`} testId="perf-max-dd" />
        <Stat label="Top concentration" value={topConcentration ? `${topConcentration.symbol} (${topConcentration.pct.toFixed(0)}%)` : '—'} />
        <Stat label="Hit ratio" value={hitRatio ? `${(hitRatio.winRate * 100).toFixed(0)}% (${hitRatio.totalClosed})` : '—'} />
      </div>
    </div>
  );
}

function Stat({ label, value, testId }) {
  return (
    <div data-testid={testId} style={{ background: THEME.bgTile, padding: 8, borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted }}>{label}</div>
      <div style={{ fontWeight: 700, color: THEME.textPrimary }}>{value}</div>
    </div>
  );
}

function ReturnLines({ portfolio, benchmark }) {
  const all = [...portfolio, ...benchmark];
  if (!all.length) return null;
  const min = Math.min(...all);
  const max = Math.max(...all);
  const range = max - min || 1;
  const W = 520, H = 120;
  const toPoints = (arr) => arr.map((v, i) => `${(i * (W / Math.max(arr.length - 1, 1))).toFixed(2)},${(H - ((v - min) / range) * H).toFixed(2)}`).join(' ');
  return (
    <svg width={W} height={H} aria-label="return-lines">
      <polyline points={toPoints(benchmark)} fill="none" stroke={THEME.textMuted} strokeWidth={1.5} strokeDasharray="4 3" />
      <polyline points={toPoints(portfolio)} fill="none" stroke={THEME.accentWarm} strokeWidth={2} />
    </svg>
  );
}
