import React, { useEffect, useState } from 'react';
import { getStreak } from '../../api/profile';

export default function StreakWidget() {
  const [data, setData] = useState(null);
  useEffect(() => { getStreak().then(setData).catch(() => {}); }, []);
  if (!data) return null;
  const { streak_days = 0, last_active_date, games_completed = 0 } = data;
  const today = new Date().toISOString().slice(0, 10);
  const claimedToday = last_active_date === today;
  return (
    <div className="rounded-lg p-4 bg-gradient-to-r from-orange-50 to-amber-50 border border-amber-200 flex items-center justify-between">
      <div>
        <div className="text-2xl font-bold text-amber-900">🔥 {streak_days} day streak</div>
        <div className="text-xs text-amber-800">{games_completed} games completed</div>
      </div>
      {!claimedToday && (
        <a href="/games" className="px-3 py-2 rounded bg-amber-600 text-white text-sm font-medium hover:bg-amber-700">
          Play 1 game to keep your streak
        </a>
      )}
      {claimedToday && (
        <div className="text-sm text-green-700 font-medium">✅ Today claimed</div>
      )}
    </div>
  );
}
