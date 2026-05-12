/**
 * ModuleDetailPage — the lesson player.
 *
 * Visual style mirrors GameDiscoveryPage (warm amber / cream palette) so
 * Modules feels like a first-class citizen alongside Games.
 *
 * Layout:
 *   - Sticky top header  (logo + count chip + action icons row)
 *   - Module hero strip  (icon, title, week chips, progress)
 *   - 3-column body      [left rail | lesson pane | right rail]
 *      • left rail   : week + lesson navigation
 *      • center pane : the active lesson, rendered by type
 *      • right rail  : lesson meta, week checklist, skills, related games, autosave
 *
 * Multi-user safe: reads progress for the current JWT user only.
 * Worksheet answers autosave (debounced).
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaArrowLeft, FaTrophy, FaSignOutAlt, FaBook, FaChartLine,
  FaGraduationCap, FaPlayCircle, FaCheckCircle, FaCircle,
  FaClock, FaBolt, FaLightbulb, FaPenAlt, FaGamepad,
  FaChevronRight, FaCheck, FaListUl, FaCompass, FaLayerGroup, FaTimes,
} from 'react-icons/fa';
import {
  getModule,
  startModule,
  saveLesson,
  completeLesson,
} from '../api/modules';
import WorksheetRenderer from '../components/module/worksheets';
import FieldMissionRenderer from '../components/module/FieldMissionRenderer';
import VoiceLessonRenderer from '../components/module/VoiceLessonRenderer';
import WorksheetRubricResult from '../components/module/WorksheetRubricResult';
import AudioLessonRenderer from '../components/module/AudioLessonRenderer';
import PitchCoachRenderer from '../components/module/PitchCoachRenderer';
import InterviewSimRenderer from '../components/module/InterviewSimRenderer';
import MicroQuestRenderer from '../components/module/MicroQuestRenderer';
import CaseStudyCardRenderer from '../components/module/CaseStudyCardRenderer';
import FailureCardRenderer from '../components/module/FailureCardRenderer';
import CohortLiveSessionCard from '../components/module/CohortLiveSessionCard';
import UnknownLessonRenderer from '../components/module/UnknownLessonRenderer';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import CoinCounter from '../components/ui/CoinCounter';
import NotificationCenter from '../components/ui/NotificationCenter';

/* ═══════════════════════════════════════════════════════════════════════════
   Design tokens — match GameDiscoveryPage warm amber / cream palette
   ═══════════════════════════════════════════════════════════════════════════ */
const C = {
  primary:      '#F59E0B',
  primaryLight: '#FCD34D',
  primaryDark:  '#D97706',
  primaryGlow:  '#FEF3C7',

  bg:        '#FFF8F0',
  bgWarm:    '#FFF5E6',
  card:      '#FFFFFF',
  surface:   '#FEF7ED',
  surfaceAlt:'#FFF1DB',

  text:      '#1C1917',
  textMid:   '#57534E',
  textLight: '#A8A29E',

  border:    '#E7E5E4',
  borderWarm:'#FED7AA',

  indigo:    '#0EA5E9',
  indigoDk:  '#0369A1',
  purple:    '#14B8A6',
  emerald:   '#059669',
  emeraldBg: '#ECFDF5',
  rose:      '#e11d48',
  roseBg:    '#FFF1F2',
};

const TYPE_LABELS = {
  lesson:     { label: 'Lesson',     icon: '📖', color: C.indigo,  bg: '#E0F2FE' },
  worksheet:  { label: 'Worksheet',  icon: '📝', color: C.primary, bg: C.primaryGlow },
  reflection: { label: 'Reflection', icon: '💭', color: C.purple,  bg: '#CCFBF1' },
  game:       { label: 'Game',       icon: '🎮', color: C.emerald, bg: C.emeraldBg },
  quiz:       { label: 'Quiz',       icon: '🧪', color: '#0ea5e9', bg: '#E0F2FE' },
  assessment: { label: 'Assessment', icon: '🎯', color: C.rose,    bg: C.roseBg },
  field_mission: { label: 'Field Mission', icon: '🕵️', color: C.indigoDk, bg: '#E0F2FE' },
  voice_recording: { label: 'Speak', icon: '🎙️', color: C.indigoDk, bg: '#EEF2FF' },
};

const DIM_ICONS = {
  creativity: '🎨',
  strategic_thinking: '🧠',
  empathy: '❤️',
  resilience: '💪',
  ethical_reasoning: '⚖️',
  risk_tolerance: '🎲',
  delayed_gratification: '⏳',
  adaptability: '🔄',
};

/* ─── Inline mini-quiz (1-question MCQ with reveal) ─── */
function MiniQuiz({ quiz }) {
  const [picked, setPicked] = useState(null);
  if (!quiz?.options) return null;
  const correctIdx = quiz.correct_index ?? 0;
  return (
    <div className="rounded-2xl p-4 border-2"
      style={{ background: '#F0FDF4', borderColor: '#86efac' }}>
      <div className="text-[11px] font-black uppercase tracking-wider mb-2"
        style={{ color: '#15803d' }}>
        🧪 Quick Check
      </div>
      <p className="text-base font-semibold mb-3" style={{ color: C.text }}>
        {quiz.question}
      </p>
      <div className="space-y-2">
        {quiz.options.map((opt, i) => {
          const isPicked = picked === i;
          const isCorrect = i === correctIdx;
          const showResult = picked !== null;
          let bg = C.card, color = C.text, border = C.borderWarm;
          if (showResult && isCorrect) { bg = '#DCFCE7'; color = '#15803d'; border = '#86efac'; }
          else if (showResult && isPicked && !isCorrect) { bg = C.roseBg; color = C.rose; border = '#fda4af'; }
          return (
            <button key={i} type="button"
              disabled={picked !== null}
              onClick={() => setPicked(i)}
              className="w-full text-left rounded-xl px-3 py-2.5 text-sm font-medium flex items-center gap-2 transition-colors"
              style={{ background: bg, color, border: `1.5px solid ${border}` }}>
              <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                style={{ background: showResult && isCorrect ? '#22c55e' : showResult && isPicked ? C.rose : C.surface, color: showResult ? '#fff' : C.textMid }}>
                {showResult && isCorrect ? '✓' : showResult && isPicked ? '✕' : String.fromCharCode(65 + i)}
              </span>
              <span className="flex-1">{opt}</span>
            </button>
          );
        })}
      </div>
      {picked !== null && quiz.explanation && (
        <motion.div
          initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
          className="mt-3 rounded-xl p-3 text-sm"
          style={{ background: '#FFFFFF', border: `1px solid ${C.borderWarm}`, color: C.textMid }}>
          <strong style={{ color: picked === correctIdx ? '#15803d' : C.primaryDark }}>
            {picked === correctIdx ? '✅ Correct! ' : '💡 '}
          </strong>
          {quiz.explanation}
        </motion.div>
      )}
    </div>
  );
}

