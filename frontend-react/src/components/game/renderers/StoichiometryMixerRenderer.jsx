/**
 * StoichiometryMixerRenderer — student adds B until reaction completes.
 *
 * Game config:
 *   {
 *     game_type: "stoichiometry_mixer",
 *     stoichiometry_mixer: {
 *       reaction: string,                  // "2H2 + O2 -> 2H2O"
 *       a_moles: number,                   // moles of reactant A pre-loaded
 *       a_coef: number, b_coef: number,    // stoichiometric coefficients
 *       b_label?: string
 *     }
 *   }
 */
import React, { useState } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function StoichiometryMixerRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const sm = cfg.stoichiometry_mixer || {};
  const aMoles = sm.a_moles ?? 4;
  const aCoef = sm.a_coef ?? 2;
  const bCoef = sm.b_coef ?? 1;
  const [added, setAdded] = useState(0);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const _add = (n) => setAdded((v) => Math.max(0, +(v + n).toFixed(3)));

  const _submit = async () => {
    if (submitting || done) return;
    setSubmitting(true);
    const res = await submitGrader(runId, 'stoichiometry-mixer', { added_b_moles: added });
    setSubmitting(false);
    setDone(true);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), added_b_moles: added });
  };

  // Visual estimate: how complete the reaction is
  const idealB = (aMoles * bCoef) / aCoef;
  const pct = Math.min(100, (added / Math.max(idealB, 1e-9)) * 100);

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>⚗️ {cfg.title || 'Stoichiometry Mixer'}</h2>
      <p style={{ fontSize: 13, color: '#D1D5DB', marginTop: 4 }}>
        Reaction: <strong>{sm.reaction || `${aCoef}A + ${bCoef}B → product`}</strong>
      </p>
      <p style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 12 }}>
        You have <strong>{aMoles} mol</strong> of reactant A. Add the right amount of {sm.b_label || 'B'} for complete reaction.
      </p>

      <div style={{ background: '#1F2937', border: '1px solid #374151',
                    borderRadius: 12, padding: 16 }}>
        <div style={{ fontSize: 32, fontWeight: 800, color: '#FCD34D' }}>
          {added.toFixed(2)} mol
        </div>
        <div style={{ fontSize: 12, color: '#9CA3AF' }}>added so far</div>
        <div style={{ marginTop: 12, height: 14, borderRadius: 8, background: '#0F172A',
                      overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: '#10B981',
                        transition: 'width 200ms' }} />
        </div>
      </div>

      {!done && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
          <button onClick={() => _add(0.1)} style={_btn('#10B981')}>+0.1</button>
          <button onClick={() => _add(0.5)} style={_btn('#10B981')}>+0.5</button>
          <button onClick={() => _add(1)} style={_btn('#3B82F6')}>+1.0</button>
          <button onClick={() => _add(-0.5)} style={_btn('#9CA3AF')}>−0.5</button>
          <button onClick={_submit} style={_btn('#F59E0B')}
            disabled={submitting || added <= 0}>
            {submitting ? 'Grading…' : 'Stop & grade'}
          </button>
        </div>
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
