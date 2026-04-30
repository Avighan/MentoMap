import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaLightbulb, FaArrowUp, FaStar, FaBolt, FaChevronDown, FaChevronUp, FaGraduationCap, FaChartPie, FaCommentDots, FaHandsHelping, FaBullseye, FaHistory, FaPlay, FaChevronRight, FaTrophy, FaClipboardList } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import SkillDashboard from './SkillDashboard';
import SkillDefinition from './SkillDefinition';
import { getTransferExercises } from '../../api/profile';
import { getAssessmentReport } from '../../api/games';
import { useAuth } from '../../contexts/AuthContext';
import AssessmentReport from './AssessmentReport';
import { useOrg } from '../../contexts/OrgContext';
import PostGameChallenge from './PostGameChallenge';
import DimBreakdown from './v2/DimBreakdown';
import ShareCard from './v2/ShareCard';
import { getV2ShareCard, completeV2Run } from '../../api/v2';
import ExecPostGameSummary from './exec/ExecPostGameSummary';

const _DEFAULT_DIM_LABELS = {
  strategic_thinking: 'Strategic Thinking',
  risk_tolerance: 'Risk Tolerance',
  delayed_gratification: 'Delayed Gratification',
  adaptability: 'Adaptability',
  resilience: 'Resilience',
  empathy: 'Empathy',
  ethical_reasoning: 'Ethical Reasoning',
  creativity: 'Creativity',
  // Executive-tier dimensions (org-level custom_dimensions can override)
  capital_allocation: 'Capital Allocation',
  vision_setting: 'Vision Setting',
  governance_judgment: 'Governance Judgment',
  talent_strategy: 'Talent Strategy',
  commercial_acumen: 'Commercial Acumen',
  systems_thinking: 'Systems Thinking',
  narrative_persuasion: 'Narrative Persuasion',
  decision_quality: 'Decision Quality',
};
// _DIM_LABELS will be set per-component via useOrg() — see useDimLabels() hook below
const _DIM_ICONS = {
  strategic_thinking: '🧠', risk_tolerance: '⚡', delayed_gratification: '⏳',
  adaptability: '🔄', resilience: '💪', empathy: '❤️',
  ethical_reasoning: '⚖️', creativity: '🎨',
  capital_allocation: '💰', vision_setting: '🧭', governance_judgment: '🏛️',
  talent_strategy: '👥', commercial_acumen: '📈', systems_thinking: '🕸️',
  narrative_persuasion: '🎙️', decision_quality: '🎯',
};
// ── CASEL / Goleman framework mappings ───────────────────────────────────
const CASEL_MAP = {
  strategic_thinking:    { casel: 'Responsible Decision-Making', goleman: 'Self-Management' },
  risk_tolerance:        { casel: 'Responsible Decision-Making', goleman: 'Self-Management' },
  delayed_gratification: { casel: 'Self-Management',             goleman: 'Self-Regulation' },
  adaptability:          { casel: 'Self-Management',             goleman: 'Adaptability' },
  resilience:            { casel: 'Self-Management',             goleman: 'Emotional Self-Control' },
  empathy:               { casel: 'Social Awareness',            goleman: 'Empathy' },
  ethical_reasoning:     { casel: 'Responsible Decision-Making', goleman: 'Trustworthiness' },
  creativity:            { casel: 'Responsible Decision-Making', goleman: 'Achievement Orientation' },
  // Exec dimensions map to executive frameworks rather than CASEL
  capital_allocation:    { framework: 'CFO Framework',          theorist: 'Buffett / Damodaran' },
  vision_setting:        { framework: 'Strategic Leadership',    theorist: 'Kouzes & Posner' },
  governance_judgment:   { framework: 'Board Governance',        theorist: 'Cadbury / OECD' },
  talent_strategy:       { framework: 'Strategic HR',            theorist: 'Ulrich' },
  commercial_acumen:     { framework: 'Business Acumen',         theorist: 'Drucker' },
  systems_thinking:      { framework: 'Systems Theory',          theorist: 'Senge / Meadows' },
  narrative_persuasion:  { framework: 'Strategic Communication',  theorist: 'Heath / Duarte' },
  decision_quality:      { framework: 'Decision Analysis',       theorist: 'Howard / Kahneman' },
};

// ── Mastery tier color helpers ────────────────────────────────────────────
const _TIER_COLORS = {
  expert:     { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-200' },
  advanced:   { bg: 'bg-blue-100',   text: 'text-blue-700',   border: 'border-blue-200' },
  proficient: { bg: 'bg-green-100',  text: 'text-green-700',  border: 'border-green-200' },
  developing: { bg: 'bg-amber-100',  text: 'text-amber-700',  border: 'border-amber-200' },
  beginner:   { bg: 'bg-gray-100',   text: 'text-gray-600',   border: 'border-gray-200' },
};

// ── Decision style icons ──────────────────────────────────────────────────
const _DECISION_STYLE_ICONS = {
  'Quick Decider':       '⚡',
  'Balanced Thinker':    '🧠',
  'Careful Deliberator': '🔍',
};

// ── SurpriseRewardBanner sub-component ───────────────────────────────────
function SurpriseRewardBanner({ reward }) {
  return (
    <motion.div
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 260, damping: 20 }}
      className="rounded-xl overflow-hidden border border-yellow-300"
      style={{ background: 'linear-gradient(135deg, #FFF9C4 0%, #FFD700 50%, #FFA500 100%)' }}
    >
      <div className="p-4 flex flex-col items-center text-center gap-2">
        <div className="text-4xl">{reward.icon || '🎁'}</div>
        <p className="text-xs font-black text-yellow-900 uppercase tracking-wider">🎉 Surprise Unlocked!</p>
        <p className="text-base font-bold text-yellow-900">{reward.title}</p>
        {reward.description && (
          <p className="text-[11px] text-yellow-800 leading-relaxed">{reward.description}</p>
        )}
      </div>
    </motion.div>
  );
}

const _WEAK_TIPS = {
  strategic_thinking: ['Before choosing, ask: "What happens 2 steps after this decision?"', 'Think about resources as tools — not just numbers to protect.', 'Plan backwards: what do you need to reach the final goal?'],
  risk_tolerance: ['Low-risk choices feel safer, but limit growth. Try one bold move per game.', 'Calculate the worst case. If you can recover, the risk may be worth it.', 'Bold choices build risk tolerance — what option tests your confidence?'],
  delayed_gratification: ['Investing in team, quality, or training now pays dividends later.', 'Skip the quick win — ask "which choice makes me stronger in 3 rounds?"', 'Patience is a skill. Resist the option that gives something immediately.'],
  adaptability: ['Unexpected events reward flexible thinkers. How many ways can you respond?', 'Try the option you normally wouldn\'t. Adaptability grows through discomfort.', 'When conditions change, revisit your plan — flexibility wins over rigidity.'],
  resilience: ['Stress and setbacks are part of the game. Pick choices that keep your team stable.', 'Ask: "Which choice keeps us in the game even if something goes wrong?"', 'Resilience = bouncing back. After a bad round, steady choices rebuild fast.'],
  empathy: ['Who is affected by your decision? Think about team morale and trust.', 'The most efficient choice isn\'t always the kindest — and kindness builds loyalty.', 'Ask "how would my team feel about this?" before every major decision.'],
  ethical_reasoning: ['Ethical choices build long-term trust even when they\'re costly short-term.', 'Ask: "Would I be comfortable if everyone could see this decision?"', 'Practice articulating why a choice is right, not just what to choose.'],
  creativity: ['Try the unexpected option — creative choices often open new possibilities.', 'Constraints spark creativity. What can you accomplish with limited resources?', 'Combine ideas from different domains — cross-pollination leads to innovation.'],
  capital_allocation: ['Where does each rupee earn its highest return? Compare opportunity cost across uses.', 'Reinvest, return, or reserve — every cash decision is one of these three.', 'Track ROIC and payback together. Headline returns can hide slow-payback traps.'],
  vision_setting: ['Articulate a 3-year picture that is concrete enough to disagree with.', 'Vision without trade-offs is wishful. Name what you will NOT do.', 'Repeat the vision until it bores you — that\'s when the team starts living it.'],
  governance_judgment: ['Separate operating decisions from board-level decisions. Don\'t blur the lines.', 'Document conflicts of interest before they document you.', 'Boards govern through process — disclose, deliberate, decide on the record.'],
  talent_strategy: ['Hire for the next 18 months, not just the next 18 weeks.', 'A-players want A-team peers. Compromise on a hire and you cap the team.', 'Performance + values is the matrix — manage to both, not just output.'],
  commercial_acumen: ['Unit economics first, growth second. Bad math at scale is bankruptcy.', 'Pricing is positioning. Cheap signals cheap; premium requires proof.', 'Read the P&L like a story — what\'s the protagonist line item this quarter?'],
  systems_thinking: ['Look for feedback loops, not just cause-effect. What reinforces? What balances?', 'Map second-order effects before deciding. The fix often becomes the next problem.', 'Stocks and flows: what accumulates, what drains? Time-shape matters.'],
  narrative_persuasion: ['Lead with the audience\'s problem, not your solution. Earn the right to be heard.', 'One memorable phrase beats five forgettable ones. Compress until it stings.', 'Story → Data → Story. Numbers persuade when wrapped in a believable arc.'],
  decision_quality: ['Pre-mortem before deciding: imagine it failed — why?', 'Separate the decision from the outcome. Good process can produce bad luck.', 'Calibrate confidence: how sure are you, really? Then check yourself later.'],
};

