/**
 * ModuleReportPage — student-facing end-of-module report card.
 *
 * Shows per-week breakdown, quiz averages, time spent, skill tally,
 * a composite letter grade, and (when LLM is enabled) a 3-sentence
 * Mento summary with a strength + suggestion.
 *
 * Route: /module/:moduleId/report
 */
import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FaArrowLeft, FaCheckCircle, FaClock, FaTrophy, FaBolt } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { getModuleReport, getModuleReportV2, getModuleSkillReport } from '../api/modules';
import ShareCardActions from '../components/module/ShareCardActions';

const DIM_LABELS_FULL = {
  strategic_thinking: 'Strategic Thinking',
  creativity: 'Creativity',
  empathy: 'Empathy',
  communication: 'Communication',
  resilience: 'Resilience',
  adaptability: 'Adaptability',
  risk_tolerance: 'Risk Tolerance',
  delayed_gratification: 'Delayed Gratification',
};

const C = {
  primary: '#F59E0B',
  primaryDark: '#D97706',
  primaryGlow: '#FEF3C7',
  bg: '#FFF8F0',
  card: '#FFFFFF',
  text: '#1C1917',
  textMid: '#57534E',
  textLight: '#A8A29E',
  border: '#E7E5E4',
  borderWarm: '#FED7AA',
  emerald: '#059669',
  emeraldBg: '#ECFDF5',
  rose: '#e11d48',
  roseBg: '#FFF1F2',
  indigo: '#0EA5E9',
  purple: '#14B8A6',
};

const GRADE_BG = {
  A: '#DCFCE7', B: '#E0F2FE', C: '#FEF3C7', D: '#FFE4E6', '—': '#F1F5F9',
};
const GRADE_FG = {
  A: '#15803d', B: '#075985', C: '#92400e', D: '#9f1239', '—': '#475569',
};

const SKILL_LABELS = {
  strategic_thinking: '🧠 Strategic Thinking',
  risk_tolerance: '🎲 Risk Tolerance',
  delayed_gratification: '⏳ Delayed Gratification',
  adaptability: '🌊 Adaptability',
  resilience: '💪 Resilience',
  empathy: '❤️ Empathy',
  creativity: '🎨 Creativity',
  ethical_reasoning: '⚖️ Ethical Reasoning',
};

const fmtMin = (s) => {
  const m = Math.round((s || 0) / 60);
  return m === 0 ? '<1 min' : `${m} min`;
};

const TYPE_ICON = {
  lesson: '📖', worksheet: '📝', reflection: '💭',
  game: '🎮', quiz: '🧪', assessment: '🎯', field_mission: '🕵️',
};

