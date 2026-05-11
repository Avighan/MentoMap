/**
 * CircuitDebuggerRenderer — student types node voltages they computed.
 *
 * Game config:
 *   {
 *     game_type: "circuit_debugger",
 *     circuit_debugger: {
 *       circuit_description: string,
 *       nodes: [{ id: string, label: string, true_voltage_V: number }],
 *       scoring?: { tolerance_V?: number }
 *     }
 *   }
 */
import React, { useState, useMemo } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function CircuitDebuggerRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const nodes = cfg.circuit_debugger?.nodes || [
    { id: 'A', label: 'Node A', true_voltage_V: 5 },
    { id: 'B', label: 'Node B', true_voltage_V: 2.5 },
  ];
  const [vals, setVals] = useState(() => Object.fromEntries(nodes.map((n) => [n.id, ''])));
  const [done, setDone] = useState(false);
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const allFilled = useMemo(
    () => nodes.every((n) => vals[n.id] !== '' && !Number.isNaN(parseFloat(vals[n.id]))),
    [vals, nodes],
  );

  const _set = (id, v) => setVals((o) => ({ ...o, [id]: v }));

  const _submit = async () => {
    if (!allFilled || submitting) return;
    setSubmitting(true);
    const node_voltages = Object.fromEntries(
      nodes.map((n) => [n.id, parseFloat(vals[n.id])])
    );
    const res = await submitGrader(runId, 'circuit-debugger', { node_voltages });
    setSubmitting(false);
    setDone(true);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), node_voltages });
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>🔌 {cfg.title || 'Circuit Debugger'}</h2>
      {cfg.circuit_debugger?.circuit_description && (
        <p style={{ fontSize: 13, color: '#D1D5DB', marginTop: 4, marginBottom: 12,
                    background: '#111827', padding: 10, borderRadius: 8 }}>
          {cfg.circuit_debugger.circuit_description}
        </p>
      )}
      <p style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 12 }}>
        Compute the voltage at each node and enter your answers.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {nodes.map((n) => (
          <div key={n.id} style={{ background: '#1F2937', border: '1px solid #374151',
            borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 12, color: '#9CA3AF' }}>{n.label}</div>
            <input type="number" step="0.1" value={vals[n.id]} disabled={done}
              onChange={(e) => _set(n.id, e.target.value)} placeholder="V"
              style={{ width: '100%', marginTop: 6, padding: 6, borderRadius: 6,
                       border: '1px solid #4B5563', background: '#111827', color: '#F9FAFB' }} />
          </div>
        ))}
      </div>

      {!done && (
        <button onClick={_submit} disabled={!allFilled || submitting}
          style={{ ..._btn('#10B981'), marginTop: 14, opacity: allFilled ? 1 : 0.5 }}>
          {submitting ? 'Grading…' : 'Check my voltages'}
        </button>
      )}
      {done && result && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 800 }}>⚡ Score: {result.score ?? 0}/100</div>
          {result.feedback && <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6 }}>{result.feedback}</div>}
        </div>
      )}
    </div>
  );
}
