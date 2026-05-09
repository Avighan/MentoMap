import React from 'react';
import { THEME } from '../theme';
import { ma } from '../technicals';

export default function ChartTab({ priceHistory = [], indicators = {} }) {
  const closes = priceHistory.map(p => p.mid ?? p);
  const ma20 = ma(closes, 20);
  if (closes.length === 0) {
    return <div style={{ color: THEME.textMuted, padding: 12, fontSize: 12 }}>No price data yet.</div>;
  }
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const span = Math.max(max - min, 0.01);
  const points = closes.map((c, i) => {
    const x = (i / Math.max(closes.length - 1, 1)) * 400;
    const y = 90 - ((c - min) / span) * 80;
    return `${x},${y}`;
  }).join(' ');
  return (
    <div style={{ background: THEME.bgTile, borderRadius: 8, padding: 8 }}>
      <div style={{ height: 100, position: 'relative' }}>
        <svg viewBox="0 0 400 100" preserveAspectRatio="none" style={{ width: '100%', height: '100%' }}>
          {ma20 != null && (
            <line x1="0" y1={90 - ((ma20 - min) / span) * 80} x2="400"
                  y2={90 - ((ma20 - min) / span) * 80}
                  stroke={THEME.accentWarm} strokeDasharray="3,3" strokeWidth="0.5" />
          )}
          <polyline points={points} stroke={THEME.gain} strokeWidth="2" fill="none" />
        </svg>
      </div>
      <div style={{ fontSize: 10, color: THEME.textMuted, marginTop: 4 }}>
        MA-20: {ma20 != null ? ma20.toFixed(2) : '—'} · RSI: {indicators.rsi != null ? indicators.rsi.toFixed(0) : '—'}
      </div>
    </div>
  );
}
