import React from 'react';
import { THEME } from '../theme';
import { rsi, ma, supportResistance, crossover } from '../technicals';

export default function TechnicalsTab({ priceHistory = [], stockCfg }) {
  const closes = priceHistory.map(p => p.mid ?? p);
  const rsiVal = rsi(closes, 14);
  const ma20 = ma(closes, 20);
  const ma50 = ma(closes, 50);
  const sr = supportResistance(closes, 10);
  const cross = crossover(
    closes.length >= 21 ? closes.slice(-3).map((_, i, a) => ma(closes.slice(0, closes.length - 2 + i), 20)) : [],
    closes.length >= 51 ? closes.slice(-3).map((_, i, a) => ma(closes.slice(0, closes.length - 2 + i), 50)) : []
  );
  const cell = { background: THEME.bgTile, borderRadius: 6, padding: 6 };
  const label = { fontSize: 9, color: THEME.textMuted, fontWeight: 600 };
  const val = { fontWeight: 700, fontSize: 12, color: THEME.textPrimary };
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
      <div style={cell}><div style={label}>RSI (14)</div><div style={val}>{rsiVal != null ? rsiVal.toFixed(0) : '—'}</div></div>
      <div style={cell}><div style={label}>MA-20 / MA-50</div><div style={val}>{ma20?.toFixed(2) ?? '—'} / {ma50?.toFixed(2) ?? '—'}</div></div>
      <div style={cell}><div style={label}>SUPPORT</div><div style={val}>{sr.support?.toFixed?.(2) ?? '—'}</div></div>
      <div style={cell}><div style={label}>RESISTANCE</div><div style={val}>{sr.resistance?.toFixed?.(2) ?? '—'}</div></div>
      <div style={{ ...cell, gridColumn: 'span 2' }}>
        <div style={label}>CROSSOVER</div><div style={val}>{cross}</div>
      </div>
    </div>
  );
}
