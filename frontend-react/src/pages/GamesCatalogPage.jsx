/**
 * GamesCatalogPage — browse-all-games grid. HomePage.jsx already navigates
 * here via `navigate('/games')` ("Browse Games" links) but doesn't itself
 * render a catalog for every role, so this fills that route.
 *
 * Real backend route: GET /api/games -> { meta, games: [...] } (backend/app.py
 * `games_list`), via api/games.js `listGames()`.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listGames } from '../api/games';
import { LoadingState } from '../components/ui/LoadingSpinner';

export default function GamesCatalogPage() {
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    listGames()
      .then((res) => setGames(res.games || []))
      .catch(() => setError('Could not load games right now.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState label="Loading games…" />;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ fontSize: '1.6rem', color: '#2D3047', marginBottom: 4 }}>Browse Games</h1>
      <p style={{ color: '#6D7286', marginBottom: 20 }}>{games.length} games available</p>
      {error && <div style={{ color: '#EF4444', marginBottom: 16 }}>{error}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16 }}>
        {games.map((g) => (
          <button
            key={g.game_id}
            onClick={() => !g.locked && navigate(`/play/${g.game_id}`)}
            disabled={!!g.locked}
            style={{
              textAlign: 'left',
              border: '1px solid #E5E7EB',
              borderRadius: 16,
              padding: 16,
              background: '#fff',
              cursor: g.locked ? 'not-allowed' : 'pointer',
              opacity: g.locked ? 0.55 : 1,
            }}
          >
            <div style={{ fontSize: '1.8rem', marginBottom: 8 }}>{g.icon || '🎮'}</div>
            <div style={{ fontWeight: 700, color: '#2D3047', marginBottom: 4 }}>{g.title}</div>
            <div style={{ fontSize: '0.8rem', color: '#6D7286', minHeight: 32 }}>
              {(g.description || '').slice(0, 90)}
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 10, fontSize: '0.72rem', color: '#9CA3AF' }}>
              {g.duration_minutes ? <span>⏱ {g.duration_minutes} min</span> : null}
              {g.difficulty ? <span>· {g.difficulty}</span> : null}
              {g.locked ? <span>· 🔒 {g.unlock_hint || 'Locked'}</span> : null}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
