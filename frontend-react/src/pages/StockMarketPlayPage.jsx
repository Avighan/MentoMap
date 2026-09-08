/**
 * StockMarketPlayPage — thin wrapper around the already-built
 * StockMarketGame renderer (real T+1-settlement trading sim: brokerage/
 * STT/GST charges, circuit breakers, per-sector dimension scoring — see
 * backend's /api/run/<id>/stocksim/* routes) for the 2 `minigame` games
 * with subtype "stock_market" (stock-market-day-trader, stock-market-
 * simulator). The renderer starts its own session (via api/stocksim.js's
 * startStocksim) once it has a runId and manages the whole trading loop
 * itself — this page only creates the run and takes over on completion to
 * show the same final-score layout the other play pages use.
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FaSpinner, FaExclamationTriangle, FaTrophy, FaLightbulb, FaStar, FaMedal, FaChartLine } from 'react-icons/fa';
import { startGame, endGame } from '../api/games';
import { LoadingState } from '../components/ui/LoadingSpinner';
import RobotGuide from '../assets/robo.png';
import StockMarketGame from '../components/game/renderers/StockMarketGame';

const colors = {
  primary: '#FFD166', primaryLight: '#FFE8A5', primaryDark: '#FFC145',
  background: '#FFFDF7', card: '#FFFFFF', text: '#2D3047', textLight: '#6D7286',
  purple: '#6C5CE7', teal: '#4ECDC4',
};

export default function StockMarketPlayPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState(null);
  const [game, setGame] = useState(null);
  const [report, setReport] = useState(null);
  const [finalizing, setFinalizing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    startGame(gameId)
      .then((data) => {
        if (cancelled) return;
        setRunId(data.run_id);
        setGame(data.game_data);
      })
      .catch((err) => !cancelled && setError(err?.response?.data?.error || 'Could not start this game.'))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [gameId]);

  const handleComplete = async () => {
    setFinalizing(true);
    try {
      const rpt = await endGame(runId);
      setReport(rpt);
    } catch (err) {
      setError(err?.response?.data?.error || 'Could not finalize the run.');
    } finally {
      setFinalizing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ backgroundColor: colors.background }}>
        <FaSpinner className="animate-spin text-3xl" style={{ color: colors.purple }} />
        <LoadingState label="Opening the market…" />
      </div>
    );
  }

  if (error && !game) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: colors.background }}>
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md text-center">
          <FaExclamationTriangle className="text-3xl mx-auto mb-3 text-red-500" />
          <p className="text-gray-700 mb-4">{error}</p>
          <button onClick={() => navigate('/games')} className="px-4 py-2 rounded-lg font-bold shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
            Back to games
          </button>
        </div>
      </div>
    );
  }

  if (finalizing) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ backgroundColor: colors.background }}>
        <FaSpinner className="animate-spin text-3xl" style={{ color: colors.purple }} />
        <LoadingState label="Closing the books…" />
      </div>
    );
  }

  if (report) {
    const rc = report.report_core || {};
    const mento = rc.mento_score || {};
    const dna = rc.dna_card || {};
    const skillReport = rc.skill_report || {};
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ backgroundColor: colors.background }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-3xl shadow-2xl overflow-hidden max-w-lg w-full">
          <div className="p-8 pt-6 text-center">
            <img src={RobotGuide} alt="" className="w-14 h-14 mx-auto mb-3 rounded-full bg-white p-1 shadow-lg" />
            <div className="flex items-center justify-center gap-2 mb-1">
              <FaTrophy style={{ color: colors.primaryDark }} />
              <h1 className="text-xl font-bold" style={{ color: colors.text }}>Market Closed!</h1>
            </div>
            <p className="text-sm mb-6" style={{ color: colors.textLight }}>{game.title}</p>
            <motion.div initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: 0.15, type: 'spring' }} className="text-6xl font-extrabold mb-2" style={{ color: colors.purple }}>
              {Math.round(mento.score ?? rc.final_score ?? 0)}
            </motion.div>
            {mento.rank && <span className="inline-block px-4 py-1 rounded-full text-sm font-bold mb-1" style={{ backgroundColor: colors.primaryLight, color: colors.text }}>{mento.rank}</span>}
            {dna.archetype_name && (
              <div className="mt-6 rounded-xl p-4 text-left" style={{ backgroundColor: colors.purple + '0D' }}>
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-1" style={{ color: colors.purple }}><FaStar /> Your Decision DNA</div>
                <div className="font-extrabold text-lg" style={{ color: colors.text }}>{dna.archetype_name}</div>
                {dna.decision_style && <p className="text-xs" style={{ color: colors.textLight }}>{dna.decision_style}</p>}
              </div>
            )}
            {rc.dimension_scores?.length > 0 && (
              <div className="mt-6 space-y-3 text-left">
                <div className="flex items-center gap-2 text-sm font-bold" style={{ color: colors.text }}><FaChartLine style={{ color: colors.teal }} /> Skill Breakdown</div>
                {rc.dimension_scores.map((d) => (
                  <div key={d.name}>
                    <div className="flex justify-between text-xs mb-1" style={{ color: colors.textLight }}><span>{d.label}</span><span className="font-semibold">{Math.round(d.value)}</span></div>
                    <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
                      <motion.div className="h-full rounded-full" style={{ backgroundColor: d.color || colors.teal }} initial={{ width: 0 }} animate={{ width: `${Math.min(100, d.value)}%` }} transition={{ duration: 0.6, delay: 0.2 }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
            {skillReport.summary_text && (
              <div className="mt-6 text-left rounded-xl p-4 border-l-4" style={{ borderColor: colors.primaryDark, backgroundColor: colors.primaryLight + '40' }}>
                <div className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide mb-1.5" style={{ color: colors.text }}><FaLightbulb style={{ color: colors.primaryDark }} /> Reflect</div>
                <p className="text-sm" style={{ color: colors.textLight }}>{skillReport.summary_text}</p>
              </div>
            )}
            <div className="flex gap-3 mt-8">
              <button onClick={() => window.location.reload()} className="flex-1 px-4 py-2.5 rounded-xl font-bold border-2" style={{ borderColor: colors.primary, color: colors.text, backgroundColor: colors.card }}>Play Again</button>
              <button onClick={() => navigate('/games')} className="flex-1 px-4 py-2.5 rounded-xl font-bold shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>Back to Games</button>
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <StockMarketGame
      gameData={game}
      runId={runId}
      onComplete={handleComplete}
    />
  );
}
