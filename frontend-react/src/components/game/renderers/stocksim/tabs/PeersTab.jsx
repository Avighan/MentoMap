import React from 'react';
import { THEME } from '../theme';

export default function PeersTab({ peers = [], stockCfg }) {
  const f = stockCfg?.fundamentals || {};
  const meRow = {
    symbol: stockCfg?.symbol, name: stockCfg?.name,
    pe: f.pe, growth_yoy: null, roe: f.roe, market_cap_cr: f.market_cap_cr,
  };
  const rows = [meRow, ...(peers || [])];
  const cell = { padding: '6px 8px', fontSize: 11, color: THEME.textPrimary, borderBottom: `1px solid ${THEME.borderTile}` };
  const head = { ...cell, fontWeight: 700, color: THEME.textMuted, fontSize: 10 };
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', background: THEME.bgTile, borderRadius: 6, overflow: 'hidden' }}>
      <thead>
        <tr><th style={head}>NAME</th><th style={head}>P/E</th><th style={head}>GROWTH</th><th style={head}>ROE</th><th style={head}>CAP</th></tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} style={i === 0 ? { background: '#FEF3C7' } : null}>
            <td style={cell}>{r.name || r.symbol}{i === 0 ? ' (this)' : ''}</td>
            <td style={cell}>{r.pe ?? '—'}</td>
            <td style={cell}>{r.growth_yoy != null ? `${r.growth_yoy}%` : '—'}</td>
            <td style={cell}>{r.roe != null ? `${r.roe}%` : '—'}</td>
            <td style={cell}>{r.market_cap_cr != null ? `₹${(r.market_cap_cr / 100000).toFixed(1)}L Cr` : '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
