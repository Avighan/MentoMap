/**
 * OpticsLabRenderer — derive focal length from object/image distances.
 *
 * Game config:
 *   {
 *     game_type: "optics_lab",
 *     optics_lab: {
 *       trials: [{ object_distance_cm: number, true_image_distance_cm: number, true_focal_length_cm: number }]
 *     }
 *   }
 *
 * Student records the measured image distance for each trial.
 */
import React, { useState, useMemo } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function OpticsLabRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const trials = cfg.optics_lab?.trials || [
    { object_distance_cm: 30, true_image_distance_cm: 15, true_focal_length_cm: 10 },
    { object_distance_cm: 20, true_image_distance_cm: 20, true_focal_length_cm: 10 },
  ];
  const [vals, setVals] = useState(trials.map(() => ''));
  const [done, setDone] = useState(false);
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const allFilled = useMemo(() => vals.every((v) => v !== '' && !Number.isNaN(parseFloat(v))), [vals]);
  const _set = (i, v) => setVals((arr) => arr.map((x, idx) => idx === i ? v : x));

  const _submit = async () => {
    if (!allFilled || submitting) return;
    setSubmitting(true);
    const payload = trials.map((t, i) => ({
      object_distance_cm: t.object_distance_cm,
      measured_image_distance_cm: parseFloat(vals[i]),
    }));
    const res = await submitGrader(runId, 'optics-lab', { measurements: payload });
    setSubmitting(false);
    setDone(true);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), measurements: payload });
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>🔍 {cfg.title || 'Optics Lab'}</h2>
      <p style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 12 }}>
        Measure where the image forms for each object distance. Backend uses 1/f = 1/d₀ + 1/dᵢ.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {trials.map((t, i) => (
          <div key={i} style={{ background: '#1F2937', border: '1px solid #374151',
            borderRadius: 12, padding: 12, display: 'flex', alignItems: 'center',
            gap: 12, flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 200px' }}>
              <div style={{ fontSize: 12, color: '#9CA3AF' }}>Trial {i + 1}</div>
              <div style={{ fontWeight: 700 }}>Object distance: {t.object_distance_cm} cm</div>
            </div>
            <div>
              <label style={{ fontSize: 12, color: '#9CA3AF', marginRight: 6 }}>Image distance (cm):</label>
              <input type="number" step="0.1" value={vals[i]} disabled={done}
                onChange={(e) => _set(i, e.target.value)}
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
          <div style={{ fontWeight: 800 }}>📊 Score: {result.score ?? 0}/100</div>
          {result.feedback && <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6 }}>{result.feedback}</div>}
        </div>
      )}
    </div>
  );
}