// ── Transfer Prompt — "Apply Your Learning" ──────────────────────────────

function TransferPromptSection({ gameId }) {
  const [response, setResponse] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!response.trim() || saving) return;
    setSaving(true);
    try {
      await fetch('/api/profile/transfer-prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ game_id: gameId, response }),
      });
    } catch (_e) {
      // fail silently — user intent captured
    } finally {
      setSubmitted(true);
      setSaving(false);
    }
  };

  if (submitted) {
    return (
      <div className="mt-4 bg-green-50 border border-green-200 rounded-xl p-4 text-center">
        <p className="text-green-700 font-semibold text-sm">✓ Great! Applying learning to real life is what makes it stick.</p>
      </div>
    );
  }

  return (
    <div className="mt-4 bg-indigo-50 border border-indigo-100 rounded-xl p-4 space-y-3">
      <div className="flex items-start gap-3">
        <span className="text-xl">🌱</span>
        <div>
          <p className="text-indigo-900 font-semibold text-sm">Apply Your Learning</p>
          <p className="text-indigo-600 text-xs mt-0.5">
            Where will you use what you practised today? Even one real situation counts.
          </p>
        </div>
      </div>
      <textarea
        value={response}
        onChange={e => setResponse(e.target.value)}
        placeholder="e.g. In tomorrow's team meeting, I'll try listening before responding..."
        className="w-full bg-white border border-indigo-200 rounded-lg text-gray-800 placeholder-gray-400 text-sm p-3 resize-none focus:outline-none focus:border-indigo-400"
        rows={3}
        maxLength={500}
      />
      <div className="flex items-center justify-between">
        <span className="text-gray-400 text-xs">{response.length}/500</span>
        <button
          onClick={handleSubmit}
          disabled={!response.trim() || saving}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          {saving ? 'Saving...' : 'Save Reflection'}
        </button>
      </div>
    </div>
  );
}

/**
 * PostGameInsights — Actionable micro-feedback after any game.
 *
 * Enhanced with:
 * - Skill Dashboard (radar chart of soft skill dimensions)
 * - Skill Report (LLM-generated personalized assessment)
 * - Mento Score Breakdown (category-level contributions)
 * - Coach's Debrief (LLM-generated end-of-game analysis)
 *
 * Props:
 *  - summary: game summary object from the complete endpoint
 *  - state: current game state (for fallback data)
 *  - gameType: string game type key
 *  - won: boolean
 *  - reportCore: full report_core from backend (includes dimension_scores, skill_report, mento_breakdown, debrief)
 */
