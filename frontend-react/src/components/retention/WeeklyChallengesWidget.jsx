/**
 * WeeklyChallengesWidget — compact panel showing the user's 3 weekly challenges
 * with progress bars and a claim button when complete.
 *
 * Self-fetches from /api/weekly-challenges; gracefully renders nothing if not
 * authenticated (401).
 */
import React, { useEffect, useState } from 'react';
import { listWeeklyChallenges, claimWeeklyChallenge } from '../../api/retention';

export default function WeeklyChallengesWidget() {
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState(null);

  const _load = async () => {
    setLoading(true);
    try {
      const c = await listWeeklyChallenges();
      setChallenges(c);
    } catch {
      setChallenges([]);
    }
    setLoading(false);
  };

  useEffect(() => { _load(); }, []);

  const _claim = async (id) => {
    setClaiming(id);
    try {
      await claimWeeklyChallenge(id);
      await _load();
    } catch { /* ignore */ }
    setClaiming(null);
  };

  if (loading || !challenges.length) return null;

  return (
    <div style={{ background: '#1F2937', border: '1px solid #374151',
                  borderRadius: 12, padding: 14, marginBottom: 14 }}>
      <div style={{ fontWeight: 800, color: '#F9FAFB', marginBottom: 10,
                    display: 'flex', alignItems: 'center', gap: 6 }}>
        🏅 This week's challenges
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {challenges.map((c) => {
          const goal = c.goal || 1;
          const progress = Math.min(c.progress || 0, goal);
          const pct = (progress / goal) * 100;
          const isComplete = c.completed;
          const isClaimed = c.claimed;
          return (
            <div key={c.id} style={{
              background: '#0F172A', border: '1px solid #1E293B',
              borderRadius: 10, padding: 10,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between',
                            alignItems: 'baseline', flexWrap: 'wrap', gap: 6 }}>
                <div style={{ color: '#F9FAFB', fontWeight: 700, fontSize: 14 }}>
                  {c.title || c.kind}
                </div>
                <div style={{ fontSize: 12, color: '#9CA3AF' }}>
                  {progress} / {goal}
                </div>
              </div>
              {c.description && (
                <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>
                  {c.description}
                </div>
              )}
              <div style={{ marginTop: 8, height: 8, borderRadius: 6,
                            background: '#1E293B', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pct}%`,
                              background: isClaimed ? '#6B7280' :
                                         isComplete ? '#FCD34D' : '#10B981',
                              transition: 'width 200ms' }} />
              </div>
              {isComplete && !isClaimed && (
                <button onClick={() => _claim(c.id)} disabled={claiming === c.id}
                  style={{ marginTop: 8, padding: '6px 10px', borderRadius: 8,
                           background: '#FCD34D', color: '#052e16', border: 'none',
                           fontWeight: 700, cursor: 'pointer', fontSize: 12 }}>
                  {claiming === c.id ? 'Claiming…' : `🎁 Claim +${c.reward_xp || 0} XP`}
                </button>
              )}
              {isClaimed && (
                <div style={{ marginTop: 6, fontSize: 12, color: '#9CA3AF' }}>
                  ✓ Claimed
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
