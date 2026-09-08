/**
 * SkillDashboard — compact bar-chart summary of a dimension-score dict,
 * rendered inside PostGameInsights above the more detailed DimBreakdown.
 */
import { motion } from 'framer-motion';

function labelFor(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function SkillDashboard({ dimensions = {}, title = 'Skill Profile' }) {
  const entries = Object.entries(dimensions || {}).filter(
    ([, v]) => typeof v === 'number' && !Number.isNaN(v)
  );
  if (entries.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm mb-4">
      <div className="text-sm font-semibold text-slate-900 mb-3">{title}</div>
      <div className="space-y-2.5">
        {entries.map(([key, value], idx) => {
          const pct = Math.max(0, Math.min(100, value));
          return (
            <div key={key}>
              <div className="flex justify-between text-xs mb-1 text-slate-500">
                <span>{labelFor(key)}</span>
                <span className="font-semibold text-slate-700">{Math.round(value)}</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-indigo-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.5, delay: idx * 0.04 }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
