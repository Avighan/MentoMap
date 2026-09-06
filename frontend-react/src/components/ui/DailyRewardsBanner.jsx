/**
 * DailyRewardsBanner — self-contained daily-login-streak claim widget.
 * Rendered by HomePage.jsx as `{user && user.role !== 'parent' && <DailyRewardsBanner />}`
 * (no props). Backed by real routes in backend/app.py:
 *   GET  /api/daily-rewards/status -> { streak, can_claim, current_reward, calendar, next_milestone }
 *   POST /api/daily-rewards/claim  -> { success, streak, coins_awarded, ... }
 * via api/profile.js `getDailyRewardsStatus` / `claimDailyReward`.
 */
import React, { useEffect, useState } from 'react';
import { getDailyRewardsStatus, claimDailyReward } from '../../api/profile';

export default function DailyRewardsBanner() {
  const [status, setStatus] = useState(null);
  const [claiming, setClaiming] = useState(false);
  const [justClaimed, setJustClaimed] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    getDailyRewardsStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  if (!status || dismissed || (!status.can_claim && !justClaimed)) return null;

  const handleClaim = async () => {
    setClaiming(true);
    try {
      const res = await claimDailyReward();
      setJustClaimed(res);
      setStatus((s) => ({ ...s, can_claim: false, streak: res.streak ?? s.streak }));
    } catch {
      // silent — banner just stops offering the claim button
    } finally {
      setClaiming(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
        background: 'linear-gradient(135deg, #FFD166 0%, #FFB347 100%)',
        borderRadius: 16, padding: '12px 18px', margin: '0 0 16px',
        color: '#2D3047',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: '1.6rem' }}>{status.current_reward?.icon || '🎁'}</span>
        <div>
          <div style={{ fontWeight: 800, fontSize: '0.9rem' }}>
            {justClaimed ? `Claimed! +${justClaimed.coins_awarded ?? status.current_reward?.coins ?? 0} coins` : 'Daily reward ready'}
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>
            🔥 {status.streak}-day streak
            {status.next_milestone && ` · ${status.next_milestone.icon || ''} ${status.next_milestone.label || ''} at ${status.next_milestone.streak}`}
          </div>
        </div>
      </div>
      {status.can_claim ? (
        <button
          onClick={handleClaim}
          disabled={claiming}
          style={{
            padding: '8px 16px', borderRadius: 999, border: 'none', background: '#2D3047',
            color: '#fff', fontWeight: 700, fontSize: '0.85rem', cursor: claiming ? 'not-allowed' : 'pointer',
          }}
        >
          {claiming ? 'Claiming…' : `Claim +${status.current_reward?.coins ?? 0}`}
        </button>
      ) : (
        <button
          onClick={() => setDismissed(true)}
          style={{ border: 'none', background: 'transparent', color: '#2D3047', cursor: 'pointer', fontSize: '1.1rem' }}
          aria-label="Dismiss"
        >
          ✕
        </button>
      )}
    </div>
  );
}
