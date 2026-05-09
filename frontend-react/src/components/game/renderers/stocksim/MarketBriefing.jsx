import React from 'react';
import { THEME } from './theme';

const MOOD_COLOR = { positive: THEME.gain, neutral: THEME.textMuted, negative: THEME.loss };

export default function MarketBriefing({ briefing, stocks = [], onBegin }) {
  const b = briefing || {};
  return (
    <div style={{
      background: THEME.bgPage, borderRadius: 12, padding: 24, maxWidth: 640, margin: '24px auto',
      border: `1px solid ${THEME.borderTile}`,
    }}>
      <div style={{ fontSize: 11, color: THEME.textMuted, fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>
        📈 MARKET BRIEFING
      </div>
      <h2 style={{ margin: '0 0 6px', color: THEME.textPrimary, fontSize: 20 }}>{b.headline}</h2>
      <p style={{ margin: '0 0 14px', color: THEME.textMuted, fontSize: 13 }}>{b.sub}</p>

      {b.macro_tone && (
        <div style={{ background: THEME.bgTile, borderLeft: `3px solid ${THEME.accentWarm}`, padding: 10, borderRadius: 6, fontSize: 12, color: THEME.textPrimary, marginBottom: 12 }}>
          🌐 {b.macro_tone}
        </div>
      )}

      {b.sector_mood && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
          {Object.entries(b.sector_mood).map(([sec, mood]) => (
            <span key={sec} style={{
              background: THEME.bgTile, color: MOOD_COLOR[mood] || THEME.textPrimary,
              border: `1px solid ${THEME.borderTile}`, borderRadius: 14, padding: '2px 10px', fontSize: 11, fontWeight: 700,
            }}>{sec} · {mood}</span>
          ))}
        </div>
      )}

      <div style={{ fontSize: 10, color: THEME.textMuted, fontWeight: 700, marginBottom: 4 }}>STOCKS IN PLAY</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 6, marginBottom: 16 }}>
        {stocks.map(s => (
          <div key={s.symbol} style={{ background: THEME.bgTile, borderRadius: 6, padding: 6 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: THEME.textPrimary }}>{s.symbol}</div>
            <div style={{ fontSize: 9, color: THEME.textMuted }}>{s.sector}</div>
            <div style={{ fontSize: 11, color: THEME.textPrimary }}>₹{s.starting_price}</div>
          </div>
        ))}
      </div>

      <button
        onClick={onBegin}
        style={{
          background: THEME.gain, color: '#fff', border: 'none', borderRadius: 18,
          padding: '10px 20px', fontSize: 14, fontWeight: 700, cursor: 'pointer',
        }}
      >Begin Trading →</button>
    </div>
  );
}
