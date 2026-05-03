/**
 * DecisionPanelWidget — per-round multi-lever decision form for HBR sims.
 *
 * Renders `payload.ux_executive.decision_panel` (built by
 * backend/engines/decision_panel_engine.build_decision_panel_payload).
 *
 * Shape:
 *   {
 *     round_id: "round_1",
 *     title: "Decision Panel",
 *     locked: false,
 *     controls: [{
 *       id, type ('slider'|'dial'|'number'|'dropdown'),
 *       label, description, value, default, min, max, step, options,
 *       expert_pick, applies_to, unit,
 *       drift_label?: 'on_track'|'modest'|'wide'|'extreme',
 *       drift_pct?: number
 *     }, ...]
 *   }
 *
 * Submission flow:
 *   - Local state holds the player's current draft values
 *   - On Submit, calls onSubmit({control_id: value}) — the parent (typically
 *     GamePlayPage) forwards to /api/run/<id>/decision-panel
 *   - Once locked, fields become read-only and drift chips appear
 *
 * Returns null when payload is null (no decision_panel on the round).
 */
import React, { useEffect, useMemo, useState } from 'react';

const DRIFT_STYLE = {
  on_track: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/40',
  modest:   'bg-amber-900/40 text-amber-300 border-amber-700/40',
  wide:     'bg-orange-900/40 text-orange-300 border-orange-700/40',
  extreme:  'bg-rose-900/40 text-rose-300 border-rose-700/40',
};

const DRIFT_LABEL = {
  on_track: 'On track',
  modest:   'Modest drift',
  wide:     'Wide drift',
  extreme:  'Extreme drift',
};

function ControlRow({ ctrl, value, onChange, locked }) {
  const isNumeric = ['slider', 'dial', 'number'].includes(ctrl.type);
  const drift = ctrl.drift_label;
  return (
    <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-white">{ctrl.label || ctrl.id}</div>
          {ctrl.description && (
            <div className="text-[11px] text-gray-400 mt-0.5">{ctrl.description}</div>
          )}
        </div>
        {drift && (
          <span
            className={`text-[10px] uppercase font-mono tracking-wider border rounded px-1.5 py-0.5 ${
              DRIFT_STYLE[drift] || 'bg-gray-800 text-gray-300 border-gray-700'
            }`}
          >
            {DRIFT_LABEL[drift] || drift}
          </span>
        )}
      </div>

      {isNumeric ? (
        <>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={ctrl.min}
              max={ctrl.max}
              step={ctrl.step || 1}
              value={typeof value === 'number' ? value : (ctrl.default ?? ctrl.min ?? 0)}
              disabled={locked}
              onChange={(e) => onChange(parseFloat(e.target.value))}
              className="flex-1 accent-amber-500"
            />
            <div className="w-20 text-right text-sm font-mono tabular-nums text-white">
              {typeof value === 'number'
                ? (ctrl.unit === 'pct' ? `${(value * 100).toFixed(1)}%` : value.toFixed(2))
                : '—'}
              {ctrl.unit && ctrl.unit !== 'pct' && (
                <span className="text-[10px] text-gray-500 ml-0.5">{ctrl.unit}</span>
              )}
            </div>
          </div>
          {ctrl.expert_pick !== undefined && ctrl.expert_pick !== null && (
            <div className="text-[10px] text-cyan-400 mt-1">
              📌 Expert pick:{' '}
              {typeof ctrl.expert_pick === 'number'
                ? (ctrl.unit === 'pct' ? `${(ctrl.expert_pick * 100).toFixed(1)}%` : ctrl.expert_pick.toString())
                : String(ctrl.expert_pick)}
            </div>
          )}
        </>
      ) : ctrl.type === 'dropdown' ? (
        <>
          <select
            value={value ?? ctrl.default ?? ''}
            disabled={locked}
            onChange={(e) => onChange(e.target.value)}
            className="w-full bg-gray-800 text-white text-sm rounded px-2 py-1.5 border border-gray-700 disabled:opacity-50"
          >
            {(ctrl.options || []).map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          {ctrl.expert_pick !== undefined && ctrl.expert_pick !== null && (
            <div className="text-[10px] text-cyan-400 mt-1">
              📌 Expert pick: {String(ctrl.expert_pick)}
            </div>
          )}
        </>
      ) : (
        <div className="text-xs text-gray-400">Unsupported control type: {ctrl.type}</div>
      )}
    </div>
  );
}

export default function DecisionPanelWidget({ payload, onSubmit = null, className = '' }) {
  if (!payload || !Array.isArray(payload.controls) || payload.controls.length === 0) return null;

  // Initial draft = each control's current `value` (which is submitted-or-default)
  const initial = useMemo(() => {
    const out = {};
    for (const c of payload.controls) {
      out[c.id] = c.value;
    }
    return out;
  }, [payload]);

  const [draft, setDraft] = useState(initial);
  // Reset draft if the round changes (different round_id)
  useEffect(() => {
    setDraft(initial);
  }, [payload.round_id, initial]);

  const locked = !!payload.locked;
  const handleChange = (id, v) => setDraft((d) => ({ ...d, [id]: v }));

  const submit = () => {
    if (typeof onSubmit === 'function' && !locked) {
      onSubmit(draft);
    }
  };

  return (
    <div className={`bg-gray-900/60 border border-gray-700 rounded-xl p-5 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold text-white">🎛️ {payload.title || 'Decision Panel'}</h3>
          {payload.subtitle && (
            <div className="text-[11px] text-gray-400 mt-0.5">{payload.subtitle}</div>
          )}
        </div>
        {locked && (
          <span className="text-[10px] uppercase font-mono tracking-wider bg-gray-800 text-gray-300 border border-gray-700 rounded px-2 py-0.5">
            🔒 Submitted
          </span>
        )}
      </div>

      <div className="space-y-2">
        {payload.controls.map((ctrl) => (
          <ControlRow
            key={ctrl.id}
            ctrl={ctrl}
            value={draft[ctrl.id]}
            onChange={(v) => handleChange(ctrl.id, v)}
            locked={locked}
          />
        ))}
      </div>

      {!locked && typeof onSubmit === 'function' && (
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={submit}
            className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-sm font-bold shadow"
          >
            Commit Decisions
          </button>
        </div>
      )}
    </div>
  );
}
