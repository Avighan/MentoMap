/**
 * GeometryConstructorRenderer — place points; backend evaluates required
 * geometric features (length_eq, length, angle).
 *
 * Game config:
 *   {
 *     game_type: "geometry_constructor",
 *     geometry_constructor: {
 *       prompt: string,
 *       required_points: string[],            // e.g. ["A", "B", "C"]
 *       features: [
 *         { type: "length_eq", points: ["A","B","B","C"] },   // |AB| ≈ |BC|
 *         { type: "length",    points: ["A","B"], value: 5 },
 *         { type: "angle",     points: ["A","B","C"], value: 90 }
 *       ]
 *     }
 *   }
 */
import React, { useState, useRef } from 'react';
import { submitGrader } from './_graderSubmit';

const _btn = (bg) => ({
  padding: '8px 12px', borderRadius: 10, fontWeight: 700, background: bg,
  color: '#052e16', border: 'none', cursor: 'pointer', fontSize: 13,
});

export default function GeometryConstructorRenderer({ gameData, game, runId, onComplete }) {
  const cfg = (gameData || game) || {};
  const gc = cfg.geometry_constructor || {};
  const requiredPoints = gc.required_points || ['A', 'B', 'C'];
  const [points, setPoints] = useState({});
  const [activePoint, setActivePoint] = useState(requiredPoints[0]);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const svgRef = useRef(null);

  const _onSvgClick = (e) => {
    if (done) return;
    const rect = svgRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setPoints((p) => ({ ...p, [activePoint]: { x, y } }));
    // advance to next missing point
    const next = requiredPoints.find((id) => !points[id] && id !== activePoint);
    if (next) setActivePoint(next);
  };

  const _submit = async () => {
    if (submitting) return;
    if (requiredPoints.some((id) => !points[id])) return;
    setSubmitting(true);
    const res = await submitGrader(runId, 'geometry-constructor', { points });
    setSubmitting(false);
    setDone(true);
    setResult(res.summary || { score: 0 });
    if (typeof onComplete === 'function') onComplete({ ...(res.summary || {}), points });
  };

  const placedAll = requiredPoints.every((id) => points[id]);

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB' }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>📐 {cfg.title || 'Geometry Constructor'}</h2>
      {gc.prompt && <p style={{ fontSize: 13, color: '#D1D5DB', marginTop: 6 }}>{gc.prompt}</p>}

      <div style={{ marginTop: 10, fontSize: 13, color: '#9CA3AF' }}>
        Click on the canvas to place point <strong style={{ color: '#FCD34D' }}>{activePoint}</strong>.
        Use the buttons below to switch which point you're placing.
      </div>

      <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {requiredPoints.map((id) => (
          <button key={id} onClick={() => setActivePoint(id)}
            style={{ ..._btn(activePoint === id ? '#FCD34D' : '#4B5563'),
                     color: activePoint === id ? '#052e16' : '#F9FAFB' }}>
            {id}{points[id] ? ' ✓' : ''}
          </button>
        ))}
      </div>

      <svg ref={svgRef} onClick={_onSvgClick}
        width="100%" height="360" viewBox="0 0 720 360"
        style={{ marginTop: 12, background: '#0F172A', border: '1px solid #374151',
                 borderRadius: 12, cursor: done ? 'default' : 'crosshair' }}>
        {Object.entries(points).map(([id, p]) => (
          <g key={id}>
            <circle cx={p.x} cy={p.y} r="6" fill="#FCD34D" />
            <text x={p.x + 10} y={p.y - 8} fill="#F9FAFB" fontWeight="800">{id}</text>
          </g>
        ))}
        {/* Light edges between consecutive placed points */}
        {(() => {
          const placed = requiredPoints.filter((id) => points[id]);
          const lines = [];
          for (let i = 0; i < placed.length - 1; i++) {
            const a = points[placed[i]];
            const b = points[placed[i + 1]];
            lines.push(<line key={`l-${i}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke="#94A3B8" strokeWidth="2" strokeDasharray="4 4" />);
          }
          return lines;
        })()}
      </svg>

      {!done && (
        <button onClick={_submit} disabled={!placedAll || submitting}
          style={{ ..._btn('#10B981'), marginTop: 12, opacity: placedAll ? 1 : 0.5 }}>
          {submitting ? 'Grading…' : 'Submit construction'}
        </button>
      )}
      {done && result && (
        <div style={{ marginTop: 14, background: '#1F2937', border: '1px solid #374151',
                      borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 800 }}>📐 Score: {result.score ?? 0}/100</div>
          {result.feedback && <div style={{ fontSize: 13, color: '#93C5FD', marginTop: 6 }}>{result.feedback}</div>}
        </div>
      )}
    </div>
  );
}
