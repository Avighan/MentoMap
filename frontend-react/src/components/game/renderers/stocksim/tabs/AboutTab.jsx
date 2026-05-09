import React from 'react';
import { THEME } from '../theme';

export default function AboutTab({ about, imageUrl }) {
  const a = about || {};
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{
        height: 140, borderRadius: 8, background: imageUrl ? `url(${imageUrl}) center/cover` : `linear-gradient(135deg, ${THEME.accentWarm}, ${THEME.textMuted})`,
      }} />
      {a.description && (
        <div style={{ fontSize: 12, color: THEME.textPrimary }}>{a.description}</div>
      )}
      {(a.founded || a.hq) && (
        <div style={{ fontSize: 11, color: THEME.textMuted }}>
          {a.founded && <>Founded {a.founded}</>}{a.founded && a.hq && ' · '}{a.hq && <>HQ {a.hq}</>}
        </div>
      )}
      {Array.isArray(a.key_people) && a.key_people.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11, color: THEME.textPrimary }}>
          {a.key_people.map((p, i) => <li key={i}>{p.role}: {p.name}</li>)}
        </ul>
      )}
    </div>
  );
}
