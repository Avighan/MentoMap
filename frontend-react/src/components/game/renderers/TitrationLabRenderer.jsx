/**
 * TitrationLabRenderer — discovery-based titration sim (Item 13).
 *
 * A skeleton renderer for a "lab_titration" game type. The student adds
 * titrant (base) drop-by-drop or in larger volumes to a flask of acid;
 * the simulator computes pH from a simple strong-acid/strong-base model
 * and shows a color indicator (universal-style). The student must stop
 * adding titrant when the indicator changes — overshoot or undershoot
 * loses points.
 *
 * Self-contained — no backend coupling. Driven by a `game` prop:
 *   {
 *     game_type: "lab_titration",
 *     title: string,
 *     titration: {
 *       analyte: { name: string, concentration_M: number, volume_mL: number },
 *       titrant: { name: string, concentration_M: number },
 *       indicator?: { name: string, transition_pH_low: number, transition_pH_high: number },
 *       scoring?: { ideal_volume_mL?: number, tolerance_mL?: number }
 *     },
 *     coaching?: string
 *   }
 *
 * Props:
 *   - game: spec above
 *   - onComplete?: (result: {score, added_mL, ideal_mL, final_pH}) => void
 */
import React, { useMemo, useState } from 'react';

// Compute pH for a strong-acid + strong-base titration.
// analyteMoles_init - addedMoles → if >0 acid excess; else base excess.
function _computePh({ caM, vaML, cbM, addedML }) {
  const va = (vaML || 0) / 1000;
  const vb = (addedML || 0) / 1000;
  const totalV = Math.max(va + vb, 1e-9);
  const acidMoles = (caM || 0) * va;
  const baseMoles = (cbM || 0) * vb;
  if (acidMoles > baseMoles) {
    const excess = (acidMoles - baseMoles) / totalV;
    return Math.max(0, -Math.log10(Math.max(excess, 1e-14)));
  }
  if (baseMoles > acidMoles) {
    const excess = (baseMoles - acidMoles) / totalV;
    const pOH = Math.max(0, -Math.log10(Math.max(excess, 1e-14)));
    return Math.min(14, 14 - pOH);
  }
  return 7;
}

// Universal-indicator-style color for a given pH (0..14)
function _phColor(pH) {
  if (pH < 3)   return '#DC2626'; // red
  if (pH < 5)   return '#F97316'; // orange
  if (pH < 6.5) return '#FACC15'; // yellow
  if (pH < 7.5) return '#84CC16'; // light green
  if (pH < 9)   return '#0EA5E9'; // blue-cyan
  if (pH < 11)  return '#3B82F6'; // blue
  return '#7C3AED';                // violet
}

const _DROP_VOLUME_ML = 0.05;

