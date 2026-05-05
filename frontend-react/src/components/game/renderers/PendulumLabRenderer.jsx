/**
 * PendulumLabRenderer — derive g from pendulum period.
 *
 * Game config:
 *   {
 *     game_type: "pendulum_lab",
 *     title: string,
 *     pendulum_lab: {
 *       trials: [{ length_m: number, true_period_s: number }],
 *       scoring?: { tolerance_pct?: number }
 *     },
 *     coaching?: string
 *   }
 *
 * Student records measured period for each trial; backend re-derives g.
 */
import React, { useState, useMemo } from 'react';
import { submitGrader } from './_graderSubmit';

function _btn(bg) {
  return {
    padding: '8px 12px', borderRadius: 10, fontWeight: 700,
    background: bg, color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
  };
}

export default function PendulumLabRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const trials = cfg.pendulum_lab?.trials || [
    { length_m: 0.5, true_period_s: 1.42 },
    { length_m: 1.0, true_period_s: 2.01 },
  ];
  const [measurements, setMeasurements] = useState(trials.map(() => ({ measured_period_s: '' })));
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const allFilled = useMemo(
    () => measurements.every((m) => m.measured_period_s !== '' && !Number.isNaN(parseFloat(m.measured_period_s))),
    [measurements],
  );

  const _setVal = (idx, v) => setMeasurements((arr) => arr.map((m, i) => i === idx ? { measured_period_s: v } : m));

  const _submit = async () => {
    if (!allFilled || submitting) return;
    setSubmitting(true);
    const payload = measurements.map((m, i) => ({
      length_m: trials[i].length_m,
      measured_period_s: parseFloat(m.measured_period_s),
    }));
    const res = await submitGrader(runId, 'pendulum-lab', { measurements: payload });
    setSubmitting(false);
    setDone(true);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') {
      onComplete({ ...(res.summary || {}), measurements: payload });
    }
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>
        🪁 {cfg.title || 'Pendulum Lab'}
      </h2>
      <p style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 12 }}>
        Time the period (one full back-and-forth swing) for each pendulum length.
        We'll use T = 2π√(L/g) to derive g.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {trials.map((t, i) => (
          <div key={i} style={{
            background: '#1F2937', border: '1px solid #374151',
            borderRadius: 12, padding: 12, display: 'flex',
            alignItems: 'center', gap: 12, flexWrap: 'wrap',
          }}>
            <div style={{ flex: '1 1 200px' }}>
              <div style={{ fontSize: 12, color: '#9CA3AF' }}>Trial {i + 1}</div>
              <div style={{ fontWeight: 700 }}>Length: {t.length_m} m</div>
            </div>
            <div>
              <label style={{ fontSize: 12, color: '#9CA3AF', marginRight: 6 }}>Measured period (s):</label>
              <input type="number" step="0.01" value={measurements[i].measured_period_s}
                onChange={(e) => _setVal(i, e.target.value)} disabled={done}
                style={{ width: 90, padding: 6, borderRadius: 6, border: '1px solid #4B5563',
                         background: '#111827', color: '#F9FAFB' }} />
            </div>
          </div>
        ))}
      </div>

      {!done && (
        <button onClick={_submit} disabled={!allFilled || submitting}
          style={{ ..._btn('#10B981'), marginTop: 14, opacity: allFilled ? 1 : 0.5 }}>
          {submitting ? 'Grading…' : 'Submit measurements'}
        </button>
      )}

      {done && result && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 800, fontSize: 16 }}>📊 Result</div>
          <div style={{ fontSize: 14, color: '#E5E7EB', marginTop: 6 }}>
            Score: <strong>{result.score ?? 0}</strong>/100
          </div>
          {result.feedback && (
            <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6 }}>{result.feedback}</div>
          )}
        </div>
      )}

      {cfg.coaching && (
        <div style={{ marginTop: 14, background: '#0F172A', border: '1px solid #1E293B',
                      borderRadius: 10, padding: '8px 12px', fontSize: 12, color: '#93C5FD' }}>
          💡 {cfg.coaching}
        </div>
      )}
    </div>
  );
}
