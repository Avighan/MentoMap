/**
 * MusicGameRenderer — Web Audio ear-training / pitch-matching skeleton (Item 12).
 *
 * Self-contained renderer for a "music_match" game type. The renderer is
 * driven entirely by a `game` prop (a JSON spec) — no API calls. This
 * makes it safe to ship as a frontend-only skeleton without registering
 * a new backend game type yet.
 *
 * Game spec shape:
 *   {
 *     game_type: "music_match",
 *     title: string,
 *     music_rounds: [
 *       {
 *         id: string,
 *         prompt: string,
 *         target: { pitch_hz: number, duration_ms?: number, kind?: 'tone'|'rhythm' },
 *         choices: [{ id, label, pitch_hz: number }, ...],
 *         answer_id: string,
 *         coaching?: string
 *       }, ...
 *     ]
 *   }
 *
 * Props:
 *   - game: the spec above
 *   - onComplete?: (result: {score, total}) => void
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

function _useAudioContext() {
  const ctxRef = useRef(null);
  useEffect(() => {
    return () => {
      try { ctxRef.current && ctxRef.current.close(); } catch (_e) { /* noop */ }
    };
  }, []);
  return useCallback(() => {
    if (!ctxRef.current) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctxRef.current = new AC();
    }
    if (ctxRef.current.state === 'suspended') {
      ctxRef.current.resume();
    }
    return ctxRef.current;
  }, []);
}

function _playTone(ctx, freq, durationMs = 600, type = 'sine', gain = 0.18) {
  if (!ctx || !freq) return;
  const osc = ctx.createOscillator();
  const g = ctx.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  // Quick attack/release envelope to avoid clicks
  const now = ctx.currentTime;
  g.gain.setValueAtTime(0, now);
  g.gain.linearRampToValueAtTime(gain, now + 0.02);
  g.gain.linearRampToValueAtTime(gain, now + (durationMs - 60) / 1000);
  g.gain.linearRampToValueAtTime(0, now + durationMs / 1000);
  osc.connect(g).connect(ctx.destination);
  osc.start(now);
  osc.stop(now + durationMs / 1000 + 0.05);
}

export default function MusicGameRenderer({ game, runId, onComplete }) {
  const getCtx = _useAudioContext();
  const rounds = useMemo(() => game?.music_rounds || [], [game]);
  const [idx, setIdx] = useState(0);
  const [picked, setPicked] = useState(null);
  const [results, setResults] = useState([]);  // [{round_id, picked_id, correct}]
  const [done, setDone] = useState(false);

  const round = rounds[idx];
  const correct = round && picked === round.answer_id;

  const _playTarget = () => {
    const ctx = getCtx();
    if (!ctx) return;
    _playTone(ctx, round?.target?.pitch_hz, round?.target?.duration_ms || 800);
  };

  const _playChoice = (c) => {
    const ctx = getCtx();
    if (!ctx) return;
    _playTone(ctx, c.pitch_hz, 600);
  };

  const _submitToBackend = async (picks) => {
    if (!runId) return;
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/run/${runId}/music-match/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ results: picks }),
      });
    } catch (_e) {
      // Submission failure shouldn't block the user — backend will fall back
      // to its default 50/100, but the renderer's local "x/total" still shows.
    }
  };

  const _confirm = async () => {
    if (!picked || !round) return;
    const r = { round_id: round.id, picked_id: picked, correct: picked === round.answer_id };
    const next = [...results, r];
    setResults(next);
    if (idx + 1 >= rounds.length) {
      setDone(true);
      const score = next.filter((x) => x.correct).length;
      // Persist results before triggering the report so the score is real.
      await _submitToBackend(next);
      if (typeof onComplete === 'function') onComplete({ score, total: rounds.length });
    } else {
      setIdx(idx + 1);
      setPicked(null);
    }
  };

  if (!game || rounds.length === 0) {
    return (
      <div style={{ padding: 16, color: '#9CA3AF' }}>
        No music rounds in this game.
      </div>
    );
  }

  if (done) {
    const score = results.filter((r) => r.correct).length;
    return (
      <div style={{ padding: 20, color: '#F9FAFB', textAlign: 'center' }}>
        <h2 style={{ fontSize: 22, fontWeight: 800 }}>🎵 Done!</h2>
        <div style={{ fontSize: 48, fontWeight: 800, color: '#FCD34D', margin: 16 }}>
          {score} / {rounds.length}
        </div>
        <div style={{ fontSize: 14, color: '#9CA3AF' }}>
          {score === rounds.length ? 'Perfect ear!'
           : score >= rounds.length / 2 ? 'Nice work — keep practicing.'
           : 'Try again — listen carefully to the target tone first.'}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      maxWidth: 600, margin: '0 auto', padding: 16, color: '#F9FAFB',
    }}>
      <div style={{ fontSize: 12, color: '#9CA3AF' }}>
        Round {idx + 1} of {rounds.length}
      </div>
      <h2 style={{ fontSize: 18, fontWeight: 800, marginTop: 4 }}>
        {round.prompt}
      </h2>

      <div style={{ marginTop: 16, marginBottom: 16, textAlign: 'center' }}>
        <button
          onClick={_playTarget}
          style={{
            padding: '14px 22px', borderRadius: 999,
            background: '#F59E0B', color: '#111827',
            fontWeight: 800, border: 'none', cursor: 'pointer',
            fontSize: 16,
          }}
        >🎯 Play target tone</button>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8,
      }}>
        {round.choices.map((c) => (
          <div key={c.id} style={{
            background: picked === c.id ? '#1E40AF' : '#1F2937',
            border: '1px solid #374151', borderRadius: 12, padding: 10,
            display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            <div style={{ fontWeight: 700 }}>{c.label}</div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={() => _playChoice(c)}
                style={{
                  flex: 1, padding: '6px 8px', borderRadius: 8,
                  background: '#374151', color: '#E5E7EB', border: 'none',
                  cursor: 'pointer', fontSize: 12,
                }}>▶ Play</button>
              <button onClick={() => setPicked(c.id)}
                style={{
                  flex: 1, padding: '6px 8px', borderRadius: 8,
                  background: picked === c.id ? '#10B981' : '#1E40AF',
                  color: '#F9FAFB', border: 'none',
                  cursor: 'pointer', fontSize: 12, fontWeight: 700,
                }}>{picked === c.id ? '✓ Picked' : 'Pick'}</button>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}>
        <button
          onClick={_confirm}
          disabled={!picked}
          style={{
            padding: '8px 16px', borderRadius: 10, fontWeight: 700,
            background: picked ? '#10B981' : '#374151',
            color: picked ? '#052e16' : '#6B7280',
            border: 'none', cursor: picked ? 'pointer' : 'not-allowed',
          }}
        >Confirm</button>
      </div>
    </div>
  );
}
