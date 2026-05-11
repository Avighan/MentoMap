import React from 'react';
import { THEME } from './theme';

const MODES = [
  { id: 'all', label: 'All' },
  { id: 'gainers', label: 'Gainers' },
  { id: 'losers', label: 'Losers' },
  { id: 'mine', label: 'Mine' },
  { id: 'starred', label: '⭐' },
];

export default function StockListFilters({ mode, counts = {}, setMode }) {
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {MODES.map((m) => {
        const active = mode === m.id;
        return (
          <button
            key={m.id}
            data-testid={`filter-${m.id}`}
            data-active={active ? 'true' : 'false'}
            onClick={() => setMode(m.id)}
            style={{
              background: active ? THEME.accentWarm : THEME.bgTile,
              color: active ? '#fff' : THEME.textPrimary,
              border: `1px solid ${THEME.borderTile}`,
              borderRadius: 14,
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span>{m.label}</span>
            <span style={{ opacity: 0.8, fontSize: 10 }}>{counts[m.id] ?? 0}</span>
          </button>
        );
      })}
    </div>
  );
}
