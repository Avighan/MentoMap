/**
 * GameRequestForm — modal/inline form for students to request a new game.
 *
 * Props:
 *   - onClose?: () => void
 *   - asInline?: boolean  (default false → modal overlay)
 */
import React, { useState } from 'react';
import { createGameRequest } from '../../api/retention';

const _btn = (bg) => ({
  padding: '8px 14px', borderRadius: 8, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function GameRequestForm({ onClose, asInline = false }) {
  const [title, setTitle] = useState('');
  const [topic, setTopic] = useState('');
  const [hint, setHint] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState(null);
  const [done, setDone] = useState(false);

  const _submit = async () => {
    if (!title.trim() || !topic.trim() || submitting) return;
    setSubmitting(true);
    setErr(null);
    try {
      await createGameRequest({ title: title.trim(), topic: topic.trim(),
                                game_type_hint: hint || undefined });
      setDone(true);
    } catch (e) {
      setErr(e?.response?.data?.error || 'Failed to submit. Try again.');
    }
    setSubmitting(false);
  };

  const inner = (
    <div style={{ background: '#1F2937', border: '1px solid #374151',
                  borderRadius: 12, padding: 18, color: '#F9FAFB',
                  maxWidth: 480, width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontWeight: 800, fontSize: 16 }}>💡 Request a game</div>
        {onClose && <button onClick={onClose}
          style={{ background: 'transparent', color: '#9CA3AF', border: 'none',
                   cursor: 'pointer', fontSize: 18 }}>✕</button>}
      </div>

      {done ? (
        <div>
          <div style={{ fontSize: 14, color: '#34D399' }}>
            ✓ Request submitted! We'll review it soon.
          </div>
          {onClose && <button onClick={onClose} style={{ ..._btn('#10B981'), marginTop: 12 }}>
            Close
          </button>}
        </div>
      ) : (
        <>
          <p style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 10 }}>
            Tell us what kind of game you'd like. Other students can vote your idea up.
          </p>
          <label style={{ fontSize: 12, color: '#9CA3AF' }}>Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Periodic table memory game"
            style={{ width: '100%', padding: 8, marginTop: 4, marginBottom: 10,
                     borderRadius: 6, border: '1px solid #4B5563',
                     background: '#111827', color: '#F9FAFB' }} />
          <label style={{ fontSize: 12, color: '#9CA3AF' }}>Topic / subject</label>
          <input value={topic} onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Chemistry — atomic structure"
            style={{ width: '100%', padding: 8, marginTop: 4, marginBottom: 10,
                     borderRadius: 6, border: '1px solid #4B5563',
                     background: '#111827', color: '#F9FAFB' }} />
          <label style={{ fontSize: 12, color: '#9CA3AF' }}>Game type (optional)</label>
          <select value={hint} onChange={(e) => setHint(e.target.value)}
            style={{ width: '100%', padding: 8, marginTop: 4, marginBottom: 12,
                     borderRadius: 6, border: '1px solid #4B5563',
                     background: '#111827', color: '#F9FAFB' }}>
            <option value="">— No preference —</option>
            <option value="rounds">Story / scenario</option>
            <option value="minigame">Quick minigame</option>
            <option value="board">Board game</option>
            <option value="quiz">Quiz</option>
            <option value="lab">Lab / simulation</option>
          </select>
          {err && <div style={{ color: '#F87171', fontSize: 12, marginBottom: 8 }}>{err}</div>}
          <button onClick={_submit} disabled={submitting || !title.trim() || !topic.trim()}
            style={{ ..._btn('#10B981'),
                     opacity: (!title.trim() || !topic.trim()) ? 0.5 : 1 }}>
            {submitting ? 'Submitting…' : 'Submit request'}
          </button>
        </>
      )}
    </div>
  );

  if (asInline) return inner;

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  zIndex: 1000, padding: 20 }}>
      {inner}
    </div>
  );
}
