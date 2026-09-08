/**
 * AdventureGamePlayPage — play screen for the 46 "rounds"-type games that
 * run through the generic engine.py path (backend/routes proper — see
 * api/games.js's startGame/submitChoice/endGame), as opposed to the 3
 * pilot games (dealcraft/mumbai_manufacturer/heliogrid) which have their
 * own bespoke engines and use PilotGamePlayPage instead.
 *
 * These games' backend responses are considerably richer than the pilots'
 * own game JSON (per-round server-authored narrative prose, a "Mira"
 * mentor reaction, an expert-pick comparison, skill-tag call-outs, XP/
 * badge rewards, a "DNA card" archetype summary) — this page is built
 * directly from that real response shape (see api/games.js's
 * startGame/submitChoice/endGame), not invented content.
 *
 * A state field here is a plain number for some games and a richer
 * {value, min, max, icon, label} object for others (see
 * backend/games/civic-sense-champion-game.json) — numericValue()/
 * stateMeta() below unwrap either shape, mirroring the same
 * _numeric_state_value() normalization added on the backend.
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  FaArrowLeft, FaArrowRight, FaSpinner, FaExclamationTriangle, FaTrophy,
  FaLightbulb, FaQuoteLeft, FaListOl, FaGraduationCap, FaStar, FaMedal,
  FaChartLine, FaGamepad,
} from 'react-icons/fa';
import { startGame, submitChoice, endGame } from '../api/games';
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
  green: '#1E8A5A',
  red: '#C0392B',
};

function numericValue(v) {
  if (v && typeof v === 'object') return typeof v.value === 'number' ? v.value : 0;
  return typeof v === 'number' ? v : 0;
}

// Free-text fields (description, coaching_moment, ...) are a plain string
// in most games but a richer {title, body} object in others (see e.g.
// games/cfo-quarterly-close.json) — these unwrap either shape instead of
// assuming a string and crashing React on an object child.
function textBody(v) {
  if (typeof v === 'string') return v;
  if (v && typeof v === 'object') return v.body || v.text || '';
  return '';
}
function textTitle(v) {
  return (v && typeof v === 'object' && v.title) || null;
}

function stateLabel(key, entry) {
  if (entry && typeof entry === 'object' && entry.label) return entry.label;
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function stateIcon(entry) {
  return entry && typeof entry === 'object' && entry.icon ? entry.icon : null;
}

function fmtNum(n) {
  if (typeof n !== 'number') return n;
  if (Math.abs(n) >= 1000) return n.toLocaleString('en-IN');
  return Math.round(n * 10) / 10;
}

/** Tiny inline sparkline (no charting lib) — plots a metric's value across
 * every round played so far, so the dashboard reads as a running simulation
 * trace rather than a single frozen number. */
