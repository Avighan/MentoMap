/**
 * LoadingSpinner — small inline spinner. Used as
 * `<LoadingSpinner size="small" color="currentColor" />` (HomePage.jsx).
 * Also exports a `LoadingState` full-panel variant for pages that show a
 * standalone loading screen.
 */
import React from 'react';

const SIZE_PX = { small: 16, medium: 28, large: 44 };

export default function LoadingSpinner({ size = 'medium', color = '#6C5CE7' }) {
  const px = SIZE_PX[size] || SIZE_PX.medium;
  return (
    <span
      role="status"
      aria-label="Loading"
      style={{
        display: 'inline-block',
        width: px,
        height: px,
        border: `${Math.max(2, px / 8)}px solid rgba(0,0,0,0.1)`,
        borderTopColor: color,
        borderRadius: '50%',
        animation: 'mm-spin 0.7s linear infinite',
      }}
    >
      <style>{`@keyframes mm-spin { to { transform: rotate(360deg); } }`}</style>
    </span>
  );
}

export function LoadingState({ label = 'Loading…' }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 12, padding: '3rem 1rem', color: '#6D7286',
    }}>
      <LoadingSpinner size="large" />
      <span style={{ fontSize: '0.9rem' }}>{label}</span>
    </div>
  );
}
