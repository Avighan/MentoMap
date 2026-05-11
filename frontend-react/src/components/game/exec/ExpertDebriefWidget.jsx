/**
 * ExpertDebriefWidget — per-round 100-200 word commentary.
 *
 * Renders `payload.ux_executive.expert_debrief` (built by
 * backend/engines/expert_debrief_engine.build_expert_debrief_payload).
 *
 * Shape:
 *   {
 *     round_id: "round_1",
 *     title: "Why we'd lean into the premium tilt",
 *     body: "Holding margin while ...",
 *     expert_voice: "Prof. Aaker (paraphrased)",
 *     tags: ["pricing", "competitive_strategy"],
 *     citations: [{label, url?}],
 *     locked: false  // gated until decision_panel is committed
 *   }
 *
 * Returns null when payload is null (no debrief on the round, or still
 * gated behind an uncommitted decision_panel).
 */
import React from 'react';

export default function ExpertDebriefWidget({ payload, className = '' }) {
  if (!payload || typeof payload !== 'object') return null;
  if (payload.locked) {
    return (
      <div
        className={`bg-gray-900/60 border border-gray-700 rounded-xl p-5 text-center ${className}`}
      >
        <div className="text-2xl mb-1">🔒</div>
        <div className="text-sm font-bold text-white">Expert Debrief locked</div>
        <div className="text-[11px] text-gray-400 mt-1">
          Commit your decisions to unlock the framework view.
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-900/60 border border-amber-700/40 rounded-xl p-5 ${className}`}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-white">🎓 {payload.title || 'Expert Debrief'}</h3>
          {payload.expert_voice && (
            <div className="text-[11px] text-amber-300 mt-0.5 italic">
              {payload.expert_voice}
            </div>
          )}
        </div>
        {Array.isArray(payload.tags) && payload.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 justify-end">
            {payload.tags.map((t) => (
              <span
                key={t}
                className="text-[10px] uppercase tracking-wider font-mono bg-amber-900/30 text-amber-300 border border-amber-700/40 rounded px-1.5 py-0.5"
              >
                {t.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </div>

      {payload.body && (
        <div className="text-sm text-gray-200 leading-relaxed mt-3 whitespace-pre-wrap">
          {payload.body}
        </div>
      )}

      {Array.isArray(payload.citations) && payload.citations.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">References</div>
          <ul className="space-y-1">
            {payload.citations.map((c, i) => (
              <li key={i} className="text-[11px] text-gray-400">
                {c.url ? (
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-cyan-400 hover:underline"
                  >
                    {c.label || c.url}
                  </a>
                ) : (
                  <span>📚 {c.label || ''}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
