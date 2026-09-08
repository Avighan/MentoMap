/**
 * AiLabPlayPage — play screen for `ai_lab` games (currently just
 * "ai-prompt-lab-school"). Each task shows a bad example prompt and why it
 * fails, then the student writes their own prompt; the backend runs it
 * through a real LLM call (or a heuristic fallback when no LLM is
 * configured — see backend/app.py's _ai_lab_call_model/_ai_lab_grade) and
 * a coach grades it 0-10 against a rubric, up to 5 attempts per task.
 *
 *   GET  /api/run/<id>/ai-lab/state           -> { ai_lab_config, state }
 *   POST /api/run/<id>/ai-lab/prompt {task_id, prompt}
 *     -> { attempt: {prompt, output, score, feedback}, best_score,
 *          attempts_remaining, task_completed, pass_threshold, all_tasks_complete }
 *   POST /api/run/<id>/ai-lab/advance          -> { current_task_index }
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FaArrowLeft, FaArrowRight, FaSpinner, FaExclamationTriangle, FaTrophy,
  FaLightbulb, FaTimesCircle, FaCheckCircle, FaRobot, FaStar, FaChartLine,
} from 'react-icons/fa';
import { startGame, getAiLabState, submitAiLabPrompt, advanceAiLab, endGame } from '../api/games';
import { LoadingState } from '../components/ui/LoadingSpinner';
import RobotGuide from '../assets/robo.png';

const colors = {
  primary: '#FFD166', primaryLight: '#FFE8A5', primaryDark: '#FFC145',
  background: '#FFFDF7', card: '#FFFFFF', text: '#2D3047', textLight: '#6D7286',
  purple: '#6C5CE7', teal: '#4ECDC4', green: '#1E8A5A', red: '#C0392B',
};

function TopBar({ title, icon, onBack }) {
  return (
    <div className="sticky top-0 z-20 bg-white/90 backdrop-blur-sm border-b shadow-sm">
      <div className="max-w-3xl mx-auto px-4 py-2.5 flex items-center gap-3">
        <button onClick={onBack} className="flex items-center justify-center w-9 h-9 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0" aria-label="Back to games">
          <FaArrowLeft style={{ color: colors.text }} />
        </button>
        <span className="text-2xl">{icon || '🤖'}</span>
        <h1 className="text-lg font-bold truncate" style={{ color: colors.text }}>{title}</h1>
      </div>
    </div>
  );
}

export default function AiLabPlayPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState(null);
  const [game, setGame] = useState(null);
  const [config, setConfig] = useState(null);
  const [labState, setLabState] = useState(null);
  const [showBriefing, setShowBriefing] = useState(true);
  const [promptText, setPromptText] = useState('');
  const [attempt, setAttempt] = useState(null);
  const [attemptMeta, setAttemptMeta] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [report, setReport] = useState(null);
  const [finalizing, setFinalizing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    startGame(gameId)
      .then(async (data) => {
        if (cancelled) return;
        setRunId(data.run_id);
        setGame(data.game_data);
        const st = await getAiLabState(data.run_id);
        if (cancelled) return;
        setConfig(st.ai_lab_config);
        setLabState(st.state);
      })
      .catch((err) => !cancelled && setError(err?.response?.data?.error || 'Could not start this game.'))
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

  const tasks = config?.tasks || [];
  const taskIndex = Math.min(labState?.current_task_index ?? 0, tasks.length - 1);
  const task = tasks[taskIndex];

  const handleSubmit = async () => {
    if (!promptText.trim()) return;
    setSubmitting(true);
    setError('');
    try {
      const res = await submitAiLabPrompt(runId, task.id, promptText.trim());
      setAttempt(res.attempt);
      setAttemptMeta(res);
    } catch (err) {
      setError(err?.response?.data?.error || 'Could not grade that prompt.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextTask = async () => {
    setSubmitting(true);
    try {
      await advanceAiLab(runId);
      setLabState((s) => ({ ...s, current_task_index: Math.min(tasks.length - 1, taskIndex + 1) }));
      setAttempt(null);
      setAttemptMeta(null);
      setPromptText('');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSeeResults = async () => {
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

  // ---------- Briefing ----------
  if (showBriefing) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ backgroundColor: colors.background }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl shadow-2xl overflow-hidden max-w-2xl w-full bg-white">
          <div className="h-40 relative flex flex-col justify-end p-6" style={{ background: `linear-gradient(135deg, ${colors.purple}, ${colors.teal})` }}>
            <span className="self-start mb-2 text-[11px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full text-white bg-black/20">
              {game.icon ? `${game.icon} ` : ''}AI Literacy
            </span>
            <h1 className="text-2xl font-extrabold text-white drop-shadow-lg leading-tight">{game.title}</h1>
          </div>
          <div className="p-7">
            <p className="text-sm leading-relaxed mb-4" style={{ color: colors.text }}>{game.description}</p>
            {config?.intro && (
              <div className="flex gap-3 p-4 rounded-xl mb-5" style={{ backgroundColor: colors.primaryLight + '40' }}>
                <FaRobot className="flex-shrink-0 mt-0.5" style={{ color: colors.primaryDark }} />
                <p className="text-sm font-medium" style={{ color: colors.text }}>{config.intro}</p>
              </div>
            )}
            <div className="mb-6">
              <div className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>Tasks</div>
              <div className="space-y-1.5">
                {tasks.map((t, i) => (
                  <div key={t.id} className="flex items-center gap-2.5 text-sm">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full text-white text-xs font-bold flex items-center justify-center" style={{ backgroundColor: colors.purple }}>{i + 1}</span>
                    <span className="font-semibold" style={{ color: colors.text }}>{t.title}</span>
                  </div>
                ))}
              </div>
            </div>
            <button onClick={() => setShowBriefing(false)} className="w-full py-3.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
              Begin <FaArrowRight />
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  if (finalizing) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ backgroundColor: colors.background }}>
        <FaSpinner className="animate-spin text-3xl" style={{ color: colors.purple }} />
        <LoadingState label="Grading your work…" />
      </div>
    );
  }

  // ---------- Final score screen ----------
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
              <h1 className="text-xl font-bold" style={{ color: colors.text }}>Lab Complete!</h1>
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

  if (!task) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: colors.background }}>
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md text-center">
          <p className="text-gray-700 mb-4">No tasks configured for this lab.</p>
          <button onClick={() => navigate('/games')} className="px-4 py-2 rounded-lg font-bold shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>Back to games</button>
        </div>
      </div>
    );
  }

  const passed = attemptMeta?.task_completed;
  const attemptsLeft = attemptMeta?.attempts_remaining ?? 5;

  return (
    <div className="min-h-screen pb-16" style={{ backgroundColor: colors.background }}>
      <TopBar title={game.title} icon={game.icon} onBack={() => navigate('/games')} />
      <div className="max-w-3xl mx-auto px-4 mt-6">
        <div className="flex justify-between text-xs font-semibold mb-4" style={{ color: colors.textLight }}>
          <span>Task {taskIndex + 1} of {tasks.length}</span>
          <span>{Math.round(((taskIndex + (passed ? 1 : 0)) / tasks.length) * 100)}%</span>
        </div>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm flex items-center gap-2">
            <FaExclamationTriangle /> {error}
          </div>
        )}

        <motion.div key={task.id} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="bg-white rounded-2xl shadow-md p-6">
          <h2 className="text-xl font-bold mb-2" style={{ color: colors.text }}>{task.title}</h2>
          <p className="text-sm mb-4" style={{ color: colors.text }}>{task.scenario}</p>

          <div className="rounded-xl p-4 mb-3 border-l-4" style={{ borderColor: colors.red, backgroundColor: colors.red + '0D' }}>
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-1" style={{ color: colors.red }}>
              <FaTimesCircle /> Bad Prompt Example
            </div>
            <p className="text-sm italic mb-1.5" style={{ color: colors.text }}>"{task.bad_example}"</p>
            <p className="text-xs" style={{ color: colors.textLight }}>{task.why_bad}</p>
          </div>

          <div className="rounded-xl p-4 mb-4" style={{ backgroundColor: colors.primaryLight + '40' }}>
            <div className="text-xs font-bold uppercase tracking-wide mb-1" style={{ color: colors.textLight }}>Your Goal</div>
            <p className="text-sm" style={{ color: colors.text }}>{task.goal}</p>
          </div>

          {task.hints?.length > 0 && (
            <div className="mb-4">
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide mb-2" style={{ color: colors.textLight }}>
                <FaLightbulb style={{ color: colors.primaryDark }} /> Hints
              </div>
              <ul className="space-y-1">
                {task.hints.map((h, i) => (
                  <li key={i} className="text-xs flex gap-2" style={{ color: colors.textLight }}><span>•</span>{h}</li>
                ))}
              </ul>
            </div>
          )}

          <textarea
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            disabled={submitting || passed}
            placeholder="Write your prompt here…"
            rows={4}
            className="w-full rounded-xl border-2 border-gray-200 p-3 text-sm mb-3 focus:outline-none focus:border-current disabled:bg-gray-50"
            style={{ color: colors.text }}
          />

          {!passed && (
            <button
              onClick={handleSubmit}
              disabled={submitting || !promptText.trim() || attemptsLeft <= 0}
              className="w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg disabled:opacity-60"
              style={{ backgroundColor: colors.primary, color: colors.text }}
            >
              {submitting ? <><FaSpinner className="animate-spin" /> Running your prompt…</> : <>Run This Prompt</>}
            </button>
          )}

          {attempt && (
            <div className="mt-5 rounded-xl p-4" style={{ backgroundColor: '#F5F4EF' }}>
              <div className="flex items-center gap-2 mb-2">
                <FaRobot style={{ color: colors.purple }} />
                <span className="text-xs font-bold uppercase tracking-wide" style={{ color: colors.textLight }}>AI Output</span>
              </div>
              <p className="text-sm whitespace-pre-line leading-relaxed mb-3" style={{ color: colors.text }}>{attempt.output}</p>
              <div className="flex items-center gap-2 mb-2">
                {passed ? <FaCheckCircle style={{ color: colors.green }} /> : <FaTimesCircle style={{ color: colors.red }} />}
                <span className="font-bold text-sm" style={{ color: passed ? colors.green : colors.red }}>Score: {attempt.score}/10</span>
                {!passed && <span className="text-xs" style={{ color: colors.textLight }}>({attemptsLeft} attempts left)</span>}
              </div>
              <p className="text-xs" style={{ color: colors.textLight }}>{attempt.feedback}</p>
            </div>
          )}

          {passed && (
            <button onClick={attemptMeta.all_tasks_complete ? handleSeeResults : handleNextTask} className="w-full mt-4 py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg" style={{ backgroundColor: colors.primary, color: colors.text }}>
              {attemptMeta.all_tasks_complete ? 'See Final Results' : 'Next Task'} <FaArrowRight />
            </button>
          )}
          {!passed && attemptsLeft <= 0 && (
            <button onClick={attemptMeta?.all_tasks_complete ? handleSeeResults : handleNextTask} className="w-full mt-4 py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg" style={{ backgroundColor: colors.textLight, color: 'white' }}>
              Out of attempts — Move On <FaArrowRight />
            </button>
          )}
        </motion.div>
      </div>
    </div>
  );
}
