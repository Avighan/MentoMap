/**
 * BoggleRenderer — find words in a fixed letter grid.
 *
 * Game config:
 *   {
 *     game_type: "boggle",
 *     boggle: {
 *       grid: [["A","B","C","D"],["E","F","G","H"],...],
 *       dictionary: string[],
 *       time_limit_s?: 120
 *     }
 *   }
 */
import React, { useState, useEffect, useRef } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function BoggleRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const grid = cfg.boggle?.grid || [
    ['A', 'B', 'C', 'D'],
    ['E', 'F', 'G', 'H'],
    ['I', 'J', 'K', 'L'],
    ['M', 'N', 'O', 'P'],
  ];
  const timeLimit = cfg.boggle?.time_limit_s ?? 120;
  const [words, setWords] = useState([]);
  const [current, setCurrent] = useState('');
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
      if (left <= 0) _finish(words);
    }, 250);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done, words]);

  const _addWord = () => {
    const w = current.trim().toUpperCase();
    if (!w || w.length < 3) return;
    if (words.includes(w)) { setCurrent(''); return; }
    setWords([...words, w]);
    setCurrent('');
  };

  const _finish = async (finalWords) => {
    if (done) return;
    setDone(true);
    setSubmitting(true);
    const res = await submitGrader(runId, 'boggle', { words: finalWords });
    setSubmitting(false);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), words: finalWords });
  };

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>🔤 {cfg.title || 'Boggle'}</h2>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12,
                    color: '#9CA3AF', marginTop: 6 }}>
        <span>Find words by adjacent letters (≥3 letters)</span>
        <span>⏱ {timeLeft}s</span>
      </div>

      <div style={{ marginTop: 12, display: 'inline-grid',
                    gridTemplateColumns: `repeat(${grid[0].length}, 56px)`, gap: 6 }}>
        {grid.flatMap((row, r) =>
          row.map((ch, c) => (
            <div key={`${r}-${c}`} style={{
              width: 56, height: 56, display: 'flex', alignItems: 'center',
              justifyContent: 'center', background: '#1F2937', border: '1px solid #374151',
              borderRadius: 8, fontSize: 24, fontWeight: 800,
            }}>
              {ch}
            </div>
          ))
        )}
      </div>

      {!done && (
        <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
          <input value={current} onChange={(e) => setCurrent(e.target.value.toUpperCase())}
            onKeyDown={(e) => { if (e.key === 'Enter') _addWord(); }}
            placeholder="Type a word…"
            style={{ flex: 1, padding: 8, borderRadius: 8, border: '1px solid #4B5563',
                     background: '#111827', color: '#F9FAFB' }} />
          <button onClick={_addWord} style={_btn('#10B981')}>Add</button>
          <button onClick={() => _finish(words)} style={_btn('#F59E0B')}>Done</button>
        </div>
      )}

      {words.length > 0 && (
        <div style={{ marginTop: 12, fontSize: 13, color: '#D1D5DB' }}>
          <strong>{words.length}</strong> words: {words.join(', ')}
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
