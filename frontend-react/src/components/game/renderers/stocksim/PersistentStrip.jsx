import React from 'react';
import { THEME, gainLossColor } from './theme';

function formatINR(n) {
  // Indian-grouped rupee format. e.g. 100000 -> "1,00,000"
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(Math.round(n));
  const s = String(abs);
  if (s.length <= 3) return `${sign}₹${s}`;
  const last3 = s.slice(-3);
  const rest = s.slice(0, -3);
  const grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
  return `${sign}₹${grouped},${last3}`;
}

function formatPnl(n) {
  const sign = n > 0 ? '+' : n < 0 ? '-' : '';
  const fixed = Math.abs(n).toFixed(2);
  return `${sign}₹${fixed}`;
}

export default function PersistentStrip({ cash, holdingsValue, netWorth, pnl, currentTick, tickCount }) {
  const cellLabel = { fontSize: 9, color: THEME.textMuted, letterSpacing: 0.5, fontWeight: 600 };
  const cellValue = { fontSize: 14, fontWeight: 800, color: THEME.textPrimary };
  return (
    <div
      style={{
        background: '#fff',
        border: `1px solid ${THEME.borderTile}`,
        borderRadius: 10,
        padding: '8px 12px',
        display: 'flex',
        justifyContent: 'space-between',
        gap: 12,
      }}
    >
      <div>
        <div style={cellLabel}>CASH</div>
        <div style={{ ...cellValue, color: THEME.textMuted }}>{formatINR(cash)}</div>
      </div>
      <div>
        <div style={cellLabel}>HOLDINGS</div>
        <div style={cellValue}>{formatINR(holdingsValue)}</div>
      </div>
      <div>
        <div style={cellLabel}>NET WORTH</div>
        <div style={{ ...cellValue, color: THEME.gain }}>{formatINR(netWorth)}</div>
      </div>
      <div>
        <div style={cellLabel}>P&amp;L</div>
        <div data-testid="persistent-pnl" style={{ ...cellValue, color: gainLossColor(pnl) }}>{formatPnl(pnl)}</div>
      </div>
      <div>
        <div style={cellLabel}>TICK</div>
        <div style={cellValue}>{currentTick} / {tickCount}</div>
      </div>
    </div>
  );
}
