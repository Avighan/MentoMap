import React from 'react';
import { useTranslation } from 'react-i18next';
import { THEME } from '../theme';
import { journalistFlavor } from '../npcDialog';

export default function NewsTab({ news = [], symbol, currentTick = 0 }) {
  const { t } = useTranslation();
  const items = (news || []).filter(n => {
    const syms = n.symbols || n.affected_symbols || [];
    return Array.isArray(syms) && syms.includes(symbol);
  });
  if (items.length === 0) {
    return <div style={{ color: THEME.textMuted, padding: 12, fontSize: 12 }}>No news yet for {symbol}.</div>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {items.map((n, i) => {
        const flav = journalistFlavor(n);
        return (
          <div key={i} style={{ background: THEME.bgTile, borderLeft: `3px solid ${THEME.accentWarm}`, borderRadius: 6, padding: 8 }}>
            <div style={{ fontSize: 9, color: THEME.textMuted }}>Tick {n.tick}{n.tick > currentTick ? ' (upcoming)' : ''}</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: THEME.textPrimary }}>{n.headline}</div>
            {flav && (
              <div style={{ fontSize: 11, color: THEME.textMuted, marginTop: 4 }}>📰 {t(flav.key, flav.props)}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}
