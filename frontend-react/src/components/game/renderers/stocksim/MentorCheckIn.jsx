import React from 'react';
import { useTranslation } from 'react-i18next';
import { THEME } from './theme';
import { mentorCheckIn } from './npcDialog';

const REPLIES = [
  { id: 'diversify', label: 'I should diversify', dim: { delayed_gratification: 5 } },
  { id: 'hold', label: 'Stay the course', dim: { resilience: 3 } },
  { id: 'take_profit', label: 'Take profit now', dim: { risk_tolerance: -5 } },
];

export default function MentorCheckIn({ state, onReply }) {
  const { t } = useTranslation();
  const line = mentorCheckIn(state);
  return (
    <div style={{
      background: '#FFF3DC', border: `1px solid ${THEME.borderTile}`, borderLeft: `4px solid ${THEME.accentWarm}`,
      borderRadius: 8, padding: 14, margin: '12px 0',
    }}>
      <div style={{ fontSize: 11, color: THEME.textMuted, fontWeight: 700, marginBottom: 4 }}>🧭 MENTOR CHECK-IN</div>
      <div style={{ fontSize: 13, color: THEME.textPrimary, marginBottom: 10 }}>{t(line.key, line.props)}</div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {REPLIES.map(r => (
          <button
            key={r.id}
            data-testid={`mentor-reply-${r.id}`}
            onClick={() => onReply?.(r.id, r.dim)}
            style={{
              background: '#fff', border: `1px solid ${THEME.borderTile}`, borderRadius: 14,
              padding: '6px 12px', fontSize: 11, fontWeight: 700, color: THEME.textPrimary, cursor: 'pointer',
            }}
          >{r.label}</button>
        ))}
      </div>
    </div>
  );
}