export default function PostGameInsights({ summary, state, gameType, won, reportCore, runId, recommendations = [], mentoPercentile = null, uxExecutive = null, execActionsLog = [], currency = 'USD', epilogueSlot = null }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { customDimensions } = useOrg();
  // Merge org custom dimension labels over defaults
  const _DIM_LABELS = customDimensions
    ? { ..._DEFAULT_DIM_LABELS, ...Object.fromEntries(Object.entries(customDimensions).map(([k, v]) => [k, v.label || v])) }
    : _DEFAULT_DIM_LABELS;
  const insights = summary?.insights || generateInsights(summary, state, gameType, won);
  const dimensionScores = reportCore?.dimension_scores || null;
  const skillReport = reportCore?.skill_report || null;
  const mentoBreakdown = reportCore?.mento_breakdown || null;
  const mentoScore = reportCore?.mento_score || null;
  const debrief = reportCore?.debrief || null;
  const metaDebrief = summary?.meta_debrief || null;
  const chatAnalysis = reportCore?.mento_chat_analysis || null;
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [showChoiceReplay, setShowChoiceReplay] = useState(false);
  const [showAssessment, setShowAssessment] = useState(false);
  const [showFrameworks, setShowFrameworks] = useState(false);
  const [transferDismissed, setTransferDismissed] = useState(false);
  const [showDecisionStyleDesc, setShowDecisionStyleDesc] = useState(false);
  const [transferExercises, setTransferExercises] = useState([]);
  const [prefetchedAssessment, setPrefetchedAssessment] = useState(null);
  const [careerMatches, setCareerMatches] = useState(null);
  const [v2ShareCard, setV2ShareCard] = useState(null);
  const [v2CompleteData, setV2CompleteData] = useState(null);

  const canViewAssessment = user && ['admin', 'teacher', 'school_admin', 'hr'].includes(user.role);

  // Compute weak dimensions for targeted coaching (all known dimensions + graceful fallback for unknowns)
  const weakDimensions = dimensionScores
    ? Object.entries(dimensionScores)
        .sort((a, b) => a[1] - b[1])
        .slice(0, 2)
    : [];

  // Choice history for replay (from summary or state)
  const choiceHistory = summary?.choice_history || state?.choice_history || [];

  // Load transfer exercises
  useEffect(() => {
    if (runId) {
      getTransferExercises(runId).then(data => {
        setTransferExercises(data.exercises || []);
      }).catch(() => {});
    }
  }, [runId]);

  // V2 engine — fetch share card + record completion for legacy rewards
  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    getV2ShareCard(runId)
      .then((data) => {
        if (cancelled || !data?.v2) return;
        setV2ShareCard(data.share_card || null);
      })
      .catch(() => {});
    completeV2Run(runId)
      .then((data) => {
        if (cancelled || !data?.v2) return;
        setV2CompleteData(data);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [runId]);

  // Pre-fetch assessment for teachers/admins so it loads instantly on expand
  useEffect(() => {
    if (canViewAssessment && runId) {
      getAssessmentReport(runId).then(data => setPrefetchedAssessment(data)).catch(() => {});
    }
  }, [canViewAssessment, runId]);

  // Fetch career recommendations based on skill profile
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetch('/api/career/recommendations', { headers: { Authorization: `Bearer ${token}` } })
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setCareerMatches(d.recommendations || d); })
        .catch(() => {});
    }
  }, []);

  const hasInsights = insights && (insights.strengths?.length || insights.improvements?.length || insights.fun_facts?.length);
  const hasAnything = hasInsights || dimensionScores || skillReport || mentoBreakdown || debrief;

  if (!hasAnything && !epilogueSlot) return null;

  return (
    <div className="space-y-3">
      {/* Mystery-room epilogue slot (Task 22) — rendered first so the
          chosen ending leads the post-game review. */}
      {epilogueSlot}

      {/* Scoring warning banner */}
      {reportCore?.scoring_warning && (
        <div className="mb-4 px-4 py-2 bg-amber-50 border border-amber-300 rounded-lg text-amber-800 text-sm">
          ⚠️ {reportCore.scoring_warning}
        </div>
      )}

      {/* Executive performance rollup — only for sim games with simulation_config blocks. */}
      {uxExecutive?.any_executive_subsystem_active && (
        <ExecPostGameSummary uxExecutive={uxExecutive} execActionsLog={execActionsLog} currency={currency} />
      )}

      {/* META-DEBRIEF — what 90-scorers do that you didn't */}
      {metaDebrief && (metaDebrief.deltas?.length > 0 || metaDebrief.what_high_scorers_do?.length > 0) && (
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl border-2 p-5 shadow-md"
          style={{ background: '#FFFBF2', borderColor: '#E0B96A' }}
        >
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-[10px] font-extrabold uppercase tracking-wider opacity-70" style={{ color: '#5B3A1E' }}>
                Cohort comparison
              </div>
              <div className="text-base font-extrabold" style={{ color: '#3A2A0F' }}>
                {metaDebrief.score_band_label || 'Your run vs. the 90th percentile'}
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-extrabold" style={{ color: '#5B3A1E' }}>{metaDebrief.score}</div>
              <div className="text-[10px] opacity-60" style={{ color: '#5B3A1E' }}>
                90+ band: {metaDebrief.threshold_high}
              </div>
            </div>
          </div>

          {Array.isArray(metaDebrief.deltas) && metaDebrief.deltas.length > 0 && (
            <div className="space-y-2 mb-3">
              <div className="text-xs font-bold mb-1" style={{ color: '#5B3A1E' }}>
                Where 90-scorers diverged from you ({metaDebrief.deltas.length})
              </div>
              {metaDebrief.deltas.slice(0, 4).map((d, i) => (
                <div key={i} className="rounded-lg border p-3 bg-white" style={{ borderColor: '#F0DEB8' }}>
                  <div className="text-[11px] uppercase tracking-wider opacity-60 mb-1" style={{ color: '#5B3A1E' }}>
                    {String(d.round_id).replace(/_/g, ' ')}
                  </div>
                  <div className="text-sm">
                    <span className="opacity-60 line-through" style={{ color: '#5B3A1E' }}>
                      {d.your_label || d.your_pick}
                    </span>
                    <span className="mx-2 font-bold" style={{ color: '#D88B5A' }}>→</span>
                    <span className="font-semibold" style={{ color: '#3A6B2F' }}>
                      {d.expert_label || d.expert_pick}
                    </span>
                  </div>
                  <div className="text-xs mt-1.5 leading-snug" style={{ color: '#5B3A1E' }}>
                    {d.lesson}
                  </div>
                </div>
              ))}
            </div>
          )}

          {Array.isArray(metaDebrief.what_high_scorers_do) && metaDebrief.what_high_scorers_do.length > 0 && (
            <div className="rounded-lg p-3" style={{ background: '#F4FBE8', border: '1px solid #C7E0A1' }}>
              <div className="text-[11px] font-extrabold uppercase tracking-wider mb-1.5" style={{ color: '#3A6B2F' }}>
                What 90+ scorers consistently do
              </div>
              <ul className="space-y-1">
                {metaDebrief.what_high_scorers_do.map((s, i) => (
                  <li key={i} className="text-xs leading-snug" style={{ color: '#3A6B2F' }}>
                    <span className="mr-1.5">✓</span>{s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(metaDebrief.your_signature_strength || metaDebrief.your_biggest_gap) && (
            <div className="grid grid-cols-2 gap-2 mt-3">
              {metaDebrief.your_signature_strength && (
                <div className="rounded-lg p-2 text-center" style={{ background: '#EAF6E0' }}>
                  <div className="text-[10px] uppercase tracking-wider opacity-70" style={{ color: '#3A6B2F' }}>Signature</div>
                  <div className="text-xs font-bold" style={{ color: '#3A6B2F' }}>
                    {String(metaDebrief.your_signature_strength).replace(/_/g, ' ')}
                  </div>
                </div>
              )}
              {metaDebrief.your_biggest_gap && (
                <div className="rounded-lg p-2 text-center" style={{ background: '#FBE9DD' }}>
                  <div className="text-[10px] uppercase tracking-wider opacity-70" style={{ color: '#A14D2A' }}>Biggest gap</div>
                  <div className="text-xs font-bold" style={{ color: '#A14D2A' }}>
                    {String(metaDebrief.your_biggest_gap).replace(/_/g, ' ')}
                  </div>
                </div>
              )}
            </div>
          )}
        </motion.div>
      )}

      {/* Feature 5: Surprise Reward Banner */}
      {reportCore?.surprise_reward && (
        <SurpriseRewardBanner reward={reportCore.surprise_reward} />
      )}

      {/* Feature 4: Decision Style Badge */}
      {reportCore?.decision_style && (
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="space-y-1"
        >
          <button
            onClick={() => setShowDecisionStyleDesc(v => !v)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-100 border border-indigo-200 hover:bg-indigo-200 transition-colors"
          >
            <span className="text-base">
              {_DECISION_STYLE_ICONS[reportCore.decision_style] || '🧩'}
            </span>
            <span className="text-xs font-semibold text-indigo-800">{reportCore.decision_style}</span>
            {reportCore.avg_choice_time_ms && (
              <span className="text-[10px] text-indigo-500 ml-1">
                ({(reportCore.avg_choice_time_ms / 1000).toFixed(1)}s avg)
              </span>
            )}
            <span className="text-[10px] text-indigo-400 ml-1">
              {showDecisionStyleDesc ? '▲' : '▼'}
            </span>
          </button>
          <AnimatePresence>
            {showDecisionStyleDesc && reportCore.decision_style_description && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="px-3 py-2 bg-indigo-50 border border-indigo-100 rounded-lg text-[11px] text-indigo-700 leading-relaxed">
                  {reportCore.decision_style_description}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Skill Dashboard — Radar Chart */}
      {dimensionScores && (
        <SkillDashboard dimensions={dimensionScores} title="Your Soft Skill Profile" />
      )}

      {/* V2 — Share Card */}
      {v2ShareCard && (
        <ShareCard shareCard={v2ShareCard} />
      )}

      {/* V2 — Dimension Breakdown with deltas */}
      {dimensionScores && Object.keys(dimensionScores).length > 0 && (
        <DimBreakdown
          dimensions={dimensionScores}
          initialDimensions={reportCore?.initial_dimension_scores || {}}
          enabled={!!v2CompleteData || !!v2ShareCard}
        />
      )}

      {/* Feature 1: Mastery Tier Labels — "Your Skill Levels" */}
      {reportCore?.mastery_tiers && Object.keys(reportCore.mastery_tiers).length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-gradient-to-br from-slate-50 to-indigo-50 rounded-xl p-4 border border-indigo-100"
        >
          <p className="text-xs font-black text-indigo-800 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <FaTrophy className="text-indigo-400" /> Your Skill Levels
          </p>
          <div className="space-y-2">
            {Object.entries(reportCore.mastery_tiers).map(([dim, info]) => {
              const tierKey = (info.tier_key || 'beginner').toLowerCase();
              const colors = _TIER_COLORS[tierKey] || _TIER_COLORS.beginner;
              return (
                <div key={dim} className="flex items-start gap-3 bg-white/60 rounded-lg px-3 py-2.5">
                  <span className="text-base flex-shrink-0">{_DIM_ICONS[dim] || '📊'}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[11px] font-bold text-gray-800">
                        {_DIM_LABELS[dim] || dim}
                      </span>
                      <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full border ${colors.bg} ${colors.text} ${colors.border}`}>
                        {info.tier || info.tier_key}
                      </span>
                      <span className="text-[10px] font-semibold text-indigo-600">
                        {info.score}/100
                      </span>
                    </div>
                    {info.label && (
                      <p className="text-[10px] font-medium text-gray-700 mt-0.5">{info.label}</p>
                    )}
                    {info.description && (
                      <p className="text-[10px] text-gray-500 leading-relaxed mt-0.5">{info.description}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Skill Report — LLM personalized assessment */}
      {skillReport && skillReport.summary_text && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl p-4 border border-indigo-200"
        >
          <p className="text-xs font-black text-indigo-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <FaGraduationCap className="text-indigo-500" /> Skill Assessment
          </p>
          <p className="text-[11px] text-indigo-700 leading-relaxed">{skillReport.summary_text}</p>
          {skillReport.growth_area && skillReport.growth_area.suggestion && (
            <div className="mt-2 px-3 py-2 bg-white/60 rounded-lg">
              <p className="text-[10px] text-indigo-600">
                <span className="font-bold">Growth area:</span> {skillReport.growth_area.suggestion}
              </p>
            </div>
          )}
        </motion.div>
      )}

      {/* Coach's Debrief */}
      {debrief && debrief.debrief_text && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-4 border border-amber-200"
        >
          <p className="text-xs font-black text-amber-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <FaCommentDots className="text-amber-500" /> Coach's Debrief
          </p>
          <p className="text-[11px] text-amber-800 leading-relaxed">{debrief.debrief_text}</p>
          {debrief.key_insight && (
            <div className="mt-2 px-3 py-2 bg-white/60 rounded-lg">
              <p className="text-[10px] text-amber-700 font-semibold">{debrief.key_insight}</p>
            </div>
          )}
          {debrief.real_world_connection && (
            <p className="text-[10px] text-amber-600 mt-2 italic">{debrief.real_world_connection}</p>
          )}
        </motion.div>
      )}

      {/* Mento Chat Psychological Analysis */}
      {chatAnalysis?.summary && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.28 }}
          className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-xl p-4 border border-violet-200"
        >
          <p className="text-xs font-black text-violet-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <FaCommentDots className="text-violet-500" /> How You Used Coaching
          </p>
          <p className="text-[11px] text-violet-800 leading-relaxed">{chatAnalysis.summary}</p>
          {chatAnalysis.coaching_style_response && (
            <p className="text-[10px] text-violet-600 mt-1.5 italic">{chatAnalysis.coaching_style_response}</p>
          )}
          {chatAnalysis.patterns?.length > 0 && (
            <div className="mt-2 space-y-1">
              {chatAnalysis.patterns.slice(0, 3).map((p, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-sm flex-shrink-0">{_DIM_ICONS[p.dimension] || '•'}</span>
                  <div className="min-w-0">
                    <span className="text-[10px] font-semibold text-violet-700">{_DIM_LABELS[p.dimension] || p.label}</span>
                    {p.evidence && <span className="text-[10px] text-violet-500 italic ml-1">"{p.evidence}"</span>}
                  </div>
                  {p.signal && (
                    <span className={`ml-auto text-[9px] px-1.5 py-0.5 rounded-full flex-shrink-0 font-semibold ${
                      p.signal === 'positive' ? 'bg-green-100 text-green-700' :
                      p.signal === 'growth' ? 'bg-amber-100 text-amber-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>{p.signal}</span>
                  )}
                </div>
              ))}
            </div>
          )}
          {chatAnalysis.growth_signal && (
            <div className="mt-2.5 px-3 py-2 bg-white/60 rounded-lg border border-violet-100">
              <p className="text-[10px] text-violet-700 font-semibold">💡 {chatAnalysis.growth_signal}</p>
            </div>
          )}
        </motion.div>
      )}

      {/* Mento Score Breakdown */}
      {mentoBreakdown && mentoBreakdown.length > 0 && mentoScore && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-br from-yellow-50 to-amber-50 rounded-xl p-4 border border-yellow-200"
        >
          <button
            onClick={() => setShowBreakdown(!showBreakdown)}
            className="w-full flex items-center justify-between"
          >
            <p className="text-xs font-black text-yellow-800 uppercase tracking-wider flex items-center gap-1.5">
              <FaChartPie className="text-yellow-500" /> Mento Score: {Math.round(mentoScore.score || 0)}
              <span className="normal-case font-medium text-yellow-600 ml-1">({mentoScore.rank})</span>
            </p>
            {showBreakdown ? <FaChevronUp className="text-yellow-500 text-xs" /> : <FaChevronDown className="text-yellow-500 text-xs" />}
          </button>
          <AnimatePresence>
            {showBreakdown && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden mt-3 space-y-1.5"
              >
                {mentoBreakdown.map((cat) => (
                  <div key={cat.key} className="flex items-center gap-2">
                    <span className="text-[10px] text-yellow-700 w-28 truncate flex-shrink-0 font-medium">
                      {cat.category}
                    </span>
                    <div className="flex-1 h-2 bg-yellow-200 rounded-full">
                      <div
                        className="h-full rounded-full bg-yellow-500 transition-all"
                        style={{ width: `${Math.min(100, cat.score)}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-bold text-yellow-800 w-8 text-right">
                      {Math.round(cat.score)}
                    </span>
                    <span className="text-[9px] text-yellow-500 w-10 text-right">
                      ({Math.round(cat.weight * 100)}%)
                    </span>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Strengths */}
      {insights.strengths?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border border-green-200"
        >
          <p className="text-xs font-black text-green-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <FaStar className="text-green-500" /> What You Did Well
          </p>
          <div className="space-y-2">
            {insights.strengths.map((s, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-sm mt-0.5">{s.icon || '✅'}</span>
                <div>
                  <p className="text-[11px] font-bold text-green-900">{s.title}</p>
                  <p className="text-[10px] text-green-700 leading-relaxed">{s.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Improvements */}
      {insights.improvements?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-200"
        >
          <p className="text-xs font-black text-blue-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <FaArrowUp className="text-blue-500" /> Next Time, Try
          </p>
          <div className="space-y-2">
            {insights.improvements.map((s, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-sm mt-0.5">{s.icon || '💡'}</span>
                <div>
                  <p className="text-[11px] font-bold text-blue-900">{s.title}</p>
                  <p className="text-[10px] text-blue-700 leading-relaxed">{s.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Fun Facts */}
      {insights.fun_facts?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-3 border border-purple-200"
        >
          <p className="text-xs font-black text-purple-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <FaBolt className="text-purple-500" /> Fun Facts
          </p>
          <div className="space-y-1.5">
            {insights.fun_facts.map((f, i) => (
              <p key={i} className="text-[10px] text-purple-700 flex items-start gap-1.5">
                <span>{f.icon || '🎲'}</span> {f.text}
              </p>
            ))}
          </div>
        </motion.div>
      )}

      {/* Transfer Exercises — Try This In Real Life */}
      {transferExercises.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          className="bg-gradient-to-br from-teal-50 to-cyan-50 rounded-xl p-4 border border-teal-200"
        >
          <p className="text-xs font-black text-teal-800 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <FaHandsHelping className="text-teal-500" /> Try This In Real Life
          </p>
          <div className="space-y-3">
            {transferExercises.map((ex, i) => (
              <div key={i} className="bg-white/60 rounded-lg p-3">
                {ex.game_context && (
                  <p className="text-[10px] text-teal-600 italic mb-1">{ex.game_context}</p>
                )}
                <p className="text-[11px] text-teal-900 font-medium leading-relaxed">{ex.real_world}</p>
                {ex.challenge && (
                  <div className="mt-2 bg-teal-100/50 rounded-lg px-3 py-2">
                    <p className="text-[10px] font-bold text-teal-800">Weekly Challenge:</p>
                    <p className="text-[10px] text-teal-700">{ex.challenge}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Feature 3: Transfer Activity — "Try This IRL" card (from reportCore) */}
      {reportCore?.transfer_activity && !transferDismissed && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.95 }}
          className="rounded-xl p-4 border border-yellow-300"
          style={{ background: 'linear-gradient(135deg, #FFFDE7 0%, #FFF9C4 100%)' }}
        >
          <div className="flex items-start justify-between gap-2 mb-2">
            <p className="text-xs font-black text-yellow-900 uppercase tracking-wider flex items-center gap-1.5">
              🌍 Try This IRL
            </p>
            <button
              onClick={() => setTransferDismissed(true)}
              className="text-yellow-500 hover:text-yellow-700 text-xs font-bold flex-shrink-0 transition-colors"
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
          {reportCore.transfer_activity.prompt && (
            <p className="text-[10px] text-yellow-700 italic mb-2">{reportCore.transfer_activity.prompt}</p>
          )}
          <p className="text-[12px] font-semibold text-yellow-900 leading-relaxed">
            {reportCore.transfer_activity.activity}
          </p>
          {reportCore.transfer_activity.dimension_label && (
            <p className="text-[10px] text-yellow-600 mt-2">
              Based on your <span className="font-semibold">{reportCore.transfer_activity.dimension_label}</span> performance
            </p>
          )}
          <button
            onClick={() => setTransferDismissed(true)}
            className="mt-3 px-4 py-1.5 bg-yellow-400 hover:bg-yellow-500 text-yellow-900 font-semibold text-xs rounded-lg transition-colors"
          >
            Got it!
          </button>
        </motion.div>
      )}

      {/* Weak Dimension Coaching — Targeted tips for lowest scoring skills */}
      {weakDimensions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0 }}
          className="bg-gradient-to-br from-rose-50 to-pink-50 rounded-xl p-4 border border-rose-200"
        >
          <p className="text-xs font-black text-rose-800 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <FaBullseye className="text-rose-500" /> Skills to Grow Next
          </p>
          <div className="space-y-3">
            {weakDimensions.map(([dim, score]) => {
              const tips = _WEAK_TIPS[dim] || [];
              const tip = tips[Math.floor(Math.random() * tips.length)];
              return (
                <div key={dim} className="bg-white/60 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-base">{_DIM_ICONS[dim]}</span>
                    <SkillDefinition skill={dim}>
                      <span
                        className="text-[11px] font-bold text-rose-900 cursor-pointer underline hover:text-blue-600"
                        onClick={() => navigate('/glossary?term=' + encodeURIComponent(_DIM_LABELS[dim] || dim))}
                      >
                        {_DIM_LABELS[dim]}
                      </span>
                    </SkillDefinition>
                    <span className="ml-auto text-[10px] font-bold text-rose-600 bg-rose-100 px-2 py-0.5 rounded-full">{score}/100</span>
                    <span
                      className="text-[9px] text-blue-500 cursor-pointer hover:text-blue-700 underline whitespace-nowrap"
                      onClick={() => navigate('/glossary?term=' + encodeURIComponent(_DIM_LABELS[dim] || dim))}
                    >
                      → see in Glossary
                    </span>
                  </div>
                  {tip && <p className="text-[10px] text-rose-700 leading-relaxed">{tip}</p>}
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Peer Benchmark — How you compare */}
      {mentoPercentile !== null && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.05 }}
          className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-xl p-4 border border-violet-200"
        >
          <p className="text-xs font-black text-violet-800 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <FaTrophy className="text-violet-500" /> How You Compare
          </p>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="text-2xl font-black text-violet-700">
                Top {Math.max(1, 100 - mentoPercentile)}%
              </div>
              <div className="text-[11px] text-violet-600 mt-0.5">
                You scored higher than {mentoPercentile}% of players on this game
              </div>
            </div>
            <div className="w-16 h-16 rounded-full border-4 border-violet-300 flex items-center justify-center bg-white">
              <span className="text-lg font-black text-violet-700">{mentoPercentile}%</span>
            </div>
          </div>
          <div className="mt-3 h-2 bg-violet-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-violet-400 to-purple-500 rounded-full transition-all"
              style={{ width: `${mentoPercentile}%` }}
            />
          </div>
        </motion.div>
      )}

      {/* Next Game Recommendations */}
      {recommendations.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.1 }}
          className="bg-gradient-to-br from-sky-50 to-blue-50 rounded-xl p-4 border border-sky-200"
        >
          <p className="text-xs font-black text-sky-800 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <FaPlay className="text-sky-500" /> Play Next
          </p>
          <div className="space-y-2">
            {recommendations.slice(0, 3).map((rec, i) => (
              <div
                key={rec.game_id || i}
                onClick={() => navigate(`/play/${rec.game_id}`)}
                className="flex items-center gap-3 p-2.5 bg-white/70 rounded-lg cursor-pointer hover:bg-white transition-all hover:shadow-sm"
              >
                <span className="text-xl">{rec.icon || '🎮'}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] font-bold text-sky-900 truncate">{rec.title}</p>
                  {rec.reasons?.[0] && (
                    <p className="text-[9px] text-sky-600 truncate">{rec.reasons[0]}</p>
                  )}
                </div>
                <FaChevronRight className="text-sky-300 text-xs flex-shrink-0" />
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Assessment Report (teacher/admin roles only) */}
      {canViewAssessment && runId && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.12 }}
          className="bg-white rounded-xl p-4 border border-gray-100"
        >
          <button
            onClick={() => setShowAssessment(!showAssessment)}
            className="w-full flex items-center justify-between"
          >
            <p className="text-xs font-black text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
              <FaClipboardList className="text-indigo-400" /> Assessment Report
              <span className="normal-case font-medium text-indigo-400 ml-1 text-[10px]">Teacher View</span>
            </p>
            {showAssessment ? <FaChevronUp className="text-gray-400 text-xs" /> : <FaChevronDown className="text-gray-400 text-xs" />}
          </button>
          <AnimatePresence>
            {showAssessment && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden mt-3"
              >
                <AssessmentReport runId={runId} initialData={prefetchedAssessment} />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Certificate + Rubric download buttons */}
      {runId && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0 }}
          className="flex gap-2"
        >
          <button
            onClick={() => window.open(`/api/run/${runId}/certificate`, '_blank')}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold border border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors"
          >
            <FaGraduationCap className="text-amber-500" /> Certificate
          </button>
          <button
            onClick={() => window.open(`/api/run/${runId}/rubric`, '_blank')}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold border border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
          >
            <FaClipboardList className="text-indigo-500" /> Academic Rubric
          </button>
        </motion.div>
      )}

      {/* Choice Replay — See which rounds exercised which skills */}
      {choiceHistory.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.1 }}
          className="bg-white rounded-xl p-4 border border-gray-100"
        >
          <button
            onClick={() => setShowChoiceReplay(!showChoiceReplay)}
            className="w-full flex items-center justify-between"
          >
            <p className="text-xs font-black text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
              <FaHistory className="text-gray-400" /> Your Choices This Game
              <span className="normal-case font-medium text-gray-400 ml-1">({choiceHistory.length} rounds)</span>
            </p>
            {showChoiceReplay ? <FaChevronUp className="text-gray-400 text-xs" /> : <FaChevronDown className="text-gray-400 text-xs" />}
          </button>
          <AnimatePresence>
            {showChoiceReplay && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden mt-3 space-y-2"
              >
                {choiceHistory.slice(0, 8).map((entry, i) => {
                  // Prefer human-readable label, fall back to cleaning up ID
                  const label = entry.choice_label
                    || entry.choice_text
                    || entry.choice
                    || (entry.choice_id
                        ? entry.choice_id.replace(/^[a-z]\d+_/i, '').replace(/_/g, ' ')
                        : null)
                    || 'Choice made';
                  return (
                    <div key={i} className="flex items-start gap-2 text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
                      <span className="font-bold text-gray-400 min-w-[20px]">{entry.scene_title ? `${i + 1}.` : `R${(entry.round ?? i) + 1}`}</span>
                      <span className="flex-1 capitalize">{label}</span>
                      {entry.skill_tags?.length > 0 && (
                        <div className="flex gap-1 flex-wrap">
                          {entry.skill_tags.slice(0, 2).map(tag => (
                            <span key={tag} className="text-[9px] px-1.5 py-0.5 bg-indigo-100 text-indigo-600 rounded-full">
                              {_DIM_ICONS[tag]} {_DIM_LABELS[tag]?.split(' ')[0]}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Skill Debrief — connects specific choices to skills */}
      {choiceHistory.length > 0 && choiceHistory.some(e => e.skill_tags?.length > 0) && (() => {
        // Aggregate choices by skill dimension
        const skillEvidence = {};
        choiceHistory.forEach(entry => {
          (entry.skill_tags || []).forEach(tag => {
            if (!skillEvidence[tag]) skillEvidence[tag] = [];
            skillEvidence[tag].push(entry.scene_title || entry.choice_label || 'a key moment');
          });
        });
        // Get top 3 dimensions with most evidence
        const topDims = Object.entries(skillEvidence)
          .sort((a, b) => b[1].length - a[1].length)
          .slice(0, 3)
          .filter(([, scenes]) => scenes.length >= 2);
        if (topDims.length === 0) return null;
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.1 }}
            className="mt-4 bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl p-4 border border-emerald-200"
          >
            <p className="text-xs font-bold uppercase tracking-wider text-emerald-700 mb-3">
              Your Skill Footprint
            </p>
            <div className="space-y-3">
              {topDims.map(([dim, scenes]) => (
                <div key={dim}>
                  <p className="text-sm font-semibold text-emerald-800">
                    {_DIM_ICONS[dim]} You demonstrated <span className="text-emerald-600">{_DIM_LABELS[dim] || dim.replace(/_/g, ' ')}</span> in {scenes.length} key moments:
                  </p>
                  <ul className="mt-1 ml-5 space-y-0.5">
                    {scenes.slice(0, 3).map((scene, j) => (
                      <li key={j} className="text-xs text-emerald-700 list-disc">&ldquo;{scene}&rdquo;</li>
                    ))}
                    {scenes.length > 3 && <li className="text-xs text-emerald-500 italic">...and {scenes.length - 3} more</li>}
                  </ul>
                </div>
              ))}
            </div>
          </motion.div>
        );
      })()}

      {/* Cognitive Profile */}
      {reportCore?.cognitive_profile && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.15 }}
          className="mt-4 bg-purple-50 rounded-lg p-3 border border-purple-100"
        >
          <div className="text-xs font-semibold text-purple-700 mb-1">🧠 Your Thinking Style</div>
          <div className="text-sm text-purple-800">
            {reportCore.cognitive_profile.thinking_style_label || (
              reportCore.cognitive_profile.bloom_level
                ? `${reportCore.cognitive_profile.bloom_level.charAt(0).toUpperCase() + reportCore.cognitive_profile.bloom_level.slice(1)} level thinker`
                : 'Analytical thinker'
            )}
          </div>
        </motion.div>
      )}

      {/* Transfer Prompt — Apply Your Learning */}
      {user?.role === 'student' && (
        <TransferPromptSection gameId={reportCore?.game_id || summary?.game_id || 'unknown'} />
      )}

      {/* Feature 2: CASEL / Goleman Frameworks Developed — collapsible */}
      {dimensionScores && Object.keys(dimensionScores).length > 0 && (() => {
        const dimKeys = Object.keys(dimensionScores);
        const uniqueCasel = [...new Set(dimKeys.map(d => CASEL_MAP[d]?.casel).filter(Boolean))];
        const uniqueGoleman = [...new Set(dimKeys.map(d => CASEL_MAP[d]?.goleman).filter(Boolean))];
        if (!uniqueCasel.length && !uniqueGoleman.length) return null;
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.22 }}
            className="bg-white rounded-xl p-4 border border-gray-100"
          >
            <button
              onClick={() => setShowFrameworks(v => !v)}
              className="w-full flex items-center justify-between"
            >
              <p className="text-xs font-black text-gray-600 uppercase tracking-wider flex items-center gap-1.5">
                <FaGraduationCap className="text-indigo-400" /> Frameworks Developed
              </p>
              <span className="text-[10px] text-indigo-500 font-medium">
                {showFrameworks ? 'Hide ↑' : 'See learning frameworks →'}
              </span>
            </button>
            <AnimatePresence>
              {showFrameworks && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden mt-3 space-y-3"
                >
                  {uniqueCasel.length > 0 && (
                    <div>
                      <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">CASEL Competencies</p>
                      <div className="flex flex-wrap gap-1.5">
                        {uniqueCasel.map(c => (
                          <span key={c} className="text-[10px] px-2.5 py-1 rounded-full bg-blue-100 text-blue-700 border border-blue-200 font-medium">
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {uniqueGoleman.length > 0 && (
                    <div>
                      <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">Goleman EQ Domains</p>
                      <div className="flex flex-wrap gap-1.5">
                        {uniqueGoleman.map(g => (
                          <span key={g} className="text-[10px] px-2.5 py-1 rounded-full bg-purple-100 text-purple-700 border border-purple-200 font-medium">
                            {g}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })()}

      {/* Career Matches */}
      {careerMatches && careerMatches.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.2 }}
          className="mt-6 border-t border-gray-100 pt-4"
        >
          <details>
            <summary className="cursor-pointer text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
              🎯 Career Matches <span className="font-normal text-gray-400 text-xs">(based on your skill profile)</span>
            </summary>
            <div className="space-y-3 mt-2">
              {careerMatches.slice(0, 3).map((career, i) => (
                <div key={i} className="bg-gray-50 rounded-lg p-3">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium text-gray-800">{career.career}</span>
                    <span className="text-sm font-bold text-blue-600">{Math.round((career.match_score || 0) * 100)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${Math.round((career.match_score || 0) * 100)}%` }} />
                  </div>
                  {career.gap_dims && career.gap_dims.length > 0 && (
                    <div className="text-xs text-gray-500 mt-1">Develop: {career.gap_dims.slice(0, 2).join(', ')}</div>
                  )}
                </div>
              ))}
            </div>
          </details>
        </motion.div>
      )}

      {/* What to play next — single highlighted recommendation from backend */}
      {reportCore?.next_recommended_game && (
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.25 }}
          className="rounded-xl overflow-hidden border border-indigo-200 bg-gradient-to-br from-indigo-50 to-blue-50"
        >
          <div className="px-4 pt-3 pb-1">
            <p className="text-xs font-black text-indigo-700 uppercase tracking-wider flex items-center gap-1.5">
              <FaPlay className="text-indigo-400" /> Up Next for You
            </p>
          </div>
          <div
            className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-indigo-100/60 transition-colors"
            onClick={() => navigate(`/play/${reportCore.next_recommended_game.game_id}`)}
          >
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center flex-shrink-0 text-white text-lg">
              {reportCore.next_recommended_game.icon || '🎮'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-indigo-900 truncate">{reportCore.next_recommended_game.title}</p>
              <p className="text-[10px] text-indigo-500 truncate">{reportCore.next_recommended_game.reason || 'Recommended based on your performance'}</p>
            </div>
            <FaChevronRight className="text-indigo-400 flex-shrink-0" />
          </div>
        </motion.div>
      )}

      {/* #23 ── Run Timeline — round-by-round choice + money delta ─ */}
      {choiceHistory && choiceHistory.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.05 }}
          className="rounded-2xl border p-5 bg-white shadow-sm">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            🕒 Run Timeline
          </h3>
          <ol className="space-y-2">
            {choiceHistory.map((entry, i) => {
              const round = (entry.round != null ? entry.round : i) + 1;
              const label = entry.label || entry.choice_label || entry.choice_id || '—';
              const delta = entry.money_delta
                ?? entry.delta?.money
                ?? entry.delta?.cash
                ?? null;
              const sign = typeof delta === 'number' ? (delta >= 0 ? '+' : '−') : '';
              const tone = typeof delta === 'number' ? (delta >= 0 ? 'text-emerald-700' : 'text-rose-700') : 'text-gray-500';
              return (
                <li key={i} className="flex items-start gap-3 text-sm">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold flex items-center justify-center">
                    {round}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-800 font-semibold truncate">{label}</p>
                  </div>
                  <span className={`text-xs font-bold tabular-nums ${tone}`}>
                    {typeof delta === 'number' ? `${sign}₹${Math.abs(Math.round(delta)).toLocaleString('en-IN')}` : '—'}
                  </span>
                </li>
              );
            })}
          </ol>
        </motion.div>
      )}

      {/* ── Decision Map — visual path through all rounds ────────── */}
      {reportCore?.hidden_metrics?._choice_history?.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.1 }}
          className="rounded-2xl border p-5 bg-white shadow-sm">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            🗺️ Your Decision Map
          </h3>
          <div className="relative">
            {/* Timeline path */}
            <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gradient-to-b from-indigo-400 to-purple-400" />
            <div className="space-y-3">
              {reportCore.hidden_metrics._choice_history.map((ch, i) => (
                <div key={i} className="relative pl-12">
                  <div className="absolute left-3 top-1 w-5 h-5 rounded-full bg-indigo-500 text-white text-[10px] font-bold flex items-center justify-center shadow">
                    {i + 1}
                  </div>
                  <div className="bg-gray-50 rounded-xl px-4 py-2.5 border border-gray-100">
                    <p className="text-sm font-semibold text-gray-700">{ch.choice_label || ch.choice_id}</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(ch.skill_tags || []).map(t => (
                        <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">{t}</span>
                      ))}
                      {(ch.flags_set || []).map(f => (
                        <span key={f} className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium">🚩 {f}</span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* ── Hidden Metrics Reveal — "Behind the Scenes" ────────── */}
      {reportCore?.hidden_metrics && reportCore?.anti_cheat_score && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.2 }}
          className="rounded-2xl border p-5 bg-gradient-to-br from-slate-50 to-slate-100 shadow-sm">
          <h3 className="text-lg font-bold text-gray-800 mb-1 flex items-center gap-2">
            🔍 Behind the Scenes
          </h3>
          <p className="text-xs text-gray-500 mb-4">Hidden metrics tracked your decision quality beyond what was visible.</p>

          {/* Final Grade */}
          <div className="flex items-center gap-4 mb-4 p-3 rounded-xl bg-white border">
            <div className={`text-4xl font-black ${reportCore.anti_cheat_score.grade === 'S' ? 'text-yellow-500' : reportCore.anti_cheat_score.grade === 'A' ? 'text-green-600' : reportCore.anti_cheat_score.grade === 'B' ? 'text-blue-600' : 'text-gray-600'}`}>
              {reportCore.anti_cheat_score.grade}
            </div>
            <div>
              <p className="font-bold text-gray-800">{reportCore.anti_cheat_score.title}</p>
              <p className="text-sm text-gray-500">
                Score: {reportCore.anti_cheat_score.score}/100 | Profile: {reportCore.anti_cheat_score.profile_name}
                {reportCore.anti_cheat_score.momentum !== 1.0 && ` | Momentum: ${reportCore.anti_cheat_score.momentum}x`}
              </p>
            </div>
          </div>

          {/* Hidden metric bars */}
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(reportCore.anti_cheat_score.breakdown || {}).map(([key, data]) => (
              <div key={key} className="bg-white rounded-lg p-2.5 border">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-semibold text-gray-600 truncate">{key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                  <span className="text-xs font-bold text-gray-800">{Math.round(data.raw)}</span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${Math.min(100, Math.max(0, data.raw))}%`, background: data.raw >= 70 ? '#22C55E' : data.raw >= 40 ? '#F59E0B' : '#EF4444' }} />
                </div>
                <p className="text-[9px] text-gray-400 mt-0.5">Weight: {Math.round(data.weight * 100)}%</p>
              </div>
            ))}
          </div>

          {/* Pattern penalties if any */}
          {Object.keys(reportCore.anti_cheat_score.pattern_penalties || {}).length > 0 && (
            <div className="mt-3 p-2.5 rounded-lg bg-red-50 border border-red-100">
              <p className="text-xs font-semibold text-red-700 mb-1">Pattern Penalties Applied:</p>
              {Object.entries(reportCore.anti_cheat_score.pattern_penalties).map(([res, val]) => (
                <p key={res} className="text-[11px] text-red-600">{res.replace(/_/g, ' ')}: {val > 0 ? '+' : ''}{val}</p>
              ))}
            </div>
          )}
        </motion.div>
      )}

      {/* Challenge a friend — async peer challenge card */}
      {user?.role === 'student' && reportCore?.game_id && (
        <PostGameChallenge
          gameId={reportCore.game_id}
          score={Math.round(reportCore?.mento_score?.score || reportCore?.final_score || 0)}
        />
      )}

      {/* Dashboard link */}
      {user?.role === 'student' && (
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.4 }}
          className="flex justify-center"
        >
          <button
            onClick={() => navigate('/home/student')}
            className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-500 transition-colors"
          >
            <span>🏠</span> My Dashboard
          </button>
        </motion.div>
      )}
    </div>
  );
}

