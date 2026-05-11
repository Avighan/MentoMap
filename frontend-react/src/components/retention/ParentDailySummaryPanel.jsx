/**
 * ParentDailySummaryPanel — shows today's soft-skill highlights for a child.
 *
 * Props:
 *   - childId?: string   (parent of multiple children passes the active one)
 *   - date?: string      ("YYYY-MM-DD"; defaults to backend's "today")
 */
import React, { useEffect, useState } from 'react';
import { getParentDailySummary } from '../../api/retention';

export default function ParentDailySummaryPanel({ childId, date }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getParentDailySummary({ childId, date })
      .then((s) => { if (!cancelled) setSummary(s); })
      .catch(() => { if (!cancelled) setSummary(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [childId, date]);

  if (loading) {
    return <div style={{ color: '#9CA3AF', padding: 14 }}>Loading today's summary…</div>;
  }
  if (!summary) return null;

  const skills = summary.skills_practiced || [];
  const top = summary.top_skill_today;
  const tps = summary.talking_points || [];

  return (
    <div style={{ background: '#1F2937', border: '1px solid #374151',
                  borderRadius: 12, padding: 16, color: '#F9FAFB',
                  marginBottom: 14 }}>
      <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 6 }}>
        🌟 Today's summary
      </div>
      <div style={{ fontSize: 13, color: '#D1D5DB', marginBottom: 10 }}>
        {summary.games_played > 0
          ? `${summary.games_played} game${summary.games_played === 1 ? '' : 's'} played · ${summary.minutes || 0} min`
          : 'No games played yet today.'}
      </div>

      {top && (
        <div style={{ marginTop: 4, padding: 10, background: '#0F172A',
                      border: '1px solid #1E293B', borderRadius: 10,
                      marginBottom: 10 }}>
          <div style={{ fontSize: 12, color: '#FCD34D', fontWeight: 700 }}>
            ⭐ Top skill today
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, marginTop: 2 }}>
            {top.name}
          </div>
          {top.score !== undefined && (
            <div style={{ fontSize: 12, color: '#9CA3AF' }}>Score: {top.score}</div>
          )}
        </div>
      )}

      {skills.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 4 }}>
            Skills practiced
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {skills.map((s) => (
              <span key={s.name} style={{
                padding: '4px 10px', borderRadius: 999,
                background: '#0F172A', border: '1px solid #1E293B',
                fontSize: 12,
              }}>
                {s.name} · {s.score ?? '—'}
              </span>
            ))}
          </div>
        </div>
      )}

      {tps.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 4 }}>
            💬 Try asking
          </div>
          <ul style={{ paddingLeft: 18, fontSize: 13, color: '#D1D5DB',
                       margin: 0 }}>
            {tps.slice(0, 3).map((tp, i) => (
              <li key={i} style={{ marginBottom: 4 }}>{tp}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
