/**
 * GeneticsCrossRenderer — Punnett square phenotype prediction.
 *
 * Game config:
 *   {
 *     game_type: "genetics_cross",
 *     genetics_cross: {
 *       parent_a_genotype: string,   // e.g. "Aa"
 *       parent_b_genotype: string,
 *       phenotypes: [{ name: string, dominant_required?: boolean }]  // e.g. tall/short
 *     }
 *   }
 *
 * Student enters expected percentage for each phenotype.
 */
import React, { useState, useMemo } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function GeneticsCrossRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const gcfg = cfg.genetics_cross || {};
  const phenotypes = gcfg.phenotypes || [
    { name: 'Tall', dominant_required: true },
    { name: 'Short', dominant_required: false },
  ];
  const [preds, setPreds] = useState(() =>
    Object.fromEntries(phenotypes.map((p) => [p.name, ''])));
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const allFilled = useMemo(
    () => phenotypes.every((p) => preds[p.name] !== '' && !Number.isNaN(parseFloat(preds[p.name]))),
    [preds, phenotypes],
  );

  const _set = (name, v) => setPreds((o) => ({ ...o, [name]: v }));

  const _submit = async () => {
    if (!allFilled || submitting) return;
    setSubmitting(true);
    const predictions = Object.fromEntries(
      phenotypes.map((p) => [p.name, parseFloat(preds[p.name])])
    );
    const res = await submitGrader(runId, 'genetics-cross', { predictions });
    setSubmitting(false);
    setDone(true);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), predictions });
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>🧬 {cfg.title || 'Genetics Cross'}</h2>
      <p style={{ fontSize: 13, color: '#D1D5DB', marginTop: 6, marginBottom: 12 }}>
        Cross: <strong>{gcfg.parent_a_genotype || 'Aa'}</strong> × <strong>{gcfg.parent_b_genotype || 'Aa'}</strong>
      </p>
      <p style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 12 }}>
        For each phenotype, predict the expected % of offspring (0–100).
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {phenotypes.map((p) => (
          <div key={p.name} style={{ background: '#1F2937', border: '1px solid #374151',
            borderRadius: 12, padding: 12, display: 'flex', alignItems: 'center',
            justifyContent: 'space-between' }}>
            <div style={{ fontWeight: 700 }}>
              {p.name} {p.dominant_required ? '(dominant)' : '(recessive)'}
            </div>
            <div>
              <input type="number" step="1" min="0" max="100" value={preds[p.name]}
                onChange={(e) => _set(p.name, e.target.value)} disabled={done}
                style={{ width: 80, padding: 6, borderRadius: 6, border: '1px solid #4B5563',
                         background: '#111827', color: '#F9FAFB' }} />
              <span style={{ marginLeft: 4, color: '#9CA3AF' }}>%</span>
            </div>
          </div>
        ))}
      </div>
      {!done && (
        <button onClick={_submit} disabled={!allFilled || submitting}
          style={{ ..._btn('#10B981'), marginTop: 14, opacity: allFilled ? 1 : 0.5 }}>
          {submitting ? 'Grading…' : 'Submit predictions'}
        </button>
      )}
      {done && result && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 800 }}>🧪 Score: {result.score ?? 0}/100</div>
          {result.feedback && <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6 }}>{result.feedback}</div>}
        </div>
      )}
    </div>
  );
}