/* ──────────── Client-side insight generator ──────────── */

function generateInsights(summary, state, gameType, won) {
  const strengths = [];
  const improvements = [];
  const fun_facts = [];

  if (!state && !summary) return { strengths, improvements, fun_facts };

  // Game-type-specific insight generation
  switch (gameType) {
    case 'strategy_grid':
      generateStrategyGridInsights(summary, state, won, strengths, improvements, fun_facts);
      break;
    case 'chess_strategy':
      generateChessInsights(summary, state, won, strengths, improvements, fun_facts);
      break;
    case 'go_territory':
      generateGoInsights(summary, state, won, strengths, improvements, fun_facts);
      break;
    case 'reversi':
      generateReversiInsights(summary, state, won, strengths, improvements, fun_facts);
      break;
    case 'tower_defense':
      generateTowerDefenseInsights(summary, state, won, strengths, improvements, fun_facts);
      break;
    case 'puzzle_match':
      generatePuzzleInsights(summary, state, won, strengths, improvements, fun_facts);
      break;
    case 'board':
      generateBoardInsights(summary, state, won, strengths, improvements, fun_facts);
      break;
    default:
      generateGenericInsights(summary, state, won, strengths, improvements, fun_facts);
  }

  return { strengths: strengths.slice(0, 3), improvements: improvements.slice(0, 3), fun_facts: fun_facts.slice(0, 3) };
}

