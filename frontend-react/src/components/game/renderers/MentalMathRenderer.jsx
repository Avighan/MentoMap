/**
 * MentalMathRenderer — speed + accuracy drill.
 *
 * Game config:
 *   {
 *     game_type: "mental_math",
 *     mental_math: { problems: [{ id, prompt: "12 + 7", answer: 19 }], time_limit_s?: 60 }
 *   }
 */
import React, { useState, useEffect, useRef } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function MentalMathRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const problems = cfg.mental_math?.problems || [
    { id: '1', prompt: '12 + 7', answer: 19 },
    { id: '2', prompt: '8 × 6', answer: 48 },
    { id: '3', prompt: '45 − 19', answer: 26 },
  ];
  const timeLimit = cfg.mental_math?.time_limit_s ?? 60;
  const [idx, setIdx] = useState(0);
  const [val, setVal] = useState('');
  const [attempts, setAttempts] = useState([]);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [timeLeft, setTimeLeft] = useState(timeLimit);
  const startRef = useRef(Date.now());

  useEffect(() => {
    if (done) return;
    const t = setInterval(() => {
      const left = Math.max(0, timeLimit - Math.floor((Date.now() - startRef.current) / 1000));
      setTimeLeft(left);
      if (left <= 0) _finish(attempts);
    }, 250);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done, attempts]);

  const _finish = async (finalAttempts) => {
    if (done) return;
    setDone(true);
    setSubmitting(true);
    const elapsedS = Math.min(timeLimit, Math.floor((Date.now() - startRef.current) / 1000));
    const res = await submitGrader(runId, 'mental-math', {
      attempts: finalAttempts,
      elapsed_s: elapsedS,
    });
    setSubmitting(false);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), attempts: finalAttempts });
  };

  const _submitOne = () => {
    if (done || val === '') return;
    const next = [...attempts, { id: problems[idx].id, answer: parseFloat(val) }];
    setAttempts(next);
    setVal('');
    if (idx + 1 >= problems.length) {
      _finish(next);
    } else {
      setIdx(idx + 1);
    }
  };

  return (
    <div style={{ maxWidth: 520, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>🧮 {cfg.title || 'Mental Math'}</h2>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12,
                    color: '#9CA3AF', marginTop: 6 }}>
        <span>Q {idx + 1} / {problems.length}</span>
        <span>⏱ {timeLeft}s</span>
      </div>
      {!done && problems[idx] && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 36, fontWeight: 800, color: '#FCD34D' }}>
            {problems[idx].prompt} = ?
          </div>
          <input type="number" value={val} autoFocus
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') _submitOne(); }}
            style={{ marginTop: 16, fontSize: 24, padding: 8, width: 160, textAlign: 'center',
                     borderRadius: 8, border: '1px solid #4B5563', background: '#111827',
                     color: '#F9FAFB' }} />
          <div style={{ marginTop: 12 }}>
            <button onClick={_submitOne} style={_btn('#10B981')} disabled={val === ''}>
              Next
            </button>
          </div>
        </div>
      )}
      {done && result && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 800 }}>🎯 Score: {result.score ?? 0}/100</div>
          {result.feedback && <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6 }}>{result.feedback}</div>}
          {submitting && <div style={{ fontSize: 12, color: '#9CA3AF' }}>Grading…</div>}
        </div>
      )}
    </div>
  );
}
