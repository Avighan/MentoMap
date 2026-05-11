/**
 * LogicGridRenderer — zebra-style logic puzzle.
 *
 * Game config:
 *   {
 *     game_type: "logic_grid",
 *     logic_grid: {
 *       prompt: string,
 *       clues: string[],
 *       categories: { anchor: string[], <attr>: string[] },
 *       solution: { [attr]: { [anchor_value]: string } }   // backend uses this
 *     }
 *   }
 */
import React, { useState } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function LogicGridRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const lg = cfg.logic_grid || {};
  const categories = lg.categories || { anchor: [], };
  const anchorKey = Object.keys(categories)[0] || 'anchor';
  const anchorVals = categories[anchorKey] || [];
  const attrKeys = Object.keys(categories).filter((k) => k !== anchorKey);

  const [submission, setSubmission] = useState(() => {
    const init = {};
    attrKeys.forEach((attr) => {
      init[attr] = {};
      anchorVals.forEach((av) => { init[attr][av] = ''; });
    });
    return init;
  });
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const _set = (attr, anchorVal, v) => setSubmission((s) => ({
    ...s, [attr]: { ...s[attr], [anchorVal]: v }
  }));

  const _submit = async () => {
    if (submitting) return;
    setSubmitting(true);
    const res = await submitGrader(runId, 'logic-grid', { submission });
    setSubmitting(false);
    setDone(true);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), submission });
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>🧠 {cfg.title || 'Logic Grid'}</h2>
      {lg.prompt && (
        <p style={{ fontSize: 13, color: '#D1D5DB', marginTop: 6 }}>{lg.prompt}</p>
      )}

      {(lg.clues || []).length > 0 && (
        <div style={{ marginTop: 10, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 10, padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Clues</div>
          <ol style={{ paddingLeft: 18, fontSize: 13, color: '#D1D5DB' }}>
            {lg.clues.map((c, i) => <li key={i} style={{ marginBottom: 2 }}>{c}</li>)}
          </ol>
        </div>
      )}

      <div style={{ marginTop: 12, overflow: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ padding: 8, textAlign: 'left', borderBottom: '1px solid #374151' }}>
                {anchorKey}
              </th>
              {attrKeys.map((k) => (
                <th key={k} style={{ padding: 8, textAlign: 'left', borderBottom: '1px solid #374151' }}>
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {anchorVals.map((av) => (
              <tr key={av}>
                <td style={{ padding: 8, fontWeight: 700 }}>{av}</td>
                {attrKeys.map((attr) => (
                  <td key={attr} style={{ padding: 4 }}>
                    <select value={submission[attr]?.[av] || ''}
                      onChange={(e) => _set(attr, av, e.target.value)}
                      disabled={done}
                      style={{ padding: 6, borderRadius: 6, background: '#111827',
                               color: '#F9FAFB', border: '1px solid #4B5563' }}>
                      <option value="">—</option>
                      {(categories[attr] || []).map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!done && (
        <button onClick={_submit} style={{ ..._btn('#10B981'), marginTop: 12 }}
          disabled={submitting}>
          {submitting ? 'Grading…' : 'Submit'}
        </button>
      )}
      {done && result && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 800 }}>🧩 Score: {result.score ?? 0}/100</div>
          {result.feedback && <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6 }}>{result.feedback}</div>}
        </div>
      )}
    </div>
  );
}