function generateStrategyGridInsights(summary, state, won, strengths, improvements, fun_facts) {
  const r = summary?.reflection || {};
  const captures = (state?.player_captured || []).length;
  const turns = state?.turn_number || 0;
  const currency = state?.player_currency || 0;

  if (won) strengths.push({ icon: '🏆', title: 'Victory Secured', detail: `You won in ${turns} turns — great strategic execution!` });
  if (captures >= 3) strengths.push({ icon: '⚔️', title: 'Aggressive Capturer', detail: `You captured ${captures} enemy pieces, controlling the board.` });
  if (currency >= 15) strengths.push({ icon: '💰', title: 'Resource Manager', detail: `You ended with ${currency} resources — strong economy.` });
  if (r.abilities_used >= 3) strengths.push({ icon: '🌟', title: 'Ability Expert', detail: `You used ${r.abilities_used} special abilities effectively.` });

  if (!won) improvements.push({ icon: '🛡️', title: 'Protect Your King', detail: 'Focus on keeping your key pieces safe in the early game.' });
  if (captures < 2) improvements.push({ icon: '🎯', title: 'Take More Captures', detail: 'Look for opportunities to capture enemy pieces when they overextend.' });
  if (r.abilities_used < 2) improvements.push({ icon: '✨', title: 'Use Abilities More', detail: 'Special abilities can turn the tide — try using them proactively.' });

  fun_facts.push({ icon: '📊', text: `Total moves made: ${r.total_moves || turns}` });
  if (r.morale_final != null) fun_facts.push({ icon: '💪', text: `Your army morale ended at ${r.morale_final}%` });
  fun_facts.push({ icon: '🗺️', text: `Battlefield size: ${state?.grid_width || 10}×${state?.grid_height || 10}` });
}

