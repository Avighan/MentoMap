import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getDailyChallenge, getNextRecommendations } from '../api/journey';
import { getProfile } from '../api/profile';
import DailyChallenge from '../components/home/DailyChallenge';
import WeakSpotCard from '../components/home/WeakSpotCard';
import ContinueCard from '../components/home/ContinueCard';
import StreakWidget from '../components/home/StreakWidget';
import ReviewQueueWidget from '../components/home/ReviewQueueWidget';
import MobileBottomNav from '../components/ui/MobileBottomNav';

export default function StudentHomePage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [challenge, setChallenge] = useState(null);
  const [recs, setRecs] = useState([]);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [streakRestored, setStreakRestored] = useState(false);

  const handleUseShield = async () => {
    try {
      const res = await fetch('/api/profile/streak-shield/use', {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      const data = await res.json();
      if (data.ok) {
        setStreakRestored(true);
        setProfile(p => ({ ...p, streak_days: data.streak_days, streak_shield_count: data.streak_shield_count }));
      }
    } catch (e) {}
  };

  useEffect(() => {
    Promise.all([
      getDailyChallenge(),
      getNextRecommendations(),
      getProfile().catch(() => null),
    ]).then(([ch, r, p]) => {
      setChallenge(ch);
      setRecs(r || []);
      setProfile(p);
      setLoading(false);
      // Onboarding gate disabled — users keep their saved profile and can
      // complete onboarding voluntarily from settings if desired.
    });
  }, []);

  const lastGame = profile?.game_history?.slice(-1)[0] || null;
  const activeCourse = profile?.active_course || null;
  const streak = profile?.streak_days || 0;
  const level = profile?.level || 1;
  const firstName = (user?.username || 'there').split(/[_\s]/)[0];

  return (
    <div className="min-h-screen pb-24" style={{ background: '#FFFDF7' }}>
      {/* Header */}
      <div className="px-5 pt-8 pb-2">
        <p className="text-sm" style={{ color: '#64748B' }}>Hey {firstName} 👋</p>
        <div className="flex items-center justify-between mt-1">
          <h1 className="text-2xl font-bold" style={{ color: '#2D3047' }}>Your Journey</h1>
          <div className="flex items-center gap-2">
            {streak > 0 && (
              <div className="flex items-center gap-1 px-3 py-1.5 rounded-full" style={{ background: '#FFF3CD', border: '1px solid #FFD166' }}>
                <span>🔥</span>
                <span className="font-bold text-sm" style={{ color: '#B45309' }}>{streak}</span>
              </div>
            )}
            <div className="flex items-center gap-1 px-3 py-1.5 rounded-full" style={{ background: '#FFF8E7', border: '1px solid #FFD166' }}>
              <span className="font-bold text-sm" style={{ color: '#2D3047' }}>Lv {level}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="px-5 space-y-4 mt-4">
        {/* Baseline nudge banner — disabled, baseline is opt-in only */}
        {false && profile?.baseline_skipped && !profile?.baseline_complete && (
          <div
            className="rounded-xl p-3 flex items-center gap-3 cursor-pointer"
            style={{ background: '#FFF3CD', border: '2px solid #FFD166' }}
            onClick={() => nav('/onboarding')}
          >
            <span className="text-2xl">🎯</span>
            <div className="flex-1">
              <p className="font-bold text-sm" style={{ color: '#92400E' }}>Complete your baseline assessment</p>
              <p className="text-xs" style={{ color: '#B45309' }}>Required before playing games — takes ~10 minutes</p>
            </div>
            <span className="text-sm font-bold" style={{ color: '#B45309' }}>→</span>
          </div>
        )}

        {/* Streak shield recovery banner */}
        {!streakRestored && profile?.streak_days === 0 && profile?.streak_shield_count > 0 && (
          <div className="rounded-xl p-3 flex items-center gap-3" style={{ background: '#FFF3CD', border: '2px solid #FFD166' }}>
            <span className="text-2xl">🛡️</span>
            <div className="flex-1">
              <p className="font-bold text-sm" style={{ color: '#92400E' }}>Your streak broke — but you have a Learning Shield!</p>
              <p className="text-xs" style={{ color: '#B45309' }}>{profile.streak_shield_count} shield{profile.streak_shield_count > 1 ? 's' : ''} available</p>
            </div>
            <button onClick={handleUseShield} className="text-xs font-bold px-3 py-1.5 rounded-xl" style={{ background: '#FFD166', color: '#92400E' }}>
              Use Shield
            </button>
          </div>
        )}

        {/* Streak + due reviews (Phase 5 audit follow-up) */}
        <StreakWidget />
        <ReviewQueueWidget />

        {/* Continue */}
        <ContinueCard lastGame={lastGame} activeCourse={activeCourse} loading={loading} />

        {/* Today's Challenge */}
        <DailyChallenge game={challenge} loading={loading} />

        {/* Weak spot */}
        {(loading || recs[0]) && <WeakSpotCard recommendation={recs[0]} loading={loading} />}

        {/* Additional recommendations */}
        {!loading && recs.slice(1, 3).length > 0 && (
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-wide font-semibold px-1" style={{ color: '#64748B' }}>Also for you</p>
            {recs.slice(1, 3).map(rec => (
              <div
                key={rec.game_id}
                className="flex items-center gap-3 rounded-xl p-3 cursor-pointer transition-colors"
                style={{ background: '#FFFFFF', border: '1px solid #E2E8F0' }}
                onClick={() => nav(`/play/${rec.game_id}`)}
              >
                <span className="text-lg">🎮</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: '#2D3047' }}>{rec.title}</p>
                  <p className="text-xs" style={{ color: '#64748B' }}>{rec.estimated_duration_minutes || 15} min · {rec.reason}</p>
                </div>
                <span style={{ color: '#64748B' }}>›</span>
              </div>
            ))}
          </div>
        )}

        {/* Explore more */}
        <button
          onClick={() => nav('/discover')}
          className="w-full py-3 rounded-xl text-sm font-medium transition-colors"
          style={{ border: '1px solid #E2E8F0', color: '#64748B' }}
        >
          Explore all games →
        </button>
      </div>

      <MobileBottomNav />
    </div>
  );
}