export default function TitrationLabRenderer({ game, runId, onComplete }) {
  const cfg = game?.titration || {};
  const analyte = cfg.analyte || { name: 'HCl', concentration_M: 0.1, volume_mL: 25 };
  const titrant = cfg.titrant || { name: 'NaOH', concentration_M: 0.1 };
  const ideal = cfg.scoring?.ideal_volume_mL ??
                ((analyte.concentration_M * analyte.volume_mL) / titrant.concentration_M);
  const tolerance = cfg.scoring?.tolerance_mL ?? 0.5;

  const [addedML, setAddedML] = useState(0);
  const [done, setDone] = useState(false);
  const [stopped, setStopped] = useState(false);

  const pH = useMemo(() => _computePh({
    caM: analyte.concentration_M, vaML: analyte.volume_mL,
    cbM: titrant.concentration_M, addedML,
  }), [analyte, titrant, addedML]);
  const color = _phColor(pH);

  const _addDrops = (n) => {
    if (done) return;
    setAddedML((v) => +(v + n * _DROP_VOLUME_ML).toFixed(3));
  };
  const _addBolus = (mL) => {
    if (done) return;
    setAddedML((v) => +(v + mL).toFixed(3));
  };
  const _reset = () => {
    setAddedML(0); setDone(false); setStopped(false);
  };

  const _submitToBackend = async (addedML_value) => {
    if (!runId) return;
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/run/${runId}/lab-titration/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ added_mL: addedML_value }),
      });
    } catch (_e) {
      // Submission failure shouldn't block the user; backend default applies.
    }
  };

  const _stop = async () => {
    setStopped(true);
    setDone(true);
    const diff = Math.abs(addedML - ideal);
    let score = 0;
    if (diff <= tolerance) score = 100;
    else if (diff <= tolerance * 3) score = 70;
    else if (diff <= tolerance * 6) score = 40;
    else score = 10;
    await _submitToBackend(addedML);
    if (typeof onComplete === 'function') {
      onComplete({ score, added_mL: addedML, ideal_mL: +ideal.toFixed(3), final_pH: +pH.toFixed(2) });
    }
  };

  const indicator = cfg.indicator || {
    name: 'Universal indicator', transition_pH_low: 6.5, transition_pH_high: 9,
  };
  const inTransition = pH >= indicator.transition_pH_low && pH <= indicator.transition_pH_high;

  return (
    <div style={{
      maxWidth: 720, margin: '0 auto', padding: 16, color: '#F9FAFB',
    }}>
      <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>
        🧪 {game?.title || 'Titration Lab'}
      </h2>
      <p style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 12 }}>
        Add {titrant.name} drop by drop. Watch the indicator color — stop
        as soon as it changes.
      </p>

      {/* Lab visualization */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16,
        marginBottom: 12,
      }}>
        <div style={{
          background: '#1F2937', border: '1px solid #374151',
          borderRadius: 12, padding: 12,
        }}>
          <div style={{ fontSize: 12, color: '#9CA3AF' }}>In the flask</div>
          <div style={{ fontWeight: 700, marginTop: 2 }}>
            {analyte.volume_mL} mL of {analyte.name} ({analyte.concentration_M} M)
          </div>
          <div style={{
            marginTop: 12, height: 120, borderRadius: 12,
            background: color, transition: 'background 200ms',
            display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
            color: '#111827', fontWeight: 800, paddingBottom: 8,
          }}>
            pH {pH.toFixed(2)}
          </div>
          {inTransition && (
            <div style={{
              marginTop: 8, fontSize: 12, color: '#FCD34D', fontWeight: 700,
            }}>
              ⚠ Indicator is in transition — endpoint is near.
            </div>
          )}
        </div>

        <div style={{
          background: '#1F2937', border: '1px solid #374151',
          borderRadius: 12, padding: 12,
        }}>
          <div style={{ fontSize: 12, color: '#9CA3AF' }}>From the buret</div>
          <div style={{ fontWeight: 700, marginTop: 2 }}>
            {titrant.name} ({titrant.concentration_M} M)
          </div>
          <div style={{
            marginTop: 16, fontSize: 32, fontWeight: 800, color: '#FCD34D',
          }}>
            {addedML.toFixed(2)} mL
          </div>
          <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>
            added so far
          </div>
          {!done && (
            <div style={{ marginTop: 14, display: 'flex',
                          flexDirection: 'column', gap: 6 }}>
              <button onClick={() => _addDrops(1)}
                style={_btn('#10B981')}>+1 drop</button>
              <button onClick={() => _addDrops(5)}
                style={_btn('#10B981')}>+5 drops</button>
              <button onClick={() => _addBolus(1)}
                style={_btn('#3B82F6')}>+1.0 mL</button>
              <button onClick={() => _addBolus(5)}
                style={_btn('#6366F1')}>+5.0 mL</button>
              <button onClick={_stop}
                style={_btn('#F59E0B')}>I think we're done — stop</button>
            </div>
          )}
        </div>
      </div>

      {done && (
        <div style={{
          background: '#1F2937', border: '1px solid #374151',
          borderRadius: 12, padding: 16, marginTop: 8,
        }}>
          <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 6 }}>
            🧫 Result
          </div>
          <div style={{ fontSize: 14, color: '#E5E7EB' }}>
            You added <strong>{addedML.toFixed(2)} mL</strong> of {titrant.name}.
            Equivalence point is at <strong>{ideal.toFixed(2)} mL</strong>.
            Final pH was <strong>{pH.toFixed(2)}</strong>.
          </div>
          <div style={{ marginTop: 10, fontSize: 13,
                        color: Math.abs(addedML - ideal) <= tolerance ? '#34D399' : '#F87171' }}>
            {Math.abs(addedML - ideal) <= tolerance
              ? '✓ Excellent — within tolerance.'
              : addedML > ideal
                ? `⚠ Overshot by ${(addedML - ideal).toFixed(2)} mL.`
                : `⚠ Undershot by ${(ideal - addedML).toFixed(2)} mL.`}
          </div>
          <button onClick={_reset}
            style={{ ..._btn('#10B981'), marginTop: 12 }}>Try again</button>
        </div>
      )}

      {game?.coaching && (
        <div style={{
          marginTop: 14, background: '#0F172A',
          border: '1px solid #1E293B', borderRadius: 10,
          padding: '8px 12px', fontSize: 12, color: '#93C5FD',
        }}>
          💡 {game.coaching}
        </div>
      )}
    </div>
  );
}

function _btn(bg) {
  return {
    padding: '8px 12px', borderRadius: 10, fontWeight: 700,
    background: bg, color: '#052e16', border: 'none',
    cursor: 'pointer', fontSize: 13,
  };
}
