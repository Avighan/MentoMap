// DayHeader.jsx
import React from 'react';
import { THEME } from './theme';

export default function DayHeader({ day }) {
  if (!day) return null;
  return (
    <div
      data-testid="day-header"
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: THEME.bgTile, color: THEME.textPrimary,
        padding: '4px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700,
        border: `1px solid ${THEME.borderTile}`, marginBottom: 6,
      }}
    >
      <span aria-hidden>📅</span>
      <span>{day.label}</span>
      <span style={{ color: THEME.textMuted, fontWeight: 500 }}>· Day {day.index + 1} of {day.of}</span>
    </div>
  );
}