function generateChessInsights(summary, state, won, strengths, improvements, fun_facts) {
  const captured = state?.captured_by_player?.length || 0;
  const lost = state?.captured_by_ai?.length || 0;
  const valuation = state?.player_valuation || 0;
  const turns = state?.turn_number || 0;

  if (won) strengths.push({ icon: '👑', title: 'Checkmate!', detail: 'You outmaneuvered your opponent and secured victory.' });
  if (captured > lost) strengths.push({ icon: '⚔️', title: 'Material Advantage', detail: `You captured ${captured} pieces while only losing ${lost}.` });
  if (valuation > (state?.ai_valuation || 0)) strengths.push({ icon: '📈', title: 'Value Leader', detail: 'You maintained higher piece value throughout the game.' });

  if (lost >= 4) improvements.push({ icon: '🛡️', title: 'Piece Protection', detail: `You lost ${lost} pieces — try to trade more favorably.` });
  if (turns > 40) improvements.push({ icon: '⚡', title: 'Faster Execution', detail: 'Try to find winning positions earlier in the game.' });
  if (!won) improvements.push({ icon: '🔍', title: 'Watch for Threats', detail: 'Scan the board for opponent threats before each move.' });

  fun_facts.push({ icon: '🎯', text: `Pieces captured: ${captured}` });
  fun_facts.push({ icon: '⏱️', text: `Game lasted ${turns} turns` });
  if (valuation) fun_facts.push({ icon: '💰', text: `Final valuation: $${(valuation / 1000000).toFixed(1)}M` });
}