export default function ModuleReportPage() {
  const { moduleId } = useParams();
  const navigate = useNavigate();
  const { t: i18n } = useTranslation();
  const [report, setReport] = useState(null);
  const [reportV2, setReportV2] = useState(null);
  const [skillReport, setSkillReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const [v1, v2, sk] = await Promise.all([
          getModuleReport(moduleId),
          getModuleReportV2(moduleId).catch(() => null),
          getModuleSkillReport(moduleId).catch(() => null),
        ]);
        if (!cancel) {
          setReport(v1);
          setReportV2(v2);
          setSkillReport(sk);
        }
      } catch (e) {
        if (!cancel) setError(e.response?.data?.error || e.message);
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => { cancel = true; };
  }, [moduleId]);

  if (loading) {
    return (
      <div style={{ background: C.bg, minHeight: '100vh' }}>
        <div className="max-w-4xl mx-auto p-6 animate-pulse text-stone-500 text-sm">
          Building your report card…
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ background: C.bg, minHeight: '100vh' }}>
        <div className="max-w-2xl mx-auto p-6">
          <div className="rounded-2xl p-4" style={{ background: C.roseBg, border: `1.5px solid ${C.rose}` }}>
            <p className="text-sm font-semibold" style={{ color: C.rose }}>{error || 'Report not available'}</p>
          </div>
          <Link to="/modules" className="mt-3 inline-block text-sm font-semibold" style={{ color: C.indigo }}>
            ← Back to modules
          </Link>
        </div>
      </div>
    );
  }

  const t = report.totals || {};
  const summary = report.summary || {};

  return (
    <div style={{ background: C.bg, minHeight: '100vh' }}>
      <header className="sticky top-0 z-30 backdrop-blur-md"
        style={{ background: 'rgba(255,248,240,0.85)', borderBottom: `1px solid ${C.borderWarm}` }}>
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => navigate(`/modules/${moduleId}`)}
            className="text-sm font-semibold flex items-center gap-1.5"
            style={{ color: C.textMid }}>
            <FaArrowLeft /> Back to module
          </button>
          <span className="ml-auto text-xs font-bold uppercase tracking-wider" style={{ color: C.primaryDark }}>
            Report Card
          </span>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-3xl p-5 md:p-7 mb-5 relative overflow-hidden"
          style={{
            background: `linear-gradient(135deg, ${C.primaryGlow}, #FFFFFF)`,
            border: `2px solid ${C.borderWarm}`,
          }}>
          <div className="flex items-start gap-4 flex-wrap">
            <div className="text-5xl">{report.module_icon || '📚'}</div>
            <div className="flex-1 min-w-[200px]">
              <div className="text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: C.primaryDark }}>
                Module Complete
              </div>
              <h1 className="text-2xl md:text-3xl font-black" style={{ color: C.text }}>
                {report.module_title}
              </h1>
              <div className="mt-2 flex items-center gap-2 text-xs flex-wrap" style={{ color: C.textMid }}>
                <span>📅 Started {report.started_at?.slice(0,10) || '—'}</span>
                {report.completed_at && (
                  <>
                    <span>·</span>
                    <span>✓ Finished {report.completed_at.slice(0,10)}</span>
                  </>
                )}
                <span>·</span>
                <span><FaClock className="inline mr-1" /> {t.time_spent_minutes || 0} min total</span>
              </div>
            </div>
            <div className="flex flex-col items-center justify-center min-w-[110px] rounded-2xl px-4 py-3"
              style={{ background: GRADE_BG[report.grade] || '#F1F5F9', color: GRADE_FG[report.grade] || '#475569' }}>
              <div className="text-[10px] font-bold uppercase tracking-wider opacity-80">Grade</div>
              <div className="text-5xl font-black leading-none my-1">{report.grade}</div>
              <div className="text-[10px] font-semibold opacity-80">{report.composite_score}%</div>
            </div>
          </div>

          {report.mento_summary && (
            <div className="mt-5 rounded-2xl p-4 flex items-start gap-3"
              style={{ background: '#fff', border: `1.5px solid ${C.borderWarm}` }}>
              <div className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-lg"
                style={{ background: `linear-gradient(135deg, ${C.indigo}, ${C.purple})` }}>
                🦊
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] font-bold uppercase tracking-wider mb-0.5" style={{ color: C.indigo }}>
                  Mento says
                </div>
                <p className="text-sm leading-relaxed" style={{ color: C.text }}>{report.mento_summary}</p>
              </div>
            </div>
          )}
        </motion.div>

        {/* Module Composite v2 — 5-channel score */}
        {reportV2?.composite && typeof reportV2.composite.score === 'number' && (
          <motion.section
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl p-4 md:p-5 mb-5"
            style={{ background: C.card, border: `1.5px solid ${C.borderWarm}` }}>
            <div className="flex items-baseline justify-between gap-3 mb-3 flex-wrap">
              <div>
                <h3 className="text-sm font-black uppercase tracking-wider" style={{ color: C.primaryDark }}>
                  📊 {i18n('module.composite.title', 'Module composite')}
                </h3>
                <p className="text-xs mt-0.5" style={{ color: C.textMid }}>
                  {i18n('module.composite.subtitle', '5-channel score across quiz, rubric, reflection, anchored gameplay, and time-on-task.')}
                </p>
              </div>
              <div className="text-4xl font-black leading-none" style={{ color: C.primaryDark }}>
                {Math.round(reportV2.composite.score)}
                <span className="text-sm text-stone-400 font-bold ml-1">/100</span>
              </div>
            </div>
            <div className="space-y-2">
              {Object.entries(reportV2.composite.channels || {}).map(([key, val]) => (
                <ChannelBar
                  key={key}
                  label={i18n(`module.composite.${key}`, key.replace(/_/g, ' '))}
                  value={val}
                  weight={reportV2.composite.weights?.[key]}
                />
              ))}
            </div>

            {/* What changed (v1 vs v2) */}
            {typeof report.composite_score === 'number' && (
              <div className="mt-4 rounded-xl p-3 text-xs flex items-start gap-2"
                style={{ background: C.primaryGlow, border: `1px solid ${C.borderWarm}`, color: C.text }}>
                <span aria-hidden="true">ℹ️</span>
                <span>
                  {i18n(
                    'module.composite.what_changed',
                    'Earlier composite (v1): {{v1}}%. New 5-channel composite (v2): {{v2}}. v2 weights timing, rubric depth, and anchored gameplay alongside quizzes.',
                    { v1: report.composite_score, v2: Math.round(reportV2.composite.score) }
                  )}
                </span>
              </div>
            )}
          </motion.section>
        )}

        {/* Stats grid */}
        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          <StatCard icon="🧪" label="Quiz Average"
            value={t.quiz_average_pct != null ? `${t.quiz_average_pct}%` : '—'}
            sub={`${t.quiz_attempts_total || 0} attempts`} />
          <StatCard icon="📝" label="Worksheets"
            value={`${t.worksheets_filled || 0}/${t.worksheets_total || 0}`}
            sub="filled" />
          <StatCard icon="💭" label="Reflections"
            value={`${t.reflections_filled || 0}/${t.reflections_total || 0}`}
            sub="written" />
          <StatCard icon="🎮" label="Sims Played"
            value={`${t.games_played || 0}`}
            sub={`${t.field_mission_entries || 0} field captures`} />
        </div>

        {/* Skill tally */}
        {Object.keys(report.skill_tally || {}).length > 0 && (
          <div className="rounded-2xl p-4 md:p-5 mb-5"
            style={{ background: C.card, border: `1.5px solid ${C.borderWarm}` }}>
            <h3 className="text-sm font-black uppercase tracking-wider mb-3" style={{ color: C.primaryDark }}>
              <FaBolt className="inline mr-1" /> Skills Trained
            </h3>
            <div className="flex flex-wrap gap-2">
              {Object.entries(report.skill_tally)
                .sort((a, b) => b[1] - a[1])
                .map(([k, v]) => (
                  <span key={k}
                    className="text-xs font-bold px-2.5 py-1.5 rounded-full"
                    style={{ background: C.primaryGlow, color: C.primaryDark }}>
                    {SKILL_LABELS[k] || k} × {v}
                  </span>
                ))}
            </div>
          </div>
        )}

        {/* Per-week breakdown */}
        <div className="rounded-2xl p-4 md:p-5 mb-5"
          style={{ background: C.card, border: `1.5px solid ${C.borderWarm}` }}>
          <h3 className="text-sm font-black uppercase tracking-wider mb-3" style={{ color: C.primaryDark }}>
            <FaTrophy className="inline mr-1" /> Week-by-week
          </h3>
          <div className="space-y-3">
            {(report.weeks || []).map((w) => (
              <div key={w.week_id} className="rounded-xl p-3"
                style={{ background: w.completed ? C.emeraldBg : '#F8FAFC',
                         border: `1.5px solid ${w.completed ? '#86efac' : C.border}` }}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider"
                    style={{ color: w.completed ? C.emerald : C.textMid }}>
                    Week {w.number}
                  </span>
                  <span className="font-bold flex-1 text-sm" style={{ color: C.text }}>{w.title}</span>
                  <span className="text-xs font-bold" style={{ color: C.textMid }}>
                    {w.lessons_completed}/{w.lessons_total} · {fmtMin(w.time_spent_seconds)}
                  </span>
                  {w.completed && <FaCheckCircle className="text-emerald-500" />}
                </div>
                <div className="space-y-1">
                  {(w.lessons || []).map((l) => (
                    <div key={l.lesson_id} className="flex items-center gap-2 text-xs">
                      <span className="w-5">{l.completed ? '✅' : '⚪'}</span>
                      <span>{TYPE_ICON[l.type] || '📄'}</span>
                      <span className="flex-1 truncate" style={{ color: C.textMid }}>
                        {l.title}
                        {l.optional && <span className="ml-1 text-[10px]" style={{ color: '#92400e' }}>⭐ Bonus</span>}
                      </span>
                      {l.quiz && l.quiz.max_score ? (
                        <span className="text-[11px] font-bold"
                          style={{ color: l.quiz.passed ? C.emerald : C.rose }}>
                          {l.quiz.score}/{l.quiz.max_score}
                          {l.quiz.attempts > 1 && <span className="opacity-60"> · {l.quiz.attempts}×</span>}
                        </span>
                      ) : l.field_mission_count != null ? (
                        <span className="text-[11px] font-bold" style={{ color: C.indigo }}>
                          {l.field_mission_count} captures
                        </span>
                      ) : l.runs?.length ? (
                        <span className="text-[11px] font-bold" style={{ color: C.indigo }}>
                          {l.runs.length} run{l.runs.length === 1 ? '' : 's'}
                        </span>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Skill scores (Phase C) */}
        {skillReport?.dimensions && (
          <div className="rounded-2xl p-4 md:p-5 mb-5"
            style={{ background: C.card, border: `1.5px solid ${C.borderWarm}` }}>
            <h3 className="text-sm font-black uppercase tracking-wider mb-3" style={{ color: C.primaryDark }}>
              🧭 Skill Scores
            </h3>
            <div className="space-y-2">
              {Object.entries(skillReport.dimensions).map(([k, v]) => (
                <div key={k}>
                  <div className="flex justify-between text-xs mb-1">
                    <span style={{ color: C.text }}>{DIM_LABELS_FULL[k] || k}</span>
                    <span className="font-bold" style={{ color: C.textMid }}>{v}</span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: '#F1F5F9' }}>
                    <div className="h-full rounded-full"
                      style={{
                        width: `${Math.max(0, Math.min(100, v))}%`,
                        background: `linear-gradient(90deg, ${C.primary}, ${C.primaryDark})`,
                      }} />
                  </div>
                </div>
              ))}
            </div>
            {skillReport.highlights?.length > 0 && (
              <div className="mt-4">
                <div className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: C.textMid }}>
                  Highlights
                </div>
                <ul className="list-disc pl-5 space-y-0.5 text-xs" style={{ color: C.text }}>
                  {skillReport.highlights.map((h) => <li key={h.dimension}>{h.label}</li>)}
                </ul>
              </div>
            )}
            {skillReport.recommendations?.length > 0 && (
              <div className="mt-4">
                <div className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: C.textMid }}>
                  Try next
                </div>
                <ul className="space-y-1 text-xs">
                  {skillReport.recommendations.map((r) => (
                    <li key={r.module_id}>
                      <a className="font-semibold underline" style={{ color: C.indigo }}
                        href={`/modules/${r.module_id}`}>{r.title}</a>
                      <span style={{ color: C.textMid }}> — to grow your {r.because_of.replace(/_/g, ' ')}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Parent-shareable card (Phase C) */}
        <div className="mb-5">
          <ShareCardActions moduleId={moduleId} />
        </div>

        {/* Footer actions */}
        <div className="flex items-center gap-3 flex-wrap">
          <Link to={`/modules/${moduleId}`}
            className="inline-flex items-center gap-2 font-bold text-sm px-4 py-2.5 rounded-xl"
            style={{ background: C.card, color: C.text, border: `1.5px solid ${C.borderWarm}` }}>
            ← Back to module
          </Link>
          <Link to="/modules"
            className="inline-flex items-center gap-2 font-bold text-sm px-4 py-2.5 rounded-xl shadow"
            style={{ background: `linear-gradient(90deg, ${C.primary}, ${C.primaryDark})`, color: '#fff' }}>
            Browse more modules →
          </Link>
        </div>
      </div>
    </div>
  );
}

function ChannelBar({ label, value, weight }) {
  const v = typeof value === 'number' && !Number.isNaN(value)
    ? Math.max(0, Math.min(100, value))
    : 0;
  const w = typeof weight === 'number' && weight > 0 ? Math.round(weight * 100) : null;
  return (
    <div>
      <div className="flex items-center justify-between mb-1 text-xs">
        <span className="font-semibold capitalize" style={{ color: C.text }}>
          {label}
          {w != null && (
            <span className="ml-1.5 text-[10px] font-normal" style={{ color: C.textLight }}>
              ({w}%)
            </span>
          )}
        </span>
        <span className="text-[11px] font-bold" style={{ color: C.textMid }}>
          {Math.round(v)}
        </span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#F1F5F9' }}>
        <div className="h-full rounded-full"
          style={{ width: `${v}%`, background: `linear-gradient(90deg, ${C.primary}, ${C.primaryDark})` }} />
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, sub }) {
  return (
    <div className="rounded-2xl p-4"
      style={{ background: C.card, border: `1.5px solid ${C.borderWarm}` }}>
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-[10px] font-bold uppercase tracking-wider mb-0.5" style={{ color: C.textMid }}>
        {label}
      </div>
      <div className="text-xl font-black" style={{ color: C.text }}>{value}</div>
      {sub && <div className="text-[10px]" style={{ color: C.textLight }}>{sub}</div>}
    </div>
  );
}
