import React from 'react';
import { useTranslation } from 'react-i18next';

/**
 * WorksheetRubricResult
 *
 * Displays the rubric grading result returned from the lesson-complete API
 * when grade_worksheet_freetext is called for textarea-heavy schema types
 * (reflection, pitch_builder, customer_profile, idea_scorecard).
 *
 * Props:
 *   rubric: { score, strengths, improvements, dim_signals } | null | undefined
 */
export default function WorksheetRubricResult({ rubric }) {
  const { t } = useTranslation();

  if (!rubric || typeof rubric.score !== 'number') return null;

  const score = Math.round(rubric.score);
  const strengths = Array.isArray(rubric.strengths) ? rubric.strengths : [];
  const improvements = Array.isArray(rubric.improvements) ? rubric.improvements : [];
  const dimSignals = rubric.dim_signals && typeof rubric.dim_signals === 'object'
    ? rubric.dim_signals
    : {};

  const scoreColor =
    score >= 75 ? '#16a34a' :
    score >= 50 ? '#d97706' :
    '#dc2626';

  return (
    <div
      className="rounded-2xl border p-4 mt-4 space-y-3"
      style={{ background: '#fafaf9', borderColor: '#e7e5e4' }}
    >
      {/* Score header */}
      <div className="flex items-center gap-3">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white font-black text-sm flex-shrink-0"
          style={{ background: scoreColor }}
        >
          {score}
        </div>
        <div>
          <div className="text-[11px] font-black uppercase tracking-wider text-stone-400">
            {t('worksheet.rubric_score', 'Rubric score')}
          </div>
          <div className="text-sm font-semibold text-stone-700">{score}/100</div>
        </div>
      </div>

      {/* Strengths */}
      {strengths.length > 0 && (
        <div>
          <div className="text-[11px] font-black uppercase tracking-wider mb-1.5 text-green-700">
            {t('worksheet.strengths', 'Strengths')}
          </div>
          <ul className="space-y-1">
            {strengths.slice(0, 4).map((s, i) => (
              <li key={i} className="text-sm flex gap-2 text-stone-700">
                <span className="flex-shrink-0 text-green-600">✓</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Improvements */}
      {improvements.length > 0 && (
        <div>
          <div className="text-[11px] font-black uppercase tracking-wider mb-1.5 text-amber-700">
            {t('worksheet.improvements', 'Areas to improve')}
          </div>
          <ul className="space-y-1">
            {improvements.slice(0, 4).map((s, i) => (
              <li key={i} className="text-sm flex gap-2 text-stone-700">
                <span className="flex-shrink-0 text-amber-600">→</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Dimension signals */}
      {Object.keys(dimSignals).length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {Object.entries(dimSignals).map(([dim, delta]) => {
            const pos = delta >= 0;
            return (
              <span
                key={dim}
                className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
                style={{
                  background: pos ? '#dcfce7' : '#fee2e2',
                  color: pos ? '#15803d' : '#b91c1c',
                }}
              >
                {dim} {pos ? '+' : ''}{delta}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
