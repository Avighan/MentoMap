/**
 * MockInterviewRenderer — answer interview questions; LLM (or heuristic) grades.
 *
 * Game config:
 *   {
 *     game_type: "mock_interview",
 *     mock_interview: {
 *       questions: [{ id, prompt, rubric?: { keywords?: string[] } }],
 *       persona?: string
 *     }
 *   }
 */
import React, { useState } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function MockInterviewRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const questions = cfg.mock_interview?.questions || [
    { id: 'q1', prompt: 'Tell me about yourself.' },
    { id: 'q2', prompt: 'What is your biggest strength?' },
  ];
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [val, setVal] = useState('');
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const _next = () => {
    const a = val.trim();
    if (!a) return;
    const updated = [...answers, { id: questions[idx].id, answer: a }];
    setAnswers(updated);
    setVal('');
    if (idx + 1 >= questions.length) {
      _finish(updated);
    } else {
      setIdx(idx + 1);
    }
  };

  const _finish = async (transcript) => {
    if (done) return;
    setDone(true);
    setSubmitting(true);
    const res = await submitGrader(runId, 'mock-interview', { transcript });
    setSubmitting(false);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), transcript });
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>💼 {cfg.title || 'Mock Interview'}</h2>
      {cfg.mock_interview?.persona && (
        <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>
          Interviewer: {cfg.mock_interview.persona}
        </div>
      )}
      <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 6 }}>
        Question {idx + 1} of {questions.length}
      </div>

      {!done && questions[idx] && (
        <div style={{ marginTop: 12, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 14 }}>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>
            {questions[idx].prompt}
          </div>
          <textarea value={val} onChange={(e) => setVal(e.target.value)} autoFocus
            placeholder="Your answer…"
            style={{ width: '100%', minHeight: 120, padding: 10, borderRadius: 8,
                     background: '#111827', color: '#F9FAFB', border: '1px solid #4B5563',
                     fontSize: 14 }} />
          <button onClick={_next} disabled={!val.trim()}
            style={{ ..._btn('#10B981'), marginTop: 10, opacity: val.trim() ? 1 : 0.5 }}>
            {idx + 1 >= questions.length ? 'Finish' : 'Next question'}
          </button>
        </div>
      )}

      {done && result && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 800 }}>📋 Score: {result.score ?? 0}/100</div>
          {result.feedback && (
            <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6, whiteSpace: 'pre-wrap' }}>
              {result.feedback}
            </div>
          )}
          {submitting && <div style={{ fontSize: 12, color: '#9CA3AF' }}>Grading…</div>}
        </div>
      )}
    </div>
  );
}
