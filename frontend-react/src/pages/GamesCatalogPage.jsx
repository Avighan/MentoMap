/**
 * GamesCatalogPage — browse-all-games grid. HomePage.jsx already navigates
 * here via `navigate('/games')` ("Browse Games" links) but doesn't itself
 * render a catalog for every role, so this fills that route.
 *
 * Real backend route: GET /api/games -> { meta, games: [...] } (backend/app.py
 * `games_list`), via api/games.js `listGames()`.
 *
 * Design deliberately mirrors HomePage.jsx's own "Popular Learning
 * Adventures" card exactly — same `colors`/`themeConfig` values, same
 * category-pill/duration-badge/Play-Now-button conventions — rather than
 * inventing a separate visual language for this page. The one addition is
 * a real photo behind the gradient for the 3 pilot games that have one
 * (reference/simulok-source/assets/sim/); everything else (badges, button,
 * layout) is unchanged from HomePage's pattern so the app reads as one
 * consistent product.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FaHeart, FaRocket, FaBrain, FaGamepad, FaClock, FaLock, FaPlayCircle, FaArrowRight } from 'react-icons/fa';
import { GiMoneyStack, GiPuzzle, GiLemon } from 'react-icons/gi';
import { listGames } from '../api/games';
import { LoadingState } from '../components/ui/LoadingSpinner';
import dealcraftImg from '../assets/games/dealcraft.jpg';
import mumbaiImg from '../assets/games/mumbai_manufacturer.jpg';
import heliogridImg from '../assets/games/heliogrid.jpg';

// Same object as HomePage.jsx's `colors` — kept in sync by eye since neither
// file exports it. Values must match if either changes.
const colors = {
  primary: '#FFD166',
  background: '#FFFDF7',
  card: '#FFFFFF',
  text: '#2D3047',
  textLight: '#6D7286',
  primaryLight: '#FFF3D6',

  business: '#4ECDC4',
  social: '#FF6B6B',
  puzzle: '#9B5DE5',
  adventure: '#118AB2',
  strategy: '#06D6A0',
  lemon: '#FFD93D',
};

// Identical to HomePage.jsx's `themeConfig` — same keys, same gradients —
// so a game rendered here and on the home carousel looks like the same card.
const themeConfig = {
  business: { color: colors.business, icon: <GiMoneyStack />, bgGradient: 'linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%)' },
  social: { color: colors.social, icon: <FaHeart />, bgGradient: 'linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%)' },
  puzzle: { color: colors.puzzle, icon: <GiPuzzle />, bgGradient: 'linear-gradient(135deg, #9B5DE5 0%, #7C4DFF 100%)' },
  adventure: { color: colors.adventure, icon: <FaRocket />, bgGradient: 'linear-gradient(135deg, #118AB2 0%, #06BEE1 100%)' },
  strategy: { color: colors.strategy, icon: <FaBrain />, bgGradient: 'linear-gradient(135deg, #06D6A0 0%, #00CF8A 100%)' },
  lemon: { color: colors.lemon, icon: <GiLemon />, bgGradient: 'linear-gradient(135deg, #FFD93D 0%, #FFB347 100%)' },
  default: { color: colors.primary, icon: <FaGamepad />, bgGradient: 'linear-gradient(135deg, #FFD166 0%, #FFB347 100%)' },
};

function getGameConfig(game) {
  const theme = game.theme?.toLowerCase();
  return themeConfig[theme] || themeConfig.default;
}

// Real Simulok cover photography (reference/simulok-source/assets/sim/) for
// the 3 pilot games — layered under the same gradient the other cards use.
const HERO_IMAGES = {
  dealcraft: dealcraftImg,
  mumbai_manufacturer: mumbaiImg,
  heliogrid: heliogridImg,
};

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

        <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
          {games.map((g) => {
            const hero = HERO_IMAGES[g.game_id];
            const config = getGameConfig(g);
            const ageGroup = g.age_category === 'kids' ? '8+' : g.age_category === 'teens' ? '13+' : g.age_category === 'adults' ? '18+' : 'All ages';
            return (
              <motion.div
                key={g.game_id}
                whileHover={g.locked ? {} : { y: -4 }}
                className="rounded-3xl overflow-hidden shadow-md hover:shadow-xl transition-shadow"
                style={{ backgroundColor: colors.card }}
              >
                <div
                  className="h-40 relative"
                  style={{
                    background: hero
                      ? `linear-gradient(to top, rgba(0,0,0,0.6), rgba(0,0,0,0.05)), url(${hero}) center/cover`
                      : config.bgGradient,
                  }}
                >
                  {!hero && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-xl">
                        <div className="text-3xl text-white">{g.icon || config.icon}</div>
                      </div>
                    </div>
                  )}
                  {hero && (
                    <span className="absolute bottom-3 left-4 right-4 text-white font-extrabold text-lg leading-tight drop-shadow line-clamp-2">
                      {g.title}
                    </span>
                  )}
                  {g.duration_minutes && (
                    <div className={`absolute top-3 right-3 ${hero ? '' : 'bottom-3 top-auto'}`}>
                      <div className="flex items-center px-2.5 py-1 rounded-full bg-black/30 backdrop-blur-sm">
                        <FaClock className="text-white text-xs mr-1" />
                        <span className="text-xs font-bold text-white">{g.duration_minutes} min</span>
                      </div>
                    </div>
                  )}
                  {g.locked && (
                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                      <FaLock className="text-white text-2xl" />
                    </div>
                  )}
                </div>

                <div className="p-5">
                  {!hero && (
                    <h3 className="text-lg font-bold mb-2 line-clamp-1" style={{ color: colors.text }}>{g.title}</h3>
                  )}
                  <div className="flex items-center mb-3">
                    <span
                      className="text-xs font-semibold px-3 py-1 rounded-full"
                      style={{ backgroundColor: config.color + '20', color: config.color }}
                    >
                      {g.theme || 'Adventure'}
                    </span>
                  </div>
                  <p className="text-sm mb-4 line-clamp-2" style={{ color: colors.textLight, minHeight: 40 }}>
                    {g.description}
                  </p>

                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs text-gray-400 flex items-center gap-1">
                      <FaBrain className="flex-shrink-0 text-amber-400" size={10} />
                      {g.difficulty || 'Soft Skills'}
                    </span>
                    <div
                      className="text-xs font-semibold px-3 py-1 rounded-full flex-shrink-0"
                      style={{ backgroundColor: colors.primaryLight, color: colors.text }}
                    >
                      {ageGroup}
                    </div>
                  </div>

                  {g.locked ? (
                    <div className="text-xs font-semibold text-center py-2" style={{ color: colors.textLight }}>
                      🔒 {g.unlock_hint || 'Locked'}
                    </div>
                  ) : (
                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => navigate(`/play/${g.game_id}`)}
                      className="w-full py-3 rounded-xl font-bold flex items-center justify-center shadow-lg"
                      style={{ backgroundColor: config.color, color: colors.text }}
                    >
                      <FaPlayCircle className="mr-2 text-lg" />
                      Play Now
                      <FaArrowRight className="ml-2" />
                    </motion.button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