/* ─── Full multi-question Quiz (used for weekly checkpoint quizzes) ─── */
function Quiz({ schema, value, onChange, onResult }) {
  const fields = schema?.fields || [];
  const passThreshold = schema?.pass_threshold ?? 0.6; // default 60% to pass
  const [submitted, setSubmitted] = useState(false);

  const answers = value || {};
  const setAnswer = (id, v) => {
    const next = { ...answers, [id]: v };
    onChange?.(next);
  };

  const allAnswered = fields.every((f) => answers[f.id] !== undefined && answers[f.id] !== null && answers[f.id] !== '');
  const correctCount = fields.filter((f) => answers[f.id] === f.correct).length;
  const total = fields.length;
  const pct = total > 0 ? correctCount / total : 0;
  const passed = pct >= passThreshold;

  function handleSubmit() {
    setSubmitted(true);
    onResult?.({
      passed,
      score: correctCount,
      max_score: total,
      ratio: pct,
      threshold: passThreshold,
    });
  }

  function handleReset() {
    setSubmitted(false);
    onChange?.({});
    onResult?.(null);
  }

  return (
    <div className="space-y-5">
      {schema?.intro && (
        <div className="rounded-2xl p-4 border-l-4"
          style={{ background: '#E0F2FE', borderColor: '#0ea5e9' }}>
          <p className="text-sm" style={{ color: '#075985' }}>🧪 {schema.intro}</p>
        </div>
      )}

      {fields.map((f, idx) => {
        const picked = answers[f.id];
        const isCorrect = submitted && picked === f.correct;
        const isWrong = submitted && picked !== undefined && picked !== f.correct;
        return (
          <div key={f.id} className="rounded-2xl p-4"
            style={{ background: C.card, border: `1.5px solid ${C.borderWarm}` }}>
            <div className="flex items-start gap-2 mb-3">
              <span className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-black"
                style={{ background: C.primaryGlow, color: C.primaryDark }}>
                {idx + 1}
              </span>
              <p className="text-base font-semibold flex-1" style={{ color: C.text }}>{f.question}</p>
              {submitted && (
                <span className="text-lg flex-shrink-0">
                  {isCorrect ? '✅' : isWrong ? '❌' : ''}
                </span>
              )}
            </div>
            <div className="space-y-2">
              {(f.options || []).map((opt) => {
                const isPicked = picked === opt.value;
                const isAnswerCorrect = submitted && opt.value === f.correct;
                const isPickedWrong = submitted && isPicked && opt.value !== f.correct;
                let bg = C.card, color = C.text, border = C.borderWarm;
                if (isAnswerCorrect) { bg = '#DCFCE7'; color = '#15803d'; border = '#86efac'; }
                else if (isPickedWrong) { bg = C.roseBg; color = C.rose; border = '#fda4af'; }
                else if (!submitted && isPicked) { bg = C.primaryGlow; color = C.primaryDark; border = C.primaryLight; }
                return (
                  <button key={opt.value} type="button"
                    disabled={submitted}
                    onClick={() => setAnswer(f.id, opt.value)}
                    className="w-full text-left rounded-xl px-3 py-2.5 text-sm font-medium flex items-center gap-2 transition-colors"
                    style={{ background: bg, color, border: `1.5px solid ${border}` }}>
                    <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0"
                      style={{
                        background: isPicked || isAnswerCorrect ? (isAnswerCorrect ? '#22c55e' : isPickedWrong ? C.rose : C.primary) : C.surface,
                        color: isPicked || isAnswerCorrect ? '#fff' : C.textMid,
                      }}>
                      {isAnswerCorrect ? '✓' : isPickedWrong ? '✕' : opt.value.toUpperCase()}
                    </span>
                    <span className="flex-1">{opt.label}</span>
                  </button>
                );
              })}
            </div>
            {submitted && f.explanation && (
              <motion.div
                initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                className="mt-3 rounded-xl p-3 text-sm"
                style={{ background: C.surface, border: `1px solid ${C.borderWarm}`, color: C.textMid }}>
                <strong style={{ color: isCorrect ? '#15803d' : C.primaryDark }}>
                  {isCorrect ? '✅ Correct! ' : '💡 '}
                </strong>
                {f.explanation}
              </motion.div>
            )}
          </div>
        );
      })}

      {!submitted ? (
        <button type="button" onClick={handleSubmit}
          disabled={!allAnswered}
          className="w-full inline-flex items-center justify-center gap-2 font-black text-base px-5 py-3 rounded-2xl shadow transition-all disabled:opacity-50"
          style={{
            background: `linear-gradient(90deg, ${C.indigo}, ${C.purple})`,
            color: '#fff',
          }}>
          {allAnswered ? '🧪 Submit Quiz' : `Answer all ${total} questions to submit`}
        </button>
      ) : (
        <div className="rounded-2xl p-5 text-center"
          style={{
            background: passed
              ? `linear-gradient(135deg, ${C.emeraldBg}, #DCFCE7)`
              : `linear-gradient(135deg, ${C.roseBg}, #FFE4E6)`,
            border: `2px solid ${passed ? '#86efac' : '#fda4af'}`,
          }}>
          <div className="text-4xl mb-2">{passed ? '🎉' : '🔁'}</div>
          <div className="text-2xl font-black mb-1"
            style={{ color: passed ? '#15803d' : C.rose }}>
            {correctCount} / {total} correct
          </div>
          <p className="text-sm mb-3" style={{ color: passed ? '#166534' : C.rose }}>
            {passed
              ? 'Nice work — you cleared the checkpoint!'
              : `You need ${Math.ceil(passThreshold * total)} correct to pass. Review and try again.`}
          </p>
          <button type="button" onClick={handleReset}
            className="text-xs font-bold px-4 py-2 rounded-xl"
            style={{ background: C.card, color: C.textMid, border: `1.5px solid ${C.borderWarm}` }}>
            🔄 Reset & retry
          </button>
        </div>
      )}
    </div>
  );
}

