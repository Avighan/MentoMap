/**
 * PilotGamePlayPage — real play-through UI for the three Phase 1 pilot
 * games (dealcraft, mumbai_manufacturer, heliogrid). These have a
 * different backend contract than the legacy generic engine GamePlayPage.jsx
 * uses (routes/grader_routes.py's per-game /choose, /quarter, /complete
 * endpoints — see that file's docstring), and GamePlayPage.jsx itself
 * depends on ~50 other components/contexts that were never committed to
 * this repo (a much larger gap than the "restore the bootstrap files"
 * scope this page fills) — so this is a new, focused page rather than an
 * attempt to route pilot games through that page.
 *
 * Visual language matches the rest of the rebuilt app (see HomePage.jsx's
 * `colors` object and its use of framer-motion/react-icons) rather than
 * inventing a separate style — this was plain unstyled HTML in an earlier
 * pass and has been redone to actually look like part of MentoMap.
 *
 * Backend routes exercised here, all real (see backend/routes/grader_routes.py):
 *   POST /api/run/start                          -> { run_id, game_data, ... }
 *   POST /api/run/<id>/dealcraft/choose           { round_id, choice_id }
 *   POST /api/run/<id>/mumbai_manufacturer/choose { round_id, choice_id, event_choice_id? }
 *   POST /api/run/<id>/heliogrid/quarter          { action }
 *   POST /api/run/<id>/complete                   -> { summary: { score, band, dimension_scores } }
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  FaArrowLeft, FaTrophy, FaChartLine, FaGamepad, FaSpinner, FaExclamationTriangle,
} from 'react-icons/fa';
import { startGame, dealcraftChoose, mumbaiManufacturerChoose, heliogridQuarter, completePilotRun } from '../api/games';
import { LoadingState } from '../components/ui/LoadingSpinner';
import RobotGuide from '../assets/robo.png';

const colors = {
  primary: '#FFD166',
  primaryLight: '#FFE8A5',
  primaryDark: '#FFC145',
  background: '#FFFDF7',
  card: '#FFFFFF',
  text: '#2D3047',
  textLight: '#6D7286',
  purple: '#6C5CE7',
  teal: '#4ECDC4',
};

const GAME_META = {
  dealcraft: { icon: '🤝', accent: colors.purple, label: 'Negotiation Simulation' },
  mumbai_manufacturer: { icon: '🏭', accent: colors.teal, label: 'Inventory & Operations' },
  heliogrid: { icon: '☀️', accent: colors.primaryDark, label: 'Strategy Simulation' },
};

const PILOT_GAME_IDS = new Set(Object.keys(GAME_META));

const RANK_STYLES = {
  A: { bg: '#D1FAE5', text: '#065F46' },
  B: { bg: '#DBEAFE', text: '#1E40AF' },
  C: { bg: '#FEF3C7', text: '#92400E' },
  D: { bg: '#FFE4E6', text: '#9F1239' },
  F: { bg: '#FEE2E2', text: '#991B1B' },
};

// heliogrid's action is a multi-lever pricing/ops form (listPrice, discounts
// per segment, sales allocation per segment, headcount, spend) rather than a
// pick-one-of-four choice — a full lever-by-lever editor is future work, so
// this plays a single reasonable default action each quarter (still a real
// POST to the real endpoint, just not an interactive form for every lever).
const HELIOGRID_DEFAULT_ACTION = {
  listPrice: 162000,
  discounts: { campus_estates: 5, process_plants: 0, retail_chains: 8, installer_guild: 10 },
  salesAlloc: { campus_estates: 30, process_plants: 15, retail_chains: 30, installer_guild: 25 },
  headcount: 12,
  commsSpend: 60000,
  researchSpend: 40000,
};

function TopBar({ title, icon, onBack }) {
  return (
    <div className="sticky top-0 z-10 bg-white/90 backdrop-blur-sm border-b shadow-sm">
      <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center justify-center w-9 h-9 rounded-lg hover:bg-gray-100 transition-colors"
          aria-label="Back to games"
        >
          <FaArrowLeft style={{ color: colors.text }} />
        </button>
        <span className="text-2xl">{icon}</span>
        <h1 className="text-lg font-bold" style={{ color: colors.text }}>{title}</h1>
      </div>
    </div>
  );
}

function ProgressBar({ current, total, accent }) {
  const pct = Math.min(100, Math.round((current / total) * 100));
  return (
    <div className="max-w-3xl mx-auto px-4 pt-4">
      <div className="flex justify-between text-xs font-semibold mb-1" style={{ color: colors.textLight }}>
        <span>Step {current} of {total}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: accent }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4 }}
        />
      </div>
    </div>
  );
}

export default function PilotGamePlayPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState(null);
  const [game, setGame] = useState(null);
  const [roundIndex, setRoundIndex] = useState(0);
  const [quarterIndex, setQuarterIndex] = useState(0);
  const [log, setLog] = useState([]);
  const [summary, setSummary] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const meta = GAME_META[gameId] || { icon: '🎮', accent: colors.primaryDark, label: 'Simulation' };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    startGame(gameId)
      .then((data) => {
        if (cancelled) return;
        setRunId(data.run_id);
        setGame(data.game_data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.response?.data?.error || 'Could not start this game.');
      })
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [gameId]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ backgroundColor: colors.background }}>
        <FaSpinner className="animate-spin text-3xl" style={{ color: colors.purple }} />
        <LoadingState label="Starting your run…" />
      </div>
    );
  }

  if (error && !game) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: colors.background }}>
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md text-center">
          <FaExclamationTriangle className="text-3xl mx-auto mb-3 text-red-500" />
          <p className="text-gray-700 mb-4">{error}</p>
          <button
            onClick={() => navigate('/games')}
            className="px-4 py-2 rounded-lg font-bold text-white"
            style={{ backgroundColor: colors.purple }}
          >
            Back to games
          </button>
        </div>
      </div>
    );
  }

  if (!PILOT_GAME_IDS.has(gameId)) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: colors.background }}>
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-lg text-center">
          <img src={RobotGuide} alt="" className="w-16 h-16 mx-auto mb-4" />
          <p className="text-gray-700 mb-2">
            <strong>"{game?.title || gameId}"</strong> isn't wired into the rebuilt UI yet — only
            Dealcraft, Mumbai Manufacturer, and HelioGrid have a play screen so far.
          </p>
          <p className="text-sm text-gray-400 mb-4">A run was started for it on the backend (run id: {runId}).</p>
          <button
            onClick={() => navigate('/games')}
            className="px-4 py-2 rounded-lg font-bold text-white"
            style={{ backgroundColor: colors.purple }}
          >
            Back to games
          </button>
        </div>
      </div>
    );
  }

  const handleDealMumbaiChoice = async (choiceId) => {
    const rounds = game.rounds;
    const round = rounds[roundIndex];
    setSubmitting(true);
    setError('');
    try {
      let res;
      if (gameId === 'dealcraft') {
        res = await dealcraftChoose(runId, round.id, choiceId);
      } else {
        // mumbai_manufacturer schedules a crisis event after some rounds —
        // the route 400s with the event payload when one is due and no
        // event_choice_id was sent. Auto-picking the first event option
        // keeps this page's flow to one click per round rather than adding
        // a second modal step for the ~1/3 of rounds that have one.
        try {
          res = await mumbaiManufacturerChoose(runId, round.id, choiceId);
        } catch (err) {
          const event = err?.response?.data?.event;
          if (err?.response?.status === 400 && event?.choices?.length) {
            res = await mumbaiManufacturerChoose(runId, round.id, choiceId, event.choices[0].id);
          } else {
            throw err;
          }
        }
      }
      setLog((prev) => [...prev, { round: round.title, choice: choiceId, state: res.state }]);
      if (roundIndex + 1 >= rounds.length) {
        const done = await completePilotRun(runId);
        setSummary(done.summary);
      } else {
        setRoundIndex((i) => i + 1);
      }
    } catch (err) {
      setError(err?.response?.data?.error || 'Choice failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleHeliogridQuarter = async () => {
    setSubmitting(true);
    setError('');
    try {
      const res = await heliogridQuarter(runId, HELIOGRID_DEFAULT_ACTION);
      setLog((prev) => [...prev, { quarter: quarterIndex + 1, result: res.quarter_result }]);
      const totalQuarters = (game.simulation_config?.quarters) || 4;
      if (quarterIndex + 1 >= totalQuarters) {
        const done = await completePilotRun(runId);
        setSummary(done.summary);
      } else {
        setQuarterIndex((i) => i + 1);
      }
    } catch (err) {
      setError(err?.response?.data?.error || 'Quarter simulation failed.');
    } finally {
      setSubmitting(false);
    }
  };

  // ---------- Final score screen ----------
  if (summary) {
    const rankLetter = (summary.band || summary.rank || '?')[0]?.toUpperCase();
    const rankStyle = RANK_STYLES[rankLetter] || RANK_STYLES.C;
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ backgroundColor: colors.background }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-3xl shadow-xl p-8 max-w-lg w-full text-center"
        >
          <img src={RobotGuide} alt="" className="w-14 h-14 mx-auto mb-3" />
          <div className="flex items-center justify-center gap-2 mb-1">
            <FaTrophy style={{ color: colors.primaryDark }} />
            <h1 className="text-xl font-bold" style={{ color: colors.text }}>Run Complete!</h1>
          </div>
          <p className="text-sm mb-6" style={{ color: colors.textLight }}>{game.title}</p>

          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.15, type: 'spring' }}
            className="text-6xl font-extrabold mb-2"
            style={{ color: colors.purple }}
          >
            {Math.round(summary.score ?? 0)}
          </motion.div>

          <span
            className="inline-block px-4 py-1 rounded-full text-sm font-bold mb-2"
            style={{ backgroundColor: rankStyle.bg, color: rankStyle.text }}
          >
            Rank {summary.band || summary.rank}
          </span>
          {summary.label && <p className="text-sm font-medium mt-1" style={{ color: colors.text }}>{summary.label}</p>}

          {summary.dimension_scores && (
            <div className="mt-6 space-y-3 text-left">
              <div className="flex items-center gap-2 text-sm font-bold" style={{ color: colors.text }}>
                <FaChartLine style={{ color: colors.teal }} />
                Skill Breakdown
              </div>
              {Object.entries(summary.dimension_scores).map(([dim, val]) => (
                <div key={dim}>
                  <div className="flex justify-between text-xs mb-1" style={{ color: colors.textLight }}>
                    <span>{dim}</span>
                    <span className="font-semibold">{Math.round(val)}</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ backgroundColor: colors.teal }}
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, val)}%` }}
                      transition={{ duration: 0.6, delay: 0.2 }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-3 mt-8">
            <button
              onClick={() => window.location.reload()}
              className="flex-1 px-4 py-2.5 rounded-xl font-bold border-2"
              style={{ borderColor: colors.purple, color: colors.purple }}
            >
              Play Again
            </button>
            <button
              onClick={() => navigate('/games')}
              className="flex-1 px-4 py-2.5 rounded-xl font-bold text-white"
              style={{ backgroundColor: colors.purple }}
            >
              Back to Games
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // ---------- Round / quarter play screen ----------
  const currentRound = gameId !== 'heliogrid' ? game.rounds[roundIndex] : null;
  const totalSteps = gameId === 'heliogrid' ? ((game.simulation_config?.quarters) || 4) : game.rounds.length;
  const currentStep = gameId === 'heliogrid' ? quarterIndex + 1 : roundIndex + 1;

  return (
    <div className="min-h-screen pb-16" style={{ backgroundColor: colors.background }}>
      <TopBar title={game.title} icon={meta.icon} onBack={() => navigate('/games')} />
      <ProgressBar current={currentStep} total={totalSteps} accent={meta.accent} />

      <div className="max-w-3xl mx-auto px-4 mt-6">
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm flex items-center gap-2">
            <FaExclamationTriangle /> {error}
          </div>
        )}

        <AnimatePresence mode="wait">
          {gameId === 'heliogrid' ? (
            <motion.div
              key="heliogrid-quarter"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-2xl shadow-md p-6"
            >
              <div className="flex items-center gap-2 mb-2" style={{ color: colors.textLight }}>
                <FaGamepad />
                <span className="text-xs font-bold uppercase tracking-wide">{meta.label}</span>
              </div>
              <h2 className="text-xl font-bold mb-3" style={{ color: colors.text }}>Quarter {quarterIndex + 1}</h2>
              <p className="text-sm mb-6" style={{ color: colors.textLight }}>
                Running a balanced pricing/ops strategy this quarter (a full lever-by-lever control panel
                is a future enhancement — this still resolves the real quarter through the live backend).
              </p>
              <button
                disabled={submitting}
                onClick={handleHeliogridQuarter}
                className="w-full py-3 rounded-xl font-bold text-white disabled:opacity-60 transition-opacity"
                style={{ backgroundColor: meta.accent }}
              >
                {submitting ? 'Resolving quarter…' : 'Run This Quarter'}
              </button>
            </motion.div>
          ) : (
            <motion.div
              key={`round-${roundIndex}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-2xl shadow-md p-6"
            >
              <div className="flex items-center gap-2 mb-2" style={{ color: colors.textLight }}>
                <FaGamepad />
                <span className="text-xs font-bold uppercase tracking-wide">{meta.label}</span>
              </div>
              <h2 className="text-xl font-bold mb-2" style={{ color: colors.text }}>{currentRound.title}</h2>
              <p className="text-sm mb-5" style={{ color: colors.textLight }}>{currentRound.prompt}</p>

              <div className="flex flex-col gap-3">
                {currentRound.choices.map((c, idx) => (
                  <motion.button
                    key={c.id}
                    disabled={submitting}
                    onClick={() => handleDealMumbaiChoice(c.id)}
                    whileHover={{ scale: submitting ? 1 : 1.01 }}
                    whileTap={{ scale: submitting ? 1 : 0.99 }}
                    className="text-left p-4 rounded-xl border-2 border-gray-100 hover:border-current disabled:opacity-60 transition-colors"
                    style={{ color: meta.accent }}
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white"
                        style={{ backgroundColor: meta.accent }}
                      >
                        {String.fromCharCode(65 + idx)}
                      </span>
                      <div>
                        <div className="font-bold" style={{ color: colors.text }}>{c.label}</div>
                        {c.description && (
                          <div className="text-sm mt-0.5" style={{ color: colors.textLight }}>{c.description}</div>
                        )}
                      </div>
                    </div>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {log.length > 0 && (
          <p className="text-center text-xs mt-6" style={{ color: colors.textLight }}>
            {log.length} step{log.length === 1 ? '' : 's'} played so far
          </p>
        )}
      </div>
    </div>
  );
}
