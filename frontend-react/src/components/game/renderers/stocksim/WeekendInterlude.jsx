// WeekendInterlude.jsx
import React, { useEffect, useState } from 'react';
import { THEME } from './theme';

const SKIP_AFTER_MS = 3000;
const AUTO_ADVANCE_MS = 10000;

export default function WeekendInterlude({ open, event, onAdvance }) {
  const [skippable, setSkippable] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSkippable(false);
    const skipTimer = setTimeout(() => setSkippable(true), SKIP_AFTER_MS);
    const advTimer = setTimeout(() => onAdvance?.(), AUTO_ADVANCE_MS);
    return () => { clearTimeout(skipTimer); clearTimeout(advTimer); };
  }, [open, event?.type, onAdvance]);

  if (!open || !event) return null;

  return (
    <div
      data-testid="weekend-backdrop"
      style={{
        position: 'fixed', inset: 0, background: 'rgba(40,30,5,0.85)',
        zIndex: 130, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div style={{ background: '#fff', borderRadius: 14, maxWidth: 560, width: '100%', padding: 24, border: `1px solid ${THEME.borderTile}` }}>
        <div style={{ fontSize: 11, color: THEME.textMuted, textTransform: 'uppercase', letterSpacing: 1 }}>
          {event.type === 'saturday_news' ? 'Saturday' : 'Sunday'}
        </div>
        <div data-testid="weekend-title" style={{ fontSize: 22, fontWeight: 800, color: THEME.textPrimary, marginBottom: 10 }}>
          {event.title}
        </div>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {(event.items || []).map((it, i) => (
            <li
              key={i}
              data-testid={`weekend-item-${i}`}
              style={{
                padding: '8px 10px', marginBottom: 6,
                background: THEME.bgTile, borderRadius: 6, color: THEME.textPrimary,
                borderLeft: `3px solid ${it.scope === 'stock' ? THEME.accentWarm : THEME.textMuted}`,
              }}
            >
              {it.scope === 'stock' && <strong>{it.symbol}: </strong>}{it.text}
            </li>
          ))}
        </ul>
        <button
          data-testid="weekend-skip"
          disabled={!skippable}
          onClick={onAdvance}
          style={{
            marginTop: 16, padding: '10px 16px', width: '100%',
            background: skippable ? THEME.accentWarm : THEME.bgTile,
            color: skippable ? '#fff' : THEME.textMuted,
            border: 'none', borderRadius: 8, fontWeight: 700,
            cursor: skippable ? 'pointer' : 'not-allowed',
          }}
        >{skippable ? 'Continue →' : 'Continue (auto in a moment)'}</button>
      </div>
    </div>
  );
}
