import React from 'react';
import { THEME, gainLossColor } from './theme';

export default function StockCard({ stock, quote = {}, position, starred, imageUrl, onOpen, onStar }) {
  const { symbol, name, sector } = stock;
  const change = quote.last_change_pct ?? 0;
  return (
    <div
      data-testid={`card-${symbol}`}
      onClick={() => onOpen?.(symbol)}
      style={{
        background: '#fff', border: `1px solid ${THEME.borderTile}`, borderRadius: 8,
        padding: 8, cursor: 'pointer', position: 'relative',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 13, color: THEME.textPrimary }}>{symbol}</div>
          <div style={{ fontSize: 9, color: THEME.textMuted }}>{sector}</div>
        </div>
        <button
          data-testid={`star-${symbol}`}
          onClick={(e) => { e.stopPropagation(); onStar?.(symbol); }}
          aria-label={starred ? 'unstar' : 'star'}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 14, color: starred ? THEME.accentWarm : THEME.textMuted }}
        >{starred ? '★' : '☆'}</button>
      </div>

      {imageUrl && (
        <div style={{ height: 36, borderRadius: 4, marginTop: 4, background: `url(${imageUrl}) center/cover` }} />
      )}

      <div style={{ marginTop: 6, fontSize: 12, fontWeight: 700, color: gainLossColor(change) }}>
        ₹{quote.mid?.toFixed(2) ?? '—'} {change ? (change >= 0 ? '▲' : '▼') : ''}
      </div>

      {quote.last_reason && (
        <div
          data-testid={`why-chip-${symbol}`}
          style={{
            marginTop: 6, fontSize: 9, color: THEME.textMuted,
            background: THEME.bgTile, borderLeft: `2px solid ${THEME.accentWarm}`,
            padding: '2px 6px', borderRadius: 4,
          }}
        >Why? {quote.last_reason}</div>
      )}

      {position?.qty > 0 && (
        <div style={{ marginTop: 4, fontSize: 9, color: THEME.gain }}>You own {position.qty}</div>
      )}
    </div>
  );
}
