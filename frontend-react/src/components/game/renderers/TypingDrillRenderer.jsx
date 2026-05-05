/**
 * TypingDrillRenderer — char accuracy + WPM.
 *
 * Game config:
 *   {
 *     game_type: "typing_drill",
 *     typing_drill: { passages: [{ id, text }], time_limit_s?: 60 }
 *   }
 */
import React, { useState, useEffect, useRef } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function TypingDrillRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const passages = cfg.typing_drill?.passages || [
    { id: 'p1', text: 'The quick brown fox jumps over the lazy dog.' },
  ];
  const timeLimit = cfg.typing_drill?.time_limit_s ?? 60;
  const [typed, setTyped] = useState('');
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [timeLeft, setTimeLeft] = useState(timeLimit);
  const startRef = useRef(null);

  useEffect(() => {
    if (done || startRef.current === null) return;
    const t = setInterval(() => {
      const left = Math.max(0, timeLimit - Math.floor((Date.now() - startRef.current) / 1000));
      setTimeLeft(left);
      if (left <= 0) _finish();
    }, 250);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done, typed]);

  const _onChange = (v) => {
    if (done) return;
    if (startRef.current === null) startRef.current = Date.now();
    setTyped(v);
  };

  const _finish = async () => {
    if (done) return;
    setDone(true);
    setSubmitting(true);
    const elapsedS = startRef.current
      ? Math.min(timeLimit, Math.max(1, Math.floor((Date.now() - startRef.current) / 1000)))
      : timeLimit;
    const attempts = [{ id: passages[0].id, typed, elapsed_s: elapsedS }];
    const res = await submitGrader(runId, 'typing-drill', { attempts });
    setSubmitting(false);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), attempts });
  };

  const target = passages[0]?.text || '';

  // Color-code each character
  const charSpans = target.split('').map((ch, i) => {
    let color = '#9CA3AF';
    if (i < typed.length) color = typed[i] === ch ? '#34D399' : '#F87171';
    return <span key={i} style={{ color }}>{ch}</span>;
  });

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>⌨️ {cfg.title || 'Typing Drill'}</h2>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12,
                    color: '#9CA3AF', marginTop: 6 }}>
        <span>Type the passage exactly</span>
        <span>⏱ {timeLeft}s</span>
      </div>
      <div style={{ marginTop: 12, background: '#1F2937', border: '1px solid #374151',
                    borderRadius: 12, padding: 14, fontSize: 16, lineHeight: 1.6,
                    fontFamily: 'monospace' }}>
        {charSpans}
      </div>
      {!done && (
        <>
          <textarea value={typed} onChange={(e) => _onChange(e.target.value)} autoFocus
            style={{ marginTop: 10, width: '100%', minHeight: 80, padding: 10,
                     borderRadius: 8, background: '#111827', color: '#F9FAFB',
                     border: '1px solid #4B5563', fontFamily: 'monospace', fontSize: 14 }} />
          <button onClick={_finish} style={{ ..._btn('#F59E0B'), marginTop: 10 }}>
            I'm done
          </button>
        </>
      )}
      {done && result && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 800 }}>📊 Score: {result.score ?? 0}/100</div>
          {result.wpm !== undefined && (
            <div style={{ fontSize: 13, color: '#D1D5DB', marginTop: 4 }}>
              {result.wpm} WPM · {result.char_accuracy_pct ?? 0}% accuracy
            </div>
          )}
          {result.feedback && <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6 }}>{result.feedback}</div>}
          {submitting && <div style={{ fontSize: 12, color: '#9CA3AF' }}>Grading…</div>}
        </div>
      )}
    </div>
  );
}
