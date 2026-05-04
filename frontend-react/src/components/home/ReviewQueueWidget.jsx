import React, { useEffect, useState } from 'react';
import apiClient from '../../api/client';

export default function ReviewQueueWidget() {
  const [data, setData] = useState(null);
  useEffect(() => {
    apiClient.get('/api/spaced-repetition/due').then(r => setData(r.data)).catch(() => {});
  }, []);
  // Backend returns {reviews: [...], count: N}; guard against bare array or {due: []}
  const due = Array.isArray(data)
    ? data
    : data?.reviews || data?.due || [];
  if (due.length === 0) return null;
  return (
    <div className="rounded-lg p-4 bg-blue-50 border border-blue-200">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold text-blue-900">🔄 Reviews due</div>
        <a href="/spaced-repetition" className="text-sm text-blue-700 underline">See all</a>
      </div>
      <ul className="space-y-1">
        {due.slice(0, 3).map((d, idx) => (
          <li key={d.skill || d.id || d.dimension || idx} className="text-sm text-blue-800 flex justify-between">
            <span>{d.skill || d.title || d.dimension || 'Review'}</span>
            {(d.recommended_game || d.game_id) && (
              <a href={`/play/${d.recommended_game || d.game_id}`} className="text-blue-700 underline">Practice</a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