function Sparkline({ values, color }) {
  if (!values || values.length < 2) return null;
  const w = 56;
  const h = 20;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="mx-auto mt-0.5" aria-hidden="true">
      <polyline points={pts.join(' ')} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Sticky headline resource dashboard — picks the "surface" resources (state
 * fields without a `category` tag; the NEP/psychological dimensions carry
 * one and are better shown in full on the final report) rather than
 * hardcoding field names, since every game's state schema differs. Reads
 * as a live simulation dashboard (current value + trend + delta) instead
 * of a single static score, which is what made these screens feel like a
 * quiz rather than a running simulation. */
// Bookkeeping fields the engine adds to every run's state — never a
// player-facing resource, so never a KpiBar candidate.
const META_STATE_KEYS = new Set([
  'round_index', 'score', 'completed', 'dimension_scores', 'choice_history',
  'rounds_completed', 'total_rounds', 'current_round', 'log',
]);

function surfaceStateKeys(state) {
  return Object.entries(state || {})
    .filter(([k, v]) => !META_STATE_KEYS.has(k) && (
      typeof v === 'number' ||
      (v && typeof v === 'object' && typeof v.value === 'number' && v.category !== 'Story & Narrative')
    ))
    .map(([k]) => k)
    .slice(0, 8);
}

function KpiBar({ state, prevState, history }) {
  const surfaceKeys = surfaceStateKeys(state);
  if (!surfaceKeys.length) return null;
  return (
    <div className="sticky top-[57px] z-10 bg-white border-b shadow-sm">
      <div className="max-w-3xl mx-auto px-4 py-2.5">
        <div className="text-[9px] font-bold uppercase tracking-widest mb-1.5" style={{ color: colors.textLight }}>
          Simulation Dashboard
        </div>
        <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${Math.min(surfaceKeys.length, 4)}, 1fr)` }}>
          {surfaceKeys.map((key) => {
            const entry = state[key];
            const value = numericValue(entry);
            const prev = prevState ? numericValue(prevState[key]) : null;
            const delta = prev !== null ? value - prev : 0;
            const flash = delta > 0 ? 'bg-green-50' : delta < 0 ? 'bg-red-50' : 'bg-gray-50';
            const icon = stateIcon(entry);
            const trend = (history || []).map((h) => numericValue(h[key]));
            return (
              <motion.div
                key={key}
                className={`rounded-lg px-2 py-1.5 text-center ${flash}`}
                animate={{ scale: delta !== 0 ? [1, 1.06, 1] : 1 }}
                transition={{ duration: 0.4 }}
              >
                <div className="text-[10px] font-bold uppercase tracking-wide truncate" style={{ color: colors.textLight }}>
                  {icon ? `${icon} ` : ''}{stateLabel(key, entry)}
                </div>
                <div className="text-sm font-extrabold" style={{ color: colors.text }}>{fmtNum(value)}</div>
                {delta !== 0 && (
                  <div className="text-[10px] font-bold" style={{ color: delta > 0 ? colors.green : colors.red }}>
                    {delta > 0 ? '+' : ''}{fmtNum(delta)}
                  </div>
                )}
                <Sparkline values={trend} color={delta < 0 ? colors.red : colors.teal} />
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ current, total }) {
  const pct = total ? Math.min(100, Math.round((current / total) * 100)) : 0;
  return (
    <div className="max-w-3xl mx-auto px-4 pt-4">
      <div className="flex justify-between text-xs font-semibold mb-1" style={{ color: colors.textLight }}>
        <span>Round {current} of {total}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: colors.primary }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4 }}
        />
      </div>
    </div>
  );
}

/** Horizontal stage-by-stage pip tracker underneath the progress bar — gives
 * the run a visible multi-stage shape (like a simulation's day/quarter
 * timeline) instead of feeling like an open-ended series of questions. */
function StageRoadmap({ current, total }) {
  if (!total || total < 2) return null;
  const stages = Array.from({ length: total }, (_, i) => i + 1);
  return (
    <div className="max-w-3xl mx-auto px-4 pt-2 flex items-center gap-1 overflow-x-auto">
      {stages.map((n) => {
        const done = n < current;
        const active = n === current;
        return (
          <div
            key={n}
            className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-colors"
            style={{
              backgroundColor: done ? colors.teal : active ? colors.purple : '#EEEDE7',
              color: done || active ? '#fff' : colors.textLight,
              boxShadow: active ? `0 0 0 3px ${colors.purple}33` : 'none',
            }}
            title={`Stage ${n}`}
          >
            {done ? '✓' : n}
          </div>
        );
      })}
    </div>
  );
}

/** Renders a round-authored `decision_data` block — structured numbers a
 * player needs to actually reason about the decision (a budget breakdown,
 * a financial snapshot, a performance trend) instead of prose alone. Mirrors
 * PilotGamePlayPage's "Key data this stage" table for the pilot engine. */
function DecisionDataPanel({ data }) {
  if (!data?.rows?.length) return null;
  return (
    <div className="mb-4 rounded-xl border border-gray-100 overflow-hidden">
      <div className="text-xs font-bold uppercase tracking-wide px-3 py-2 bg-gray-50 flex items-center gap-1.5" style={{ color: colors.textLight }}>
        <FaChartLine style={{ color: colors.teal }} /> {data.title || 'Key data this stage'}
      </div>
      {data.rows.map((row, idx) => (
        <div key={row.label} className={`flex justify-between items-center px-3 py-1.5 text-sm ${idx % 2 ? 'bg-gray-50/60' : ''}`}>
          <span style={{ color: colors.textLight }}>{row.icon ? `${row.icon} ` : ''}{row.label}</span>
          <span className="font-semibold" style={{ color: colors.text }}>{row.value}</span>
        </div>
      ))}
    </div>
  );
}

/** Compact preview of every non-zero resource a choice would move, not just
 * the single largest one — lets the player weigh a real trade-off (e.g.
 * "+12 infrastructure, -8 budget") before committing, the way a simulation's
 * decision-consequence preview works. */
function ImpactPreview({ delta }) {
  const entries = Object.entries(delta || {}).filter(([, v]) => typeof v === 'number' && v !== 0);
  if (!entries.length) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1.5">
      {entries.map(([key, val]) => (
        <span
          key={key}
          className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
          style={{ backgroundColor: val > 0 ? '#D1FAE5' : '#FEE2E2', color: val > 0 ? colors.green : colors.red }}
        >
          {val > 0 ? '+' : ''}{fmtNum(val)} {stateLabel(key)}
        </span>
      ))}
    </div>
  );
}

function TopBar({ title, icon, onBack }) {
  return (
    <div className="sticky top-0 z-20 bg-white/90 backdrop-blur-sm border-b shadow-sm">
      <div className="max-w-3xl mx-auto px-4 py-2.5 flex items-center gap-3">
        <button onClick={onBack} className="flex items-center justify-center w-9 h-9 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0" aria-label="Back to games">
          <FaArrowLeft style={{ color: colors.text }} />
        </button>
        <span className="text-2xl">{icon || '🎮'}</span>
        <h1 className="text-lg font-bold truncate" style={{ color: colors.text }}>{title}</h1>
      </div>
    </div>
  );
}

export default function AdventureGamePlayPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState(null);
  const [game, setGame] = useState(null);
  const [showBriefing, setShowBriefing] = useState(true);
  const [round, setRound] = useState(null);
  const [roundIndex, setRoundIndex] = useState(1);
  const [totalRounds, setTotalRounds] = useState(1);
  const [state, setState] = useState(null);
  const [prevState, setPrevState] = useState(null);
  // One snapshot per round played (starting state first) so the dashboard
  // can plot a trend per resource instead of just a single before/after —
  // this is what makes the run read as a simulation trajectory.
  const [stateHistory, setStateHistory] = useState([]);
  const [phase, setPhase] = useState('choice'); // 'choice' | 'outcome' | 'complete'
  const [pendingOutcome, setPendingOutcome] = useState(null);
  const [newSkills, setNewSkills] = useState([]);
  const [report, setReport] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    startGame(gameId)
      .then((data) => {
        if (cancelled) return;
        setRunId(data.run_id);
        setGame(data.game_data);
        setRound(data.round || null);
        const initialState = data.state || data.game_data?.initial_state || null;
        setState(initialState);
        setStateHistory(initialState ? [initialState] : []);
        setTotalRounds(data.game_data?.rounds?.length || 1);
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
          <button onClick={() => navigate('/games')} className="px-4 py-2 rounded-lg font-bold shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
            Back to games
          </button>
        </div>
      </div>
    );
  }

  const handleChoice = async (choice) => {
    setSubmitting(true);
    setError('');
    const answeredRound = round;
    try {
      const res = await submitChoice(runId, choice.id);
      setPrevState(state);
      setState(res.state);
      setStateHistory((h) => [...h, res.state]);
      const outcome = res.outcome || null;
      if (outcome) {
        // expert_pick is a full {choice_id, reason} object in some games
        // (e.g. civic-sense-champion-game.json) but just the winning
        // choice_id as a bare string in others (e.g. cfo-quarterly-close.json)
        // — resolve the string form against the round we just answered so
        // there's still a label + reason to show, not a blank box.
        if (typeof outcome.expert_pick === 'string') {
          const pick = (answeredRound?.choices || []).find((c) => c.id === outcome.expert_pick);
          outcome.expert_pick = pick
            ? { choice_id: pick.id, label: pick.label, reason: pick.expert_rationale || `An expert would choose: "${pick.label}"` }
            : null;
        }
        if (answeredRound?.expert_debrief) {
          outcome.expert_debrief = answeredRound.expert_debrief;
        }
      }
      setPendingOutcome(outcome);
      setNewSkills(res.new_skills_introduced || []);
      if (res.round) {
        setRound(res.round);
        setRoundIndex((i) => i + 1);
      }
      setIsDone(!!(res.done || res.game_over));
      setPhase('outcome');
    } catch (err) {
      setError(err?.response?.data?.error || 'Choice failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleContinue = async () => {
    if (isDone) {
      setSubmitting(true);
      try {
        const rpt = await endGame(runId);
        setReport(rpt);
        setPhase('complete');
      } catch (err) {
        setError(err?.response?.data?.error || 'Could not finalize the run.');
      } finally {
        setSubmitting(false);
      }
    } else {
      setPhase('choice');
      setPendingOutcome(null);
    }
  };

  // ---------- Briefing screen ----------
  if (showBriefing) {
    const howTo = game.how_to_play;
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ backgroundColor: colors.background }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl shadow-2xl overflow-hidden max-w-2xl w-full bg-white">
          <div className="h-40 relative flex flex-col justify-end p-6" style={{ background: `linear-gradient(135deg, ${colors.purple}, ${colors.teal})` }}>
            <span className="self-start mb-2 text-[11px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full text-white bg-black/20">
              {game.icon ? `${game.icon} ` : ''}{game.theme || 'Adventure'}
            </span>
            <h1 className="text-2xl font-extrabold text-white drop-shadow-lg leading-tight">{game.title}</h1>
          </div>

          <div className="p-7 max-h-[65vh] overflow-y-auto">
            <p className="text-sm leading-relaxed mb-4" style={{ color: colors.text }}>{textBody(game.description)}</p>

            {game.coaching_moment && (
              <div className="flex gap-3 p-4 rounded-xl mb-5" style={{ backgroundColor: colors.primaryLight + '40' }}>
                <FaQuoteLeft className="flex-shrink-0 mt-0.5" style={{ color: colors.primaryDark }} />
                <div>
                  {textTitle(game.coaching_moment) && (
                    <div className="text-sm font-bold mb-0.5" style={{ color: colors.text }}>{textTitle(game.coaching_moment)}</div>
                  )}
                  <p className="text-sm italic font-medium" style={{ color: colors.text }}>{textBody(game.coaching_moment)}</p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-3 gap-2.5 mb-5">
              {game.duration_minutes && (
                <div className="rounded-lg px-3 py-2 bg-gray-50 text-center">
                  <div className="text-[10px] font-bold uppercase" style={{ color: colors.textLight }}>Duration</div>
                  <div className="text-sm font-bold" style={{ color: colors.text }}>{game.duration_minutes} min</div>
                </div>
              )}
              {game.difficulty && (
                <div className="rounded-lg px-3 py-2 bg-gray-50 text-center">
                  <div className="text-[10px] font-bold uppercase" style={{ color: colors.textLight }}>Difficulty</div>
                  <div className="text-sm font-bold capitalize" style={{ color: colors.text }}>{game.difficulty}</div>
                </div>
              )}
              {game.target_audience && (
                <div className="rounded-lg px-3 py-2 bg-gray-50 text-center">
                  <div className="text-[10px] font-bold uppercase" style={{ color: colors.textLight }}>For</div>
                  <div className="text-sm font-bold" style={{ color: colors.text }}>{game.target_audience}</div>
                </div>
              )}
            </div>

            {howTo?.steps?.length > 0 && (
              <div className="mb-5">
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
                  <FaListOl /> {howTo.title || 'How to Play'}
                </div>
                <ol className="space-y-1.5">
                  {howTo.steps.map((s, i) => (
                    <li key={i} className="flex gap-2 text-sm" style={{ color: colors.text }}>
                      <span className="flex-shrink-0 w-4 h-4 rounded-full text-white text-[10px] font-bold flex items-center justify-center mt-0.5" style={{ backgroundColor: colors.purple }}>
                        {i + 1}
                      </span>
                      {s}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {game.learning_objectives?.length > 0 && (
              <div className="mb-6">
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
                  <FaGraduationCap /> You'll Practice
                </div>
                <ul className="space-y-1.5">
                  {game.learning_objectives.slice(0, 4).map((s, i) => (
                    <li key={i} className="text-sm flex gap-2" style={{ color: colors.textLight }}>
                      <span style={{ color: colors.teal }}>•</span> {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button
              onClick={() => setShowBriefing(false)}
              className="w-full py-3.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg sticky bottom-0"
              style={{ backgroundColor: colors.primary, color: colors.text }}
            >
              Begin Simulation <FaArrowRight />
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // ---------- Final score screen ----------
  if (phase === 'complete' && report) {
    const rc = report.report_core || {};
    const mento = rc.mento_score || {};
    const dna = rc.dna_card || {};
    const skillReport = rc.skill_report || {};
    const badges = report.xp_reward?.new_badges || [];
    const xp = report.xp_reward?.xp_earned;
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ backgroundColor: colors.background }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-3xl shadow-2xl overflow-hidden max-w-lg w-full">
          <div className="p-8 pt-6 text-center">
            <img src={RobotGuide} alt="" className="w-14 h-14 mx-auto mb-3 rounded-full bg-white p-1 shadow-lg" />
            <div className="flex items-center justify-center gap-2 mb-1">
              <FaTrophy style={{ color: colors.primaryDark }} />
              <h1 className="text-xl font-bold" style={{ color: colors.text }}>Run Complete!</h1>
            </div>
            <p className="text-sm mb-6" style={{ color: colors.textLight }}>{game.title}</p>

            <motion.div initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: 0.15, type: 'spring' }} className="text-6xl font-extrabold mb-2" style={{ color: colors.purple }}>
              {Math.round(mento.score ?? rc.final_score ?? 0)}
            </motion.div>
            {mento.rank && (
              <span className="inline-block px-4 py-1 rounded-full text-sm font-bold mb-1" style={{ backgroundColor: colors.primaryLight, color: colors.text }}>
                {mento.rank}
              </span>
            )}
            {typeof mento.percentile === 'number' && (
              <p className="text-xs mt-1" style={{ color: colors.textLight }}>Better than {mento.percentile}% of players</p>
            )}

            {stateHistory.length > 1 && surfaceStateKeys(state).length > 0 && (
              <div className="mt-6 rounded-xl p-4 text-left border border-gray-100">
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-3" style={{ color: colors.textLight }}>
                  <FaChartLine style={{ color: colors.teal }} /> Simulation Trajectory
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {surfaceStateKeys(state).slice(0, 4).map((key) => {
                    const trend = stateHistory.map((h) => numericValue(h[key]));
                    const start = trend[0];
                    const end = trend[trend.length - 1];
                    const delta = end - start;
                    return (
                      <div key={key} className="rounded-lg bg-gray-50 px-3 py-2">
                        <div className="text-[10px] font-bold uppercase tracking-wide truncate" style={{ color: colors.textLight }}>
                          {stateIcon(state[key]) ? `${stateIcon(state[key])} ` : ''}{stateLabel(key, state[key])}
                        </div>
                        <div className="flex items-center justify-between mt-0.5">
                          <span className="text-xs" style={{ color: colors.textLight }}>{fmtNum(start)} → <span className="font-bold" style={{ color: colors.text }}>{fmtNum(end)}</span></span>
                          <span className="text-[10px] font-bold" style={{ color: delta >= 0 ? colors.green : colors.red }}>{delta > 0 ? '+' : ''}{fmtNum(delta)}</span>
                        </div>
                        <Sparkline values={trend} color={delta < 0 ? colors.red : colors.teal} />
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {dna.archetype_name && (
              <div className="mt-6 rounded-xl p-4 text-left" style={{ backgroundColor: colors.purple + '0D' }}>
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-1" style={{ color: colors.purple }}>
                  <FaStar /> Your Decision DNA
                </div>
                <div className="font-extrabold text-lg" style={{ color: colors.text }}>{dna.archetype_name}</div>
                {dna.decision_style && <p className="text-xs mb-2" style={{ color: colors.textLight }}>{dna.decision_style}</p>}
                {dna.top_traits?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {dna.top_traits.map((t) => (
                      <span key={t.id} className="text-xs font-semibold px-2.5 py-1 rounded-full bg-white" style={{ color: colors.text }}>
                        {t.label}: {Math.round(t.score)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {rc.dimension_scores?.length > 0 && (
              <div className="mt-6 space-y-3 text-left">
                <div className="flex items-center gap-2 text-sm font-bold" style={{ color: colors.text }}>
                  <FaChartLine style={{ color: colors.teal }} /> Skill Breakdown
                </div>
                {rc.dimension_scores.map((d) => (
                  <div key={d.name}>
                    <div className="flex justify-between text-xs mb-1" style={{ color: colors.textLight }}>
                      <span>{d.icon ? '' : ''}{d.label}</span>
                      <span className="font-semibold">{Math.round(d.value)}</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
                      <motion.div className="h-full rounded-full" style={{ backgroundColor: d.color || colors.teal }} initial={{ width: 0 }} animate={{ width: `${Math.min(100, d.value)}%` }} transition={{ duration: 0.6, delay: 0.2 }} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {skillReport.summary_text && (
              <div className="mt-6 text-left rounded-xl p-4 border-l-4" style={{ borderColor: colors.primaryDark, backgroundColor: colors.primaryLight + '40' }}>
                <div className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide mb-1.5" style={{ color: colors.text }}>
                  <FaLightbulb style={{ color: colors.primaryDark }} /> Reflect
                </div>
                <p className="text-sm" style={{ color: colors.textLight }}>{skillReport.summary_text}</p>
              </div>
            )}

            {(badges.length > 0 || xp) && (
              <div className="mt-5 flex items-center justify-center gap-4 flex-wrap">
                {badges.map((b) => (
                  <div key={b.id} className="flex items-center gap-1.5 text-sm font-bold px-3 py-1.5 rounded-full" style={{ backgroundColor: colors.primaryLight, color: colors.text }}>
                    <span>{b.icon}</span> {b.name}
                  </div>
                ))}
                {xp ? (
                  <div className="flex items-center gap-1.5 text-sm font-bold px-3 py-1.5 rounded-full" style={{ backgroundColor: colors.teal + '20', color: colors.teal }}>
                    <FaMedal /> +{xp} XP
                  </div>
                ) : null}
              </div>
            )}

            <div className="flex gap-3 mt-8">
              <button onClick={() => window.location.reload()} className="flex-1 px-4 py-2.5 rounded-xl font-bold border-2" style={{ borderColor: colors.primary, color: colors.text, backgroundColor: colors.card }}>
                Play Again
              </button>
              <button onClick={() => navigate('/games')} className="flex-1 px-4 py-2.5 rounded-xl font-bold shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
                Back to Games
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  // ---------- Round / outcome play screen ----------
  return (
    <div className="min-h-screen pb-16" style={{ backgroundColor: colors.background }}>
      <TopBar title={game.title} icon={game.icon} onBack={() => navigate('/games')} />
      <KpiBar state={state} prevState={prevState} history={stateHistory} />
      <ProgressBar current={Math.min(roundIndex, totalRounds)} total={totalRounds} />
      <StageRoadmap current={Math.min(roundIndex, totalRounds)} total={totalRounds} />

      <div className="max-w-3xl mx-auto px-4 mt-6">
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm flex items-center gap-2">
            <FaExclamationTriangle /> {error}
          </div>
        )}

        <AnimatePresence mode="wait">
          {phase === 'outcome' && pendingOutcome && (
            <motion.div key={`outcome-${roundIndex}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl shadow-md p-6">
              <div className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>Decision Outcome</div>
              <h2 className="text-lg font-bold mb-3" style={{ color: colors.text }}>{pendingOutcome.round_title}</h2>

              {pendingOutcome.events?.length > 0 && (
                <div className="rounded-xl p-4 mb-4" style={{ backgroundColor: '#F5F4EF' }}>
                  {pendingOutcome.events.map((ev, i) => (
                    <p key={i} className="text-sm leading-relaxed" style={{ color: colors.text }}>{ev}</p>
                  ))}
                </div>
              )}

              {(() => {
                const changedKeys = surfaceStateKeys(state).filter((k) => {
                  const before = prevState ? numericValue(prevState[k]) : null;
                  const after = numericValue(state[k]);
                  return before !== null && before !== after;
                });
                if (!changedKeys.length) return null;
                return (
                  <div className="mb-4 rounded-xl border border-gray-100 overflow-hidden">
                    <div className="text-xs font-bold uppercase tracking-wide px-3 py-2 bg-gray-50" style={{ color: colors.textLight }}>
                      How this changed the simulation
                    </div>
                    {changedKeys.map((k, idx) => {
                      const before = numericValue(prevState[k]);
                      const after = numericValue(state[k]);
                      const delta = after - before;
                      return (
                        <div key={k} className={`flex justify-between items-center px-3 py-1.5 text-sm ${idx % 2 ? 'bg-gray-50/60' : ''}`}>
                          <span style={{ color: colors.textLight }}>{stateIcon(state[k]) ? `${stateIcon(state[k])} ` : ''}{stateLabel(k, state[k])}</span>
                          <span className="font-semibold flex items-center gap-1.5" style={{ color: colors.text }}>
                            {fmtNum(before)} <FaArrowRight className="text-[10px]" style={{ color: colors.textLight }} /> {fmtNum(after)}
                            <span style={{ color: delta > 0 ? colors.green : colors.red }}>({delta > 0 ? '+' : ''}{fmtNum(delta)})</span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}

              {pendingOutcome.mira && (
                <div className="flex gap-3 p-4 rounded-xl mb-4" style={{ backgroundColor: colors.purple + '0D' }}>
                  <img src={RobotGuide} alt="" className="w-8 h-8 rounded-full flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium" style={{ color: colors.text }}>{textBody(pendingOutcome.mira)}</p>
                    {pendingOutcome.mira_question && (
                      <p className="text-xs italic mt-1.5" style={{ color: colors.textLight }}>{textBody(pendingOutcome.mira_question)}</p>
                    )}
                  </div>
                </div>
              )}

              {pendingOutcome.skill_callout && (
                <div className="flex items-center gap-2 mb-4 text-sm font-semibold px-3 py-2 rounded-lg" style={{ backgroundColor: (pendingOutcome.skill_callout.color || colors.teal) + '14', color: pendingOutcome.skill_callout.color || colors.teal }}>
                  <FaStar /> {textBody(pendingOutcome.skill_callout.message)}
                </div>
              )}

              {pendingOutcome.expert_pick?.reason && (
                <div className="mb-4 rounded-xl p-4 border-l-4" style={{ borderColor: colors.teal, backgroundColor: colors.teal + '0D' }}>
                  <div className="flex items-center gap-1.5 text-sm font-extrabold mb-1" style={{ color: colors.text }}>
                    <FaGraduationCap style={{ color: colors.teal }} /> What an expert would do
                  </div>
                  <p className="text-xs" style={{ color: colors.textLight }}>{textBody(pendingOutcome.expert_pick.reason)}</p>
                </div>
              )}

              {pendingOutcome.expert_debrief && (
                <div className="mb-4 rounded-xl p-4 border-l-4" style={{ borderColor: colors.purple, backgroundColor: colors.purple + '0D' }}>
                  <div className="flex items-center gap-1.5 text-sm font-extrabold mb-1" style={{ color: colors.text }}>
                    <FaGraduationCap style={{ color: colors.purple }} /> {textTitle(pendingOutcome.expert_debrief) || 'Expert Debrief'}
                  </div>
                  <p className="text-xs leading-relaxed" style={{ color: colors.textLight }}>{textBody(pendingOutcome.expert_debrief)}</p>
                </div>
              )}

              {newSkills.length > 0 && (
                <div className="mb-4 grid gap-2">
                  {newSkills.map((s) => (
                    <div key={s.id} className="flex items-center gap-2 text-sm font-semibold px-3 py-2 rounded-lg" style={{ backgroundColor: (s.color || colors.purple) + '14', color: s.color || colors.purple }}>
                      <span>{s.emoji}</span> New skill unlocked: {s.name}
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={handleContinue}
                disabled={submitting}
                className="w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg disabled:opacity-60"
                style={{ backgroundColor: colors.primary, color: colors.text }}
              >
                {submitting ? <><FaSpinner className="animate-spin" /> Loading…</> : <>{isDone ? 'See Final Results' : 'Continue'} <FaArrowRight /></>}
              </button>
            </motion.div>
          )}

          {phase === 'choice' && round && (
            <motion.div key={`round-${roundIndex}`} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="bg-white rounded-2xl shadow-md p-6">
              <div className="flex items-center gap-2 mb-2" style={{ color: colors.textLight }}>
                <FaGamepad />
                <span className="text-xs font-bold uppercase tracking-wide">{round.setting || game.theme}</span>
              </div>
              <h2 className="text-xl font-bold mb-2" style={{ color: colors.text }}>{round.title}</h2>

              {/* `situation` is the meaty scene-setting text several games
                  author (e.g. my-ward-my-responsibility.json,
                  pro-difficult-1on1.json) alongside a much shorter `story`
                  aside/moral. When both exist, `situation` takes the main
                  narrative box and `story` becomes a smaller aside — when
                  only `story` exists (the majority of games), it keeps its
                  original full-weight box treatment. */}
              {round.situation && (
                <div className="rounded-xl p-4 mb-3" style={{ backgroundColor: '#F5F4EF' }}>
                  <p className="text-sm whitespace-pre-line leading-relaxed" style={{ color: colors.text }}>{textBody(round.situation)}</p>
                </div>
              )}

              {round.story && (
                round.situation ? (
                  <p className="text-sm italic mb-3" style={{ color: colors.textLight }}>{textBody(round.story)}</p>
                ) : (
                  <div className="rounded-xl p-4 mb-3" style={{ backgroundColor: '#F5F4EF' }}>
                    <p className="text-sm whitespace-pre-line leading-relaxed" style={{ color: colors.text }}>{textBody(round.story)}</p>
                  </div>
                )
              )}

              {round.goal && <p className="text-sm font-semibold mb-3" style={{ color: colors.text }}>{textBody(round.goal)}</p>}

              <DecisionDataPanel data={round.decision_data} />

              {round.coaching_moment && (
                <div className="flex gap-2 items-start text-xs mb-4 px-3 py-2 rounded-lg" style={{ backgroundColor: colors.primaryLight + '40', color: colors.text }}>
                  <FaLightbulb className="flex-shrink-0 mt-0.5" style={{ color: colors.primaryDark }} />
                  <div>
                    {textTitle(round.coaching_moment) && <div className="font-bold mb-0.5">{textTitle(round.coaching_moment)}</div>}
                    {textBody(round.coaching_moment)}
                  </div>
                </div>
              )}

              <div className="flex flex-col gap-3">
                {(round.choices || []).map((c, idx) => (
                  <motion.button
                    key={c.id}
                    disabled={submitting}
                    onClick={() => handleChoice(c)}
                    whileHover={{ scale: submitting ? 1 : 1.01 }}
                    whileTap={{ scale: submitting ? 1 : 0.99 }}
                    className="text-left p-4 rounded-xl border-2 border-gray-100 hover:border-current disabled:opacity-60 transition-colors"
                    style={{ color: colors.purple }}
                  >
                    <div className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: colors.purple }}>
                        {String.fromCharCode(65 + idx)}
                      </span>
                      <div className="flex-1">
                        <div className="font-bold" style={{ color: colors.text }}>{c.label}</div>
                        {c.description && <div className="text-sm mt-0.5" style={{ color: colors.textLight }}>{c.description}</div>}
                        {c.consequence_hint && (
                          <div className="text-xs italic mt-1" style={{ color: colors.textLight }}>
                            💭 {c.consequence_hint}
                          </div>
                        )}
                        <ImpactPreview delta={c.delta} />
                      </div>
                    </div>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
