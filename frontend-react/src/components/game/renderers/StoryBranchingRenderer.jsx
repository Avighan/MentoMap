/**
 * StoryBranchingRenderer — Interactive branching story with storybook experience.
 *
 * Features:
 *  - Book cover → chapter select (if game has chapters) → reading → ending
 *  - Chapter unlock system via localStorage (completing ch1 unlocks ch2, etc.)
 *  - DALL-E 3 images via backend endpoint (Pollinations fallback)
 *  - Engagement system: streaks, floating deltas, screen shake
 *  - Coach panel, skill callouts, delta flashes
 *  - Data-format agnostic: handles both story_intro.scenes and story.opening/branches
 *
 * Only used by game_type === "story_branching". All other game types are unaffected.
 */
import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { submitBranchingChoice, endGame, submitStoryChallenge } from '../../../api/games';
import { getSceneStoryImage } from '../../../api/storyImages';
import { getAllFieldMissionEntries } from '../../../api/modules';
import { useSound } from '../../../contexts/SoundContext';
import { motion, AnimatePresence } from 'framer-motion';
import useEngagementSystem from '../../../hooks/useEngagementSystem';
import { FloatingDeltaLayer, StreakBanner } from '../BoardGameExtras';
import SkillCallout from '../SkillCallout';
import ChoiceExplanation from '../ChoiceExplanation';
import PostGameInsights from '../PostGameInsights';
import StoryAgent from '../StoryAgent';
import PlayerAvatarCard from '../PlayerAvatarCard';
import CharacterCard from '../CharacterCard';
import MovieRecap from '../MovieRecap';
import LiveSkillRadar from '../LiveSkillRadar';
import NarrativeChatBreakout from '../story/NarrativeChatBreakout';

// ─────────────────────────────────────────────────────────────
// Data normalisation (handles both JSON formats)
// ─────────────────────────────────────────────────────────────
function normalizeScene(scene) {
  if (!scene) return null;
  const s = { ...scene };
  if (!s.id && s.scene_id) s.id = s.scene_id;
  // Normalise scene body to s.text. Author conventions vary: narrative (canonical),
  // narration (kids/pro stories), story, description, scene, prompt. Fill in priority order.
  if (!s.text) {
    s.text = s.narrative || s.narration || s.story || s.description || s.scene || s.prompt || '';
  }
  return s;
}

function buildSceneMap(gameData) {
  const map = {};
  (gameData?.story_intro?.scenes || []).forEach(s => {
    const n = normalizeScene(s);
    if (n?.id) map[n.id] = n;
  });
  const story = gameData?.story || {};
  const opening = story.opening;
  if (opening?.id) map[opening.id] = normalizeScene(opening);
  (story.branches || []).forEach(b => {
    const n = normalizeScene(b);
    if (n?.id) map[n.id] = n;
  });
  return map;
}

function getOpeningScene(gameData, sceneMap) {
  const scenes = gameData?.story_intro?.scenes || [];
  if (scenes.length > 0) return normalizeScene(scenes[0]);
  const opening = gameData?.story?.opening;
  if (opening?.id) return normalizeScene(opening);
  return Object.values(sceneMap)[0] || null;
}

/** Find the first scene belonging to a given chapter_id */
function getChapterStartScene(gameData, sceneMap, chapterId) {
  const scenes = gameData?.story_intro?.scenes || [];
  const first = scenes.find(s => s.chapter === chapterId);
  if (first) return normalizeScene(first);
  return Object.values(sceneMap).find(s => s.chapter === chapterId) || null;
}

// ─────────────────────────────────────────────────────────────
// Story progress — save/load current scene + choice log
// ─────────────────────────────────────────────────────────────
const STORY_PROGRESS_KEY = 'mento_story_progress';

function saveStoryProgress(gameId, sceneId, log) {
  try {
    const all = JSON.parse(localStorage.getItem(STORY_PROGRESS_KEY) || '{}');
    all[gameId] = { scene_id: sceneId, log, updated: Date.now() };
    localStorage.setItem(STORY_PROGRESS_KEY, JSON.stringify(all));
  } catch {}
}

function loadStoryProgress(gameId) {
  try {
    const all = JSON.parse(localStorage.getItem(STORY_PROGRESS_KEY) || '{}');
    return all[gameId] || null;
  } catch { return null; }
}

// ─────────────────────────────────────────────────────────────
// Chapter progress — stored per game in localStorage
// ─────────────────────────────────────────────────────────────
const LS_KEY = 'mento_story_chapters_done';

function getCompletedChapters(gameId) {
  try {
    const raw = localStorage.getItem(LS_KEY);
    const data = raw ? JSON.parse(raw) : {};
    return new Set(data[gameId] || []);
  } catch { return new Set(); }
}

function markChapterComplete(gameId, chapterId) {
  if (!gameId || !chapterId) return;
  try {
    const raw = localStorage.getItem(LS_KEY);
    const data = raw ? JSON.parse(raw) : {};
    const set = new Set(data[gameId] || []);
    set.add(chapterId);
    data[gameId] = [...set];
    localStorage.setItem(LS_KEY, JSON.stringify(data));
  } catch { /* ignore */ }
}

function isChapterUnlocked(chapter, completedChapters) {
  if (chapter.always_unlocked) return true;
  if (chapter.unlocks_after) return completedChapters.has(chapter.unlocks_after);
  return true; // no lock condition = always open
}

