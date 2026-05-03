/**
 * ScorecardWidget — final weighted scorecard for HBR-parity exec sims.
 *
 * Renders `payload.ux_executive.scorecard` (built by
 * backend/engines/scorecard_engine.build_scorecard_payload).
 *
 * Shape:
 *   {
 *     overall_score: 0-100,
 *     overall_band: "great" | "good" | "below" | "unknown",
 *     business_model_label: "SaaS — SMB",
 *     dimensions: [
 *       { name, value, score, band, weight, normalized_weight,
 *         contribution, lower_better, good_band, great_band }, ...
 *     ],
 *     warning?: string
 *   }
 *
 * Returns null when `scorecard` is null (game hasn't reached scorecard
 * trigger yet, or no scorecard config on the game).
 */
import React from 'react';

const BAND_STYLES = {
  great: {
    label: 'Great',
    chip: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/40',
    bar: 'bg-emerald-500',
  },
  good: {
    label: 'Good',
    chip: 'bg-sky-900/40 text-sky-300 border-sky-700/40',
    bar: 'bg-sky-500',
  },
  below: {
    label: 'Below band',
    chip: 'bg-amber-900/40 text-amber-300 border-amber-700/40',
    bar: 'bg-amber-500',
  },
  unknown: {
    label: 'Unknown',
    chip: 'bg-gray-700 text-gray-300 border-gray-600',
    bar: 'bg-gray-500',
  },
};

const fmtName = (n) => (n || '').replace(/_/g, ' ').replace(/\bpct\b/i, '%').replace(/\blower better\b/i, '');
const fmtValue = (v, name) => {
  if (v === null || v === undefined) return '—';
  if (typeof v !== 'number') return String(v);
  if (/pct/i.test(name)) return `${v.toFixed(1)}%`;
  return Number.isInteger(v) ? v.toString() : v.toFixed(2);
};
const fmtBand = (band) => `[${band[0]}–${band[1]}]`;

export default function ScorecardWidget({ payload, className = '' }) {
  if (!payload || typeof payload !== 'object') return null;
  if (!payload.dimensions || payload.dimensions.length === 0) return null;

  const overallBand = BAND_STYLES[payload.overall_band] || BAND_STYLES.unknown;

  return (
    <div className={`bg-gray-900/60 border border-gray-700 rounded-xl p-5 ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4 gap-4">
        <div>
          <h3 className="text-lg font-bold text-white">📊 Final Scorecard</h3>
          {payload.business_model_label && (
            <p className="text-xs text-gray-400 mt-0.5">
              Benchmarked against <span className="text-gray-300 font-medium">{payload.business_model_label}</span>
            </p>
          )}
        </div>
        <div className="text-right">
          <div className="text-3xl font-extrabold text-white">
            {Number(payload.overall_score || 0).toFixed(0)}
            <span className="text-base text-gray-400 font-normal">/100</span>
          </div>
          <span className={`inline-block mt-1 px-2 py-0.5 rounded text-xs font-mono uppercase tracking-wider border ${overallBand.chip}`}>
            {overallBand.label}
          </span>
        </div>
      </div>

      {/* Warning banner */}
      {payload.warning && (
        <div className="mb-3 px-3 py-2 rounded-lg bg-amber-900/30 border border-amber-700/40 text-xs text-amber-200">
          ⚠️ {payload.warning}
        </div>
      )}

      {/* Per-dimension rows */}
      <div className="space-y-2.5">
        {payload.dimensions.map((d) => {
          const band = BAND_STYLES[d.band] || BAND_STYLES.unknown;
          const scorePct = Math.max(0, Math.min(100, d.score || 0));
          return (
            <div
              key={d.name}
              className="bg-gray-800/60 rounded-lg p-3 border border-gray-700/60"
              data-testid={`scorecard-dim-${d.name}`}
            >
              <div className="flex items-center justify-between mb-1.5 gap-2">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-white truncate capitalize">
                    {fmtName(d.name)}
                  </div>
                  <div className="text-[11px] text-gray-400 mt-0.5">
                    Value <span className="text-gray-200 font-mono">{fmtValue(d.value, d.name)}</span>
                    {d.lower_better ? <span className="ml-1 text-gray-500">(lower = better)</span> : null}
                    {d.good_band?.length === 2 && (
                      <span className="ml-2 text-gray-500">
                        good {fmtBand(d.good_band)} · great {fmtBand(d.great_band)}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono uppercase border ${band.chip}`}>
                    {band.label}
                  </span>
                  <span className="text-sm font-bold text-white tabular-nums w-12 text-right">
                    {Number(d.score || 0).toFixed(0)}
                  </span>
                </div>
              </div>
              {/* Score bar */}
              <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${band.bar} transition-all`}
                  style={{ width: `${scorePct}%` }}
                />
              </div>
              {/* Weight + contribution caption */}
              <div className="flex justify-between mt-1 text-[10px] text-gray-500 font-mono">
                <span>weight {(d.normalized_weight * 100).toFixed(0)}%</span>
                <span>contribution {d.contribution?.toFixed?.(1) ?? '—'}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer note */}
      <p className="mt-3 text-[11px] text-gray-500 italic">
        Bands and scores are illustrative ranges synthesised from public industry reports.
        Not financial advice.
      </p>
    </div>
  );
}