function generateGoInsights(summary, state, won, strengths, improvements, fun_facts) {
  const playerStones = state?.player_stones || 0;
  const aiStones = state?.ai_stones || 0;
  const territories = state?.territories || {};
  const turns = state?.turn_number || 0;

  if (won) strengths.push({ icon: '🏆', title: 'Territory Master', detail: 'You claimed more territory than your opponent!' });
  if (playerStones > aiStones) strengths.push({ icon: '⚫', title: 'Stone Placement', detail: `You placed ${playerStones} stones strategically.` });

  if (!won) improvements.push({ icon: '🔲', title: 'Corner Strategy', detail: 'Securing corners early gives you a strong territorial base.' });
  improvements.push({ icon: '🔗', title: 'Connect Groups', detail: 'Keeping your stone groups connected makes them harder to capture.' });

  fun_facts.push({ icon: '⚫', text: `You placed ${playerStones} stones` });
  fun_facts.push({ icon: '⏱️', text: `Game lasted ${turns} turns` });
}

function generateReversiInsights(summary, state, won, strengths, improvements, fun_facts) {
  const playerDiscs = state?.player_discs || 0;
  const aiDiscs = state?.ai_discs || 0;
  const totalFlips = state?.player_flips_total || 0;
  const turns = state?.turn_number || 0;

  if (won) strengths.push({ icon: '🏆', title: 'Board Domination', detail: `You ended with ${playerDiscs} discs vs ${aiDiscs} for the opponent.` });
  if (totalFlips > 20) strengths.push({ icon: '🔄', title: 'Flip Master', detail: `You flipped ${totalFlips} discs during the game!` });

  improvements.push({ icon: '📐', title: 'Control Corners', detail: 'Corners can never be flipped — always prioritize them.' });
  if (!won) improvements.push({ icon: '🎯', title: 'Edge Strategy', detail: 'Building stable edges gives you lasting control.' });

  fun_facts.push({ icon: '🔲', text: `Final board: ${playerDiscs} vs ${aiDiscs} discs` });
  fun_facts.push({ icon: '🔄', text: `Total disc flips: ${totalFlips}` });
  fun_facts.push({ icon: '⏱️', text: `Game lasted ${turns} turns` });
}

