/**
 * SudokuRenderer — fill in the grid; backend grades vs solution.
 *
 * Game config:
 *   {
 *     game_type: "sudoku",
 *     sudoku: {
 *       puzzle: number[][],     // 9x9, 0 = empty
 *       solution: number[][]    // (used by backend; not echoed to client UI)
 *     }
 *   }
 */
import React, { useState } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

const _empty9 = () => Array.from({ length: 9 }, () => Array(9).fill(0));

export default function SudokuRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const puzzle = cfg.sudoku?.puzzle || _empty9();
  const [grid, setGrid] = useState(() => puzzle.map((row) => [...row]));
  const [hints, setHints] = useState(0);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const _set = (r, c, v) => {
    if (puzzle[r][c] !== 0) return;  // pre-filled
    const n = parseInt(v, 10);
    setGrid((g) => g.map((row, ri) =>
      row.map((cell, ci) => (ri === r && ci === c) ? (Number.isFinite(n) && n >= 1 && n <= 9 ? n : 0) : cell)
    ));
  };

  const _submit = async () => {
    if (submitting) return;
    setSubmitting(true);
    const res = await submitGrader(runId, 'sudoku', { submission: grid, hints_used: hints });
    setSubmitting(false);
    setDone(true);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), submission: grid });
  };

  return (
    <div style={{ maxWidth: 520, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>🧩 {cfg.title || 'Sudoku'}</h2>
      <div style={{ marginTop: 12, display: 'inline-grid',
                    gridTemplateColumns: 'repeat(9, 40px)', gap: 0,
                    border: '2px solid #6B7280' }}>
        {grid.map((row, r) =>
          row.map((cell, c) => {
            const preFilled = puzzle[r][c] !== 0;
            const borderRight = (c === 2 || c === 5) ? '2px solid #6B7280' : '1px solid #374151';
            const borderBottom = (r === 2 || r === 5) ? '2px solid #6B7280' : '1px solid #374151';
            return (
              <input key={`${r}-${c}`} type="text" maxLength={1}
                value={cell || ''} disabled={preFilled || done}
                onChange={(e) => _set(r, c, e.target.value)}
                style={{
                  width: 40, height: 40, textAlign: 'center', fontSize: 16,
                  background: preFilled ? '#1F2937' : '#0F172A',
                  color: preFilled ? '#9CA3AF' : '#FCD34D',
                  border: 'none', borderRight, borderBottom,
                  outline: 'none', fontWeight: preFilled ? 800 : 600,
                }} />
            );
          })
        )}
      </div>

      {!done && (
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button onClick={() => setHints(hints + 1)} style={_btn('#9CA3AF')}>
            Use hint ({hints})
          </button>
          <button onClick={_submit} style={_btn('#10B981')} disabled={submitting}>
            {submitting ? 'Grading…' : 'Submit'}
          </button>
        </div>
      )}
      {done && result && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 800 }}>🧠 Score: {result.score ?? 0}/100</div>
          {result.feedback && <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6 }}>{result.feedback}</div>}
        </div>
      )}
    </div>
  );
}