/* ─── Lesson body renderer (read-only content blocks) ─── */
function LessonContent({ content }) {
  if (!content) return null;
  return (
    <div className="space-y-4">
      {/* Hero image — illustrations or photos at the top of the lesson */}
      {content.image_url && (
        <div className="rounded-2xl overflow-hidden"
          style={{ border: `1.5px solid ${C.borderWarm}` }}>
          <img src={content.image_url} alt={content.image_alt || ''}
            className="w-full h-auto block"
            style={{ maxHeight: '320px', objectFit: 'cover' }}
            onError={(e) => { e.target.parentElement.style.display = 'none'; }} />
        </div>
      )}

      {content.intro && (
        <p className="text-base md:text-lg leading-relaxed" style={{ color: C.text }}>
          {content.intro}
        </p>
      )}

      {/* Mento speech bubble — coach-style direct address */}
      {content.mento_says && (
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-2xl shadow-md"
            style={{ background: `linear-gradient(135deg, ${C.indigo}, ${C.purple})` }}>
            🦊
          </div>
          <div className="flex-1 rounded-2xl rounded-tl-none p-3 relative"
            style={{ background: '#E0F2FE', border: `1.5px solid #bae6fd` }}>
            <div className="text-[10px] font-black uppercase tracking-wider mb-0.5"
              style={{ color: C.indigoDk }}>
              MENTO SAYS
            </div>
            <p className="text-sm md:text-base font-medium leading-relaxed" style={{ color: '#1e1b4b' }}>
              {content.mento_says}
            </p>
          </div>
        </div>
      )}

      {content.question && (
        <div className="rounded-2xl p-4 border-l-4"
          style={{ background: '#E0F2FE', borderColor: C.indigo }}>
          <p className="text-base font-semibold" style={{ color: C.indigoDk }}>
            🤔 {content.question}
          </p>
        </div>
      )}

      {content.cards && (
        <div className="grid sm:grid-cols-2 gap-3">
          {content.cards.map((c, i) => (
            <div key={i} className="rounded-2xl p-4 transition-transform hover:-translate-y-0.5"
              style={{
                background: C.card,
                border: `1.5px solid ${C.borderWarm}`,
                boxShadow: '0 1px 6px rgba(245,158,11,0.06)',
              }}>
              <div className="text-3xl mb-1.5">{c.icon}</div>
              <div className="font-bold mb-1" style={{ color: C.text }}>{c.title}</div>
              <p className="text-sm leading-relaxed" style={{ color: C.textMid }}>{c.body}</p>
            </div>
          ))}
        </div>
      )}

      {content.myths && (
        <div className="space-y-3">
          {content.myths.map((m, i) => (
            <div key={i} className="rounded-2xl overflow-hidden"
              style={{ border: `1.5px solid ${C.borderWarm}` }}>
              <div className="p-3" style={{ background: C.roseBg }}>
                <div className="text-[11px] font-bold mb-0.5" style={{ color: C.rose }}>❌ MYTH</div>
                <div className="text-sm font-medium" style={{ color: C.text }}>{m.myth}</div>
              </div>
              <div className="p-3 border-t" style={{ background: C.emeraldBg, borderColor: C.borderWarm }}>
                <div className="text-[11px] font-bold mb-0.5" style={{ color: C.emerald }}>✅ REALITY</div>
                <div className="text-sm font-medium" style={{ color: C.text }}>{m.reality}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {content.examples && (
        <div className="space-y-2">
          {content.examples.map((ex, i) => (
            <div key={i}
              className="flex items-center gap-3 rounded-xl p-3"
              style={{ background: C.surface, border: `1px solid ${C.borderWarm}` }}>
              <div className="text-sm font-medium flex-1" style={{ color: C.rose }}>
                😤 {ex.complaint}
              </div>
              <FaChevronRight className="text-amber-400 text-xs" />
              <div className="text-sm font-medium flex-1" style={{ color: C.emerald }}>
                💡 {ex.idea}
              </div>
            </div>
          ))}
        </div>
      )}

      {content.tests && (
        <div className="grid sm:grid-cols-3 gap-3">
          {content.tests.map((t, i) => (
            <div key={i} className="rounded-2xl p-4 text-center"
              style={{ background: C.card, border: `1.5px solid ${C.borderWarm}` }}>
              <div className="text-3xl mb-1">{t.icon}</div>
              <div className="font-bold mb-1" style={{ color: C.text }}>{t.name} TEST</div>
              <p className="text-sm" style={{ color: C.textMid }}>{t.question}</p>
            </div>
          ))}
        </div>
      )}

      {content.example_chain && (
        <div className="space-y-2">
          {content.example_chain.map((row, i) => (
            <div key={i} className="rounded-xl p-3 border-l-4"
              style={{ background: C.surface, borderColor: C.indigo }}>
              <div className="text-[11px] font-bold" style={{ color: C.indigo }}>WHY #{i + 1}</div>
              <div className="text-sm font-semibold mt-0.5" style={{ color: C.text }}>{row.why}</div>
              <div className="text-sm mt-1" style={{ color: C.textMid }}>A: {row.answer}</div>
            </div>
          ))}
        </div>
      )}

      {content.sources && (
        <div className="grid sm:grid-cols-2 gap-3">
          {content.sources.map((s, i) => (
            <div key={i} className="rounded-2xl p-4"
              style={{ background: C.card, border: `1.5px solid ${C.borderWarm}` }}>
              <div className="text-3xl mb-1">{s.icon}</div>
              <div className="font-bold mb-1" style={{ color: C.text }}>{s.title}</div>
              <p className="text-sm" style={{ color: C.textMid }}>{s.body}</p>
            </div>
          ))}
        </div>
      )}

      {content.value_axes && (
        <div className="grid sm:grid-cols-2 gap-3">
          {content.value_axes.map((v, i) => (
            <div key={i} className="rounded-2xl p-4"
              style={{ background: C.card, border: `1.5px solid ${C.borderWarm}` }}>
              <div className="text-3xl mb-1">{v.icon}</div>
              <div className="font-bold mb-1" style={{ color: C.text }}>{v.title}</div>
              <p className="text-sm" style={{ color: C.textMid }}>{v.body}</p>
            </div>
          ))}
        </div>
      )}

      {content.parts && (
        <div className="space-y-2">
          {content.parts.map((p, i) => (
            <div key={i} className="rounded-xl p-3 border-l-4"
              style={{ background: '#CCFBF1', borderColor: C.purple }}>
              <div className="text-[11px] font-bold" style={{ color: C.purple }}>
                PART {i + 1} · {p.duration} · {p.name}
              </div>
              <div className="text-sm italic mt-1" style={{ color: C.text }}>"{p.template}"</div>
            </div>
          ))}
        </div>
      )}

      {content.stories && (
        <div className="space-y-2">
          {content.stories.map((s, i) => (
            <div key={i} className="rounded-xl p-3 border-l-4"
              style={{ background: C.surfaceAlt, borderColor: C.primary }}>
              <div className="font-bold" style={{ color: C.text }}>{s.name}</div>
              <p className="text-sm" style={{ color: C.textMid }}>{s.moment}</p>
            </div>
          ))}
        </div>
      )}

      {content.rule && (
        <div className="rounded-2xl p-4 border-2"
          style={{
            background: `linear-gradient(135deg, ${C.primaryGlow}, ${C.surfaceAlt})`,
            borderColor: C.primaryLight,
          }}>
          <p className="text-base font-bold" style={{ color: C.primaryDark }}>📏 {content.rule}</p>
        </div>
      )}

      {content.story_hook && (
        <div className="rounded-2xl p-4 border-l-4"
          style={{ background: '#CCFBF1', borderColor: C.purple }}>
          <p className="text-sm italic" style={{ color: C.text }}>📖 {content.story_hook}</p>
        </div>
      )}

      {/* Pillars — same shape as cards, different visual emphasis */}
      {content.pillars && (
        <div className="grid sm:grid-cols-3 gap-3">
          {content.pillars.map((p, i) => (
            <div key={i} className="rounded-2xl p-4 text-center"
              style={{
                background: `linear-gradient(180deg, ${C.surface}, ${C.card})`,
                border: `1.5px solid ${C.borderWarm}`,
                boxShadow: '0 1px 6px rgba(245,158,11,0.06)',
              }}>
              <div className="text-3xl mb-1">{p.icon}</div>
              <div className="font-bold text-sm" style={{ color: C.primaryDark }}>{p.title}</div>
              <p className="text-xs mt-1 leading-relaxed" style={{ color: C.textMid }}>{p.body}</p>
            </div>
          ))}
        </div>
      )}

      {/* Founder spotlight — bio card for real entrepreneurs */}
      {content.founder_spotlight && (
        <div className="rounded-2xl overflow-hidden"
          style={{ border: `2px solid ${C.primaryLight}` }}>
          <div className="px-4 py-2 text-[10px] font-black uppercase tracking-widest"
            style={{ background: C.primaryGlow, color: C.primaryDark }}>
            🌟 Founder Spotlight
          </div>
          <div className="p-4 flex gap-4 items-start" style={{ background: C.card }}>
            <div className="flex-shrink-0 text-5xl">{content.founder_spotlight.emoji || '👤'}</div>
            <div className="flex-1 min-w-0">
              <div className="font-black text-base" style={{ color: C.text }}>
                {content.founder_spotlight.name}
              </div>
              <div className="text-xs font-semibold mb-2" style={{ color: C.primaryDark }}>
                {content.founder_spotlight.company}
              </div>
              <p className="text-sm leading-relaxed" style={{ color: C.textMid }}>
                {content.founder_spotlight.story}
              </p>
              {content.founder_spotlight.lesson && (
                <div className="mt-2 text-xs italic" style={{ color: C.indigoDk }}>
                  💡 {content.founder_spotlight.lesson}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Quiz — 1-question MCQ check */}
      {content.quiz && <MiniQuiz quiz={content.quiz} />}

      {/* Week summary — bullets recap + try-this-with-family */}
      {content.week_summary && (
        <div className="rounded-2xl p-4 border-2"
          style={{
            background: `linear-gradient(135deg, ${C.emeraldBg}, ${C.surface})`,
            borderColor: '#86efac',
          }}>
          <div className="text-[11px] font-black uppercase tracking-wider mb-2"
            style={{ color: C.emerald }}>
            ✅ Week Recap
          </div>
          {content.week_summary.points && (
            <ul className="space-y-1.5 mb-3">
              {content.week_summary.points.map((pt, i) => (
                <li key={i} className="flex items-start gap-2 text-sm" style={{ color: C.text }}>
                  <span className="text-emerald-600 mt-0.5">✓</span>
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          )}
          {content.week_summary.try_this && (
            <div className="rounded-xl p-3 text-sm"
              style={{ background: C.card, border: `1px solid ${C.borderWarm}`, color: C.textMid }}>
              <strong style={{ color: C.primaryDark }}>👨‍👩‍👧 Try this with family: </strong>
              {content.week_summary.try_this}
            </div>
          )}
        </div>
      )}

      {content.key_takeaway && (
        <div className="rounded-2xl p-4 border-2"
          style={{
            background: `linear-gradient(135deg, #E0F2FE, #CCFBF1)`,
            borderColor: C.indigo,
          }}>
          <div className="text-[11px] font-bold uppercase tracking-wide mb-1"
            style={{ color: C.indigo }}>
            ⭐ Key Takeaway
          </div>
          <p className="text-base font-semibold" style={{ color: C.indigoDk }}>
            {content.key_takeaway}
          </p>
        </div>
      )}
    </div>
  );
}

/* ─── Right rail building blocks ─── */
function RailCard({ title, icon, children }) {
  return (
    <div className="rounded-2xl p-4 mb-3"
      style={{
        background: C.card,
        border: `1.5px solid ${C.borderWarm}`,
        boxShadow: '0 1px 4px rgba(245,158,11,0.05)',
      }}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-base">{icon}</span>
        <h4 className="text-[11px] font-black uppercase tracking-wider" style={{ color: C.primaryDark }}>
          {title}
        </h4>
      </div>
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════════════════════ */
export default function ModuleDetailPage() {
  const { moduleId } = useParams();
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { t } = useTranslation();

  const [module, setModule] = useState(null);
  const [progress, setProgress] = useState(null);
  const [activeLessonId, setActiveLessonId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [answers, setAnswers] = useState({});
  const [saving, setSaving] = useState(false);
  const [coachingToast, setCoachingToast] = useState(null); // { xp, message, skills }
  const [aiFeedback, setAiFeedback] = useState(null); // { strengths, improvements, next_step, encouragement, quality_score }
  const [rubric, setRubric] = useState(null); // { score, strengths, improvements, dim_signals }
  const [pendingNextLessonId, setPendingNextLessonId] = useState(null);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [fieldMissionCount, setFieldMissionCount] = useState(0);
  // Per-active-lesson quiz state — { passed, score, max_score, ratio, threshold }
  const [quizState, setQuizState] = useState(null);
  const saveTimer = useRef(null);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const data = await getModule(moduleId);
        if (cancel) return;
        if (!data?.module) {
          throw new Error('This module is not available yet. Ask your teacher to assign it.');
        }
        setModule(data.module);
        let prog = data.progress;
        if (!prog || !prog.started_at) {
          const r = await startModule(moduleId);
          prog = r?.progress;
        }
        setProgress(prog);
        const flat = (data.module.weeks || []).flatMap((w) => w.lessons || []);
        const cur =
          prog?.current_lesson_id || (flat[0] && flat[0].lesson_id) || null;
        setActiveLessonId(cur);
        const lessonAnswers =
          prog?.worksheets?.[cur]?.answers ||
          prog?.reflections?.[cur]?.answers ||
          {};
        setAnswers(lessonAnswers);
      } catch (e) {
        if (!cancel) setError(e.response?.data?.error || e.message);
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => { cancel = true; };
  }, [moduleId]);

  const flatLessons = useMemo(() => {
    if (!module) return [];
    return (module.weeks || []).flatMap((w) =>
      (w.lessons || []).map((l) => ({ ...l, week: w }))
    );
  }, [module]);

  const activeLesson = useMemo(
    () => flatLessons.find((l) => l.lesson_id === activeLessonId) || null,
    [flatLessons, activeLessonId]
  );

  const completedSet = useMemo(
    () => new Set(progress?.completed_lesson_ids || []),
    [progress]
  );

  const quizMap = useMemo(() => progress?.quizzes || {}, [progress]);

  // Week unlock state — mirrors backend _is_week_unlocked.
  // Linear progression (default): a week is locked until every required
  // lesson (and any quiz/assessment with passed=true) in all prior weeks
  // is complete. progression='free' on the module disables gating.
  const weekUnlockMap = useMemo(() => {
    const map = {};
    if (!module) return map;
    const linear = (module.progression || 'linear').toLowerCase() === 'linear';
    const weeks = module.weeks || [];
    let priorOk = true;
    for (let i = 0; i < weeks.length; i++) {
      const w = weeks[i];
      map[w.week_id] = !linear || i === 0 ? true : priorOk;
      // Compute whether THIS week is fully complete (for the next iteration)
      const required = (w.lessons || []).filter((l) => !l.optional);
      const allDone = required.every((l) => {
        if (!completedSet.has(l.lesson_id)) return false;
        if (l.type === 'quiz' || l.type === 'assessment') {
          const q = quizMap[l.lesson_id];
          if (!q?.passed) return false;
        }
        return true;
      });
      priorOk = priorOk && allDone;
    }
    return map;
  }, [module, completedSet, quizMap]);

  const isLessonUnlocked = (lesson) => {
    if (!lesson) return false;
    const wid = lesson.week?.week_id || lesson.week_id;
    return weekUnlockMap[wid] !== false;
  };

  const activeIdx = useMemo(
    () => flatLessons.findIndex((l) => l.lesson_id === activeLessonId),
    [flatLessons, activeLessonId]
  );

  const [lockToast, setLockToast] = useState(null);
  function switchLesson(lessonId) {
    const target = flatLessons.find((l) => l.lesson_id === lessonId);
    if (target && !isLessonUnlocked(target)) {
      // Find the prior week the student should finish first.
      const wid = target.week?.week_id || target.week_id;
      const idx = (module?.weeks || []).findIndex((w) => w.week_id === wid);
      const priorWeek = idx > 0 ? module.weeks[idx - 1] : null;
      setLockToast(
        priorWeek
          ? `Finish Week ${priorWeek.number}: "${priorWeek.title}" first to unlock this.`
          : 'This lesson is locked.'
      );
      setTimeout(() => setLockToast(null), 3500);
      return;
    }
    setActiveLessonId(lessonId);
    setRubric(null);
    const saved =
      progress?.worksheets?.[lessonId]?.answers ||
      progress?.reflections?.[lessonId]?.answers ||
      progress?.quizzes?.[lessonId]?.answers ||
      {};
    setAnswers(saved);
    // Hydrate quizState from server record if present (e.g. resuming a passed quiz)
    const qrec = progress?.quizzes?.[lessonId];
    setQuizState(qrec ? {
      passed: !!qrec.passed,
      score: qrec.score,
      max_score: qrec.max_score,
      ratio: qrec.ratio,
      threshold: qrec.pass_threshold,
    } : null);
    // Smooth scroll the main pane to top
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  function handleAnswersChange(newAnswers) {
    setAnswers(newAnswers);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      try {
        setSaving(true);
        await saveLesson(moduleId, activeLessonId, newAnswers);
      } catch (e) {
        // silent
      } finally {
        setSaving(false);
      }
    }, 1000);
  }

  async function handleComplete(extraPayload = {}) {
    if (!activeLessonId) return;
    try {
      const payload = { ...extraPayload };
      if (
        ['worksheet', 'reflection', 'quiz', 'assessment', 'voice_recording'].includes(activeLesson?.type) &&
        Object.keys(answers || {}).length
      ) {
        payload.answers = answers;
      }
      // Quiz/assessment: include score + pass for backend to store and gate.
      if (
        ['quiz', 'assessment'].includes(activeLesson?.type) &&
        quizState
      ) {
        payload.score = quizState.score;
        payload.max_score = quizState.max_score;
        payload.passed = !!quizState.passed;
      }
      const r = await completeLesson(moduleId, activeLessonId, payload);
      // Server signals quiz_failed when below threshold — don't advance.
      if (r?.quiz_failed) {
        setLockToast(r.message || 'You need to pass this checkpoint to continue.');
        setTimeout(() => setLockToast(null), 3500);
        if (r.summary) setProgress((p) => ({ ...(p || {}), ...r.progress }));
        return;
      }
      setProgress(r.progress);

      // Coaching toast — celebrate XP + show Mento's note before advancing
      const xpGain = r.xp_awarded ?? 25;
      const mentoNote = r.coaching_message ||
        activeLesson?.coaching_moment ||
        "Nice work — every reps trains your entrepreneur brain.";
      const skillGains = r.skill_gains || activeLesson?.skill_tags || [];
      setCoachingToast({ xp: xpGain, message: mentoNote, skills: skillGains });
      setTimeout(() => setCoachingToast(null), 4500);

      const next =
        r.progress?.current_lesson_id ||
        flatLessons.find((l) => !r.progress.completed_lesson_ids.includes(l.lesson_id))
          ?.lesson_id;

      // If backend returned a rubric for this worksheet, surface it inline.
      if (r?.rubric && typeof r.rubric.score === 'number') {
        setRubric(r.rubric);
      }

      // If backend returned AI feedback for this submission, surface a richer
      // modal and defer the auto-advance until the student dismisses it.
      const fb = r?.ai_feedback;
      const hasFeedback = fb && (
        (Array.isArray(fb.strengths) && fb.strengths.length) ||
        (Array.isArray(fb.improvements) && fb.improvements.length) ||
        fb.next_step || fb.encouragement
      );
      if (hasFeedback) {
        setAiFeedback(fb);
        setPendingNextLessonId(next && next !== activeLessonId ? next : null);
      } else if (next && next !== activeLessonId) {
        // small delay so the toast is visible before content swaps
        setTimeout(() => switchLesson(next), 900);
      }
    } catch (e) {
      alert(e.response?.data?.error || 'Could not save. Try again.');
    }
  }

  function handleStartGame() {
    if (!activeLesson?.game_id) return;
    const url = `/play/${activeLesson.game_id}?from_module=${moduleId}&lesson=${activeLessonId}`;
    navigate(url);
  }

  /* ── Loading / error states ── */
  if (loading) {
    return (
      <div style={{ background: C.bg, minHeight: '100vh' }}>
        <div className="max-w-7xl mx-auto p-6">
          <div className="animate-pulse text-stone-500 text-sm">Loading module…</div>
          <div className="mt-4 grid md:grid-cols-[260px_1fr_280px] gap-5">
            <div className="h-96 rounded-2xl bg-white/60" style={{ border: `1px solid ${C.borderWarm}` }} />
            <div className="h-96 rounded-2xl bg-white/60" style={{ border: `1px solid ${C.borderWarm}` }} />
            <div className="h-96 rounded-2xl bg-white/60 hidden lg:block" style={{ border: `1px solid ${C.borderWarm}` }} />
          </div>
        </div>
      </div>
    );
  }

  if (error || !module) {
    return (
      <div style={{ background: C.bg, minHeight: '100vh' }}>
        <div className="max-w-3xl mx-auto p-6">
          <div className="rounded-2xl p-4" style={{ background: C.roseBg, border: `1.5px solid ${C.rose}` }}>
            <p className="text-sm font-semibold" style={{ color: C.rose }}>{error || 'Module not found'}</p>
          </div>
          <Link to="/modules" className="mt-3 inline-block text-sm font-semibold" style={{ color: C.indigo }}>
            ← Back to modules
          </Link>
        </div>
      </div>
    );
  }

  /* ── Computed UI values ── */
  const totalLessons = flatLessons.length;
  const doneLessons = progress?.completed_lesson_ids?.length || 0;
  const summaryPct = Math.round((100 * doneLessons) / Math.max(1, totalLessons));
  const isCompleted = !!progress?.completed_at;
  const isLessonComplete = activeLessonId ? completedSet.has(activeLessonId) : false;

  const lessonType = activeLesson?.type || 'lesson';
  const typeMeta = TYPE_LABELS[lessonType] || TYPE_LABELS.lesson;

  // Active week computed
  const activeWeek = activeLesson?.week;
  const weekLessons = activeWeek?.lessons || [];
  const weekDone = weekLessons.filter((l) => completedSet.has(l.lesson_id)).length;
  const weekPct = Math.round((100 * weekDone) / Math.max(1, weekLessons.length));

  // Skills & target dims (lesson-level if present, else module-level)
  const lessonSkills = activeLesson?.skill_tags || activeLesson?.target_skills || [];
  const moduleSkills = module.target_skills || [];
  const skillsToShow = lessonSkills.length ? lessonSkills : moduleSkills;

  // Related games (game-type lessons in the module that are not the active one)
  const relatedGames = flatLessons
    .filter((l) => l.type === 'game' && l.lesson_id !== activeLessonId)
    .slice(0, 4);

  return (
    <div style={{ background: C.bg, minHeight: '100vh' }}>
      {/* ═══════════ COACHING TOAST — fires on lesson complete ═══════════ */}
      <AnimatePresence>
        {coachingToast && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="fixed top-20 right-4 z-50 max-w-sm w-[calc(100%-2rem)] sm:w-96 rounded-2xl shadow-2xl overflow-hidden"
            style={{ background: '#fff', border: `2px solid ${C.primaryLight}` }}>
            <div className="px-4 py-2 flex items-center gap-2"
              style={{ background: `linear-gradient(90deg, ${C.primary}, ${C.primaryDark})`, color: '#fff' }}>
              <span className="text-lg">⭐</span>
              <span className="text-sm font-black flex-1">+{coachingToast.xp} XP earned</span>
              <button onClick={() => setCoachingToast(null)}
                className="text-white/80 hover:text-white text-sm" aria-label="Dismiss">✕</button>
            </div>
            <div className="p-3 flex items-start gap-2">
              <div className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-lg"
                style={{ background: `linear-gradient(135deg, ${C.indigo}, ${C.purple})` }}>
                🦊
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] font-bold uppercase tracking-wider"
                  style={{ color: C.indigoDk }}>
                  Mento says
                </div>
                <p className="text-sm leading-snug" style={{ color: C.text }}>
                  {coachingToast.message}
                </p>
                {coachingToast.skills?.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {coachingToast.skills.slice(0, 3).map((s) => (
                      <span key={s}
                        className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                        style={{ background: C.primaryGlow, color: C.primaryDark }}>
                        {DIM_ICONS[s] || '✨'} +{s.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════ WORKSHEET RUBRIC RESULT — inline panel after submit ═══════════ */}
      {rubric && (
        <div className="fixed bottom-6 right-6 z-[55] w-80 shadow-2xl rounded-2xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2"
            style={{ background: 'linear-gradient(90deg, #6366f1, #8b5cf6)', color: '#fff' }}>
            <span className="text-sm font-black">{t('worksheet.rubric_feedback', 'Rubric Feedback')}</span>
            <button
              onClick={() => setRubric(null)}
              className="text-white/80 hover:text-white text-lg leading-none"
              aria-label="Close rubric panel">
              ×
            </button>
          </div>
          <div className="bg-white">
            <WorksheetRubricResult rubric={rubric} />
          </div>
        </div>
      )}

      {/* ═══════════ AI FEEDBACK MODAL — shown after worksheet/reflection submit ═══════════ */}
      <AnimatePresence>
        {aiFeedback && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-center justify-center p-4"
            style={{ background: 'rgba(15, 23, 42, 0.55)' }}
            onClick={() => {
              const nx = pendingNextLessonId;
              setAiFeedback(null);
              setPendingNextLessonId(null);
              if (nx) setTimeout(() => switchLesson(nx), 100);
            }}>
            <motion.div
              initial={{ y: 30, scale: 0.96, opacity: 0 }}
              animate={{ y: 0, scale: 1, opacity: 1 }}
              exit={{ y: 10, scale: 0.97, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 220, damping: 22 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden bg-white"
              style={{ border: `2px solid ${C.primaryLight}` }}>
              <div className="px-5 py-3 flex items-center gap-2"
                style={{ background: `linear-gradient(90deg, ${C.indigo}, ${C.purple})`, color: '#fff' }}>
                <span className="text-xl">🦊</span>
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] font-black uppercase tracking-wider text-white/80">
                    Mento reviewed your work
                  </div>
                  <div className="text-sm font-black truncate">Personalized feedback</div>
                </div>
                {typeof aiFeedback.quality_score === 'number' && (
                  <div className="text-xs font-black px-2 py-1 rounded-full"
                    style={{ background: 'rgba(255,255,255,0.18)' }}>
                    {Math.round(aiFeedback.quality_score)}/100
                  </div>
                )}
              </div>
              <div className="p-5 space-y-3 max-h-[70vh] overflow-y-auto">
                {Array.isArray(aiFeedback.strengths) && aiFeedback.strengths.length > 0 && (
                  <div>
                    <div className="text-[11px] font-black uppercase tracking-wider mb-1.5"
                      style={{ color: C.green || '#16a34a' }}>
                      ✨ What you did well
                    </div>
                    <ul className="space-y-1.5">
                      {aiFeedback.strengths.slice(0, 4).map((s, i) => (
                        <li key={i} className="text-sm flex gap-2" style={{ color: C.text }}>
                          <span className="flex-shrink-0">•</span>
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {Array.isArray(aiFeedback.improvements) && aiFeedback.improvements.length > 0 && (
                  <div>
                    <div className="text-[11px] font-black uppercase tracking-wider mb-1.5"
                      style={{ color: C.amberDk || '#b45309' }}>
                      🎯 Try next time
                    </div>
                    <ul className="space-y-1.5">
                      {aiFeedback.improvements.slice(0, 4).map((s, i) => (
                        <li key={i} className="text-sm flex gap-2" style={{ color: C.text }}>
                          <span className="flex-shrink-0">•</span>
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {aiFeedback.next_step && (
                  <div className="rounded-xl p-3"
                    style={{ background: C.primaryGlow || '#fef3c7', border: `1px solid ${C.primaryLight}` }}>
                    <div className="text-[10px] font-black uppercase tracking-wider mb-1"
                      style={{ color: C.primaryDark }}>
                      One small step
                    </div>
                    <p className="text-sm" style={{ color: C.text }}>{aiFeedback.next_step}</p>
                  </div>
                )}
                {aiFeedback.encouragement && (
                  <p className="text-sm italic text-center pt-1" style={{ color: C.indigoDk }}>
                    "{aiFeedback.encouragement}"
                  </p>
                )}
              </div>
              <div className="px-5 py-3 flex justify-end gap-2"
                style={{ background: '#fafaf9', borderTop: `1px solid ${C.borderWarm}` }}>
                <button
                  onClick={() => {
                    const nx = pendingNextLessonId;
                    setAiFeedback(null);
                    setPendingNextLessonId(null);
                    if (nx) setTimeout(() => switchLesson(nx), 100);
                  }}
                  className="px-4 py-2 rounded-xl text-sm font-black text-white"
                  style={{ background: `linear-gradient(135deg, ${C.indigo}, ${C.purple})` }}>
                  {pendingNextLessonId ? 'Continue →' : 'Got it'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════ LOCK TOAST — when student tries to skip ahead ═══════════ */}
      <AnimatePresence>
        {lockToast && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="fixed top-20 left-1/2 -translate-x-1/2 z-50 max-w-md w-[calc(100%-2rem)] rounded-2xl shadow-xl px-4 py-3 flex items-start gap-3"
            style={{ background: '#fff', border: `2px solid ${C.rose}` }}>
            <span className="text-lg">🔒</span>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] font-black uppercase tracking-wider" style={{ color: C.rose }}>
                Locked
              </div>
              <p className="text-sm" style={{ color: C.text }}>{lockToast}</p>
            </div>
            <button onClick={() => setLockToast(null)}
              className="text-stone-400 hover:text-stone-600 text-sm" aria-label="Dismiss">✕</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════ STICKY HEADER (matches GameDiscoveryPage) ═══════════ */}
      <header className="sticky top-0 z-40 backdrop-blur-md"
        style={{
          background: 'linear-gradient(180deg, #FFFBF0 0%, #FFF8F0 100%)',
          borderBottom: `1px solid ${C.borderWarm}`,
          boxShadow: '0 2px 12px rgba(245,158,11,0.08)',
        }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <button onClick={() => navigate('/modules')}
                className="p-2 rounded-xl hover:bg-amber-50 transition-colors flex-shrink-0"
                title="Back to modules">
                <FaArrowLeft className="text-sm" style={{ color: C.primaryDark }} />
              </button>
              <button onClick={() => setShowMobileMenu(true)}
                className="lg:hidden p-2 rounded-xl hover:bg-amber-50 transition-colors flex-shrink-0"
                title="Open curriculum">
                <FaListUl className="text-sm" style={{ color: C.primaryDark }} />
              </button>
              <h1 className="text-lg sm:text-2xl font-black tracking-tight whitespace-nowrap" style={{ color: C.text }}>
                Module<span style={{ color: C.indigo }}>Hub</span>
              </h1>
              <span className="inline-flex items-center text-[10px] sm:text-[11px] font-bold px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full whitespace-nowrap"
                style={{ backgroundColor: '#E0F2FE', color: C.indigoDk }}>
                {doneLessons}/{totalLessons} · {summaryPct}%
              </span>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              <CoinCounter />
              <button onClick={() => navigate('/discover')}
                className="px-2.5 py-1.5 rounded-xl text-[11px] font-bold hidden md:flex items-center gap-1.5 transition-colors hover:bg-amber-50"
                style={{ color: C.primaryDark }}>
                <FaGamepad className="text-xs" /> Games
              </button>
              <button onClick={() => navigate('/profile')}
                className="px-2.5 py-1.5 rounded-xl text-[11px] font-bold hidden md:flex items-center gap-1.5 transition-colors hover:bg-amber-50"
                style={{ color: C.primaryDark }}>
                <FaChartLine className="text-xs" /> My Progress
              </button>
              <button onClick={() => navigate('/glossary')}
                className="px-2.5 py-1.5 rounded-xl text-[11px] font-bold hidden md:flex items-center gap-1.5 transition-colors hover:bg-amber-50"
                style={{ color: C.primaryDark }}>
                <FaBook className="text-xs" /> Journal
              </button>
              <NotificationCenter />
              <button onClick={() => navigate('/leaderboard')} className="p-2 rounded-xl hover:bg-amber-50 transition-colors">
                <FaTrophy className="text-amber-500 text-sm" />
              </button>
              <button onClick={() => { logout(); navigate('/login', { replace: true }); }}
                className="p-2 rounded-xl hover:bg-red-50 transition-colors" title="Logout">
                <FaSignOutAlt className="text-red-400 text-sm" />
              </button>
            </div>
          </div>

          {/* Module hero strip — compact */}
          <div className="mt-3 flex items-center gap-3 rounded-2xl px-3 py-2.5"
            style={{
              background: `linear-gradient(90deg, ${C.indigo}, ${C.purple})`,
              color: '#fff',
            }}>
            <div className="text-2xl flex-shrink-0">{module.icon || '🎓'}</div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-black break-words leading-tight">{module.title}</div>
              {module.subtitle && (
                <div className="text-[11px] opacity-90 break-words leading-snug mt-0.5">{module.subtitle}</div>
              )}
            </div>
            <div className="hidden sm:flex flex-col items-end flex-shrink-0">
              <div className="text-[10px] font-bold opacity-80">PROGRESS</div>
              <div className="text-sm font-black">{summaryPct}%</div>
            </div>
            <div className="hidden sm:block w-32 h-2 rounded-full overflow-hidden bg-white/20 flex-shrink-0">
              <div className="h-full rounded-full transition-all"
                style={{ width: `${summaryPct}%`, background: '#fff' }} />
            </div>
          </div>
        </div>
      </header>

      {/* ═══════════ COMPLETION BANNER ═══════════ */}
      {isCompleted && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-4">
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl p-5 shadow-lg"
            style={{
              background: 'linear-gradient(90deg, #10b981, #059669)',
              color: '#fff',
            }}>
            <div className="flex items-center gap-3">
              <div className="text-3xl">🎉</div>
              <div className="flex-1">
                <div className="text-lg font-black">You finished {module.title}!</div>
                <p className="text-emerald-50 text-sm mt-0.5">
                  {module.completion_award?.title || 'Module complete.'} Your XP and badge are on your profile.
                </p>
              </div>
              <Link to={`/modules/${moduleId}/report`}
                className="bg-white text-emerald-700 font-bold text-xs px-3 py-2 rounded-xl whitespace-nowrap hover:scale-105 transition-transform">
                📊 View Report Card →
              </Link>
              <Link to="/profile" className="bg-emerald-700/40 hover:bg-emerald-700/60 text-white font-bold text-xs px-3 py-2 rounded-xl whitespace-nowrap transition-colors">
                Badge
              </Link>
            </div>
          </motion.div>
        </div>
      )}

      {/* ═══════════ MAIN GRID — left | center | right ═══════════ */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5">
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr_280px] gap-5">

          {/* ──────── LEFT RAIL: weeks + lessons (desktop) ──────── */}
          <aside className="hidden lg:block rounded-2xl p-3 sticky top-[148px] self-start max-h-[calc(100vh-170px)] overflow-y-auto"
            style={{
              background: C.card,
              border: `1.5px solid ${C.borderWarm}`,
              boxShadow: '0 1px 6px rgba(245,158,11,0.05)',
            }}>
            <div className="flex items-center gap-2 mb-3 px-1">
              <FaListUl className="text-xs" style={{ color: C.primaryDark }} />
              <h3 className="text-[11px] font-black uppercase tracking-wider" style={{ color: C.primaryDark }}>
                Curriculum
              </h3>
              <span className="ml-auto text-[10px] font-bold" style={{ color: C.textLight }}>
                {totalLessons} lessons
              </span>
            </div>

            {(module.weeks || []).map((w) => {
              const wLessons = w.lessons || [];
              const wDone = wLessons.filter((l) => completedSet.has(l.lesson_id)).length;
              const wPct = Math.round((100 * wDone) / Math.max(1, wLessons.length));
              const wUnlocked = weekUnlockMap[w.week_id] !== false;
              return (
                <div key={w.week_id} className="mb-4 last:mb-0">
                  <div className="rounded-xl px-2.5 py-2 mb-1.5"
                    style={{
                      background: wUnlocked
                        ? `linear-gradient(90deg, ${w.color || C.indigo}, ${C.purple})`
                        : 'linear-gradient(90deg, #94a3b8, #64748b)',
                      color: '#fff',
                      opacity: wUnlocked ? 1 : 0.85,
                    }}>
                    <div className="text-[10px] font-black uppercase tracking-wider opacity-90 flex items-center gap-1">
                      <span>Week {w.number}</span>
                      {!wUnlocked && <span title="Locked">🔒</span>}
                    </div>
                    <div className="text-xs font-bold leading-tight break-words">{w.title}</div>
                    <div className="mt-1 flex items-center gap-1.5">
                      <div className="flex-1 h-1 rounded-full bg-white/25 overflow-hidden">
                        <div className="h-full bg-white rounded-full transition-all" style={{ width: `${wPct}%` }} />
                      </div>
                      <span className="text-[10px] font-bold opacity-90">{wDone}/{wLessons.length}</span>
                    </div>
                  </div>
                  {wLessons.map((l) => {
                    const done = completedSet.has(l.lesson_id);
                    const active = activeLessonId === l.lesson_id;
                    const lt = TYPE_LABELS[l.type] || TYPE_LABELS.lesson;
                    const locked = !wUnlocked;
                    return (
                      <button key={l.lesson_id} type="button"
                        onClick={() => { switchLesson(l.lesson_id); setShowMobileMenu(false); }}
                        className="w-full text-left flex items-start gap-2 rounded-xl px-2 py-2 mb-1 transition-colors text-sm hover:bg-amber-50/60"
                        style={{
                          background: active ? C.primaryGlow : 'transparent',
                          color: active ? C.primaryDark : (locked ? C.textLight : C.text),
                          border: active ? `1.5px solid ${C.primaryLight}` : '1.5px solid transparent',
                          fontWeight: active ? 700 : 500,
                          opacity: locked ? 0.55 : 1,
                          cursor: locked ? 'not-allowed' : 'pointer',
                        }}>
                        <span className="w-4 flex-shrink-0 pt-0.5">
                          {locked ? (
                            <span className="text-stone-400 text-xs">🔒</span>
                          ) : done ? (
                            <FaCheckCircle className="text-emerald-500 text-sm" />
                          ) : (
                            <FaCircle className="text-stone-200 text-[10px]" />
                          )}
                        </span>
                        <span className="flex-1 leading-snug text-[13px] break-words">
                          <span className="mr-1">{l.icon}</span>{l.title}
                          {l.optional && (
                            <span className="ml-1.5 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded align-middle"
                              style={{ background: '#FEF3C7', color: '#92400e' }}>
                              ⭐ Bonus
                            </span>
                          )}
                        </span>
                        <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5"
                          style={{ background: lt.bg, color: lt.color }}>
                          {lt.icon}
                        </span>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </aside>

          {/* ──────── CENTER PANE: active lesson ──────── */}
          <main className="rounded-2xl"
            style={{
              background: C.card,
              border: `1.5px solid ${C.borderWarm}`,
              boxShadow: '0 1px 8px rgba(245,158,11,0.05)',
            }}>
            {!activeLesson ? (
              <div className="p-8 text-center" style={{ color: C.textMid }}>
                Select a lesson from the left.
              </div>
            ) : (
              <div className="p-5 md:p-7">
                {/* Lesson breadcrumb / meta */}
                <div className="flex items-center gap-2 flex-wrap text-[11px] font-bold uppercase tracking-wide mb-2"
                  style={{ color: C.textMid }}>
                  <span className="px-2 py-1 rounded-full"
                    style={{ background: typeMeta.bg, color: typeMeta.color }}>
                    {typeMeta.icon} {typeMeta.label}
                  </span>
                  <span style={{ color: C.textLight }}>·</span>
                  <span>Week {activeLesson.week.number}</span>
                  {activeLesson.estimated_minutes && (
                    <>
                      <span style={{ color: C.textLight }}>·</span>
                      <span className="flex items-center gap-1">
                        <FaClock className="text-[10px]" />
                        ~{activeLesson.estimated_minutes} min
                      </span>
                    </>
                  )}
                  {activeLesson.optional && (
                    <span className="px-2 py-1 rounded-full text-[10px] font-black uppercase tracking-wider"
                      style={{ background: '#FEF3C7', color: '#92400e' }}>
                      ⭐ {activeLesson.optional_label || 'Bonus'}
                    </span>
                  )}
                  {isLessonComplete && (
                    <span className="ml-auto inline-flex items-center gap-1 normal-case font-bold"
                      style={{ color: C.emerald }}>
                      <FaCheckCircle /> Completed
                    </span>
                  )}
                </div>

                <h2 className="text-2xl md:text-3xl font-black leading-tight" style={{ color: C.text }}>
                  <span className="mr-2">{activeLesson.icon}</span>
                  {activeLesson.title}
                </h2>

                {activeLesson.summary && (
                  <p className="mt-1 text-sm" style={{ color: C.textMid }}>{activeLesson.summary}</p>
                )}

                {/* Body */}
                <motion.div
                  key={activeLessonId}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className="mt-5">
                  {activeLesson.type === 'lesson' && (
                    <LessonContent content={activeLesson.content} />
                  )}

                  {(activeLesson.type === 'worksheet' || activeLesson.type === 'reflection') && (
                    <>
                      {activeLesson.content?.intro && (
                        <p className="mb-4 text-base leading-relaxed" style={{ color: C.text }}>
                          {activeLesson.content.intro}
                        </p>
                      )}
                      {(() => {
                        // Allow simple-shape reflections: content.prompt (string or array)
                        // gets auto-wrapped into a reflection schema with prompts[].
                        let effectiveSchema = activeLesson.schema;
                        if ((!effectiveSchema || !effectiveSchema.type) && activeLesson.type === 'reflection') {
                          const c = activeLesson.content || {};
                          const promptList = Array.isArray(c.prompts)
                            ? c.prompts
                            : (c.prompt ? [c.prompt] : []);
                          if (promptList.length > 0) {
                            effectiveSchema = { type: 'reflection', prompts: promptList, min_chars: c.min_chars };
                          }
                        }
                        return (
                          <WorksheetRenderer
                            schema={effectiveSchema}
                            value={answers}
                            onChange={handleAnswersChange}
                          />
                        );
                      })()}
                      <div className="mt-3 flex items-center gap-2 text-xs italic"
                        style={{ color: saving ? C.primaryDark : C.textLight }}>
                        {saving ? (
                          <>
                            <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                            Saving…
                          </>
                        ) : (
                          <>
                            <FaCheck className="text-emerald-500" />
                            Autosaves as you type.
                          </>
                        )}
                      </div>
                    </>
                  )}

                  {activeLesson.type === 'field_mission' && (
                    <>
                      {activeLesson.content?.intro && (
                        <p className="mb-4 text-base leading-relaxed" style={{ color: C.text }}>
                          {activeLesson.content.intro}
                        </p>
                      )}
                      <FieldMissionRenderer
                        moduleId={moduleId}
                        lessonId={activeLessonId}
                        schema={activeLesson.schema}
                        onCountChange={setFieldMissionCount}
                      />
                    </>
                  )}

                  {activeLesson.type === 'voice_recording' && (
                    <>
                      {activeLesson.content?.intro && (
                        <p className="mb-4 text-base leading-relaxed" style={{ color: C.text }}>
                          {activeLesson.content.intro}
                        </p>
                      )}
                      <VoiceLessonRenderer
                        moduleId={moduleId}
                        lessonId={activeLessonId}
                        schema={activeLesson.schema}
                        savedAnswers={answers}
                        onAnswersChange={(a) => setAnswers(a || {})}
                      />
                    </>
                  )}

                  {(activeLesson.type === 'quiz' || activeLesson.type === 'assessment') && (
                    <>
                      {activeLesson.content?.intro && (
                        <p className="mb-4 text-base leading-relaxed" style={{ color: C.text }}>
                          {activeLesson.content.intro}
                        </p>
                      )}
                      {(() => {
                        // Allow simple-shape quizzes: lesson.questions[] with
                        // {question, options:[strings], correct_index, explanation}
                        // gets converted into Quiz's schema.fields format.
                        let effectiveSchema = activeLesson.schema;
                        if ((!effectiveSchema?.fields?.length) && Array.isArray(activeLesson.questions) && activeLesson.questions.length > 0) {
                          effectiveSchema = {
                            pass_threshold: activeLesson.pass_threshold ?? 0.6,
                            fields: activeLesson.questions.map((q, qi) => {
                              const correctIdx = typeof q.correct_index === 'number' ? q.correct_index : 0;
                              const opts = (q.options || []).map((o, oi) => {
                                if (o && typeof o === 'object' && 'value' in o) return o;
                                const value = String.fromCharCode(97 + oi); // 'a','b','c',...
                                return { value, label: String(o) };
                              });
                              return {
                                id: q.id || `q${qi + 1}`,
                                question: q.question || q.prompt || '',
                                options: opts,
                                correct: opts[correctIdx]?.value,
                                explanation: q.explanation,
                              };
                            }),
                          };
                        }
                        return (
                          <Quiz
                            schema={effectiveSchema}
                            value={answers}
                            onChange={handleAnswersChange}
                            onResult={(res) => setQuizState(res)}
                          />
                        );
                      })()}
                    </>
                  )}

                  {activeLesson.type === 'game' && (
                    <div className="rounded-2xl p-6 md:p-7 text-center relative overflow-hidden"
                      style={{
                        background: `linear-gradient(135deg, #E0F2FE, ${C.primaryGlow})`,
                        border: `2px solid ${C.indigo}`,
                      }}>
                      <div className="text-6xl mb-3">{activeLesson.icon || '🎮'}</div>
                      <div className="text-[10px] font-black uppercase tracking-widest mb-1"
                        style={{ color: C.indigo }}>
                        SIMULATION CHALLENGE
                      </div>
                      <div className="font-black text-xl md:text-2xl mb-2" style={{ color: C.text }}>
                        {activeLesson.title}
                      </div>
                      {activeLesson.game_purpose && (
                        <p className="text-sm mb-5 max-w-xl mx-auto leading-relaxed" style={{ color: C.textMid }}>
                          {activeLesson.game_purpose}
                        </p>
                      )}
                      <button type="button" onClick={handleStartGame}
                        className="inline-flex items-center gap-2 font-black text-base px-7 py-3.5 rounded-2xl shadow-lg transition-all hover:scale-105"
                        style={{
                          background: `linear-gradient(90deg, ${C.indigo}, ${C.purple})`,
                          color: '#fff',
                          boxShadow: '0 6px 20px rgba(99,102,241,0.35)',
                        }}>
                        <FaPlayCircle /> Play this Sim
                      </button>
                      <div className="mt-4 text-xs" style={{ color: C.textMid }}>
                        When you finish the game, return here and click <strong>Mark complete</strong>.
                      </div>
                    </div>
                  )}

                  {activeLesson.type === 'audio_lesson' && (
                    <AudioLessonRenderer lesson={activeLesson} onComplete={handleComplete} />
                  )}

                  {activeLesson.type === 'pitch_coach' && (
                    <PitchCoachRenderer lesson={activeLesson} onComplete={handleComplete} />
                  )}

                  {activeLesson.type === 'interview_sim' && (
                    <InterviewSimRenderer lesson={activeLesson} onComplete={handleComplete} />
                  )}

                  {activeLesson.type === 'micro_quest' && (
                    <MicroQuestRenderer lesson={activeLesson} onComplete={handleComplete} />
                  )}

                  {activeLesson.type === 'case_study_card' && (
                    <CaseStudyCardRenderer lesson={activeLesson} onComplete={handleComplete} />
                  )}

                  {activeLesson.type === 'failure_card' && (
                    <FailureCardRenderer lesson={activeLesson} onComplete={handleComplete} />
                  )}

                  {activeLesson.type === 'cohort_live_session' && (
                    <CohortLiveSessionCard lesson={activeLesson} />
                  )}

                  {![
                    'lesson', 'worksheet', 'reflection', 'field_mission', 'voice_recording',
                    'quiz', 'assessment', 'game',
                    'audio_lesson', 'pitch_coach', 'interview_sim', 'micro_quest',
                    'case_study_card', 'failure_card', 'cohort_live_session',
                  ].includes(activeLesson.type) && (
                    <UnknownLessonRenderer lesson={activeLesson} />
                  )}
                </motion.div>

                {/* Footer actions */}
                <div className="mt-8 pt-5 flex items-center justify-between gap-2 sm:gap-3"
                  style={{ borderTop: `1.5px solid ${C.borderWarm}` }}>
                  <button type="button"
                    disabled={activeIdx <= 0}
                    onClick={() => {
                      if (activeIdx > 0) switchLesson(flatLessons[activeIdx - 1].lesson_id);
                    }}
                    className="text-sm font-semibold px-2.5 sm:px-3 py-2 rounded-xl transition-colors disabled:opacity-40 flex-shrink-0"
                    title="Previous lesson"
                    style={{ color: C.textMid }}>
                    <span aria-hidden="true">←</span>
                    <span className="hidden sm:inline ml-1">Previous</span>
                  </button>

                  <div className="flex items-center gap-2 flex-1 justify-center min-w-0">
                    {(() => {
                      const fmTarget = activeLesson.schema?.target_count || 5;
                      const fmGoalNotMet = activeLesson.type === 'field_mission' && fieldMissionCount < fmTarget;
                      const isQuiz = activeLesson.type === 'quiz' || activeLesson.type === 'assessment';
                      const quizNotPassed = isQuiz && !quizState?.passed;
                      const blocked = fmGoalNotMet || quizNotPassed;
                      if (isLessonComplete) {
                        return (
                          <span className="inline-flex items-center gap-1.5 text-sm font-bold"
                            style={{ color: C.emerald }}>
                            <FaCheckCircle /> Completed
                          </span>
                        );
                      }
                      let label = 'Mark complete & continue';
                      let shortLabel = 'Mark complete';
                      if (fmGoalNotMet) {
                        label = `Collect ${fmTarget - fieldMissionCount} more case file${fmTarget - fieldMissionCount === 1 ? '' : 's'}`;
                        shortLabel = label;
                      } else if (quizNotPassed) {
                        label = quizState
                          ? `Score ${Math.round((quizState.threshold || 0.6) * 100)}% to continue`
                          : 'Submit the quiz first';
                        shortLabel = label;
                      }
                      return (
                        <button type="button" onClick={() => handleComplete()}
                          disabled={blocked}
                          className="inline-flex items-center gap-2 font-bold text-sm px-4 sm:px-5 py-2.5 rounded-xl shadow transition-transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed max-w-full"
                          style={{
                            background: `linear-gradient(90deg, ${C.emerald}, #10b981)`,
                            color: '#fff',
                          }}>
                          <FaCheckCircle className="flex-shrink-0" />
                          <span className="hidden sm:inline truncate">{label}</span>
                          <span className="sm:hidden truncate">{shortLabel}</span>
                        </button>
                      );
                    })()}
                  </div>

                  <button type="button"
                    disabled={activeIdx >= flatLessons.length - 1}
                    onClick={() => {
                      if (activeIdx < flatLessons.length - 1)
                        switchLesson(flatLessons[activeIdx + 1].lesson_id);
                    }}
                    className="text-sm font-semibold px-2.5 sm:px-3 py-2 rounded-xl transition-colors disabled:opacity-40 flex-shrink-0"
                    title="Next lesson"
                    style={{ color: C.textMid }}>
                    <span className="hidden sm:inline mr-1">Next</span>
                    <span aria-hidden="true">→</span>
                  </button>
                </div>
              </div>
            )}
          </main>

          {/* ──────── RIGHT RAIL: meta + week + skills + related ──────── */}
          <aside className="lg:sticky lg:top-[148px] lg:self-start lg:max-h-[calc(100vh-170px)] lg:overflow-y-auto pr-1">
            {/* Lesson Info */}
            {activeLesson && (
              <RailCard title="Lesson Info" icon="ℹ️">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span style={{ color: C.textMid }}>Type</span>
                    <span className="font-bold px-2 py-0.5 rounded-full text-[10px]"
                      style={{ background: typeMeta.bg, color: typeMeta.color }}>
                      {typeMeta.icon} {typeMeta.label}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span style={{ color: C.textMid }}>Estimated</span>
                    <span className="font-bold" style={{ color: C.text }}>
                      ~{activeLesson.estimated_minutes || 5} min
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span style={{ color: C.textMid }}>Status</span>
                    <span className="font-bold" style={{ color: isLessonComplete ? C.emerald : C.primaryDark }}>
                      {isLessonComplete ? '✓ Done' : 'In progress'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span style={{ color: C.textMid }}>Lesson</span>
                    <span className="font-bold" style={{ color: C.text }}>
                      {activeIdx + 1} / {totalLessons}
                    </span>
                  </div>
                </div>
              </RailCard>
            )}

            {/* Week progress */}
            {activeWeek && (
              <RailCard title={`Week ${activeWeek.number} Checklist`} icon="🗓️">
                <div className="mb-2 flex items-center gap-2">
                  <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: C.surface }}>
                    <div className="h-full transition-all"
                      style={{ width: `${weekPct}%`, background: `linear-gradient(90deg, ${C.primary}, ${C.primaryDark})` }} />
                  </div>
                  <span className="text-[11px] font-bold" style={{ color: C.primaryDark }}>
                    {weekDone}/{weekLessons.length}
                  </span>
                </div>
                <div className="space-y-1">
                  {weekLessons.map((l) => {
                    const done = completedSet.has(l.lesson_id);
                    const active = activeLessonId === l.lesson_id;
                    return (
                      <button key={l.lesson_id} type="button"
                        onClick={() => switchLesson(l.lesson_id)}
                        className="w-full flex items-start gap-2 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-amber-50"
                        style={{
                          background: active ? C.primaryGlow : 'transparent',
                        }}>
                        <span className="flex-shrink-0 pt-0.5">
                          {done ? (
                            <FaCheckCircle className="text-emerald-500 text-xs" />
                          ) : (
                            <FaCircle className="text-stone-200 text-[8px]" />
                          )}
                        </span>
                        <span className="flex-1 text-[11px] font-medium leading-snug break-words"
                          style={{ color: active ? C.primaryDark : C.text }}>
                          <span className="mr-1">{l.icon}</span>{l.title}
                        </span>
                      </button>
                    );
                  })}
                </div>
                {activeWeek.homework_summary && (
                  <div className="mt-2 pt-2 text-[11px] italic"
                    style={{ borderTop: `1px dashed ${C.borderWarm}`, color: C.textMid }}>
                    📌 {activeWeek.homework_summary}
                  </div>
                )}
              </RailCard>
            )}

            {/* Skills */}
            {skillsToShow.length > 0 && (
              <RailCard title="What You'll Build" icon="🧠">
                <div className="flex flex-wrap gap-1.5">
                  {skillsToShow.map((s) => (
                    <span key={s} className="text-[11px] font-bold px-2 py-1 rounded-full"
                      style={{ background: '#E0F2FE', color: C.indigoDk }}>
                      {DIM_ICONS[s] || '✨'} {s.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </RailCard>
            )}

            {/* Difficulty (game lesson only) */}
            {activeLesson?.type === 'game' && (
              <RailCard title="Difficulty" icon="⚡">
                <div className="grid grid-cols-3 gap-1.5">
                  {['easy', 'normal', 'hard'].map((d) => {
                    const isCurrent = (module.difficulty || 'intermediate').toLowerCase().startsWith(d[0]);
                    return (
                      <div key={d}
                        className="text-center text-[10px] font-bold uppercase py-1.5 rounded-lg"
                        style={{
                          background: isCurrent ? C.primaryGlow : C.surface,
                          color: isCurrent ? C.primaryDark : C.textLight,
                          border: isCurrent ? `1.5px solid ${C.primaryLight}` : `1px solid ${C.borderWarm}`,
                        }}>
                        {d}
                      </div>
                    );
                  })}
                </div>
                <p className="mt-2 text-[10px] italic" style={{ color: C.textLight }}>
                  Difficulty matches your module level. Adjustable in Profile → Settings.
                </p>
              </RailCard>
            )}

            {/* Related games (other game lessons in this module) */}
            {relatedGames.length > 0 && (
              <RailCard title="More Sims in This Module" icon="🎮">
                <div className="space-y-1.5">
                  {relatedGames.map((g) => (
                    <button key={g.lesson_id} type="button"
                      onClick={() => switchLesson(g.lesson_id)}
                      className="w-full flex items-center gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-amber-50"
                      style={{ background: C.surface, border: `1px solid ${C.borderWarm}` }}>
                      <span className="text-base">{g.icon || '🎮'}</span>
                      <span className="flex-1 text-[11px] font-bold leading-snug break-words"
                        style={{ color: C.text }}>
                        {g.title}
                      </span>
                      <FaChevronRight className="text-[10px] flex-shrink-0" style={{ color: C.primaryDark }} />
                    </button>
                  ))}
                </div>
              </RailCard>
            )}

            {/* Module skills overall */}
            {module.target_skills?.length > 0 && (
              <RailCard title="Module Outcomes" icon="🎯">
                <ul className="space-y-1 text-[11px]" style={{ color: C.textMid }}>
                  {module.target_skills.map((s) => (
                    <li key={s} className="flex items-center gap-1.5">
                      <FaCheck className="text-emerald-500 text-[9px] flex-shrink-0" />
                      <span className="font-medium">{DIM_ICONS[s] || '✨'} {s.replace(/_/g, ' ')}</span>
                    </li>
                  ))}
                </ul>
              </RailCard>
            )}

            {/* Certificate hint */}
            {module.certificate_id && !isCompleted && (
              <RailCard title="On Completion" icon="🏆">
                <div className="flex items-center gap-2">
                  <div className="text-2xl">🎓</div>
                  <div className="flex-1">
                    <div className="text-[11px] font-bold" style={{ color: C.text }}>
                      Earn the Mento Entrepreneur Badge
                    </div>
                    <div className="text-[10px]" style={{ color: C.textMid }}>
                      +250 XP · Certificate
                    </div>
                  </div>
                </div>
              </RailCard>
            )}
          </aside>
        </div>
      </div>

      {/* ═══════════ MOBILE CURRICULUM DRAWER ═══════════ */}
      {showMobileMenu && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/40"
            onClick={() => setShowMobileMenu(false)} />
          <motion.aside
            initial={{ x: -300 }}
            animate={{ x: 0 }}
            exit={{ x: -300 }}
            transition={{ type: 'tween', duration: 0.22 }}
            className="relative w-[80vw] max-w-[320px] h-full overflow-y-auto p-3"
            style={{ background: C.card }}>
            <div className="flex items-center justify-between mb-3 px-1">
              <div className="flex items-center gap-2">
                <FaListUl className="text-xs" style={{ color: C.primaryDark }} />
                <h3 className="text-[12px] font-black uppercase tracking-wider" style={{ color: C.primaryDark }}>
                  Curriculum
                </h3>
              </div>
              <button onClick={() => setShowMobileMenu(false)}
                className="p-1.5 rounded-lg hover:bg-amber-50"
                aria-label="Close curriculum">
                <FaTimes className="text-sm" style={{ color: C.primaryDark }} />
              </button>
            </div>
            {(module.weeks || []).map((w) => {
              const wLessons = w.lessons || [];
              const wDone = wLessons.filter((l) => completedSet.has(l.lesson_id)).length;
              const wPct = Math.round((100 * wDone) / Math.max(1, wLessons.length));
              const wUnlocked = weekUnlockMap[w.week_id] !== false;
              return (
                <div key={w.week_id} className="mb-4 last:mb-0">
                  <div className="rounded-xl px-2.5 py-2 mb-1.5"
                    style={{
                      background: wUnlocked
                        ? `linear-gradient(90deg, ${w.color || C.indigo}, ${C.purple})`
                        : 'linear-gradient(90deg, #94a3b8, #64748b)',
                      color: '#fff',
                      opacity: wUnlocked ? 1 : 0.85,
                    }}>
                    <div className="text-[10px] font-black uppercase tracking-wider opacity-90 flex items-center gap-1">
                      <span>Week {w.number}</span>
                      {!wUnlocked && <span title="Locked">🔒</span>}
                    </div>
                    <div className="text-xs font-bold leading-tight break-words">{w.title}</div>
                    <div className="mt-1 flex items-center gap-1.5">
                      <div className="flex-1 h-1 rounded-full bg-white/25 overflow-hidden">
                        <div className="h-full bg-white rounded-full transition-all" style={{ width: `${wPct}%` }} />
                      </div>
                      <span className="text-[10px] font-bold opacity-90">{wDone}/{wLessons.length}</span>
                    </div>
                  </div>
                  {wLessons.map((l) => {
                    const done = completedSet.has(l.lesson_id);
                    const active = activeLessonId === l.lesson_id;
                    const lt = TYPE_LABELS[l.type] || TYPE_LABELS.lesson;
                    const locked = !wUnlocked;
                    return (
                      <button key={l.lesson_id} type="button"
                        onClick={() => { switchLesson(l.lesson_id); setShowMobileMenu(false); }}
                        className="w-full text-left flex items-start gap-2 rounded-xl px-2 py-2 mb-1 transition-colors text-sm hover:bg-amber-50/60"
                        style={{
                          background: active ? C.primaryGlow : 'transparent',
                          color: active ? C.primaryDark : (locked ? C.textLight : C.text),
                          border: active ? `1.5px solid ${C.primaryLight}` : '1.5px solid transparent',
                          fontWeight: active ? 700 : 500,
                          opacity: locked ? 0.55 : 1,
                          cursor: locked ? 'not-allowed' : 'pointer',
                        }}>
                        <span className="w-4 flex-shrink-0 pt-0.5">
                          {locked ? (
                            <span className="text-stone-400 text-xs">🔒</span>
                          ) : done ? (
                            <FaCheckCircle className="text-emerald-500 text-sm" />
                          ) : (
                            <FaCircle className="text-stone-200 text-[10px]" />
                          )}
                        </span>
                        <span className="flex-1 leading-snug text-[13px] break-words">
                          <span className="mr-1">{l.icon}</span>{l.title}
                          {l.optional && (
                            <span className="ml-1.5 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded align-middle"
                              style={{ background: '#FEF3C7', color: '#92400e' }}>
                              ⭐ Bonus
                            </span>
                          )}
                        </span>
                        <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5"
                          style={{ background: lt.bg, color: lt.color }}>
                          {lt.icon}
                        </span>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </motion.aside>
        </div>
      )}
    </div>
  );
}
