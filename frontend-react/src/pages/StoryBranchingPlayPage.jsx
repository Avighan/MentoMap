/**
 * StoryBranchingPlayPage — play screen for `story_branching` games (12 of
 * them; city-mayor, the-treaty, kids-kindness-quest, etc). These are
 * structured as chapters -> scenes -> choices with an explicit `next_scene`
 * pointer per choice (a real branching graph, not a fixed round sequence),
 * played through a different backend contract than the "rounds" games
 * AdventureGamePlayPage handles:
 *
 *   POST /api/run/start                              -> { run_id, game_data, state }
 *     game_data.story_intro.scenes[] is the full scene graph (all chapters,
 *     flattened); game_data.chapters[] is just the chapter index (id/title/
 *     icon/teaser) used for the roadmap and progress display.
 *   POST /api/run/<id>/branching-choice { scene_id, choice_id }
 *     -> { next_scene, is_ending, ending_type, ending_message,
 *          next_chapter, chapter_reward, expert_pick,
 *          counterfactual_for_chosen, state }
 *     `next_scene` is null exactly when a chapter ends (chapter_reward is
 *     set and next_chapter names the chapter to continue into — its first
 *     scene is looked up client-side from story_intro.scenes) or when
 *     is_ending is true (run is over, fetch /report same as other games).
 *
 * Narrative/teaser text uses a literal "{player_name}" placeholder the
 * backend does not substitute (unlike the "{{var}}" style used elsewhere
 * — see PilotGamePlayPage/AdventureGamePlayPage) — substituted client-side
 * with the logged-in username.
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  FaArrowLeft, FaArrowRight, FaSpinner, FaExclamationTriangle, FaTrophy,
  FaLightbulb, FaQuoteLeft, FaGraduationCap, FaStar, FaMedal, FaChartLine,
  FaBook, FaGift, FaMapMarkedAlt,
} from 'react-icons/fa';
import { startGame, submitBranchingChoice, endGame } from '../api/games';
import { useAuth } from '../contexts/AuthContext';
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

function sub(text, username) {
  if (typeof text !== 'string') return text;
  return text.replace(/\{player_name\}/g, username || 'you');
}

function fmtNum(n) {
  if (typeof n !== 'number') return n;
  if (Math.abs(n) >= 1000) return n.toLocaleString('en-IN');
  return Math.round(n * 10) / 10;
}

function kpiLabel(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function TopBar({ title, icon, onBack }) {
  return (
    <div className="sticky top-0 z-20 bg-white/90 backdrop-blur-sm border-b shadow-sm">
      <div className="max-w-3xl mx-auto px-4 py-2.5 flex items-center gap-3">
        <button onClick={onBack} className="flex items-center justify-center w-9 h-9 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0" aria-label="Back to games">
          <FaArrowLeft style={{ color: colors.text }} />
        </button>
        <span className="text-2xl">{icon || '📖'}</span>
        <h1 className="text-lg font-bold truncate" style={{ color: colors.text }}>{title}</h1>
      </div>
    </div>
  );
}

function ChapterProgressBar({ chapters, currentChapterId }) {
  const idx = Math.max(0, chapters.findIndex((c) => c.chapter_id === currentChapterId));
  const pct = chapters.length ? Math.round(((idx + 1) / chapters.length) * 100) : 0;
  return (
    <div className="max-w-3xl mx-auto px-4 pt-4">
      <div className="flex justify-between text-xs font-semibold mb-1" style={{ color: colors.textLight }}>
        <span>Chapter {idx + 1} of {chapters.length}{chapters[idx] ? ` — ${chapters[idx].title}` : ''}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
        <motion.div className="h-full rounded-full" style={{ backgroundColor: colors.primary }} initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.4 }} />
      </div>
    </div>
  );
}

export default function StoryBranchingPlayPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const username = user?.username;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState(null);
  const [game, setGame] = useState(null);
  const [showBriefing, setShowBriefing] = useState(true);
  const [scene, setScene] = useState(null);
  const [state, setState] = useState(null);
  const [prevState, setPrevState] = useState(null);
  const [phase, setPhase] = useState('scene'); // 'scene' | 'outcome' | 'chapter_complete' | 'ending' | 'complete'
  const [pendingOutcome, setPendingOutcome] = useState(null);
  const [chapterReward, setChapterReward] = useState(null);
  const [endingInfo, setEndingInfo] = useState(null);
  const [report, setReport] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    startGame(gameId)
      .then((data) => {
        if (cancelled) return;
        setRunId(data.run_id);
        setGame(data.game_data);
        const scenes = data.game_data?.story_intro?.scenes || [];
        setScene(scenes[0] || null);
        setState(data.state || data.game_data?.initial_state || null);
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

  const chapters = game.chapters || [];
  const scenesById = (game.story_intro?.scenes || []);

  const handleChoice = async (choice) => {
    setSubmitting(true);
    setError('');
    const currentScene = scene;
    try {
      const res = await submitBranchingChoice(runId, currentScene.scene_id, choice.id);
      setPrevState(state);
      setState(res.state);
      // expert_pick is a full {choice_id, reason} object in some games but
      // just the winning choice_id as a bare string in others (see the
      // same inconsistency in AdventureGamePlayPage's games) — resolve the
      // string form against the scene just answered.
      let expertPick = res.expert_pick;
      if (typeof expertPick === 'string') {
        const pick = (currentScene.choices || []).find((c) => c.id === expertPick);
        expertPick = pick ? { choice_id: pick.id, reason: pick.expert_rationale || `An expert would choose: "${pick.label}"` } : null;
      }
      setPendingOutcome({
        deltas: choice.delta || {},
        consequence_hint: choice.consequence_hint,
        expert_pick: expertPick,
        counterfactual: res.counterfactual_for_chosen,
      });

      if (res.is_ending) {
        setEndingInfo({ type: res.ending_type, message: res.ending_message });
        setPhase('ending');
      } else if (res.next_scene) {
        setScene(res.next_scene);
        setPhase('outcome');
      } else if (res.next_chapter) {
        setChapterReward({ ...res.chapter_reward, nextChapter: res.next_chapter });
        setPhase('chapter_complete');
      } else {
        // No next scene, no next chapter, not flagged as ending — treat as
        // the run being over rather than getting stuck on a dead screen.
        setEndingInfo({ type: 'complete', message: '' });
        setPhase('ending');
      }
    } catch (err) {
      setError(err?.response?.data?.error || 'Choice failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleContinueFromOutcome = () => setPhase('scene');

  const handleContinueFromChapter = () => {
    const next = scenesById.find((s) => s.chapter === chapterReward.nextChapter);
    setScene(next || null);
    setChapterReward(null);
    setPhase(next ? 'scene' : 'ending');
    if (!next) setEndingInfo({ type: 'complete', message: '' });
  };

  const handleContinueFromEnding = async () => {
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
  };

  // ---------- Briefing screen ----------
  if (showBriefing) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ backgroundColor: colors.background }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl shadow-2xl overflow-hidden max-w-2xl w-full bg-white">
          <div className="h-40 relative flex flex-col justify-end p-6" style={{ background: `linear-gradient(135deg, ${colors.purple}, ${colors.teal})` }}>
            <span className="self-start mb-2 text-[11px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full text-white bg-black/20">
              {game.icon ? `${game.icon} ` : ''}{game.theme || 'Story'}
            </span>
            <h1 className="text-2xl font-extrabold text-white drop-shadow-lg leading-tight">{game.title}</h1>
          </div>

          <div className="p-7 max-h-[65vh] overflow-y-auto">
            <p className="text-sm leading-relaxed mb-4" style={{ color: colors.text }}>{sub(game.description, username)}</p>

            {game.coaching_moment && (
              <div className="flex gap-3 p-4 rounded-xl mb-5" style={{ backgroundColor: colors.primaryLight + '40' }}>
                <FaQuoteLeft className="flex-shrink-0 mt-0.5" style={{ color: colors.primaryDark }} />
                <p className="text-sm italic font-medium" style={{ color: colors.text }}>{sub(game.coaching_moment, username)}</p>
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
              {chapters.length > 0 && (
                <div className="rounded-lg px-3 py-2 bg-gray-50 text-center">
                  <div className="text-[10px] font-bold uppercase" style={{ color: colors.textLight }}>Chapters</div>
                  <div className="text-sm font-bold" style={{ color: colors.text }}>{chapters.length}</div>
                </div>
              )}
            </div>

            {chapters.length > 0 && (
              <div className="mb-6">
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
                  <FaMapMarkedAlt /> Your Journey
                </div>
                <div className="space-y-1.5">
                  {chapters.map((c, i) => (
                    <div key={c.chapter_id} className="flex items-start gap-2.5 text-sm">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full text-white text-xs font-bold flex items-center justify-center mt-0.5" style={{ backgroundColor: c.color || colors.purple }}>
                        {i + 1}
                      </span>
                      <div>
                        <span className="font-semibold" style={{ color: colors.text }}>{c.icon} {c.title}</span>
                        {c.teaser && <span style={{ color: colors.textLight }}> — {sub(c.teaser, username)}</span>}
                      </div>
                    </div>
                  ))}
                </div>
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
              className="w-full py-3.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg"
              style={{ backgroundColor: colors.primary, color: colors.text }}
            >
              Begin Story <FaArrowRight />
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
              <h1 className="text-xl font-bold" style={{ color: colors.text }}>Story Complete!</h1>
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
                      <span>{d.label}</span>
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

  // ---------- Scene / outcome / chapter-complete / ending screen ----------
  return (
    <div className="min-h-screen pb-16" style={{ backgroundColor: colors.background }}>
      <TopBar title={game.title} icon={game.icon} onBack={() => navigate('/games')} />
      <ChapterProgressBar chapters={chapters} currentChapterId={scene?.chapter} />

      <div className="max-w-3xl mx-auto px-4 mt-6">
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm flex items-center gap-2">
            <FaExclamationTriangle /> {error}
          </div>
        )}

        <AnimatePresence mode="wait">
          {phase === 'outcome' && pendingOutcome && (
            <motion.div key="outcome" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl shadow-md p-6">
              <div className="text-xs font-bold uppercase tracking-wide mb-3" style={{ color: colors.textLight }}>What Happened</div>

              {Object.keys(pendingOutcome.deltas).length > 0 && (
                <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5 mb-4">
                  {Object.entries(pendingOutcome.deltas).filter(([, v]) => v !== 0).map(([key, val]) => (
                    <li key={key} className="flex justify-between text-sm">
                      <span style={{ color: colors.textLight }}>{kpiLabel(key)}</span>
                      <span className="font-bold" style={{ color: val > 0 ? colors.green : colors.red }}>{val > 0 ? '+' : ''}{fmtNum(val)}</span>
                    </li>
                  ))}
                </ul>
              )}

              {pendingOutcome.expert_pick?.reason && (
                <div className="mb-4 rounded-xl p-4 border-l-4" style={{ borderColor: colors.teal, backgroundColor: colors.teal + '0D' }}>
                  <div className="flex items-center gap-1.5 text-sm font-extrabold mb-1" style={{ color: colors.text }}>
                    <FaGraduationCap style={{ color: colors.teal }} /> What an expert would do
                  </div>
                  <p className="text-xs" style={{ color: colors.textLight }}>{pendingOutcome.expert_pick.reason}</p>
                </div>
              )}

              {pendingOutcome.counterfactual && (
                <div className="mb-4 rounded-xl p-4 border-l-4" style={{ borderColor: colors.purple, backgroundColor: colors.purple + '0D' }}>
                  <div className="flex items-center gap-1.5 text-sm font-extrabold mb-1" style={{ color: colors.text }}>
                    <FaLightbulb style={{ color: colors.purple }} /> If you'd chosen differently
                  </div>
                  <p className="text-xs leading-relaxed" style={{ color: colors.textLight }}>{pendingOutcome.counterfactual}</p>
                </div>
              )}

              <button onClick={handleContinueFromOutcome} className="w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
                Continue the Story <FaArrowRight />
              </button>
            </motion.div>
          )}

          {phase === 'chapter_complete' && chapterReward && (
            <motion.div key="chapter" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl shadow-md p-6 text-center">
              <FaGift className="text-3xl mx-auto mb-3" style={{ color: colors.primaryDark }} />
              <h2 className="text-lg font-bold mb-1" style={{ color: colors.text }}>Chapter Complete!</h2>
              <div className="flex items-center justify-center gap-3 my-4 flex-wrap">
                {typeof chapterReward.coins_earned === 'number' && (
                  <span className="text-sm font-bold px-3 py-1.5 rounded-full" style={{ backgroundColor: colors.primaryLight, color: colors.text }}>+{chapterReward.coins_earned} coins</span>
                )}
                {typeof chapterReward.xp_earned === 'number' && (
                  <span className="text-sm font-bold px-3 py-1.5 rounded-full" style={{ backgroundColor: colors.teal + '20', color: colors.teal }}>+{chapterReward.xp_earned} XP</span>
                )}
              </div>
              <button onClick={handleContinueFromChapter} className="w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
                Next Chapter <FaArrowRight />
              </button>
            </motion.div>
          )}

          {phase === 'ending' && endingInfo && (
            <motion.div key="ending" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl shadow-md p-6 text-center">
              <FaBook className="text-3xl mx-auto mb-3" style={{ color: colors.purple }} />
              <h2 className="text-lg font-bold mb-2" style={{ color: colors.text }}>{endingInfo.type ? `Ending: ${endingInfo.type}` : 'The End'}</h2>
              {endingInfo.message && <p className="text-sm mb-4" style={{ color: colors.textLight }}>{sub(endingInfo.message, username)}</p>}
              <button onClick={handleContinueFromEnding} disabled={submitting} className="w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg disabled:opacity-60" style={{ backgroundColor: colors.primary, color: colors.text }}>
                {submitting ? <><FaSpinner className="animate-spin" /> Loading…</> : <>See Final Results <FaArrowRight /></>}
              </button>
            </motion.div>
          )}

          {phase === 'scene' && scene && (
            <motion.div key={`scene-${scene.scene_id}`} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="bg-white rounded-2xl shadow-md p-6">
              <h2 className="text-xl font-bold mb-3" style={{ color: colors.text }}>{scene.title}</h2>

              <div className="rounded-xl p-4 mb-3" style={{ backgroundColor: '#F5F4EF' }}>
                <p className="text-sm whitespace-pre-line leading-relaxed" style={{ color: colors.text }}>{sub(scene.narrative || scene.text, username)}</p>
              </div>

              {scene.coaching_moment && (
                <div className="flex gap-2 items-start text-xs mb-4 px-3 py-2 rounded-lg" style={{ backgroundColor: colors.primaryLight + '40', color: colors.text }}>
                  <FaLightbulb className="flex-shrink-0 mt-0.5" style={{ color: colors.primaryDark }} />
                  {sub(scene.coaching_moment, username)}
                </div>
              )}

              <div className="flex flex-col gap-3">
                {(scene.choices || []).map((c, idx) => (
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
                        {c.consequence_hint && <div className="text-xs mt-1 italic" style={{ color: colors.textLight }}>{c.consequence_hint}</div>}
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
