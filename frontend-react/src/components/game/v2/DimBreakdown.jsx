/**
 * V2 Dim Breakdown — renders under PostGameInsights to show the full
 * dimension vector with per-round deltas. Explains how final scores evolved.
 *
 * P0 Task 18: optional confidenceIntervals prop renders a 90% CI band over
 * each dimension bar so learners see the uncertainty in the point estimate.
 */
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';

const DIM_META = {
  eti: { icon: '🧠', label: 'Entrepreneurial Thinking', color: 'from-indigo-400 to-indigo-600' },
  balance_score: { icon: '⚖️', label: 'Balance', color: 'from-teal-400 to-teal-600' },
  adaptability_quotient: { icon: '🌊', label: 'Adaptability', color: 'from-sky-400 to-sky-600' },
  long_game_vision: { icon: '🔭', label: 'Long-game Vision', color: 'from-purple-400 to-purple-600' },
  ethics_fairness: { icon: '⚖️', label: 'Ethics & Fairness', color: 'from-emerald-400 to-emerald-600' },
  strategic_thinking: { icon: '♟️', label: 'Strategic Thinking', color: 'from-blue-400 to-blue-600' },
  risk_tolerance: { icon: '🎲', label: 'Risk Tolerance', color: 'from-rose-400 to-rose-600' },
  delayed_gratification: { icon: '⏳', label: 'Delayed Gratification', color: 'from-amber-400 to-amber-600' },
  resilience: { icon: '💪', label: 'Resilience', color: 'from-orange-400 to-orange-600' },
  empathy: { icon: '💗', label: 'Empathy', color: 'from-pink-400 to-pink-600' },
};

export default function DimBreakdown({
  dimensions = {},
  initialDimensions = {},
  confidenceIntervals = {},
  enabled = true,
}) {
  const { t } = useTranslation();
  if (!enabled) return null;
  const entries = Object.entries(dimensions || {})
    .filter(([, v]) => typeof v === 'number' && !Number.isNaN(v))
    .sort(([, a], [, b]) => (b || 0) - (a || 0));
  if (entries.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-sm font-semibold text-slate-900">Skill Breakdown</div>
          <div className="text-xs text-slate-500">
            How your {entries.length} soft-skill dimensions ended this run.
          </div>
        </div>
      </div>
      <div className="space-y-3">
        {entries.map(([k, v], idx) => {
          const meta = DIM_META[k] || { icon: '⭐', label: k, color: 'from-slate-400 to-slate-600' };
          const initial = initialDimensions[k];
          const delta = initial != null ? v - initial : null;
          const pct = Math.max(0, Math.min(100, v));
          return (
            <motion.div
              key={k}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{meta.icon}</span>
                  <span className="text-sm font-semibold text-slate-800">{meta.label}</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-semibold text-slate-900">{Math.round(v)}</span>
                  {delta != null && delta !== 0 && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded ${
                        delta > 0
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-rose-100 text-rose-700'
                      }`}
                    >
                      {delta > 0 ? '+' : ''}
                      {Math.round(delta)}
                    </span>
                  )}
                </div>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.6, delay: idx * 0.05 }}
                  className={`h-full bg-gradient-to-r ${meta.color}`}
                />
              </div>
              {/* P0 Task 18: 90% CI band — only when backend supplies low/high */}
              {(() => {
                const ci = confidenceIntervals?.[k];
                if (!ci || typeof ci.low !== 'number' || typeof ci.high !== 'number') {
                  return null;
                }
                const lo = Math.max(0, Math.min(100, ci.low));
                const hi = Math.max(lo, Math.min(100, ci.high));
                return (
                  <div className="mt-1">
                    <div className="relative h-1 bg-slate-200 rounded">
                      <div
                        className="absolute h-full bg-blue-300 rounded"
                        style={{ left: `${lo}%`, width: `${hi - lo}%` }}
                        aria-hidden="true"
                      />
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      {t('insights.ci_label',
                        '{{low}}–{{high}} (90% confidence)',
                        { low: Math.round(lo), high: Math.round(hi) })}
                    </div>
                  </div>
                );
              })()}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