// ─────────────────────────────────────────────────────────────
// Scene image loader — DALL-E via backend → Pollinations fallback
// ─────────────────────────────────────────────────────────────
const SceneImageLoader = ({ gameId, sceneId, imagePrompt }) => {
  const [url, setUrl] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sceneId && !imagePrompt) { setLoading(false); return; }
    let cancelled = false;
    (async () => {
      try {
        if (gameId && sceneId) {
          const res = await getSceneStoryImage(gameId, sceneId);
          if (!cancelled && (res.image_url || res.fallback_url)) {
            setUrl(res.image_url || res.fallback_url);
            return;
          }
        }
      } catch { /* fall through to Pollinations */ }
      if (!cancelled && imagePrompt) {
        const p = `orange dolphin mascot Mento in a storybook scene, ${imagePrompt}, 3D cartoon style, warm lighting`;
        setUrl(`https://image.pollinations.ai/prompt/${encodeURIComponent(p)}?width=1280&height=720&nologo=true`);
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [gameId, sceneId, imagePrompt]);

  const onLoad = () => setLoading(false);
  const onError = () => setLoading(false);

  if (!url && !loading) return null;
  return (
    <div className="relative w-full overflow-hidden rounded-xl" style={{ aspectRatio: '16/9' }}>
      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-10"
          style={{ background: 'linear-gradient(135deg,#fef3d0,#fde9b5)' }}>
          <motion.div className="w-10 h-10 rounded-full mb-2"
            style={{ background: '#e8a832' }}
            animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 1.2 }} />
          <p className="text-xs text-amber-700">Mento is painting the scene…</p>
        </div>
      )}
      {url && (
        <img src={url} alt="Scene illustration"
          className="absolute inset-0 w-full h-full object-cover"
          style={{ display: loading ? 'none' : 'block' }}
          onLoad={onLoad} onError={onError} />
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Resource bar (wisdom, courage, etc.)
// ─────────────────────────────────────────────────────────────
const ResourceBar = ({ resources }) => {
  const visible = Object.entries(resources || {}).filter(
    ([, v]) => v && typeof v === 'object' && v.label && v.category !== 'Story & Narrative'
  );
  if (!visible.length) return null;
  return (
    <div className="flex flex-wrap gap-2 justify-center mb-3">
      {visible.map(([key, r]) => (
        <div key={key} className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
          style={{ background: 'rgba(245,237,216,0.9)', border: '1px solid #c9a96e', color: '#6b4c1e' }}>
          <span>{r.icon || '📊'}</span>
          <span>{r.label}</span>
          <span className="font-bold">{r.value ?? '—'}</span>
        </div>
      ))}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Coach panel
// ─────────────────────────────────────────────────────────────
const COACH_TIPS = [
  'Consider how each choice reflects your values.',
  'Think about long-term consequences before deciding.',
  'Notice how your decisions affect those around you.',
  'Reflect on what you would do differently in real life.',
  'Pay attention to the tradeoffs in each option.',
];

const CoachPanel = ({ gameData, sceneCount }) => {
  const [open, setOpen] = useState(sceneCount <= 1);
  const objectives = gameData?.learning_objectives || [];
  const concept = gameData?.learning_concept || '';
  const tip = COACH_TIPS[(sceneCount - 1) % COACH_TIPS.length];
  if (!objectives.length && !concept) return null;
  return (
    <div className="mt-3 rounded-xl border overflow-hidden"
      style={{ borderColor: '#d4b483', background: 'rgba(253,243,216,0.6)' }}>
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2 text-left">
        <span className="text-xs font-semibold" style={{ color: '#7c4a03' }}>🧠 Story Coach</span>
        <span className="text-xs" style={{ color: '#c9853a' }}>{open ? '▲' : '▼'}</span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
            className="px-4 pb-3 space-y-1.5">
            {concept && <p className="text-xs font-medium" style={{ color: '#7c4a03' }}>{concept}</p>}
            <p className="text-xs italic" style={{ color: '#9a6030' }}>💡 {tip}</p>
            {objectives.slice(0, 3).map((obj, i) => (
              <div key={i} className="text-xs flex items-start gap-1" style={{ color: '#7c4a03' }}>
                <span className="mt-0.5 shrink-0">•</span><span>{obj}</span>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Book cover
// ─────────────────────────────────────────────────────────────
const BookCover = ({ gameData, onOpen, onBack }) => {
  const title = gameData?.title || 'Interactive Story';
  const description = gameData?.description || '';
  const theme = gameData?.theme || '';
  const firstScene = normalizeScene(
    (gameData?.story_intro?.scenes || [])[0] || gameData?.story?.opening
  );
  const coverImagePrompt = gameData?.cover_image_prompt || firstScene?.image_prompt || null;

  return (
    <motion.div className="w-full max-w-lg mx-auto"
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.45, ease: 'easeOut' }}>

      {/* Back / Home button */}
      {onBack && (
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm font-semibold mb-4 px-4 py-2 rounded-xl transition-colors"
          style={{ color: '#7c2d12', background: 'rgba(124,45,18,0.08)' }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(124,45,18,0.15)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(124,45,18,0.08)'}
        >
          ← Back to Games
        </button>
      )}

      <div className="relative rounded-2xl overflow-hidden shadow-2xl cursor-pointer"
        style={{
          background: 'linear-gradient(160deg,#7c2d12 0%,#c2410c 60%,#ea580c 100%)',
          border: '3px solid #431407',
          fontFamily: 'Georgia,"Times New Roman",serif',
        }}
        onClick={onOpen}>
        {/* Spine shadow */}
        <div className="absolute left-0 top-0 bottom-0 w-6 z-10"
          style={{ background: 'linear-gradient(to right,rgba(0,0,0,0.35),transparent)' }} />

        {/* Cover image */}
        {coverImagePrompt ? (
          <SceneImageLoader gameId={gameData?.game_id}
            sceneId={firstScene?.id}
            imagePrompt={coverImagePrompt} />
        ) : (
          <div className="w-full flex items-center justify-center py-16 text-8xl">📖</div>
        )}

        {/* Title + description overlay */}
        <div className="px-6 pt-5 pb-7 text-center text-white"
          style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.3) 80%, transparent 100%)' }}>
          {theme && (
            <p className="text-[11px] tracking-[0.25em] uppercase mb-1.5 opacity-80">{theme}</p>
          )}
          <h1 className="text-3xl font-bold leading-snug drop-shadow mb-2">{title}</h1>
          {description && (
            <p className="text-sm opacity-90 leading-relaxed">{description}</p>
          )}
        </div>
      </div>

      <motion.button
        onClick={onOpen}
        whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
        className="mt-5 w-full py-4 rounded-xl font-bold text-white text-base tracking-wide shadow-md"
        style={{ background: 'linear-gradient(135deg,#c2410c,#ea580c)', border: '2px solid #9a3412', fontFamily: 'Georgia,serif' }}>
        Open Book →
      </motion.button>
    </motion.div>
  );
};

// ─────────────────────────────────────────────────────────────
// Chapter select screen
// ─────────────────────────────────────────────────────────────
const ChapterSelectScreen = ({ gameData, completedChapters, onSelectChapter, onBack }) => {
  const chapters = gameData?.chapters || [];
  const title = gameData?.title || 'Interactive Story';

  return (
    <motion.div className="max-w-lg mx-auto px-4 py-6"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}>
      {/* Header */}
      <div className="text-center mb-6" style={{ fontFamily: 'Georgia,serif' }}>
        <p className="text-[10px] tracking-[0.25em] uppercase mb-1" style={{ color: '#b08040' }}>
          {gameData?.theme || 'Interactive Story'}
        </p>
        <h1 className="text-2xl font-bold" style={{ color: '#4a2e0a' }}>{title}</h1>
        <p className="text-xs mt-1" style={{ color: '#9a6030' }}>Choose a chapter to begin</p>
      </div>

      {/* Chapter cards */}
      <div className="space-y-3">
        {chapters.map((ch) => {
          const unlocked = isChapterUnlocked(ch, completedChapters);
          const completed = completedChapters.has(ch.chapter_id);

          return (
            <motion.button
              key={ch.chapter_id}
              onClick={() => unlocked && onSelectChapter(ch.chapter_id)}
              whileHover={unlocked ? { scale: 1.02, x: 4 } : {}}
              whileTap={unlocked ? { scale: 0.98 } : {}}
              className="w-full text-left rounded-2xl overflow-hidden transition-all"
              style={{
                background: unlocked
                  ? 'linear-gradient(135deg,#fefcf0,#fef3d0)'
                  : 'linear-gradient(135deg,#f5f5f5,#ebebeb)',
                border: `2px solid ${unlocked ? (ch.color || '#d4b483') : '#d1d5db'}`,
                boxShadow: unlocked ? '0 4px 14px rgba(160,120,40,0.12)' : 'none',
                cursor: unlocked ? 'pointer' : 'not-allowed',
                opacity: unlocked ? 1 : 0.65,
                fontFamily: 'Georgia,serif',
              }}>
              <div className="flex items-center gap-4 p-4">
                {/* Chapter icon */}
                <div className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl shrink-0"
                  style={{
                    background: unlocked ? (ch.color || '#c9853a') + '22' : '#e5e7eb',
                    border: `2px solid ${unlocked ? (ch.color || '#c9853a') + '55' : '#d1d5db'}`,
                  }}>
                  {unlocked ? (ch.icon || '📖') : '🔒'}
                </div>

                {/* Chapter info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[10px] tracking-[0.15em] uppercase font-medium"
                      style={{ color: unlocked ? (ch.color || '#c9853a') : '#9ca3af' }}>
                      Chapter {ch.number}
                    </span>
                    {completed && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                        style={{ background: '#dcfce7', color: '#16a34a' }}>
                        ✓ Complete
                      </span>
                    )}
                  </div>
                  <p className="font-bold text-sm sm:text-base truncate"
                    style={{ color: unlocked ? '#4a2e0a' : '#6b7280' }}>
                    {ch.title}
                  </p>
                  {unlocked ? (
                    <p className="text-xs mt-0.5 line-clamp-1" style={{ color: '#7a5530' }}>
                      {ch.teaser}
                    </p>
                  ) : (
                    <p className="text-xs mt-0.5" style={{ color: '#9ca3af' }}>
                      Complete Chapter {ch.number - 1} to unlock
                    </p>
                  )}
                </div>

                {/* Arrow for unlocked */}
                {unlocked && (
                  <span className="text-lg shrink-0" style={{ color: ch.color || '#c9853a' }}>›</span>
                )}
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Back to cover */}
      <button onClick={onBack}
        className="mt-5 text-xs underline opacity-60 hover:opacity-100 block mx-auto"
        style={{ color: '#b08040', fontFamily: 'system-ui,sans-serif' }}>
        ← Back to Cover
      </button>
    </motion.div>
  );
};

// ─────────────────────────────────────────────────────────────
// Chapter complete screen
// ─────────────────────────────────────────────────────────────
const SKILL_INSIGHTS = {
  strategic_thinking: { emoji: '🧠', label: 'Strategic Thinking', color: '#6366F1' },
  risk_tolerance: { emoji: '🎲', label: 'Risk Tolerance', color: '#F59E0B' },
  delayed_gratification: { emoji: '⏳', label: 'Patience', color: '#8B5CF6' },
  adaptability: { emoji: '🔄', label: 'Adaptability', color: '#10B981' },
  resilience: { emoji: '💪', label: 'Resilience', color: '#EF4444' },
  empathy: { emoji: '❤️', label: 'Empathy', color: '#EC4899' },
  ethical_reasoning: { emoji: '⚖️', label: 'Ethics', color: '#14B8A6' },
  creativity: { emoji: '🎨', label: 'Creativity', color: '#F97316' },
};

const ChapterCompleteScreen = ({ gameData, completedChapterId, nextChapterId, log, resources, chapterReward, onContinue, onViewChapters, playerName }) => {
  const chapters = gameData?.chapters || [];
  const completedCh = chapters.find(c => c.chapter_id === completedChapterId);
  const nextCh = chapters.find(c => c.chapter_id === nextChapterId);
  const _inject = (text) => text ? text.replace(/\{player_name\}/g, playerName || 'You') : text;

  // Compute per-choice skill insight from delta
  const getChoiceSkill = (entry) => {
    const delta = entry?.delta || {};
    let best = null, bestVal = 0;
    for (const [k, v] of Object.entries(delta)) {
      if (typeof v === 'number' && v > bestVal && SKILL_INSIGHTS[k]) {
        best = k; bestVal = v;
      }
    }
    return best ? SKILL_INSIGHTS[best] : null;
  };

  // Aggregate strongest skills from all choices
  const skillTotals = {};
  log.forEach(entry => {
    const delta = entry?.delta || {};
    for (const [k, v] of Object.entries(delta)) {
      if (typeof v === 'number' && v > 0 && SKILL_INSIGHTS[k]) {
        skillTotals[k] = (skillTotals[k] || 0) + v;
      }
    }
  });
  const topSkills = Object.entries(skillTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([k, v]) => ({ ...SKILL_INSIGHTS[k], key: k, total: v }));

  return (
    <motion.div className="max-w-sm mx-auto px-4 py-8 flex flex-col items-center"
      initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      style={{ fontFamily: 'Georgia,serif' }}>
      {/* Completion badge */}
      <div className="relative mb-4">
        <motion.div className="w-20 h-20 rounded-full flex items-center justify-center text-4xl shadow-xl"
          style={{ background: completedCh ? completedCh.color + '22' : '#fef3d0', border: `3px solid ${completedCh?.color || '#c9853a'}` }}
          animate={{ rotate: [0, -5, 5, -3, 3, 0] }}
          transition={{ delay: 0.3, duration: 0.6 }}>
          {completedCh?.icon || '📖'}
        </motion.div>
        <motion.div className="absolute -top-1 -right-1 w-7 h-7 rounded-full bg-green-500 flex items-center justify-center text-white text-sm shadow"
          initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.5, type: 'spring' }}>
          ✓
        </motion.div>
      </div>

      {/* Text */}
      <div className="text-center mb-4">
        <p className="text-[10px] tracking-[0.2em] uppercase mb-1" style={{ color: '#b08040' }}>
          Chapter {completedCh?.number || ''} Complete!
        </p>
        <h2 className="text-xl font-bold mb-1" style={{ color: '#4a2e0a' }}>
          {completedCh?.title || 'Chapter Complete'}
        </h2>
        <p className="text-xs" style={{ color: '#7a5530' }}>
          {log.length} choice{log.length !== 1 ? 's' : ''} made in this chapter
        </p>
      </div>

      {/* XP + Coins reward banner */}
      {chapterReward && (chapterReward.xp_earned || chapterReward.coins_earned) && (
        <motion.div className="w-full mb-4 py-3 px-4 rounded-xl flex items-center justify-center gap-4"
          initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.4 }}
          style={{ background: 'linear-gradient(135deg, #FEF3C7, #FDE68A)', border: '1.5px solid #F59E0B44' }}>
          {chapterReward.xp_earned > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-lg">⭐</span>
              <span className="text-sm font-bold" style={{ color: '#92400E' }}>+{chapterReward.xp_earned} XP</span>
            </div>
          )}
          {chapterReward.coins_earned > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-lg">🪙</span>
              <span className="text-sm font-bold" style={{ color: '#92400E' }}>+{chapterReward.coins_earned} Coins</span>
            </div>
          )}
          {chapterReward.level_up && (
            <div className="flex items-center gap-1">
              <span className="text-lg">🎉</span>
              <span className="text-xs font-bold" style={{ color: '#7C3AED' }}>Level {chapterReward.new_level}!</span>
            </div>
          )}
        </motion.div>
      )}

      {/* Skills strengthened this chapter */}
      {topSkills.length > 0 && (
        <motion.div className="w-full mb-4 p-3 rounded-xl"
          initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.6 }}
          style={{ background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
          <p className="text-[10px] tracking-[0.15em] uppercase text-center mb-2 font-semibold" style={{ color: '#64748B' }}>
            Skills Strengthened
          </p>
          <div className="flex justify-center gap-3 flex-wrap">
            {topSkills.map(s => (
              <div key={s.key} className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold"
                style={{ background: s.color + '15', color: s.color, border: `1px solid ${s.color}33` }}>
                <span>{s.emoji}</span>
                <span>{s.label}</span>
                <span className="opacity-60">+{s.total}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Resources snapshot */}
      <ResourceBar resources={resources} />

      {/* Choice journal with skill callouts */}
      {log.length > 0 && (
        <div style={{ marginTop: '12px', textAlign: 'left', width: '100%' }}>
          <p style={{ fontSize: '11px', fontWeight: 700, color: '#92400E', marginBottom: '6px' }}>Your Choices:</p>
          {log.map((entry, i) => {
            const skill = getChoiceSkill(entry);
            return (
              <div key={i} style={{ fontSize: '11px', color: '#78350F', padding: '5px 0', borderBottom: '1px solid #FDE68A', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                <span style={{ flex: 1 }}>{entry.label || `Choice ${i + 1}`}</span>
                {skill && (
                  <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '9999px', background: skill.color + '15', color: skill.color, fontWeight: 600, whiteSpace: 'nowrap' }}>
                    {skill.emoji} {skill.label}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Next chapter preview */}
      {nextCh && (
        <div className="w-full mt-4 mb-4 p-4 rounded-xl"
          style={{ background: nextCh.color + '11', border: `1.5px solid ${nextCh.color}44` }}>
          <p className="text-[10px] tracking-[0.15em] uppercase mb-1 font-medium"
            style={{ color: nextCh.color }}>
            Next — Chapter {nextCh.number}
          </p>
          <p className="font-bold text-sm" style={{ color: '#4a2e0a' }}>
            {nextCh.icon} {nextCh.title}
          </p>
          <p className="text-xs mt-0.5 italic" style={{ color: '#7a5530' }}>{_inject(nextCh.teaser)}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="w-full space-y-2.5">
        {nextCh ? (
          <motion.button
            onClick={onContinue}
            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
            className="w-full py-3 rounded-xl font-semibold text-white text-sm shadow-md"
            style={{ background: `linear-gradient(135deg,${nextCh.color},${nextCh.color}cc)` }}>
            Continue to {nextCh.icon} {nextCh.title} →
          </motion.button>
        ) : (
          <p className="text-center text-sm font-semibold" style={{ color: '#16a34a' }}>
            🎉 All chapters complete!
          </p>
        )}
        <button onClick={onViewChapters}
          className="w-full py-2.5 rounded-xl text-sm font-medium"
          style={{ background: 'rgba(245,237,216,0.8)', border: '1.5px solid #d4b483', color: '#7c4a03' }}>
          View All Chapters
        </button>
      </div>
    </motion.div>
  );
};

// ─────────────────────────────────────────────────────────────
// Ending screen
// ─────────────────────────────────────────────────────────────
const EndingScreen = ({ ending, log, resources, onBack, runId, gameData, playerProfile, sceneMap = {} }) => {
  const [showRecap, setShowRecap] = useState(true);
  const [showCard, setShowCard] = useState(false);
  const [reportData, setReportData] = useState(null);

  // Fetch the final report once on mount — surfaces meta_debrief + canonical_match
  useEffect(() => {
    if (!runId) return;
    let alive = true;
    (async () => {
      try {
        const r = await endGame(runId);
        if (alive) setReportData(r || null);
      } catch (e) { /* silent — ending screen still works without report */ }
    })();
    return () => { alive = false; };
  }, [runId]);
  const palette = {
    best:       { border: '#f59e0b', bg: '#fffbeb', emoji: '🌟', label: 'Best Ending' },
    triumph:    { border: '#f59e0b', bg: '#fffbeb', emoji: '🌟', label: 'Triumph' },
    growth:     { border: '#10b981', bg: '#f0fdf4', emoji: '🌱', label: 'Growth' },
    bittersweet:{ border: '#8B5CF6', bg: '#f5f3ff', emoji: '🌅', label: 'Bittersweet' },
    redemption: { border: '#10b981', bg: '#f0fdf4', emoji: '🌱', label: 'Redemption' },
    bad:        { border: '#ef4444', bg: '#fef2f2', emoji: '💔', label: 'Difficult Ending' },
    neutral:    { border: '#FFD166', bg: '#FFFDF7', emoji: '📖', label: 'The End' },
  };
  const p = palette[ending.type] || palette.neutral;

  // Build dimension scores from resources for the character card
  const dimScores = resources?.dimension_scores
    || gameData?.initial_state?.dimension_scores
    || {};

  const playerName = playerProfile?.display_name || playerProfile?.username || 'Player';
  const gameTitle = gameData?.title || 'Story Complete';

  // Movie Recap phase
  if (showRecap && log.length > 2) {
    const choiceHistory = log.map(e => ({ label: e.label || '' }));
    return (
      <MovieRecap
        choiceHistory={choiceHistory}
        dimensionScores={dimScores}
        gameTitle={gameTitle}
        playerName={playerName}
        onComplete={() => { setShowRecap(false); setShowCard(true); }}
      />
    );
  }

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center p-4"
      style={{ background: 'linear-gradient(135deg,#FFFDF7,#FFF8E7)', fontFamily: 'Georgia,serif' }}>

      {/* Character Card phase */}
      {showCard && Object.keys(dimScores).length >= 3 && (
        <div style={{ marginBottom: '20px' }}>
          <CharacterCard
            dimensionScores={dimScores}
            gameTitle={gameTitle}
            playerName={playerName}
            mentoScore={Math.round(Object.values(dimScores).reduce((s, v) => s + (typeof v === 'number' ? v : 0), 0) / Math.max(1, Object.values(dimScores).filter(v => typeof v === 'number').length))}
            onClose={() => setShowCard(false)}
          />
        </div>
      )}

      <motion.div className="max-w-lg w-full text-center p-8 rounded-2xl shadow-xl border-2"
        initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        style={{ background: p.bg, borderColor: p.border }}>
        <div className="text-5xl mb-3">{p.emoji}</div>
        <div className="text-[10px] tracking-[0.2em] uppercase mb-1" style={{ color: p.border }}>{p.label}</div>
        <h2 className="text-2xl font-bold mb-3" style={{ color: '#2D3047' }}>
          {ending.scene?.title || 'Your Story Is Complete'}
        </h2>
        {ending.scene?.text && (
          <p style={{ color: '#64748B' }} className="mb-4 leading-relaxed">{injectPlayerName(ending.scene.text)}</p>
        )}
        {ending.message && (
          <div className="rounded-xl p-4 mb-4 italic" style={{ background: '#FFF8E7', color: '#92400E' }}>
            &ldquo;{ending.message}&rdquo;
          </div>
        )}
        <p className="text-xs mb-4" style={{ color: '#64748B' }}>
          {log.length} choice{log.length !== 1 ? 's' : ''} made · Your path shaped this story
        </p>
        <ResourceBar resources={resources} />
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '16px' }}>
          <button onClick={onBack}
            className="px-8 py-3 rounded-xl font-semibold"
            style={{ background: '#FFD166', color: '#2D3047' }}>
            Finish
          </button>
          <button onClick={() => window.location.href = '/discover'}
            className="px-6 py-3 rounded-xl font-semibold"
            style={{ background: 'white', color: '#2D3047', border: '2px solid #E2E8F0' }}>
            Home
          </button>
        </div>
        <button
          onClick={() => {
            // Clear saved progress and reload to restart
            try { localStorage.removeItem(`story_progress_${gameData?.game_id}`); } catch(e) {}
            window.location.reload();
          }}
          className="mt-3 text-xs font-medium px-4 py-2 rounded-lg mx-auto block"
          style={{ color: '#7C3AED', background: '#F5F3FF', border: '1px solid #DDD6FE' }}>
          🔄 Replay with Different Choices — develop different skills
        </button>
      </motion.div>
      {/* Story canonical-path match score + cohort hallmarks */}
      {reportData && (reportData.canonical_match || reportData.meta_debrief) && (
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.2 }}
          className="max-w-lg w-full mt-4 rounded-2xl shadow-md border-2 p-5"
          style={{ background: '#FFFDF7', borderColor: '#E0B96A', fontFamily: 'Georgia,serif' }}
        >
          {reportData.canonical_match && (() => {
            const cm = reportData.canonical_match;
            const pct = cm.percent || 0;
            const tone = pct >= 70 ? '#10B981' : pct >= 40 ? '#F59E0B' : '#EF4444';
            const label = pct >= 70 ? 'Story-savvy' : pct >= 40 ? 'Coming into your voice' : 'Re-run recommended';
            return (
              <div className="mb-4">
                <div className="text-[10px] tracking-[0.2em] uppercase" style={{ color: '#92611A' }}>
                  Path alignment
                </div>
                <div className="flex items-baseline gap-3 mt-1">
                  <div className="text-3xl font-bold" style={{ color: tone }}>{pct}%</div>
                  <div className="text-sm" style={{ color: '#5C3D14' }}>
                    {cm.matches} of {cm.total} scenes matched the expert path
                  </div>
                </div>
                <div className="text-xs mt-1" style={{ color: tone, fontWeight: 600 }}>{label}</div>
                <div className="mt-2 h-2 rounded-full overflow-hidden" style={{ background: '#F5E9CF' }}>
                  <motion.div
                    initial={{ width: 0 }} animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.8, delay: 0.4 }}
                    className="h-full" style={{ background: tone }}
                  />
                </div>
              </div>
            );
          })()}

          {reportData.meta_debrief && (() => {
            const md = reportData.meta_debrief;
            const cohort = md.matched_cohort || md.band || null;
            const high = md.cohorts?.high_score || null;
            const low = md.cohorts?.low_score || null;
            const hallmarks = (cohort === 'high_score' ? high?.hallmarks
                              : cohort === 'low_score' ? low?.hallmarks
                              : (high?.hallmarks || [])).slice(0, 4) || [];
            const cohortLabel = cohort === 'high_score' ? 'Players who score high tend to:'
                              : cohort === 'low_score' ? 'Where the gap usually opens:'
                              : 'What story-savvy players do here:';
            const tint = cohort === 'low_score' ? '#FEF3C7' : '#ECFDF5';
            const accent = cohort === 'low_score' ? '#92400E' : '#047857';
            if (hallmarks.length === 0) return null;
            return (
              <div className="rounded-xl p-3 mt-2" style={{ background: tint, border: `1px solid ${accent}33` }}>
                <div className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: accent }}>
                  {cohortLabel}
                </div>
                <ul className="space-y-1.5">
                  {hallmarks.map((h, i) => (
                    <li key={i} className="text-xs leading-snug flex gap-2" style={{ color: '#1F2937' }}>
                      <span style={{ color: accent, fontWeight: 700 }}>·</span>
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })()}
        </motion.div>
      )}

      <PostGameInsights summary={null}
        state={{
          choices_made: log.length,
          ending_type: ending.type,
          choice_history: log.map(entry => {
            const scene = sceneMap[entry.scene_id];
            const choice = scene?.choices?.find(c => c.id === entry.choice_id);
            return {
              choice_label: entry.label,
              scene_title: scene?.title || entry.scene_id,
              round: entry.scene_id,
              skill_tags: choice?.skill_tags || entry.skill_tags || [],
              delta: choice?.delta || entry.delta || {},
            };
          }),
          dimension_scores: resources?.dimension_scores || {},
        }}
        gameType="story_branching" won={ending.type === 'best' || ending.type === 'triumph'} runId={runId} />
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Choice button
// ─────────────────────────────────────────────────────────────
const ChoiceButton = ({ choice, letter, onSelect, disabled }) => {
  const [hovered, setHovered] = useState(false);
  return (
    <button onClick={() => onSelect(choice.id)} disabled={disabled}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="w-full text-left rounded-xl transition-all duration-200 disabled:opacity-50"
      style={{
        padding: '10px 14px',
        background: hovered ? '#fdf3d8' : 'rgba(255,250,240,0.85)',
        border: `1px solid ${hovered ? '#c9853a' : '#d4b483'}`,
        cursor: disabled ? 'wait' : 'pointer',
        fontFamily: 'Georgia,serif',
      }}>
      <div className="flex items-start gap-2.5">
        <span className="text-sm font-bold shrink-0 mt-0.5" style={{ color: '#c9853a', minWidth: 18 }}>
          {letter}.
        </span>
        <div>
          <span className="font-semibold text-sm sm:text-base" style={{ color: '#4a2e0a' }}>
            {choice.label}
          </span>
          {choice.description && (
            <span className="block text-xs sm:text-sm mt-0.5 italic"
              style={{ color: '#7a5530', fontFamily: 'system-ui,sans-serif' }}>
              {choice.description}
            </span>
          )}
          {choice.consequence_hint && (
            <p style={{ fontSize: '11px', color: '#9CA3AF', fontStyle: 'italic', marginTop: '4px' }}>
              {'\u{1F4AD}'} {choice.consequence_hint}
            </p>
          )}
        </div>
      </div>
    </button>
  );
};

// ─────────────────────────────────────────────────────────────
// Feature 2: Cliffhanger overlay — shown at act ends / every 3 scenes
// ─────────────────────────────────────────────────────────────
function CliffhangerOverlay({ teaser, onContinue, onSaveAndReturn }) {
  return (
    <motion.div
      className="absolute inset-0 z-50 flex flex-col items-center justify-center text-center p-6"
      style={{ background: 'linear-gradient(135deg, #FFFDF7 0%, #FFF8E7 50%, #FFF3CD 100%)' }}
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
    >
      <div className="text-6xl mb-4">🎬</div>
      <h2 style={{ color: '#2D3047' }} className="text-2xl font-black mb-2">To be continued...</h2>
      <p style={{ color: '#64748B' }} className="text-sm mb-6 max-w-xs">{teaser || "The story continues. What happens next will change everything."}</p>
      <button onClick={onContinue} className="w-full max-w-xs py-3 rounded-xl font-bold mb-3" style={{ background: '#FFD166', color: '#2D3047' }}>
        Continue Now →
      </button>
      <button onClick={onSaveAndReturn} style={{ color: '#64748B' }} className="text-sm">
        Save progress &amp; return later
      </button>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main renderer
// ─────────────────────────────────────────────────────────────
const LETTERS = ['A', 'B', 'C', 'D', 'E'];

const StoryBranchingRenderer = ({ gameData, gameState, runId, onComplete, onBack, defaultAiMode = false, playerProfile }) => {
  const { playSound } = useSound();
  const engagement = useEngagementSystem();
  const navigate = useNavigate();

  // Immersion: player name injection
  const playerName = playerProfile?.display_name || playerProfile?.username || 'You';
  const injectPlayerName = (text) => {
    if (!text) return text;
    return text.replace(/\{player_name\}/g, playerName);
  };

  const gameId = gameData?.game_id || '';
  const hasChapters = (gameData?.chapters || []).length > 0;

  const sceneMap = useMemo(() => buildSceneMap(gameData), [gameData]);
  const initialScene = useMemo(() => {
    const resumeId = gameState?.current_scene_id;
    if (resumeId && sceneMap[resumeId]) return sceneMap[resumeId];
    return getOpeningScene(gameData, sceneMap);
  }, [gameData, sceneMap, gameState]);

  // View state: 'cover' | 'chapter_select' | 'reading' | 'chapter_complete' | 'ending'
  const [view, setView] = useState('cover');
  const [currentScene, setCurrentScene] = useState(initialScene);
  const [currentChapterId, setCurrentChapterId] = useState(null);
  const [completedChapters, setCompletedChapters] = useState(() => getCompletedChapters(gameId));
  const [pendingNextChapter, setPendingNextChapter] = useState(null);
  const [chapterReward, setChapterReward] = useState(null);
  const [resources, setResources] = useState(() => {
    if (gameState && typeof gameState === 'object') return gameState;
    return gameData?.initial_state || {};
  });
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ending, setEnding] = useState(null);
  const [pageKey, setPageKey] = useState(0);
  const [deltaFlash, setDeltaFlash] = useState(null);
  const [skillCallout, setSkillCallout] = useState(null);
  const [choiceDeltas, setChoiceDeltas] = useState(null);
  // Story expert-pick reveal: { was_expert_pick, label, reason, counterfactual, scene_id, choice_id }
  const [expertReveal, setExpertReveal] = useState(null);
  // Live-LLM challenge modal — { open, history: [{role,content}], loading, scene_id, choice_id }
  const [challenge, setChallenge] = useState({ open: false, history: [], loading: false, scene_id: null, choice_id: null });
  const [challengeReply, setChallengeReply] = useState('');

  // Feature 2: Cliffhanger state — shown at act_end scenes or every 3 scenes
  const [showCliffhanger, setShowCliffhanger] = useState(false);
  const [dismissedCliffhanger, setDismissedCliffhanger] = useState(false);

  // Field mission case files — pre-loaded on the very first scene of any game
  // that belongs to a module where the student logged real-world complaints.
  const [caseFiles, setCaseFiles] = useState([]);
  const [caseFilesDismissed, setCaseFilesDismissed] = useState(false);
  useEffect(() => {
    const moduleId = gameData?.module_id;
    if (!moduleId) return;
    let cancel = false;
    (async () => {
      try {
        const r = await getAllFieldMissionEntries(moduleId);
        if (!cancel) setCaseFiles(r?.entries || []);
      } catch (e) { /* silent — feature is opt-in */ }
    })();
    return () => { cancel = true; };
  }, [gameData?.module_id]);
  const pendingSceneRef = useRef(null); // holds next scene while cliffhanger is displayed

  // Story So Far recap state
  const [showRecap, setShowRecap] = useState(false);
  const [savedProgress, setSavedProgress] = useState(null);

  // Skip cover if resuming mid-story
  useEffect(() => {
    if (gameState?.current_scene_id && sceneMap[gameState.current_scene_id]) {
      setView('reading');
    }
  }, []); // eslint-disable-line

  // Resume handler — restore scene + log from saved progress
  const handleResume = useCallback(() => {
    if (savedProgress && sceneMap[savedProgress.scene_id]) {
      setCurrentScene(sceneMap[savedProgress.scene_id]);
      setLog(savedProgress.log || []);
      setPageKey(k => k + 1);
    }
    setShowRecap(false);
    setView('reading');
  }, [savedProgress, sceneMap]);

  // Open Book button — check for saved progress, go to chapter select or reading
  const handleOpenBook = useCallback(() => {
    const progress = loadStoryProgress(gameId);
    if (progress && progress.log && progress.log.length > 0) {
      setSavedProgress(progress);
      setShowRecap(true);
      if (hasChapters) {
        setView('chapter_select');
      } else {
        setView('reading');
      }
    } else {
      if (hasChapters) {
        setView('chapter_select');
      } else {
        setView('reading');
      }
    }
  }, [hasChapters, gameId]);

  // Select a chapter from the chapter select screen
  const handleSelectChapter = useCallback((chapterId) => {
    const startScene = getChapterStartScene(gameData, sceneMap, chapterId);
    if (startScene) {
      setCurrentScene(startScene);
      setCurrentChapterId(chapterId);
      setPageKey(k => k + 1);
      setView('reading');
    }
  }, [gameData, sceneMap]);

  // Continue to the next chapter from chapter_complete screen
  const handleContinueToNextChapter = useCallback(() => {
    if (pendingNextChapter) {
      handleSelectChapter(pendingNextChapter);
      setPendingNextChapter(null);
    } else {
      setView('chapter_select');
    }
  }, [pendingNextChapter, handleSelectChapter]);

  // Open the live-LLM "challenge me" modal. Pulls scene/choice IDs from expertReveal.
  const openChallenge = useCallback(async () => {
    if (!expertReveal?.scene_id || !expertReveal?.choice_id) return;
    setChallenge({
      open: true, history: [], loading: true,
      scene_id: expertReveal.scene_id, choice_id: expertReveal.choice_id,
    });
    setChallengeReply('');
    try {
      const res = await submitStoryChallenge(runId, expertReveal.scene_id, expertReveal.choice_id, '', []);
      const npcMsg = res?.response || 'Tell me more — why did you make that call?';
      setChallenge(c => ({
        ...c, loading: false,
        history: [{ role: 'assistant', content: npcMsg, feedback: res?.feedback || '', tone: res?.tone || '' }],
      }));
    } catch (e) {
      setChallenge(c => ({ ...c, loading: false,
        history: [{ role: 'assistant', content: 'I want to push back on that — but the line dropped. Try again?', feedback: '', tone: 'neutral' }] }));
    }
  }, [expertReveal, runId]);

  const submitChallengeTurn = useCallback(async () => {
    const reply = (challengeReply || '').trim();
    if (!reply || !challenge.scene_id || !challenge.choice_id) return;
    const newHistory = [...challenge.history, { role: 'user', content: reply }];
    setChallenge(c => ({ ...c, history: newHistory, loading: true }));
    setChallengeReply('');
    try {
      const apiHistory = newHistory.map(m => ({
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: m.content,
      }));
      const res = await submitStoryChallenge(runId, challenge.scene_id, challenge.choice_id, reply, apiHistory.slice(0, -1));
      const npcMsg = res?.response || 'Hmm — say more.';
      setChallenge(c => ({
        ...c, loading: false,
        history: [...newHistory, { role: 'assistant', content: npcMsg, feedback: res?.feedback || '', tone: res?.tone || '' }],
      }));
    } catch (e) {
      setChallenge(c => ({ ...c, loading: false,
        history: [...newHistory, { role: 'assistant', content: 'Something went wrong. Try again?', feedback: '', tone: 'neutral' }] }));
    }
  }, [challengeReply, challenge, runId]);

  const handleChoice = useCallback(async (choiceId) => {
    if (loading || !currentScene) return;
    playSound?.('button_click');
    setLoading(true);
    setDeltaFlash(null);

    try {
      const result = await submitBranchingChoice(runId, currentScene.id, choiceId);
      if (result.state) setResources(result.state);

      // Engagement feedback from choice delta
      const choice = currentScene.choices?.find(c => c.id === choiceId);
      if (choice?.delta) {
        setDeltaFlash(choice.delta);
        setTimeout(() => setDeltaFlash(null), 2200);
        const rawSum = Object.values(choice.delta).reduce(
          (s, v) => s + (typeof v === 'number' ? v : 0), 0
        );
        engagement.recordChoice(rawSum);

        // Show skill callout with actual dimension name and numeric delta
        const _SKILL_DIM_LABELS = {
          strategic_thinking: 'Strategic Thinking', risk_tolerance: 'Risk Tolerance',
          delayed_gratification: 'Delayed Gratification', adaptability: 'Adaptability',
          resilience: 'Resilience', empathy: 'Empathy',
          ethical_reasoning: 'Ethical Reasoning', creativity: 'Creativity',
        };
        const _SKILL_DIM_ICONS = {
          strategic_thinking: 'brain', risk_tolerance: 'flame', delayed_gratification: 'hourglass',
          adaptability: 'refresh', resilience: 'shield', empathy: 'heart',
          ethical_reasoning: 'brain', creativity: 'brain',
        };
        const skillTags = choice.skill_tags || [];
        const primaryDim = skillTags[0] || Object.keys(choice.delta)[0] || 'strategic_thinking';
        const dimLabel = _SKILL_DIM_LABELS[primaryDim] || primaryDim.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        const sign = rawSum >= 0 ? '+' : '';
        const secondTag = skillTags[1] ? ` | ${_SKILL_DIM_LABELS[skillTags[1]] || skillTags[1].replace(/_/g, ' ')}` : '';
        setSkillCallout({
          dimension: primaryDim,
          label: dimLabel,
          delta: rawSum,
          message: `${sign}${rawSum} ${dimLabel}${secondTag}`,
          color: rawSum >= 0 ? '#10B981' : '#EF4444',
          icon: _SKILL_DIM_ICONS[primaryDim] || 'brain',
        });

        // Synthesize skill dimension deltas from skill_tags for ChoiceExplanation
        if (skillTags.length > 0) {
          const perTag = Math.max(1, Math.round(Math.abs(rawSum) / skillTags.length));
          const synthDeltas = {};
          skillTags.forEach(tag => {
            if (_SKILL_DIM_LABELS[tag]) {
              synthDeltas[tag] = rawSum >= 0 ? perTag : -perTag;
            }
          });
          if (Object.keys(synthDeltas).length > 0) {
            setChoiceDeltas(synthDeltas);
          }
        }
      }

      // Expert pick reveal — server returns expert_pick + counterfactual_for_chosen
      if (result.expert_pick) {
        const ep = result.expert_pick;
        setExpertReveal({
          was_expert_pick: !!ep.was_expert_pick,
          label: ep.label || '',
          reason: ep.reason || '',
          counterfactual: result.counterfactual_for_chosen || null,
          scene_id: currentScene?.id,
          choice_id: choiceId,
        });
      }

      const newLogEntry = {
        scene_id: currentScene.id, choice_id: choiceId, label: choice?.label || '',
        delta: choice?.delta || {}, skill_tags: choice?.skill_tags || [],
      };
      setLog(prev => {
        const updated = [...prev, newLogEntry];
        saveStoryProgress(gameId, currentScene.id, updated);
        return updated;
      });

      if (result.is_ending) {
        // Story is fully over
        const endScene = result.next_scene ? normalizeScene(result.next_scene) : null;
        setEnding({ scene: endScene, type: result.ending_type, message: result.ending_message });
        setView('ending');
        onComplete?.();
      } else if (result.next_chapter) {
        // This chapter is done — unlock next chapter and show chapter complete screen
        markChapterComplete(gameId, currentChapterId);
        const updated = getCompletedChapters(gameId);
        setCompletedChapters(updated);
        setPendingNextChapter(result.next_chapter);
        setChapterReward(result.chapter_reward || null);
        setView('chapter_complete');
      } else if (result.next_scene) {
        // Feature 2: Cliffhanger check — show at act_end scenes or every 3 choices
        const nextScene = normalizeScene(result.next_scene);
        const newLogLength = log.length + 1;
        const isActEnd = currentScene?.scene_type === 'act_end' || result.next_scene?.scene_type === 'act_end';
        const isThreeSceneMilestone = newLogLength > 0 && newLogLength % 3 === 0;
        if (!dismissedCliffhanger && (isActEnd || isThreeSceneMilestone)) {
          pendingSceneRef.current = nextScene;
          setShowCliffhanger(true);
        } else {
          // Continue within same chapter
          setCurrentScene(nextScene);
          setPageKey(k => k + 1);
        }
      }
    } catch (err) {
      console.error('Story branching choice error:', err);
    } finally {
      setLoading(false);
    }
  }, [loading, currentScene, runId, onComplete, playSound, engagement, gameId, currentChapterId]);

  const _brandBg = { background: 'linear-gradient(135deg, #FFFDF7 0%, #FFF8E7 50%, #FEF3D0 100%)', minHeight: '100vh' };

  // ── Cover ──────────────────────────────────────────────────
  if (view === 'cover') {
    return (
      <div style={_brandBg}>
        <div className="max-w-lg mx-auto px-4 py-6">
          <BookCover gameData={gameData} onOpen={handleOpenBook} onBack={onBack} />
        </div>
      </div>
    );
  }

  // ── Chapter select ─────────────────────────────────────────
  if (view === 'chapter_select') {
    return (
      <div style={_brandBg}>
        <ChapterSelectScreen
          gameData={gameData}
          completedChapters={completedChapters}
          onSelectChapter={handleSelectChapter}
          onBack={() => setView('cover')}
        />
      </div>
    );
  }

  // ── Chapter complete ───────────────────────────────────────
  if (view === 'chapter_complete') {
    return (
      <div style={_brandBg}>
        <ChapterCompleteScreen
          gameData={gameData}
          completedChapterId={currentChapterId}
          nextChapterId={pendingNextChapter}
          log={log}
          resources={resources}
          chapterReward={chapterReward}
          onContinue={handleContinueToNextChapter}
          onViewChapters={() => { setPendingNextChapter(null); setView('chapter_select'); }}
          playerName={playerName}
        />
      </div>
    );
  }

  // ── Ending ─────────────────────────────────────────────────
  if (view === 'ending' && ending) {
    return <div style={_brandBg}><EndingScreen ending={ending} log={log} resources={resources} onBack={onBack} runId={runId} gameData={gameData} playerProfile={playerProfile} sceneMap={sceneMap} /></div>;
  }

  // ── No scene data ──────────────────────────────────────────
  if (!currentScene) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-gray-500">Story not available. Check game data.</p>
      </div>
    );
  }

  // ── Reading view ───────────────────────────────────────────
  // Show current chapter breadcrumb if game has chapters
  const chapters = gameData?.chapters || [];
  const activeCh = chapters.find(c => c.chapter_id === currentChapterId);

  return (
    <div style={_brandBg}>
      <FloatingDeltaLayer floatingDeltas={engagement.floatingDeltas} />
      <StreakBanner streakCount={engagement.streakCount} streakMultiplier={engagement.streakMultiplier} />

      {/* Feature 2: Cliffhanger overlay */}
      <AnimatePresence>
        {showCliffhanger && (
          <div className="fixed inset-0 z-50">
            <CliffhangerOverlay
              teaser={pendingSceneRef.current?.teaser || pendingSceneRef.current?.title ? `Coming up: "${pendingSceneRef.current.title}"` : undefined}
              onContinue={() => {
                setShowCliffhanger(false);
                setDismissedCliffhanger(true);
                if (pendingSceneRef.current) {
                  setCurrentScene(pendingSceneRef.current);
                  setPageKey(k => k + 1);
                  pendingSceneRef.current = null;
                }
              }}
              onSaveAndReturn={() => {
                setShowCliffhanger(false);
                setDismissedCliffhanger(true);
                navigate('/home/student', { state: { savedProgress: true } });
              }}
            />
          </div>
        )}
      </AnimatePresence>

      <motion.div className="max-w-2xl md:max-w-3xl lg:max-w-4xl mx-auto px-4 md:px-6 py-5"
        animate={engagement.triggerScreenShake ? { x: [0, -5, 5, -3, 3, 0] } : {}}
        transition={engagement.triggerScreenShake ? { duration: 0.5 } : {}}>

        {/* Player avatar chip */}
        {playerProfile && (
          <PlayerAvatarCard
            name={playerProfile.display_name}
            avatar={playerProfile.avatar}
            avatarUrl={playerProfile.avatar_url}
            level={playerProfile.level}
            frame={playerProfile.avatar_frame}
            size="sm"
          />
        )}

        {/* Chapter breadcrumb (only for chapter-based games) */}
        {activeCh && (
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => setView('chapter_select')}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full"
              style={{ background: activeCh.color + '18', color: activeCh.color, border: `1px solid ${activeCh.color}44` }}>
              ← Chapters
            </button>
            <span className="text-xs font-semibold px-3 py-1.5 rounded-full"
              style={{ background: activeCh.color + '18', color: activeCh.color, border: `1px solid ${activeCh.color}44` }}>
              {activeCh.icon} Chapter {activeCh.number}: {activeCh.title}
            </span>
          </div>
        )}

        {/* Story So Far recap */}
        {showRecap && savedProgress && (
          <div style={{ padding: '16px', background: '#FFFBEB', borderRadius: '12px', border: '1px solid #FDE68A', marginBottom: '12px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#92400E', margin: 0 }}>📖 Story So Far</h4>
            <p style={{ fontSize: '12px', color: '#78350F', marginTop: '4px' }}>
              You made {savedProgress.log.length} choice{savedProgress.log.length !== 1 ? 's' : ''}. Your last scene was: {sceneMap[savedProgress.scene_id]?.title || savedProgress.scene_id}
            </p>
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <button onClick={handleResume} style={{ padding: '8px 16px', background: '#FFD166', borderRadius: '8px', fontWeight: 600, fontSize: '13px', border: 'none', cursor: 'pointer' }}>
                Continue Story
              </button>
              <button onClick={() => setShowRecap(false)} style={{ padding: '8px 16px', background: '#F3F4F6', borderRadius: '8px', fontSize: '13px', border: 'none', cursor: 'pointer' }}>
                Start Fresh
              </button>
            </div>
          </div>
        )}

        {/* Resource tracker */}
        <ResourceBar resources={resources} />

        {/* Live skill radar — compute dimension scores from choice skill_tags */}
        {log.length >= 2 && (() => {
          const dimCounts = {};
          log.forEach(entry => {
            (entry.skill_tags || []).forEach(tag => {
              dimCounts[tag] = (dimCounts[tag] || 0) + 1;
            });
          });
          const maxCount = Math.max(1, ...Object.values(dimCounts));
          const liveScores = {};
          Object.entries(dimCounts).forEach(([dim, count]) => {
            liveScores[dim] = Math.round((count / maxCount) * 80 + 20);
          });
          return Object.keys(liveScores).length >= 3
            ? <LiveSkillRadar gameState={{ dimension_scores: liveScores }} compact={true} />
            : null;
        })()}

        {/* Delta flash (brief skill highlights after choice) */}
        <AnimatePresence>
          {deltaFlash && (
            <motion.div className="flex flex-wrap gap-2 justify-center mb-3"
              initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              {Object.entries(deltaFlash).map(([key, val]) => (
                <span key={key}
                  className={`text-xs font-bold px-2.5 py-1 rounded-full ${val > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {key.replace(/_/g, ' ')}: {val > 0 ? '+' : ''}{val}
                </span>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Book page with page-flip animation */}
        <AnimatePresence mode="wait">
          <motion.div key={pageKey}
            initial={{ opacity: 0, x: 60, rotateY: 8 }}
            animate={{ opacity: 1, x: 0, rotateY: 0 }}
            exit={{ opacity: 0, x: -60, rotateY: -8 }}
            transition={{ duration: 0.35, ease: 'easeInOut' }}
            className="rounded-2xl overflow-hidden"
            style={{
              background: 'linear-gradient(160deg,#fefcf0 0%,#fef8e4 100%)',
              border: '1px solid #e8d5a3',
              boxShadow: '4px 0 0 0 #dcc480 inset, 0 8px 32px rgba(160,120,40,0.14)',
              fontFamily: 'Georgia,"Times New Roman",serif',
            }}>

            {/* Scene illustration */}
            {(currentScene.image_url || currentScene.image_prompt) && (
              <div style={{ borderBottom: '2px solid #e8d5a3' }}>
                <SceneImageLoader
                  gameId={gameId}
                  sceneId={currentScene.id}
                  imagePrompt={currentScene.image_prompt}
                />
              </div>
            )}

            {/* Scene header */}
            <div className="px-6 pt-5 pb-2">
              <div className="flex items-center gap-2 mb-2">
                <div className="flex-1 h-px" style={{ background: 'linear-gradient(to right,transparent,#c9a96e)' }} />
                <span className="text-[10px] tracking-[0.2em] uppercase" style={{ color: '#b08040' }}>
                  Scene {log.length + 1}
                </span>
                <div className="flex-1 h-px" style={{ background: 'linear-gradient(to left,transparent,#c9a96e)' }} />
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-center"
                style={{ color: '#4a2e0a', letterSpacing: '0.01em' }}>
                {currentScene.title}
              </h2>
            </div>

            {/* Feature 4b: "Previously on..." recap for story chapter starts */}
            {currentScene?.scene_id?.endsWith('_s1') && log.length > 0 && currentChapterId !== 'ch1' && (
              <div style={{ margin: '0 12px 12px', padding: '10px 14px', background: '#FFF7ED', borderRadius: '10px', border: '1px solid #FED7AA' }}>
                <p style={{ fontSize: '12px', color: '#92400E', fontStyle: 'italic' }}>
                  {'\u{1F4D6}'} <strong>Previously...</strong> {log.slice(-2).map(e => e.label).filter(Boolean).join('. Then, ')}
                </p>
              </div>
            )}

            {/* Narrative */}
            <div className="px-6 pb-5">
              <p className="text-base sm:text-lg leading-relaxed" style={{ color: '#3a2508', lineHeight: 1.9 }}>
                {injectPlayerName(currentScene.text)}
              </p>
            </div>

            {/* Case files panel — shown on the FIRST scene only, when the
                player has logged real-world complaints in a Field Mission. */}
            {log.length === 0 && caseFiles.length > 0 && !caseFilesDismissed && (
              <div className="mx-6 mb-5 rounded-xl overflow-hidden"
                style={{ border: '2px solid #c9a96e' }}>
                <div className="px-3 py-2 flex items-center justify-between"
                  style={{ background: 'linear-gradient(90deg,#92400e,#b45309)', color: '#fff' }}>
                  <span className="text-[11px] font-black uppercase tracking-widest">
                    🕵️ Your Case Files ({caseFiles.length})
                  </span>
                  <button type="button" onClick={() => setCaseFilesDismissed(true)}
                    className="text-white/80 hover:text-white text-xs font-bold">
                    Hide
                  </button>
                </div>
                <div className="px-3 py-3 space-y-1.5 max-h-44 overflow-y-auto"
                  style={{ background: '#fff7ed' }}>
                  <p className="text-[11px] italic mb-2" style={{ color: '#92400e' }}>
                    Mento taps the dossier: "These are the real complaints YOU collected. Keep them in mind as we listen to today's voices."
                  </p>
                  {caseFiles.slice(0, 6).map((cf, i) => (
                    <div key={cf.entry_id || i} className="text-xs flex items-start gap-2"
                      style={{ color: '#3a2508' }}>
                      <span className="font-black flex-shrink-0" style={{ color: '#b45309' }}>
                        #{i + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium leading-snug">"{cf.complaint || '(media note)'}"</div>
                        {(cf.person || cf.frequency) && (
                          <div className="text-[10px] opacity-70">
                            {cf.person && <>👤 {cf.person}</>}
                            {cf.person && cf.frequency && <> · </>}
                            {cf.frequency && <>🔁 {cf.frequency}</>}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {caseFiles.length > 6 && (
                    <div className="text-[10px] italic pt-1"
                      style={{ color: '#92400e' }}>
                      +{caseFiles.length - 6} more captured in your notebook…
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Divider */}
            <div className="mx-6" style={{ borderTop: '1px solid #e8d5a3' }} />

            {/* Choices */}
            <div className="px-6 pt-4 pb-6">
              <p className="text-[10px] tracking-[0.2em] uppercase text-center mb-3" style={{ color: '#b08040' }}>
                — What do you choose? —
              </p>
              <div className="space-y-2.5">
                {currentScene.chat_breakout ? (
                  <NarrativeChatBreakout
                    runId={runId}
                    scene={{ ...currentScene, scene_id: currentScene.scene_id || currentScene.id }}
                    onComplete={({ next_scene_id, outcome, outcome_label }) => {
                      if (next_scene_id && sceneMap[next_scene_id]) {
                        setCurrentScene(sceneMap[next_scene_id]);
                        setPageKey(k => k + 1);
                      } else {
                        setEnding({ scene: null, type: 'breakout', message: outcome_label || `Outcome: ${outcome}` });
                        setView('ending');
                        onComplete?.();
                      }
                    }}
                  />
                ) : (
                  (currentScene.choices || []).map((choice, i) => (
                    <ChoiceButton key={choice.id} choice={choice}
                      letter={LETTERS[i] || String(i + 1)}
                      onSelect={handleChoice} disabled={loading} />
                  ))
                )}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Coach panel */}
        <CoachPanel gameData={gameData} sceneCount={log.length + 1} />

        {/* Progress footer */}
        <div className="flex items-center justify-between mt-3 text-xs"
          style={{ color: '#b08040', fontFamily: 'system-ui,sans-serif' }}>
          <span>{log.length > 0 ? `${log.length} choice${log.length > 1 ? 's' : ''} made` : 'Your story begins…'}</span>
          {hasChapters ? (
            <button onClick={() => setView('chapter_select')}
              className="text-[11px] underline opacity-60 hover:opacity-100" style={{ color: '#b08040' }}>
              ← Chapters
            </button>
          ) : (
            <button onClick={() => setView('cover')}
              className="text-[11px] underline opacity-60 hover:opacity-100" style={{ color: '#b08040' }}>
              ← Cover
            </button>
          )}
          <span>{Object.keys(sceneMap).length} scenes</span>
        </div>
      </motion.div>

      <SkillCallout callout={skillCallout} onDismiss={() => setSkillCallout(null)} />
      <ChoiceExplanation deltas={choiceDeltas} onDismiss={() => setChoiceDeltas(null)} />

      {/* Expert pick reveal — appears after each choice */}
      <AnimatePresence>
        {expertReveal && (
          <motion.div
            key="expert-reveal"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.35 }}
            className="fixed left-1/2 -translate-x-1/2 z-50 max-w-md w-[92%]"
            style={{ bottom: '24px' }}
            onAnimationComplete={() => {
              window.clearTimeout(window.__expertRevealTO);
              window.__expertRevealTO = window.setTimeout(() => setExpertReveal(null), 6000);
            }}
          >
            <div
              className="rounded-xl shadow-2xl px-4 py-3 border-2"
              style={{
                background: expertReveal.was_expert_pick ? '#ECFDF5' : '#FFF8EA',
                borderColor: expertReveal.was_expert_pick ? '#10B981' : '#E0B96A',
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div
                    className="text-xs font-bold uppercase tracking-wide mb-1"
                    style={{ color: expertReveal.was_expert_pick ? '#047857' : '#92611A' }}
                  >
                    {expertReveal.was_expert_pick ? '✓ Expert pick' : '💡 The expert pick was'}
                  </div>
                  {!expertReveal.was_expert_pick && expertReveal.label && (
                    <div className="text-sm font-semibold mb-1" style={{ color: '#5C3D14' }}>
                      "{expertReveal.label}"
                    </div>
                  )}
                  {expertReveal.reason && (
                    <div className="text-xs leading-snug mb-1" style={{ color: '#6B4D1A' }}>
                      {expertReveal.reason}
                    </div>
                  )}
                  {!expertReveal.was_expert_pick && expertReveal.counterfactual && (
                    <div
                      className="text-xs leading-snug mt-1.5 pt-1.5 border-t"
                      style={{ color: '#5C3D14', borderColor: 'rgba(176,128,64,0.25)' }}
                    >
                      {expertReveal.counterfactual}
                    </div>
                  )}
                  <button
                    onClick={openChallenge}
                    className="mt-2 text-[11px] font-bold px-2.5 py-1 rounded-md border"
                    style={{
                      color: '#5C3D14',
                      background: 'rgba(255,255,255,0.6)',
                      borderColor: 'rgba(176,128,64,0.6)',
                    }}
                  >
                    🤔 Challenge me on this
                  </button>
                </div>
                <button
                  onClick={() => setExpertReveal(null)}
                  className="text-xs opacity-60 hover:opacity-100 leading-none p-1"
                  style={{ color: '#92611A' }}
                  aria-label="Dismiss"
                >
                  ✕
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Live-LLM Challenge Modal */}
      <AnimatePresence>
        {challenge.open && (
          <motion.div
            key="challenge-modal"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-end md:items-center justify-center p-3"
            style={{ background: 'rgba(0,0,0,0.5)' }}
            onClick={(e) => { if (e.target === e.currentTarget) setChallenge(c => ({ ...c, open: false })); }}
          >
            <motion.div
              initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
              className="w-full max-w-md rounded-2xl shadow-2xl border-2 overflow-hidden"
              style={{ background: '#FFFDF7', borderColor: '#E0B96A' }}
            >
              <div className="px-4 py-3 flex items-center justify-between border-b" style={{ borderColor: 'rgba(176,128,64,0.3)' }}>
                <div>
                  <div className="text-[10px] tracking-[0.2em] uppercase" style={{ color: '#92611A' }}>The Skeptic</div>
                  <div className="text-sm font-bold" style={{ color: '#2D3047' }}>Defend your reasoning</div>
                </div>
                <button onClick={() => setChallenge(c => ({ ...c, open: false }))}
                  className="text-base opacity-60 hover:opacity-100" style={{ color: '#92611A' }}>✕</button>
              </div>
              <div className="px-4 py-3 max-h-[55vh] overflow-y-auto space-y-3">
                {challenge.history.map((m, i) => (
                  <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className="rounded-xl px-3 py-2 max-w-[85%] text-sm leading-snug"
                      style={m.role === 'user'
                        ? { background: '#E0B96A', color: '#2D3047' }
                        : { background: '#F5E9CF', color: '#2D3047' }}
                    >
                      {m.content}
                      {m.feedback && (
                        <div className="text-[10px] mt-1.5 pt-1.5 border-t italic"
                          style={{ borderColor: 'rgba(176,128,64,0.3)', color: '#6B4D1A' }}>
                          {m.feedback}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {challenge.loading && (
                  <div className="flex justify-start">
                    <div className="rounded-xl px-3 py-2 text-xs italic" style={{ background: '#F5E9CF', color: '#6B4D1A' }}>
                      thinking…
                    </div>
                  </div>
                )}
              </div>
              <div className="px-3 py-3 border-t flex gap-2" style={{ borderColor: 'rgba(176,128,64,0.3)', background: '#FFF8E7' }}>
                <input
                  type="text"
                  value={challengeReply}
                  onChange={(e) => setChallengeReply(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !challenge.loading) submitChallengeTurn(); }}
                  placeholder="Defend your choice…"
                  disabled={challenge.loading}
                  className="flex-1 text-sm px-3 py-2 rounded-lg border"
                  style={{ borderColor: 'rgba(176,128,64,0.4)', background: 'white', color: '#2D3047' }}
                />
                <button
                  onClick={submitChallengeTurn}
                  disabled={challenge.loading || !challengeReply.trim()}
                  className="text-sm font-bold px-4 py-2 rounded-lg disabled:opacity-40"
                  style={{ background: '#E0B96A', color: '#2D3047' }}
                >
                  Reply
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <StoryAgent
        runId={runId}
        currentScene={currentScene}
        choices={currentScene?.choices}
        onChoiceSelect={handleChoice}
        gameData={gameData}
        defaultAiMode={false}
      />
    </div>
  );
};

export default StoryBranchingRenderer;
