/**
 * GamesCatalogPage — browse-all-games grid. HomePage.jsx already navigates
 * here via `navigate('/games')` ("Browse Games" links) but doesn't itself
 * render a catalog for every role, so this fills that route.
 *
 * Real backend route: GET /api/games -> { meta, games: [...] } (backend/app.py
 * `games_list`), via api/games.js `listGames()`.
 *
 * Uses the actual Simulok cover photography for the 3 pilot games (see
 * reference/simulok-source/assets/sim/) rather than emoji placeholders —
 * these are the real hero images that game's original implementation shipped.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FaClock, FaSignal, FaLock, FaPlay } from 'react-icons/fa';
import { listGames } from '../api/games';
import { LoadingState } from '../components/ui/LoadingSpinner';
import dealcraftImg from '../assets/games/dealcraft.jpg';
import mumbaiImg from '../assets/games/mumbai_manufacturer.jpg';
import heliogridImg from '../assets/games/heliogrid.jpg';

const colors = {
  primary: '#FFD166',
  primaryDark: '#FFC145',
  background: '#FFFDF7',
  text: '#2D3047',
  textLight: '#6D7286',
  purple: '#6C5CE7',
};

const HERO_IMAGES = {
  dealcraft: dealcraftImg,
  mumbai_manufacturer: mumbaiImg,
  heliogrid: heliogridImg,
};

const CARD_ACCENTS = ['#6C5CE7', '#4ECDC4', '#FF6B6B', '#118AB2', '#FFD166'];

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
    <div className="min-h-screen" style={{ backgroundColor: colors.background }}>
      <div className="max-w-6xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-extrabold mb-1" style={{ color: colors.text }}>Browse Games</h1>
        <p className="mb-8" style={{ color: colors.textLight }}>{games.length} simulation{games.length === 1 ? '' : 's'} available</p>

        {error && <div className="mb-6 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>}

        <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {games.map((g, idx) => {
            const hero = HERO_IMAGES[g.game_id];
            const accent = CARD_ACCENTS[idx % CARD_ACCENTS.length];
            return (
              <motion.button
                key={g.game_id}
                onClick={() => !g.locked && navigate(`/play/${g.game_id}`)}
                disabled={!!g.locked}
                whileHover={g.locked ? {} : { y: -4 }}
                className="text-left rounded-2xl overflow-hidden bg-white shadow-md hover:shadow-xl transition-shadow disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div
                  className="h-36 relative flex items-end p-4"
                  style={{
                    backgroundImage: hero
                      ? `linear-gradient(to top, rgba(0,0,0,0.75), rgba(0,0,0,0.05)), url(${hero})`
                      : `linear-gradient(135deg, ${accent}, ${accent}CC)`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                  }}
                >
                  {!hero && <span className="text-4xl">{g.icon || '🎮'}</span>}
                  {hero && (
                    <span className="text-white font-extrabold text-lg leading-tight drop-shadow">{g.title}</span>
                  )}
                  {g.locked && (
                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                      <FaLock className="text-white text-2xl" />
                    </div>
                  )}
                </div>

                <div className="p-4">
                  {!hero && (
                    <div className="font-bold mb-1" style={{ color: colors.text }}>{g.title}</div>
                  )}
                  <p className="text-sm mb-3" style={{ color: colors.textLight, minHeight: 40 }}>
                    {(g.description || '').slice(0, 100)}{g.description?.length > 100 ? '…' : ''}
                  </p>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 text-xs font-semibold" style={{ color: colors.textLight }}>
                      {g.duration_minutes && (
                        <span className="flex items-center gap-1"><FaClock /> {g.duration_minutes} min</span>
                      )}
                      {g.difficulty && (
                        <span className="flex items-center gap-1"><FaSignal /> {g.difficulty}</span>
                      )}
                    </div>
                    {!g.locked && (
                      <span
                        className="flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full text-white"
                        style={{ backgroundColor: accent }}
                      >
                        <FaPlay className="text-[9px]" /> Play
                      </span>
                    )}
                  </div>
                  {g.locked && (
                    <div className="text-xs mt-2 font-semibold" style={{ color: colors.textLight }}>
                      🔒 {g.unlock_hint || 'Locked'}
                    </div>
                  )}
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