function generateTowerDefenseInsights(summary, state, won, strengths, improvements, fun_facts) {
  const wavesCleared = state?.current_wave || 0;
  const totalWaves = state?.total_waves || 0;
  const kills = state?.total_kills || 0;
  const towers = (state?.towers || []).length;
  const lives = state?.lives || 0;

  if (won) strengths.push({ icon: '🏰', title: 'Perfect Defense', detail: `All ${totalWaves} waves defeated!` });
  if (lives >= 3) strengths.push({ icon: '❤️', title: 'Minimal Damage', detail: `You kept ${lives} lives — excellent positioning.` });
  if (kills > 20) strengths.push({ icon: '💥', title: 'Enemy Destroyer', detail: `You eliminated ${kills} enemies.` });

  if (lives <= 1 && won) improvements.push({ icon: '🛡️', title: 'Better Coverage', detail: 'Try spreading towers across more paths to avoid close calls.' });
  if (!won) improvements.push({ icon: '🔄', title: 'Tower Variety', detail: 'Mix tower types — different enemies have different weaknesses.' });
  if (towers < 5) improvements.push({ icon: '🏗️', title: 'Build More', detail: `You only built ${towers} towers — don't hoard resources.` });

  fun_facts.push({ icon: '🏰', text: `Towers built: ${towers}` });
  fun_facts.push({ icon: '💀', text: `Enemies eliminated: ${kills}` });
  fun_facts.push({ icon: '🌊', text: `Waves survived: ${wavesCleared}/${totalWaves}` });
}

function generatePuzzleInsights(summary, state, won, strengths, improvements, fun_facts) {
  const score = state?.score || summary?.score || 0;
  const target = state?.target_score || summary?.target_score || 0;
  const movesUsed = state?.moves_used || summary?.moves_used || 0;
  const maxChain = summary?.max_chain || 0;

  if (won) strengths.push({ icon: '🎯', title: 'Target Reached!', detail: `You scored ${score}/${target} — puzzle solved!` });
  if (maxChain >= 3) strengths.push({ icon: '🔗', title: 'Chain Reaction', detail: `Max chain of ${maxChain} — great combo thinking!` });

  if (!won && score > target * 0.7) improvements.push({ icon: '🔥', title: 'So Close!', detail: `You were ${target - score} points away — try focusing on combos.` });
  improvements.push({ icon: '👀', title: 'Look Ahead', detail: 'Plan 2-3 moves ahead to set up bigger chains.' });

  fun_facts.push({ icon: '🎯', text: `Final score: ${score}` });
  fun_facts.push({ icon: '🔢', text: `Moves used: ${movesUsed}` });
  if (maxChain) fun_facts.push({ icon: '🔗', text: `Best chain: ${maxChain}x combo` });
}

function generateBoardInsights(summary, state, won, strengths, improvements, fun_facts) {
  const playerScore = state?.player_score || state?.score || 0;
  const position = state?.player_position || 0;
  const turns = state?.turn_number || state?.round || 0;

  if (won) strengths.push({ icon: '🏆', title: 'Champion!', detail: 'You finished first — great decision making!' });
  if (playerScore > 0) strengths.push({ icon: '⭐', title: 'High Score', detail: `You scored ${playerScore} points.` });

  if (!won) improvements.push({ icon: '🎲', title: 'Risk Assessment', detail: 'Sometimes taking calculated risks pays off big.' });
  improvements.push({ icon: '📊', title: 'Track Opponents', detail: 'Watch what your opponents are doing to adjust your strategy.' });

  fun_facts.push({ icon: '🎲', text: `Turns played: ${turns}` });
  if (position) fun_facts.push({ icon: '📍', text: `Final position: tile ${position}` });
}

function generateGenericInsights(summary, state, won, strengths, improvements, fun_facts) {
  const xp = summary?.xp_earned || state?.xp_earned || 0;
  const rounds = state?.round || state?.turn || state?.round_number || summary?.rounds_played || 0;
  const dimScores = state?.dimension_scores || summary?.dimension_scores || {};
  const bestDim = Object.entries(dimScores).sort((a, b) => b[1] - a[1])[0];
  const worstDim = Object.entries(dimScores).sort((a, b) => a[1] - b[1])[0];

  if (won) {
    strengths.push({ icon: '🏆', title: 'Challenge Completed!', detail: `You finished${rounds > 0 ? ` after ${rounds} decision${rounds !== 1 ? 's' : ''}` : ''} — great persistence!` });
  }
  if (xp > 0) {
    strengths.push({ icon: '⭐', title: `+${xp} XP Earned`, detail: 'Your XP grows with every game — keep going to unlock new levels!' });
  }
  if (bestDim && _DEFAULT_DIM_LABELS[bestDim[0]]) {
    strengths.push({ icon: _DIM_ICONS[bestDim[0]] || '✅', title: `Strong: ${_DEFAULT_DIM_LABELS[bestDim[0]]}`, detail: `Your highest-performing soft skill this session — ${bestDim[1]}/100.` });
  }

  improvements.push({ icon: '💡', title: 'Notice Your Pattern', detail: 'Before each choice, pause and ask: "What does this choice build in me?" — self-awareness is the first step to growth.' });
  if (worstDim && _DEFAULT_DIM_LABELS[worstDim[0]]) {
    improvements.push({ icon: _DIM_ICONS[worstDim[0]] || '🎯', title: `Grow: ${_DEFAULT_DIM_LABELS[worstDim[0]]}`, detail: `This was your lowest skill this session at ${worstDim[1]}/100 — try games that challenge this area.` });
  } else {
    improvements.push({ icon: '🔄', title: 'Try Different Paths', detail: 'Replay with different choices — each path exercises different soft skills and reveals new strategies.' });
  }

  fun_facts.push({ icon: '🧠', text: 'Each choice in this game exercises a real-world soft skill: the same ones hiring managers and coaches look for.' });
  if (rounds > 0) fun_facts.push({ icon: '🎮', text: `You navigated ${rounds} decision point${rounds !== 1 ? 's' : ''} — each one a micro-moment of skill practice.` });
}
