import React, { useEffect, useState, useRef, Suspense } from "react";

// UUID polyfill — works on both HTTP and HTTPS contexts
const generateUUID = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
};
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaHome,
  FaRedo,
  FaMicrophone,
  FaComments,
  FaHammer,
  FaSitemap,
  FaSkullCrossbones,
  FaGamepad,
  FaChevronRight,
  FaChevronLeft,
  FaChartLine,
  FaStar,
  FaGem,
  FaLightbulb,
  FaClock,
  FaFlag,
  FaBrain,
  FaCoins,
  FaBolt,
  FaCrown,
  FaHeart,
  FaQuestionCircle,
  FaTimes,
  FaBookOpen,
} from "react-icons/fa";
import { useGame } from "../contexts/GameContext";
import { useTheme } from "../contexts/ThemeContext";
import { useAudio } from "../contexts/AudioContext";
import { games } from "../api/crud";
import { getStoryImage } from "../api/storyImages";
import { getProfile, logQuitSession, getFrustrationCheck, getLeaderboardPercentile } from "../api/profile";

import "./GamePlayPage.css";

// Import game components
import ErrorScreen from "../components/common/ErrorScreen";
import ErrorBoundary from "../components/ui/ErrorBoundary";
import StoryDisplay from "../components/game/StoryDisplay";
import ChoiceSelector from "../components/game/ChoiceSelector";
import ResourceDashboard from "../components/game/ResourceDashboard";
import RoundTakeawayModal from "../components/game/RoundTakeawayModal";
import GameOverScreen from "../components/game/GameOverScreen";
import MentoReport from "../components/game/MentoReport";
import MysteryRoomEpilogue from "../components/game/mystery/MysteryRoomEpilogue";
import PsychologyPanel from "../components/game/PsychologyPanel";
import LiveSkillRadar from "../components/game/LiveSkillRadar";
import GameIntro from "../components/game/GameIntro";
import GameTimeline from "../components/game/GameTimeline";
import GlossaryPanel from "../components/game/GlossaryPanel";
import MentoGuide from "../components/game/MentoGuide";
import ConsequenceScene from "../components/game/ConsequenceScene";
import ReflectionModal from "../components/game/ReflectionModal";
import HalftimeCheckpoint from "../components/game/HalftimeCheckpoint";
import SkillCallout from "../components/game/SkillCallout";
import TeachableMomentCard from "../components/game/TeachableMomentCard";
import PostChoiceReflection from "../components/game/PostChoiceReflection";
import ReflectionPrompt from "../components/game/ReflectionPrompt";
import ChoiceExplanation from "../components/game/ChoiceExplanation";
import FreetextInput from "../components/game/FreetextInput";
import LLMFeedbackCard from "../components/game/LLMFeedbackCard";
import SkillIntroCard from "../components/game/SkillIntroCard";
import AchievementUnlock from "../components/game/AchievementUnlock";
import NarrativeBridge from "../components/game/NarrativeBridge";
import RoundTimer from "../components/game/RoundTimer";
import CheckpointQuiz from "../components/game/CheckpointQuiz";
import LeaderboardPreview from "../components/game/LeaderboardPreview";
import SpeedRunTimer from "../components/game/SpeedRunTimer";
import PostGameRankChange from "../components/game/PostGameRankChange";
import DemoLimitModal from "../components/ui/DemoLimitModal";
import MentoAgent from "../components/game/MentoAgent";
import MarketFeed from "../components/game/MarketFeed";
import LemonadeDashboard from "../components/game/LemonadeDashboard";
import LiveInvestorModal from "../components/game/LiveInvestorModal";
import DissentJurorModal from "../components/game/DissentJurorModal";
import MentoExplainPopover from "../components/game/MentoExplainPopover";
import LiveBoardDebateModal from "../components/game/LiveBoardDebateModal";
import PvpLauncherModal from "../components/game/PvpLauncherModal";
import useSoundscape from "../hooks/useSoundscape";
import { tRound } from "../utils/gameTranslations";
import V2Panel from "../components/game/v2/V2Panel";
import ModePersonaSelector from "../components/game/v2/ModePersonaSelector";
import ChoiceHoverPreview from "../components/game/v2/ChoiceHoverPreview";
import { isV2Game, getDailyChallenge, getLegacyStatus } from "../api/v2";
import ChallengeResult from "../components/game/ChallengeResult";
import StructuredFormInput from "../components/game/inputs/StructuredFormInput";
import SliderRatingInput from "../components/game/inputs/SliderRatingInput";
import ChecklistInput from "../components/game/inputs/ChecklistInput";
import { generateRound } from "../api/games";
import { getBaselineStatus } from "../api/family";
import { useAuth } from "../contexts/AuthContext";

// Feature components
import VoiceInput from "../components/features/VoiceInput";
import DialoguePanel from "../components/features/DialoguePanel";
import CraftingPanel from "../components/features/CraftingPanel";
import TechTreePanel from "../components/features/TechTreePanel";
import RPGBattlePanel from "../components/features/RPGBattlePanel";
import AchievementPopup from "../components/features/AchievementPopup";

// Game type routing (board games, mini-games)
const GameTypeRouter = React.lazy(() => import('../components/game/GameTypeRouter'));

import useEngagementSystem from '../hooks/useEngagementSystem';
import { FloatingDeltaLayer, StreakBanner } from '../components/game/BoardGameExtras';
import apiClient from '../api/client';

// Game mode overlays
const VideoIntroOverlay = React.lazy(() => import('../components/game/overlays/VideoIntroOverlay'));
const StorybookOverlay = React.lazy(() => import('../components/game/overlays/StorybookOverlay'));
const TraitJourneyOverlay = React.lazy(() => import('../components/game/overlays/TraitJourneyOverlay'));
const QuizOverlay = React.lazy(() => import('../components/game/overlays/QuizOverlay'));
const TradingOverlay = React.lazy(() => import('../components/game/overlays/TradingOverlay'));
const SurvivalOverlay = React.lazy(() => import('../components/game/overlays/SurvivalOverlay'));
const CityBuilderOverlay = React.lazy(() => import('../components/game/overlays/CityBuilderOverlay'));
const SoundControls = React.lazy(() => import('../components/ui/SoundControls'));
const GameStorybook = React.lazy(() => import('../components/game/GameStorybook'));

const INPUT_WIDGETS = {
  structured_form: StructuredFormInput,
  slider_rating: SliderRatingInput,
  checklist: ChecklistInput,
};

// Color theme
const colors = {
  primary: "#FFD166",
  primaryLight: "#FFE8A5",
  primaryDark: "#FFC145",

  // Backgrounds
  background: "#FFFFFF", // was #FFFDF7
  card: "#FFFFFF",

  // Text
  text: "#2D3047", // keep dark for readability
  textLight: "#6B7280", // replaced gray with white

  // Status colors
  success: "#06D6A0",
  error: "#EF476F",
  warning: "#FF9B71",
};

/** On-demand DALL-E 3 story image loader with shimmer + Pollinations fallback */
const StoryImageLoader = ({ gameId, roundId, imagePrompt, sceneHint, borderColor }) => {
  const [imageUrl, setImageUrl] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchImage = async () => {
      try {
        setLoading(true);
        const result = await getStoryImage(gameId, roundId);
        if (!cancelled && result.image_url) {
          setImageUrl(result.image_url);
        } else if (!cancelled && result.fallback_url) {
          setImageUrl(result.fallback_url);
        }
      } catch {
        if (!cancelled) {
          // Fallback to Pollinations
          const prompt = imagePrompt || (typeof sceneHint === "string" ? sceneHint : "");
          if (prompt) {
            setImageUrl(
              `https://image.pollinations.ai/prompt/${encodeURIComponent(
                "orange dolphin mascot Mento in a storybook scene, " + prompt + ", 3D cartoon style"
              )}?width=1280&height=720&nologo=true`
            );
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    if (gameId && roundId) fetchImage();
    return () => { cancelled = true; };
  }, [gameId, roundId, imagePrompt, sceneHint]);

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-amber-50 to-orange-50">
        <div className="text-center">
          <div className="animate-pulse w-14 h-14 mx-auto mb-2 rounded-full bg-amber-200" />
          <p className="text-sm text-amber-700 font-medium">Generating story image...</p>
          <p className="text-xs text-amber-500 mt-1">Mento is painting the scene</p>
        </div>
      </div>
    );
  }

  if (imageUrl) {
    return <img src={imageUrl} alt="Story illustration" className="w-full h-full" />;
  }

  return (
    <div className="w-full h-full flex items-center justify-center text-sm text-gray-400">
      No media for this round
    </div>
  );
};

// Session games have their own pages — redirect instead of trying to load via game API
const SESSION_GAME_ROUTES = {
  debate:              '/debate',
  negotiation:         '/negotiation',
  job_interview:       '/interview',
  group_discussion:    '/gd',
  client_meeting:      '/client-meeting',
  conflict_mediation:  '/mediation',
  public_speaking:     '/speaking',
  stakeholder_update:  '/stakeholder',
  ai_discussion:       '/ai-discussion',
  investor_pitch:      '/pitch',
};

// Baseline game ID is now resolved dynamically via /api/profile/baseline-game

// Feature 3: 15-minute session checkpoint banner
function SessionCheckpointBanner({ onContinue, onSaveAndReturn }) {
  return (
    <div className="fixed top-4 left-4 right-4 z-50 rounded-2xl p-4 shadow-xl flex items-center gap-3"
      style={{ background: '#FFF3CD', border: '2px solid #FFD166' }}>
      <span className="text-2xl">⏱️</span>
      <div className="flex-1">
        <p className="font-bold text-sm" style={{ color: '#92400E' }}>You've been playing 15 min</p>
        <p className="text-xs" style={{ color: '#B45309' }}>Your progress is saved. Take a break or keep going!</p>
      </div>
      <div className="flex flex-col gap-1">
        <button onClick={onContinue} className="text-xs font-bold px-3 py-1 rounded-lg" style={{ background: '#FFD166', color: '#92400E' }}>
          Keep going
        </button>
        <button onClick={onSaveAndReturn} className="text-xs px-3 py-1 rounded-lg" style={{ background: '#FEF3C7', color: '#92400E' }}>
          Take a break
        </button>
      </div>
    </div>
  );
}

const GamePlayPage = () => {
  const { gameId } = useParams();
  const [searchParams] = useSearchParams();
  const resumeRunId = searchParams.get('resume');
  const assessMode = searchParams.get('mode') === 'assess'; // Clean assessment UI for HR/candidates
  const demoMode = searchParams.get('demo') === 'true'; // Live demo session (no signup)

  // Async peer challenge — detect ?challenge_id=xxx in URL
  const [challengeId] = useState(() => searchParams.get('challenge_id'));

  // Module flow — when a game is launched from a module lesson we auto-mark
  // the lesson complete on game-end and bounce back to the module.
  const [moduleId] = useState(() => searchParams.get('from_module'));
  const [moduleLessonId] = useState(() => searchParams.get('lesson'));
  const [moduleContext, setModuleContext] = useState(null); // { title, weekNumber, lessonTitle, lessonIcon }
  const [showModuleCompleteModal, setShowModuleCompleteModal] = useState(false);
  const [showChallengeResult, setShowChallengeResult] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();
  const reducedMotion = !!localStorage.getItem('accessibility_reduced_motion');
  const isFocusMode = !!localStorage.getItem('accessibility_focus_mode');

  // Session timer nudge — show a break reminder after 45 minutes
  const sessionStartRef = useRef(Date.now());
  const [showTimerNudge, setShowTimerNudge] = useState(false);
  const nudgeDismissedRef = useRef(false);
  useEffect(() => {
    const interval = setInterval(() => {
      const elapsed = (Date.now() - sessionStartRef.current) / 60000;
      if (elapsed >= 45 && !nudgeDismissedRef.current) {
        setShowTimerNudge(true);
      }
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  // Feature 1: Time-on-decision tracking — record when each round loads
  const choiceStartTimeRef = useRef(null);

  // Feature 3: 15-minute session checkpoint
  const sessionStartTimeRef = useRef(Date.now());
  const [showCheckpoint, setShowCheckpoint] = useState(false);
  const [checkpointDismissed, setCheckpointDismissed] = useState(false);
  useEffect(() => {
    const interval = setInterval(() => {
      if (Date.now() - sessionStartTimeRef.current > 15 * 60 * 1000 && !checkpointDismissed) {
        setShowCheckpoint(true);
      }
    }, 60000);
    return () => clearInterval(interval);
  }, [checkpointDismissed]);

  const { setThemeFromGame } = useTheme();

  const {
    currentGame,
    currentRound,
    gameState,
    isLoading,
    error,
    gameEnded,
    finalReport,
    startGame,
    resumeGame,
    submitChoice,
    nextRound,
    endGame,
    hasFeature,
    getResourceValue,
    runId,
    roundHistory,
    lastFailedAction,
    clearError,
    retryLastAction,
    resetGame,
    setBatchId,
    demoInfo,
  } = useGame();
  // resumeGame is available via useGame() above — used for Feature 6 dynamic rounds

  const [showDemoModal, setShowDemoModal] = useState(false);

  // Wire up batch ID from URL param so endGame records into HR assessment batch
  const batchIdFromUrl = searchParams.get('b');
  useEffect(() => {
    setBatchId(batchIdFromUrl || null);
  }, [batchIdFromUrl, setBatchId]);

  // Baseline enforcement: students must complete baseline before any other game
  // Demo accounts (demo_*) bypass this check entirely
  useEffect(() => {
    if (user?.role !== 'student') return;
    if (user?.username?.startsWith('demo_')) return;
    if (assessMode) return; // allow assessment mode bypass
    // Check baseline status and whether current game IS the baseline
    Promise.all([
      getBaselineStatus(),
      apiClient.get('/api/profile/baseline-game').then(r => r.data).catch(() => ({})),
    ]).then(([status, baselineInfo]) => {
      if (status.completed) return; // baseline done, allow any game
      // If this game is the baseline game, allow it
      if (baselineInfo?.game_id && gameId === baselineInfo.game_id) return;
      navigate('/onboarding', { replace: true });
    }).catch(() => {
      // fail-closed: can't verify baseline → redirect to onboarding
      navigate('/onboarding', { replace: true });
    });
  }, [gameId, user?.role, user?.username]); // eslint-disable-line

  const { conversationHistory, isRecording, transcript } = useAudio();

  // R15 — Soundscape for Tier-S sims; pulled from game.soundscape
  const soundscape = useSoundscape(currentGame?.soundscape);

  // Merge layout_config theme colors from game data
  const gameTheme = currentGame?.layout_config?.theme || {};
  const mergedColors = {
    ...colors,
    ...(gameTheme.primary_color && { primary: gameTheme.primary_color }),
    ...(gameTheme.secondary_color && { primaryDark: gameTheme.secondary_color }),
    ...(gameTheme.accent_color && { warning: gameTheme.accent_color }),
    ...(gameTheme.background_color && { background: gameTheme.background_color }),
    ...(gameTheme.text_color && { text: gameTheme.text_color }),
  };

  // Engagement system — streak, floating deltas, screen shake for rounds games
  const engagement = useEngagementSystem();

  // Local state
  const [selectedChoice, setSelectedChoice] = useState(null);
  const [showOutcome, setShowOutcome] = useState(false);
  const roundPresentedAt = useRef(null);
  const halftimeShown = useRef(false);
  // Reconsideration tracking
  const initialSelectionRef = useRef(null);
  const selectionChangesRef = useRef(0);
  const choiceHoverLog = useRef([]);
  const [outcomeData, setOutcomeData] = useState(null);
  const [takeawayData, setTakeawayData] = useState(null);
  const [achievements, setAchievements] = useState([]);
  const [gameStarted, setGameStarted] = useState(false);
  const [activeFeature, setActiveFeature] = useState("resources");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [assessIpLocked, setAssessIpLocked] = useState(false); // F5: IP lock violation
  const [showDemoSaveModal, setShowDemoSaveModal] = useState(false); // F8: demo save prompt
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [introGameData, setIntroGameData] = useState(null);
  const [isLoadingIntro, setIsLoadingIntro] = useState(true);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showStorybook, setShowStorybook] = useState(false);
  const [showConsequenceScene, setShowConsequenceScene] = useState(null);
  const [showReflectionModal, setShowReflectionModal] = useState(null);
  const [showHalftimeCheckpoint, setShowHalftimeCheckpoint] = useState(null);
  const [pendingChoiceId, setPendingChoiceId] = useState(null);
  const [skillCallout, setSkillCallout] = useState(null);
  const [teachableMoment, setTeachableMoment] = useState(null);
  const [postChoiceReflection, setPostChoiceReflection] = useState(null);
  const [coachMode, setCoachMode] = useState(false);
  const [aiVoiceMode, setAiVoiceMode] = useState(false);
  const [storyNarratorMode, setStoryNarratorMode] = useState(false);
  // V2 engine state (feature-flagged via game.features.v2_engine)
  const [showV2Selector, setShowV2Selector] = useState(false);
  const [v2LegacyStatus, setV2LegacyStatus] = useState(null);
  const [v2DailyChallenge, setV2DailyChallenge] = useState(null);
  const [v2Overrides, setV2Overrides] = useState(null);
  // #37 Last-run takeaway transition before re-initializing a V2 game
  const [showLastRunTakeaway, setShowLastRunTakeaway] = useState(null);
  const lastRunTakeawayTimerRef = useRef(null);
  // Fix 5: Widget challenge result
  const [challengeResult, setChallengeResult] = useState(null);
  // D1/D2/D3 new components + narrative bridge
  const [reflectionPrompt, setReflectionPrompt] = useState(null);
  const [choiceDeltas, setChoiceDeltas] = useState(null);
  const [choiceSkillExplanation, setChoiceSkillExplanation] = useState(null);
  const [achievementUnlock, setAchievementUnlock] = useState(null);
  const [skillIntroQueue, setSkillIntroQueue] = useState([]);
  const [currentSkillIntro, setCurrentSkillIntro] = useState(null);
  const [narrativeBridge, setNarrativeBridge] = useState(null);
  // Sim parity overlays — fires when backend injects market_shock / org_friction / team_health
  const [marketShock, setMarketShock] = useState(null);
  // R1 — live investor modal (Series A and other simulation rounds with live_investor)
  const [liveInvestor, setLiveInvestor] = useState(null);  // {round, choice} or null
  // R4 — dissent juror modal (Ethics Tribunal and similar rounds with dissent_juror)
  const [dissentJuror, setDissentJuror] = useState(null);  // {round, choice} or null
  // R12 — live boardroom debate modal (rounds with live_debate config)
  const [liveDebateOpen, setLiveDebateOpen] = useState(false);
  // R13 — PvP launcher modal (rounds with pvp_mode config)
  const [pvpLauncherOpen, setPvpLauncherOpen] = useState(false);
  const [orgFriction, setOrgFriction] = useState(null);
  const [teamHealth, setTeamHealth] = useState(null);
  const [timeRemaining, setTimeRemaining] = useState(null);
  const [timerActive, setTimerActive] = useState(false);
  const [roundMode, setRoundMode] = useState('core'); // tutorial | core | mastery
  const [freeTextValue, setFreeTextValue] = useState(''); // for free_text / hybrid rounds
  const [llmFeedback, setLLMFeedback] = useState(null); // Fix 7: LLM free-text evaluation feedback
  const [showContinuePrompt, setShowContinuePrompt] = useState(false); // Feature 6: dynamic round continue prompt
  const [generatingRound, setGeneratingRound] = useState(false); // Feature 6
  const [declinedContinue, setDeclinedContinue] = useState(false); // Feature 6
  const [rewardBonus, setRewardBonus] = useState(null); // variable reward UI
  const [socialPercentile, setSocialPercentile] = useState(null); // post-game percentile
  const [skillFlashDims, setSkillFlashDims] = useState(null); // brief post-game skill summary
  const [factCard, setFactCard] = useState(null); // "Did You Know?" glossary fact between rounds
  const [previouslyOn, setPreviouslyOn] = useState(null); // Feature: "Previously on..." recap
  // Fix 3: Difficulty escalation
  const [difficultyPhase, setDifficultyPhase] = useState(null);
  const [timerSeconds, setTimerSeconds] = useState(null);
  // Fix 4: Checkpoint quizzes
  const [pendingCheckpoint, setPendingCheckpoint] = useState(null);
  // Fix 6: Leaderboard Preview + Speed Run Timer
  const [showLeaderboardPreview, setShowLeaderboardPreview] = useState(false);
  const [speedRunMode, setSpeedRunMode] = useState(false);
  const [speedRunStart, setSpeedRunStart] = useState(null);
  const [preGameRank, setPreGameRank] = useState(null);
  const [postGameRank, setPostGameRank] = useState(null);

  // Immersion: player name injection — replace {player_name} tokens in narrative text
  const playerName = user?.display_name || user?.username || 'You';
  const injectPlayerName = (text) => {
    if (!text) return text;
    return text.replace(/\{player_name\}/g, playerName);
  };

  // Immersion: emotional resource sentiment labels
  const getResourceSentiment = (value, max = 100) => {
    const pct = (value / max) * 100;
    if (pct >= 70) return { label: 'Strong', color: '#10B981', emoji: '\u{1F7E2}' };
    if (pct >= 50) return { label: 'Steady', color: '#F59E0B', emoji: '\u{1F7E1}' };
    if (pct >= 30) return { label: 'Shaky', color: '#F97316', emoji: '\u{1F7E0}' };
    return { label: 'Critical', color: '#EF4444', emoji: '\u{1F534}' };
  };

  // Feature 4a: "Previously on..." recap every 3rd round
  useEffect(() => {
    const roundIdx = gameState?.round_index || 0;
    if (roundIdx > 0 && roundIdx % 3 === 0) {
      const lastLog = gameState?.choice_history?.slice(-1)[0];
      if (lastLog) {
        setPreviouslyOn(`Last time: ${lastLog.label || 'You made a tough choice'}. Let's see what happens next...`);
        const t = setTimeout(() => setPreviouslyOn(null), 5000);
        return () => clearTimeout(t);
      }
    } else {
      setPreviouslyOn(null);
    }
  }, [gameState?.round_index]); // eslint-disable-line

  // Show a 3.5-second skill flash when any game ends — covers game types that lack
  // per-choice feedback (Tower Defense, Go, Reversi, Puzzle Match, AI Arena, Mini-games)
  useEffect(() => {
    if (!gameEnded || !finalReport?.dimension_scores) return;
    const scores = finalReport.dimension_scores;
    const top = Object.entries(scores)
      .filter(([, v]) => typeof v === 'number' && v > 0)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3);
    if (top.length === 0) return;
    setSkillFlashDims(top);
    const t = setTimeout(() => setSkillFlashDims(null), 3500);
    return () => clearTimeout(t);
  }, [gameEnded, finalReport]);

  // Fetch social percentile when game ends
  useEffect(() => {
    if (!finalReport) return;
    const scores = finalReport?.dimension_scores || {};
    const topDim = Object.entries(scores).sort(([,a],[,b]) => b - a)[0]?.[0];
    if (!topDim) return;
    getLeaderboardPercentile(topDim, 'week').then(data => {
      if (data?.percentile != null) setSocialPercentile({ percentile: data.percentile, dimension: topDim, label: data.dimension_label || topDim });
    }).catch(() => {});
  }, [finalReport]);

  // Fix 6: Capture pre-game rank when game metadata loads
  useEffect(() => {
    if (!gameId || !user) return;
    apiClient.get(`/api/game/${gameId}/leaderboard-preview`).then(res => {
      const rank = res.data?.user_rank;
      if (rank?.found) setPreGameRank(rank.rank);
    }).catch(() => {});
  }, [gameId, user]);

  // Fix 6: Fetch post-game rank when game ends
  useEffect(() => {
    if (!gameEnded || !gameId || !user) return;
    apiClient.get(`/api/game/${gameId}/leaderboard-preview`).then(res => {
      const rank = res.data?.user_rank;
      if (rank?.found) setPostGameRank(rank.rank);
    }).catch(() => {});
  }, [gameEnded, gameId, user]);

  // Module flow — fetch module context (title, week, lesson title) for the
  // sticky banner that anchors the player to their lesson.
  useEffect(() => {
    if (!moduleId || !moduleLessonId) return;
    let cancelled = false;
    (async () => {
      try {
        const { getModule } = await import('../api/modules');
        const data = await getModule(moduleId);
        if (cancelled || !data?.module) return;
        const m = data.module;
        let weekNumber = null, lessonTitle = '', lessonIcon = '';
        for (const w of (m.weeks || [])) {
          for (const l of (w.lessons || [])) {
            if (l.lesson_id === moduleLessonId) {
              weekNumber = w.number;
              lessonTitle = l.title || '';
              lessonIcon = l.icon || '';
              break;
            }
          }
          if (weekNumber) break;
        }
        setModuleContext({
          title: m.title || 'Module',
          icon: m.icon || '🎓',
          weekNumber,
          lessonTitle,
          lessonIcon,
        });
      } catch (e) {
        // banner is purely cosmetic — failures are silent
      }
    })();
    return () => { cancelled = true; };
  }, [moduleId, moduleLessonId]);

  // Module flow — when game ends and we came from a module lesson, mark
  // the module lesson complete and show a return modal.
  useEffect(() => {
    if (!gameEnded || !moduleId || !moduleLessonId) return;
    let cancelled = false;
    (async () => {
      try {
        const { completeLesson } = await import('../api/modules');
        await completeLesson(moduleId, moduleLessonId, { run_id: runId });
      } catch (e) {
        // non-fatal — student can mark complete manually back in the module
      }
      if (cancelled) return;
      setTimeout(() => {
        if (!cancelled) setShowModuleCompleteModal(true);
      }, 800);
    })();
    return () => { cancelled = true; };
  }, [gameEnded, moduleId, moduleLessonId, runId]);

  // Fix 6: Leaderboard preview is shown via button in GameIntro, not auto-popup

  // Round 13: player identity, coaching, adapt hints, frustration
  const [playerProfile, setPlayerProfile] = useState(null);
  const [coachingNudge, setCoachingNudge] = useState(false);
  const [adaptHint, setAdaptHint] = useState(null); // { hint: str, difficulty_adjustment: str }
  const [frustrationMsg, setFrustrationMsg] = useState(null);

  // Set gameplay theme so CSS variables use light text colors (body color fix)
  useEffect(() => {
    const prev = document.documentElement.getAttribute('data-theme');
    document.documentElement.setAttribute('data-theme', 'gameplay');
    return () => document.documentElement.setAttribute('data-theme', prev || '');
  }, []);

  useEffect(() => {
  const url = introGameData?.intro_round?.video?.url;
  if (!url) return;

  // Preload video using a hidden video element (link preload doesn't support "video" as type)
  const vid = document.createElement("video");
  vid.preload = "auto";
  vid.src = url;
  vid.style.display = "none";
  document.body.appendChild(vid);

  return () => {
    vid.src = "";
    vid.remove();
  };
}, [introGameData]);

  // Reset game context when navigating to a new game (or re-entering the page)
  useEffect(() => {
    // Always reset stale game state when the page mounts or gameId changes
    resetGame();
    setGameStarted(false);
    setShowOutcome(false);
    setOutcomeData(null);
    setTakeawayData(null);
    setSelectedChoice(null);
    setAchievements([]);
    halftimeShown.current = false;
    // Fix 6: Reset speed run state on game change
    setSpeedRunMode(false);
    setSpeedRunStart(null);
    setPreGameRank(null);
    setPostGameRank(null);
    setShowLeaderboardPreview(false);
  }, [gameId, resetGame]);

  // Load game metadata for intro screen
  useEffect(() => {
    const loadGameMetadata = async () => {
      try {
        const data = await games.get(gameId);
        setIntroGameData(data);
      } catch (err) {
        console.error("Failed to load game metadata:", err);
      } finally {
        setIsLoadingIntro(false);
      }
    };
    setIsLoadingIntro(true);
    loadGameMetadata();
  }, [gameId]);

  // Auto-resume if ?resume= param is present
  useEffect(() => {
    if (resumeRunId && !gameStarted && !currentGame) {
      const doResume = async () => {
        try {
          setGameStarted(true);
          await resumeGame(resumeRunId);
        } catch (err) {
          console.error("Failed to resume game:", err);
          setGameStarted(false);
        }
      };
      doResume();
    }
  }, [resumeRunId]);

  // Apply theme when game loads
  useEffect(() => {
    if (currentGame) {
      setThemeFromGame(currentGame);
    }
  }, [currentGame, setThemeFromGame]);

  // --- Track when each round is presented (for time_to_decide) ---
  useEffect(() => {
    if (currentRound?.id && !showOutcome && !gameEnded) {
      roundPresentedAt.current = Date.now();
    }
  }, [currentRound?.id, showOutcome, gameEnded]);

  // Feature 1: Record choice start time whenever a new round loads
  useEffect(() => {
    if (currentRound?.id && !showOutcome && !gameEnded) {
      choiceStartTimeRef.current = Date.now();
    }
  }, [currentRound?.id, showOutcome, gameEnded]);

  // --- Countdown Timer for time_limit_seconds ---
  useEffect(() => {
    const limit = currentRound?.time_limit_seconds;
    if (!limit || showOutcome || gameEnded) {
      setTimerActive(false);
      setTimeRemaining(null);
      return;
    }
    setTimeRemaining(limit);
    setTimerActive(true);
  }, [currentRound?.id, currentRound?.time_limit_seconds, showOutcome, gameEnded]);

  useEffect(() => {
    if (!timerActive) return;
    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev === null || prev <= 1) {
          setTimerActive(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [timerActive]);

  // Redirect session games — placed here (after all hooks) to satisfy Rules of Hooks
  useEffect(() => {
    if (SESSION_GAME_ROUTES[gameId]) {
      navigate(SESSION_GAME_ROUTES[gameId], { replace: true });
    }
  }, [gameId]);

  // NOTE: The demo-limit modal used to auto-pop 2.5s after gameEnded, which covered the
  // post-game report and made it unreadable. We now surface it only when the user clicks
  // "Play Again" (see GameOverScreen / MentoReport handlers below) — their natural next-action
  // moment — so the report stays fully readable first.

  // Show ChallengeResult overlay when game ends with a challenge_id URL param
  useEffect(() => {
    if (gameEnded && challengeId && finalReport) {
      const t = setTimeout(() => setShowChallengeResult(true), 1500);
      return () => clearTimeout(t);
    }
  }, [gameEnded, challengeId, finalReport]);

  // F8: Show "Save your results" modal when a demo session game ends
  useEffect(() => {
    if (gameEnded && demoMode) {
      const t = setTimeout(() => setShowDemoSaveModal(true), 3000);
      return () => clearTimeout(t);
    }
  }, [gameEnded, demoMode]);

  // Round 13: fetch player profile for avatar in renderers
  useEffect(() => {
    getProfile().then(setPlayerProfile).catch(() => {});
  }, []);

  // Round 13: check frustration before game init
  useEffect(() => {
    if (gameId) {
      getFrustrationCheck(gameId).then((data) => {
        if (data?.support_message) setFrustrationMsg(data.support_message);
      }).catch(() => {});
    }
  }, [gameId]);

  // All hooks above this line. Safe to early-return below.
  if (SESSION_GAME_ROUTES[gameId]) return null;

  const initializeGame = async (v2Payload = null) => {
    try {
      // V2 pre-flight: if this is a V2 game and no overrides provided yet, open selector
      const gameForCheck = introGameData || currentGame;
      if (!v2Payload && isV2Game(gameForCheck)) {
        const features = gameForCheck?.features || {};
        const needsSelector = features.show_mode_selector !== false || features.show_persona_selector !== false;
        if (needsSelector && !v2Overrides) {
          try {
            const [legacy, daily] = await Promise.all([
              getLegacyStatus(gameId).catch(() => null),
              getDailyChallenge(gameId).catch(() => null),
            ]);
            setV2LegacyStatus(legacy);
            setV2DailyChallenge(daily);
          } catch (_) {}
          setShowV2Selector(true);
          return;
        }
      }

      // Reset local state so we don't get stuck showing GameOverScreen
      setShowOutcome(false);
      setOutcomeData(null);
      setTakeawayData(null);
      setSelectedChoice(null);
      setAchievements([]);
      halftimeShown.current = false;
      setGameStarted(true);
      // Fix 6: Start speed run timer if enabled
      if (speedRunMode) {
        setSpeedRunStart(Date.now());
      }
      const baseMeta = { coach_mode: coachMode, assess_lock_ip: assessMode };
      const mergedMeta = v2Payload ? { ...baseMeta, ...v2Payload } : baseMeta;
      await startGame(gameId, {}, mergedMeta);
    } catch (err) {
      console.error("Failed to start game:", err);
      setGameStarted(false);
      setSpeedRunStart(null);
    }
  };

  const handleV2SelectorConfirm = (overrides) => {
    setV2Overrides(overrides);
    setShowV2Selector(false);
    initializeGame({
      v2_mode_id: overrides?.mode_id,
      v2_persona_id: overrides?.persona_id,
      v2_daily_challenge_id: overrides?.daily_challenge_id,
    });
  };

// Track first selection (for reconsideration signal)
const trackAndSelect = (choiceId) => {
  if (initialSelectionRef.current === null) {
    initialSelectionRef.current = choiceId;
  } else if (initialSelectionRef.current !== choiceId) {
    selectionChangesRef.current++;
  }
  setSelectedChoice(choiceId);
};

const handleChoiceSubmit = async (choiceId, extraData) => {
  // extraData may be { freeText: '...' } from ChoiceSelector for hybrid/free_text modes
  const freeTextFromChoice = extraData?.freeText || '';
  // Capture initial selection if not yet tracked (for direct-submit renderers)
  if (initialSelectionRef.current === null) initialSelectionRef.current = choiceId;

  const inputType = currentRound?.input_type || 'multiple_choice';

  // For standard rounds: check if we need a reflection first (before submitting)
  if (inputType === 'multiple_choice' && !freeTextFromChoice && currentRound?.reflection_prompt && !pendingChoiceId) {
    setPendingChoiceId(choiceId);
    setShowReflectionModal(currentRound.reflection_prompt);
    return;
  }

  try {
    setIsSubmitting(true);
    setPendingChoiceId(null);
    setShowReflectionModal(null);

    // Compute time_to_decide (ms since round was presented)
    const timeToDecide = roundPresentedAt.current ? Date.now() - roundPresentedAt.current : null;
    const metadata = timeToDecide !== null ? { time_to_decide: timeToDecide } : {};

    // Feature 1: compute and attach choice_time_ms
    const choiceTimeMs = Date.now() - (choiceStartTimeRef.current || Date.now());
    metadata.choice_time_ms = choiceTimeMs;

    // Idempotency: unique request ID to prevent duplicate submissions
    metadata.request_id = generateUUID();

    // Reconsideration tracking
    metadata.reconsideration = {
      initial_selection: initialSelectionRef.current,
      changed_selection: initialSelectionRef.current !== null && initialSelectionRef.current !== choiceId,
      num_selection_changes: selectionChangesRef.current,
      hover_durations: choiceHoverLog.current,
    };
    // Reset for next round
    initialSelectionRef.current = null;
    selectionChangesRef.current = 0;
    choiceHoverLog.current = [];

    // Add free_text to metadata if present (handles both free_text and hybrid modes)
    const activeFreeText = freeTextFromChoice || extraData?.freeText || (inputType !== 'multiple_choice' ? freeTextValue : '');
    if (activeFreeText) {
      metadata.free_text = activeFreeText;
    }

    // Attach structured_response and input_type for new widget types
    if (extraData?.structured_response) {
      metadata.structured_response = extraData.structured_response;
    }
    if (extraData?.input_type) {
      metadata.input_type = extraData.input_type;
    }
    // Attach widget_data for scene widgets (brainstorm_board, drawing_canvas)
    if (extraData?.widget_data) {
      metadata.widget_data = extraData.widget_data;
    }

    // For free_text mode and new input types: submit with null choice_id
    const submitId = (inputType === 'free_text' || inputType === 'drawing_canvas' || INPUT_WIDGETS[inputType]) ? null : choiceId;

    // Save current round's choices before submitChoice updates currentRound to the next round
    const previousRoundChoices = currentRound?.choices || [];
    // R1 — capture round + choice for live-investor modal trigger
    const previousRound = currentRound;
    const previousChoice = (previousRoundChoices || []).find((c) => (c.id || c.choice_id) === choiceId);

    const response = await submitChoice(submitId, metadata);
    // Reset free-text state after submit
    setFreeTextValue('');

    // Sim parity: surface backend-injected market shocks / org friction / team health
    if (response?.market_shock) setMarketShock(response.market_shock);
    if (response?.org_friction) setOrgFriction(response.org_friction);
    if (response?.team_health) setTeamHealth(response.team_health);

    // R1 — open live investor modal if the round just played has live_investor.enabled
    if (previousRound?.live_investor?.enabled && previousChoice) {
      setLiveInvestor({ round: previousRound, choice: previousChoice });
    }
    // R4 — open dissent juror modal if the round just played has dissent_juror.enabled
    if (previousRound?.dissent_juror?.enabled && previousChoice) {
      setDissentJuror({ round: previousRound, choice: previousChoice });
    }

    const outcomeObj = response?.outcome || response;
    // Attach previous round's choices so the takeaway modal can resolve choice labels
    outcomeObj._roundChoices = previousRoundChoices;
    if (response?.round_coins) {
      outcomeObj.round_coins = response.round_coins;
    }
    // Streak + floating delta for all choice-based game types
    {
      const SKILL_DIMS = ['strategic_thinking','risk_tolerance','delayed_gratification','adaptability','resilience','empathy'];
      const deltas = outcomeObj?.choice_delta || outcomeObj?.deltas || {};
      const deltaSum = Object.entries(deltas).reduce((s, [k, v]) => SKILL_DIMS.includes(k) ? s + (v || 0) : s, 0);
      // For rounds use round_coins for game-feel parity; for others use delta sum
      const rawSum = gameType === 'rounds' ? (response?.round_coins ?? (deltaSum || 5)) : deltaSum;
      if (rawSum !== 0) engagement.recordChoice(rawSum);
    }

    // Store outcome and takeaway data
    setOutcomeData(outcomeObj);
    setTakeawayData(response?.takeaway || response?.outcome?.takeaway || null);

    // Fix 7: Show LLM feedback card when backend returns free_text_eval (hybrid/free_text modes)
    if (response?.outcome?.free_text_eval || outcomeObj?.free_text_eval) {
      setLLMFeedback(response?.outcome?.free_text_eval || outcomeObj?.free_text_eval);
    }

    // Progressive difficulty: update round mode for next round
    if (response?.round_mode) setRoundMode(response.round_mode);

    // Fix 3: Update difficulty phase + timer
    if (response?.difficulty_phase) {
      setDifficultyPhase(response.difficulty_phase);
      setTimerSeconds(response.difficulty_phase.timer_seconds || null);
    }

    // Fix 4: Check if a checkpoint quiz is required before proceeding
    if (response?.checkpoint_required) {
      setPendingCheckpoint(response.checkpoint_required);
      // Don't advance to next round until checkpoint is passed
      return;
    }

    // Check for consequence scene — show before everything else
    const consequenceScene = outcomeObj?.consequence_scene;
    if (consequenceScene) {
      setShowConsequenceScene(consequenceScene);
      // Chain continues in handleConsequenceSceneDismiss
    } else {
      // Show narrative bridge if we have meaningful skill deltas (non-rounds game types)
      const bridgeDeltas = outcomeObj?.choice_delta || outcomeObj?.deltas;
      const SKILL_DIMS = ['strategic_thinking','risk_tolerance','delayed_gratification','adaptability','resilience','empathy'];
      const hasMeaningfulDelta = bridgeDeltas && Object.entries(bridgeDeltas).some(([k, v]) => SKILL_DIMS.includes(k) && v !== 0);
      if (hasMeaningfulDelta && gameType !== 'rounds') {
        setNarrativeBridge({ deltas: bridgeDeltas, choiceLabel: outcomeObj?.choice_label || null, outcomeObj });
        // Chain continues in NarrativeBridge onDismiss
      } else {
        // Start the post-choice chain: halftime → teachable → reflection → takeaway
        showNextPostChoiceStep(outcomeObj);
      }
    }

    if (response?.outcome?.achievements_unlocked?.length > 0) {
      const unlocked = response.outcome.achievements_unlocked;
      // D3: Show full-screen AchievementUnlock animation for the FIRST unlocked achievement
      setAchievementUnlock(unlocked[0]);
      // Remaining (2nd+) show as corner popups — avoids double-rendering the first one
      if (unlocked.length > 1) {
        setAchievements(unlocked.slice(1));
      }
    }

    // Fix 1: Queue newly introduced skills for the SkillIntroCard overlay
    if (response?.new_skills_introduced?.length > 0) {
      setSkillIntroQueue(prev => [...prev, ...response.new_skills_introduced]);
      // Show the first one immediately if nothing is showing
      if (!currentSkillIntro) {
        setCurrentSkillIntro(response.new_skills_introduced[0]);
      }
    }

    // Fix 2: Pass skill_explanation from backend to ChoiceExplanation
    if (response?.skill_explanation) {
      setChoiceSkillExplanation(response.skill_explanation);
    } else {
      setChoiceSkillExplanation(null);
    }

    // Fix 5: Widget challenge result
    if (response?.challenge_result) {
      setChallengeResult(response.challenge_result);
    } else {
      setChallengeResult(null);
    }

    // Skill callout toast — enrich with skill_tags from choice_summaries
    const sc = outcomeObj?.skill_callout || response?.outcome?.skill_callout;
    const choiceSkillTags = response?.choice_summaries?.[0]?.skill_tags || outcomeObj?.choice_summaries?.[0]?.skill_tags || [];
    if (sc) {
      setSkillCallout(choiceSkillTags.length > 0 ? { ...sc, skill_tags: choiceSkillTags } : sc);
    } else if (choiceSkillTags.length > 0) {
      // Surface skill_tags even when backend didn't send a skill_callout
      const DIM_LABELS = { strategic_thinking: 'Strategic Thinking', risk_tolerance: 'Risk Tolerance', delayed_gratification: 'Delayed Gratification', adaptability: 'Adaptability', resilience: 'Resilience', empathy: 'Empathy' };
      setSkillCallout({ dimension: choiceSkillTags[0], message: `${DIM_LABELS[choiceSkillTags[0]] || choiceSkillTags[0]} practiced`, skill_tags: choiceSkillTags });
    }

    // D2: Show ChoiceExplanation with delta values
    const deltas = outcomeObj?.choice_delta || outcomeObj?.deltas || sc?.deltas;
    if (deltas && Object.keys(deltas).some(k => deltas[k] !== 0)) {
      setChoiceDeltas(deltas);
    }

    // D1: Show ReflectionPrompt if round has reflection_prompt (frequency controlled by user setting)
    const refPrompt = outcomeObj?.reflection_prompt || response?.outcome?.reflection_prompt;
    if (refPrompt) {
      const reflectionFrequency = parseInt(localStorage.getItem('reflection_frequency') || '3');
      const roundIdx = gameState?.round_index || 0;
      if (reflectionFrequency !== 0 && roundIdx % reflectionFrequency === 0) {
        // Kantian universalization mode triggers when:
        //   1. Game JSON has `kantian: true`, OR
        //   2. The choice carries an `ethical_reasoning` skill tag, OR
        //   3. Duty Mode is enabled (always Kantian framing)
        const dutyOn = (() => {
          try { return localStorage.getItem('mento_duty_mode') === '1'; } catch { return false; }
        })();
        const isKantian = !!currentGame?.kantian
          || choiceSkillTags.includes('ethical_reasoning')
          || dutyOn;
        setReflectionPrompt({ text: refPrompt, kantian: isKantian });
      }
    }

    // Round 13: coaching nudge
    if (response?.coaching_needed) {
      setCoachingNudge(true);
      setTimeout(() => setCoachingNudge(false), 8000);
    }
    // Round 13: adaptive difficulty hint chip
    if (response?.adapt_result?.hint) {
      setAdaptHint(response.adapt_result);
      setTimeout(() => setAdaptHint(null), 8000);
    }
    // Round 15: variable reward bonus chip
    if (outcomeObj?.reward_bonus || outcomeObj?.reward_multiplier) {
      setRewardBonus(outcomeObj.reward_multiplier || 2.0);
      setTimeout(() => setRewardBonus(null), 3000);
    }
  } catch (err) {
    // F5: IP lock violation
    if (err?.response?.status === 403 && err?.response?.data?.error?.includes('locked')) {
      setAssessIpLocked(true);
    } else {
      console.error("Failed to submit choice:", err);
    }
  } finally {
    setIsSubmitting(false);
  }
};

const handleReflectionSubmit = (reflectionText) => {
  if (pendingChoiceId) {
    handleChoiceSubmit(pendingChoiceId, reflectionText || '_skip');
  }
};

// Post-choice chain: halftime → teachable moment → reflection → takeaway
const showNextPostChoiceStep = (outcome) => {
  const oc = outcome || outcomeData;
  if (oc?.halftime_checkpoint && !halftimeShown.current) {
    setShowHalftimeCheckpoint(oc.halftime_checkpoint);
  } else if (oc?.teachable_moment) {
    setTeachableMoment(oc.teachable_moment);
  } else if (oc?.post_choice_reflection) {
    setPostChoiceReflection(oc.post_choice_reflection);
  } else {
    setShowOutcome(true);
  }
};

const handleConsequenceSceneDismiss = () => {
  setShowConsequenceScene(null);
  showNextPostChoiceStep(outcomeData);
};

// Fix 3: Timer expired — auto-submit a random choice
const handleTimerExpire = () => {
  if (!currentRound?.choices?.length) return;
  const choices = currentRound.choices;
  const randomChoice = choices[Math.floor(Math.random() * choices.length)];
  handleChoiceSubmit(randomChoice.id || randomChoice.choice_id);
};

// Fix 4: Checkpoint passed — clear checkpoint and proceed to next round
const handleCheckpointPass = () => {
  setPendingCheckpoint(null);
  // The round data was already loaded in the response, just let normal flow continue
  if (outcomeData) {
    showNextPostChoiceStep(outcomeData);
  }
};

const handleHalftimeContinue = (reflection) => {
  setShowHalftimeCheckpoint(null);
  halftimeShown.current = true;
  // Continue chain: teachable → reflection → takeaway
  if (outcomeData?.teachable_moment) {
    setTeachableMoment(outcomeData.teachable_moment);
  } else if (outcomeData?.post_choice_reflection) {
    setPostChoiceReflection(outcomeData.post_choice_reflection);
  } else {
    setShowOutcome(true);
  }
};

const handleTeachableMomentDismiss = () => {
  setTeachableMoment(null);
  // Continue chain: reflection → takeaway
  if (outcomeData?.post_choice_reflection) {
    setPostChoiceReflection(outcomeData.post_choice_reflection);
  } else {
    setShowOutcome(true);
  }
};

const handlePostChoiceReflectionSubmit = (answer) => {
  setPostChoiceReflection(null);
  setShowOutcome(true);
};

  const handleCloseOutcome = () => {
    setShowOutcome(false);
    setTakeawayData(null);
    setSelectedChoice(null);
  };

const handleNextRound = async () => {
  try {
    setIsTransitioning(true); // 🚦 start loader
    setShowOutcome(false);
    setSelectedChoice(null);
    setTakeawayData(null);
    setFreeTextValue('');

    await nextRound();

    // "Did You Know?" fact card from glossary
    const glossary = currentGame?.glossary_terms || currentGame?.glossary || [];
    if (glossary.length > 0) {
      const randomTerm = glossary[Math.floor(Math.random() * glossary.length)];
      setFactCard(randomTerm);
      setTimeout(() => setFactCard(null), 12000);
    }
  } catch (err) {
    console.error("Failed to advance round:", err);
  } finally {
    setIsTransitioning(false); // 🏁 done
  }
};

  // ────────────────────────────────────────────────────────────────────────
  // Module return banner — sticky at top of viewport so the player can ALWAYS
  // get back to the lesson that launched the game, regardless of game type
  // (rounds / story_branching / board / simulation / minigame / etc.).
  //
  // Rendered inside every return path below.
  // ────────────────────────────────────────────────────────────────────────
  const moduleReturnBanner = (moduleId && moduleContext) ? (
    <div className="fixed top-0 left-0 right-0 z-50 px-3 py-2 flex items-center gap-2 text-xs sm:text-sm font-semibold shadow-lg"
      style={{
        background: 'linear-gradient(90deg, #6366f1, #8b5cf6)',
        color: '#fff',
      }}>
      <span className="text-base flex-shrink-0">{moduleContext.icon}</span>
      <div className="min-w-0 flex-1 truncate">
        <span className="opacity-80 hidden sm:inline">In Module · </span>
        <span className="font-bold truncate">{moduleContext.title}</span>
        {moduleContext.weekNumber && (
          <span className="opacity-80"> · Week {moduleContext.weekNumber}</span>
        )}
        {moduleContext.lessonTitle && (
          <span className="opacity-90 hidden md:inline"> · {moduleContext.lessonIcon} {moduleContext.lessonTitle}</span>
        )}
      </div>
      <button onClick={() => navigate(`/modules/${moduleId}`)}
        className="flex-shrink-0 bg-white/25 hover:bg-white/40 px-3 py-1.5 rounded-full text-[11px] font-bold transition-colors whitespace-nowrap">
        ← Return to Module
      </button>
    </div>
  ) : null;
  // Spacer pushes content down so the fixed banner doesn't cover game UIs.
  const moduleBannerSpacer = (moduleId && moduleContext) ? (
    <div aria-hidden="true" style={{ height: '40px' }} />
  ) : null;

  // Loading screen
  if (isLoading && !currentGame) {
    return (
      <>
        {moduleReturnBanner}
        <div
          className="min-h-screen flex items-center justify-center"
          style={{ backgroundColor: colors.background }}
        >
          <div className="text-center">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
              className="text-5xl mb-6"
              style={{ color: colors.primary }}
            >
              <FaGamepad />
            </motion.div>
            <p className="text-xl font-bold mb-2" style={{ color: colors.text }}>
              Loading Game
            </p>
            <div
              className="w-48 h-1 mx-auto"
              style={{ backgroundColor: colors.primaryLight }}
            >
              <motion.div
                className="h-full"
                animate={{ x: [-48, 48] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                style={{ backgroundColor: colors.primary }}
              />
            </div>
          </div>
        </div>
      </>
    );
  }

  // Error state
  if (error && !currentGame) {
    return (
      <ErrorScreen
        message={error}
        onRetry={initializeGame}
        onBack={() => navigate("/games")}
      />
    );
  }

  // Game over state
  if (gameEnded) {
    // Safety: if gameEnded but finalReport hasn't arrived yet, show loading
    if (!finalReport) {
      return (
        <>
          {moduleReturnBanner}
          <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: colors.background }}>
            <div className="text-center">
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }} className="text-5xl mb-6" style={{ color: colors.primary }}>
                <FaGamepad />
              </motion.div>
              <p className="text-lg font-bold" style={{ color: colors.text }}>Preparing your report…</p>
              <p className="text-sm mt-2" style={{ color: colors.textLight || '#6D7286' }}>Analysing your decisions</p>
            </div>
          </div>
        </>
      );
    }
    // Baseline game completion → redirect to onboarding for SkillProfileReveal
    if (finalReport?.just_completed_baseline) {
      navigate('/onboarding', { replace: true });
      return null;
    }
    // Feature 6: Dynamic rounds — offer "Continue with a new challenge?" before game-over
    if (currentGame?.dynamic_rounds && !declinedContinue && !showContinuePrompt) {
      // Trigger the prompt once
      setTimeout(() => setShowContinuePrompt(true), 0);
    }
    if (currentGame?.dynamic_rounds && !declinedContinue) {
      return (
        <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: colors.background }}>
          <div className="max-w-sm w-full mx-4 text-center space-y-6">
            <div className="text-5xl mb-2">🔄</div>
            <h2 className="text-2xl font-bold" style={{ color: colors.text }}>You've mastered this game!</h2>
            <p className="text-gray-500 text-sm">Want to keep going with a fresh AI-generated challenge?</p>
            <div className="space-y-3">
              <button
                disabled={generatingRound}
                onClick={async () => {
                  setGeneratingRound(true);
                  try {
                    const data = await generateRound(runId);
                    if (data?.success) {
                      await resumeGame(runId);
                    } else {
                      setDeclinedContinue(true);
                    }
                  } catch {
                    setDeclinedContinue(true);
                  } finally {
                    setGeneratingRound(false);
                  }
                }}
                className="w-full py-3 rounded-xl font-bold text-sm transition-all"
                style={{ background: colors.primary, color: colors.text, opacity: generatingRound ? 0.7 : 1 }}
              >
                {generatingRound ? '⚙️ Generating…' : '🔄 Continue with a new challenge'}
              </button>
              <button
                onClick={() => setDeclinedContinue(true)}
                className="w-full py-3 rounded-xl font-semibold text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                No thanks, see my results
              </button>
            </div>
          </div>
        </div>
      );
    }

    if (assessMode) {
      // Assessment mode: clean report UI with print button
      return (
        <div className="min-h-screen bg-white">
          <div className="max-w-2xl mx-auto px-4 py-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-amber-600 mb-1">📋 Assessment Report</div>
                <h1 className="text-2xl font-bold text-gray-800">{currentGame?.title || 'Skill Assessment'}</h1>
                <p className="text-sm text-gray-500 mt-0.5">Completed {new Date().toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' })}</p>
              </div>
              <button
                onClick={() => window.print()}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-400 text-gray-900 font-semibold text-sm hover:bg-amber-500 transition-colors print:hidden"
              >
                🖨️ Print Report
              </button>
            </div>
            <GameOverScreen
              finalReport={finalReport}
              runId={runId}
              onPlayAgain={() => { const g = introGameData || currentGame; if (isV2Game(g)) { setV2Overrides(null); setV2LegacyStatus(null); setV2DailyChallenge(null); } initializeGame(); }}
              onBackToMenu={() => navigate("/games")}
              assessMode={true}
              epilogueSlot={(() => {
                const rc = finalReport?.report_core || finalReport || {};
                const ep = rc?.epilogue || null;
                if (!(currentGame?.game_type === 'mystery_room' && ep)) return null;
                const missed = (currentGame?.items || [])
                  .filter((it) => it.is_evidence)
                  .filter((it) => !((rc?.evidence_collected || []).includes(it.id)))
                  .map((it) => ({ id: it.id, label: it.name || it.label || it.id }));
                return (
                  <MysteryRoomEpilogue
                    epilogue={ep}
                    outcomeLabel={rc?.outcome_label}
                    knowledgeScore={rc?.knowledge_score}
                    missedClues={missed}
                  />
                );
              })()}
            />
          </div>
        </div>
      );
    }
    const _DIM_LABELS = {
      strategic_thinking: 'Strategic Thinking', risk_tolerance: 'Risk Tolerance',
      delayed_gratification: 'Delayed Gratification', adaptability: 'Adaptability',
      resilience: 'Resilience', empathy: 'Empathy',
      ethical_reasoning: 'Ethical Reasoning', creativity: 'Creativity',
    };
    const _DIM_ICONS = {
      strategic_thinking: '🧠', risk_tolerance: '🎯', delayed_gratification: '⏳',
      adaptability: '🔄', resilience: '💪', empathy: '❤️',
      ethical_reasoning: '⚖️', creativity: '✨',
    };
    return (
      <>
        {moduleReturnBanner}
        {moduleBannerSpacer}
        {/* Universal post-game skill flash — covers all game types that lack per-choice feedback */}
        <AnimatePresence>
          {skillFlashDims && (
            <motion.div
              key="skill-flash"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
              onClick={() => setSkillFlashDims(null)}
            >
              <motion.div
                initial={{ y: 30 }}
                animate={{ y: 0 }}
                className="rounded-3xl shadow-2xl px-8 py-7 max-w-xs w-full mx-4 text-center"
                style={{ background: '#FFFFFF', border: '1px solid #E2E8F0' }}
                onClick={e => e.stopPropagation()}
              >
                <div className="text-3xl mb-2">✨</div>
                <p className="font-bold text-lg mb-1" style={{ color: '#2D3047' }}>Skills Practised</p>
                <p className="text-xs mb-5" style={{ color: '#64748B' }}>Your performance in this session</p>
                <div className="space-y-3">
                  {skillFlashDims.map(([dim, score]) => (
                    <div key={dim} className="flex items-center gap-3">
                      <span className="text-xl w-7 flex-shrink-0">{_DIM_ICONS[dim] || '⚡'}</span>
                      <div className="flex-1 text-left">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-sm font-medium" style={{ color: '#2D3047' }}>{_DIM_LABELS[dim] || dim}</span>
                          <span className="text-emerald-400 font-bold text-sm">{score}</span>
                        </div>
                        <div className="w-full rounded-full h-1.5" style={{ background: '#E2E8F0' }}>
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${score}%` }}
                            transition={{ duration: 0.8, delay: 0.2 }}
                            className="bg-emerald-400 h-1.5 rounded-full"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setSkillFlashDims(null)}
                  className="mt-5 text-xs transition-colors" style={{ color: '#64748B' }}
                >
                  View full report →
                </button>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        <ErrorBoundary variant="gameplay" key={`report-${runId}`}
          fallback={
            <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: '#FFFDF7' }}>
              <div className="max-w-md w-full text-center p-8 bg-white rounded-3xl shadow-xl border border-amber-100">
                <div className="text-5xl mb-4">🎮</div>
                <h2 className="text-xl font-bold mb-2 text-gray-800">Game Complete!</h2>
                <p className="text-sm text-gray-500 mb-4">Your report had a display issue, but your progress has been saved.</p>
                {finalReport?.report_core?.mento_score && (
                  <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200">
                    <p className="text-xs text-amber-600 font-semibold">Mento Score</p>
                    <p className="text-3xl font-black text-amber-700">{finalReport.report_core.mento_score.score || '—'}</p>
                  </div>
                )}
                <div className="flex gap-3 justify-center">
                  <button onClick={() => { const g = introGameData || currentGame; if (isV2Game(g)) { setV2Overrides(null); setV2LegacyStatus(null); setV2DailyChallenge(null); } initializeGame(); }} className="px-5 py-2.5 rounded-xl font-medium text-sm bg-yellow-400 text-gray-800 hover:bg-yellow-500 transition-colors">Play Again</button>
                  <button onClick={() => navigate("/games")} className="px-5 py-2.5 rounded-xl font-medium text-sm bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors">Back to Games</button>
                </div>
              </div>
            </div>
          }
        >
          {(() => {
            // Gate Play Again / Back to Games on the demo limit. If the user has hit the
            // limit, surface the upgrade modal at the natural decision moment instead of
            // auto-popping over the (unread) report.
            // Demo limit only applies to guests — logged-in users already have
            // an account, so suppressing the "Create Free Account" upsell modal.
            const handlePlayAgain = () => {
              if (!user && demoInfo?.limit_reached) { setShowDemoModal(true); return; }
              // For V2 games, clear overrides so the mode/persona selector re-opens — this
              // lets the user replay with a different mode/persona (key for branching/
              // replayability) and guarantees startGame receives a valid V2 payload.
              const gameForCheck = introGameData || currentGame;
              const isV2 = isV2Game(gameForCheck);
              if (isV2) {
                setV2Overrides(null);
                setV2LegacyStatus(null);
                setV2DailyChallenge(null);
              }

              // #37 Last-run takeaway transition: show 4s modal before re-init for V2 games
              const endingTakeaway =
                takeawayData?.takeaway
                || takeawayData?.title
                || finalReport?.report_core?.last_run_summary
                || gameState?.last_run_summary
                || null;
              const summaryText = typeof endingTakeaway === 'string' ? endingTakeaway : (endingTakeaway?.text || endingTakeaway?.message);
              if (isV2 && summaryText) {
                setShowLastRunTakeaway(summaryText);
                if (lastRunTakeawayTimerRef.current) clearTimeout(lastRunTakeawayTimerRef.current);
                lastRunTakeawayTimerRef.current = setTimeout(() => {
                  setShowLastRunTakeaway(null);
                  initializeGame();
                }, 4000);
                return;
              }
              initializeGame();
            };
            const handleBackToMenu = () => {
              if (!user && demoInfo?.limit_reached) { setShowDemoModal(true); return; }
              navigate("/games");
            };
            // Mystery-room epilogue slot: rendered first inside PostGameInsights
            // for any mystery_room game whose backend report includes an epilogue.
            const _mrReportCore = finalReport?.report_core || finalReport || {};
            const _mrEpilogue = _mrReportCore?.epilogue || null;
            const _mrIsMystery = currentGame?.game_type === 'mystery_room';
            const _mrMissedClues = _mrIsMystery
              ? (currentGame?.items || [])
                  .filter((it) => it.is_evidence)
                  .filter((it) => !((_mrReportCore?.evidence_collected || []).includes(it.id)))
                  .map((it) => ({ id: it.id, label: it.name || it.label || it.id }))
              : [];
            const epilogueSlot = _mrIsMystery && _mrEpilogue ? (
              <MysteryRoomEpilogue
                epilogue={_mrEpilogue}
                outcomeLabel={_mrReportCore?.outcome_label}
                knowledgeScore={_mrReportCore?.knowledge_score}
                missedClues={_mrMissedClues}
              />
            ) : null;
            return currentGame?.game_type === 'simulation' ? (
              <MentoReport
                finalReport={finalReport}
                runId={runId}
                onPlayAgain={handlePlayAgain}
                onBackToMenu={handleBackToMenu}
              />
            ) : (
              <GameOverScreen
                finalReport={finalReport}
                runId={runId}
                onPlayAgain={handlePlayAgain}
                onBackToMenu={handleBackToMenu}
                epilogueSlot={epilogueSlot}
              />
            );
          })()}
        </ErrorBoundary>
        {/* #37 Last-run takeaway transition (4s) */}
        <AnimatePresence>
          {showLastRunTakeaway && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[80] flex items-center justify-center bg-black/60 px-4"
            >
              <motion.div
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.95, opacity: 0 }}
                className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 text-center"
              >
                <div className="text-3xl mb-2">💡</div>
                <p className="text-xs uppercase tracking-widest text-amber-600 font-bold mb-2">What you learned last run</p>
                <p className="text-base font-semibold text-slate-800 leading-relaxed">{showLastRunTakeaway}</p>
                <div className="mt-4 h-1 bg-amber-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-amber-400"
                    initial={{ width: '100%' }}
                    animate={{ width: '0%' }}
                    transition={{ duration: 4, ease: 'linear' }}
                  />
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {socialPercentile && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 bg-amber-50 border border-amber-200 rounded-2xl shadow-xl px-6 py-4 text-center max-w-xs w-full"
          >
            <p className="text-sm text-amber-600 font-semibold">You scored higher than</p>
            <p className="text-4xl font-black text-amber-700">{socialPercentile.percentile}%</p>
            <p className="text-xs text-gray-500 mt-1">of players on {socialPercentile.label.replace(/_/g, ' ')} this week</p>
            <button onClick={() => setSocialPercentile(null)} className="mt-2 text-xs text-gray-400 hover:text-gray-600">Dismiss</button>
          </motion.div>
        )}
        {/* Fix 6: Post-game rank change card */}
        {(preGameRank || postGameRank) && (
          <div className="fixed bottom-4 right-4 z-50">
            <PostGameRankChange
              oldRank={preGameRank}
              newRank={postGameRank}
              speedRunTime={speedRunMode && speedRunStart ? Math.floor((Date.now() - speedRunStart) / 1000) : null}
              personalBest={null}
            />
          </div>
        )}
        {/* Async peer challenge result overlay */}
        {showChallengeResult && challengeId && (
          <ChallengeResult
            challengeId={challengeId}
            myScore={Math.round(
              finalReport?.report_core?.mento_score?.score
              || finalReport?.report_core?.final_score
              || finalReport?.final_score
              || 0
            )}
            onDismiss={() => setShowChallengeResult(false)}
          />
        )}
        <DemoLimitModal
          isOpen={showDemoModal}
          gamesPlayed={demoInfo?.games_played}
          gamesLimit={demoInfo?.games_limit}
          onContinueAnyway={() => setShowDemoModal(false)}
          onClose={() => setShowDemoModal(false)}
        />
      </>
    );
  }

if (!gameStarted) {
  // Show loading while fetching game metadata
  if (isLoadingIntro) {
    return (
      <>
        {moduleReturnBanner}
        <div
          className="min-h-screen flex items-center justify-center"
          style={{ backgroundColor: colors.background }}
        >
          <div className="text-center">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
              className="text-5xl mb-6"
              style={{ color: colors.primary }}
            >
              <FaGamepad />
            </motion.div>
            <p className="text-xl font-bold" style={{ color: colors.text }}>
              Loading...
            </p>
          </div>
        </div>
      </>
    );
  }

  const introVideo = introGameData?.intro_round?.video?.url;

  return (
    <>
    {moduleReturnBanner}
    {moduleBannerSpacer}
    <GameIntro
      gameData={introGameData}
      introVideo={introVideo}
      onStart={initializeGame}
      isLoading={isLoading}
      coachMode={coachMode}
      onToggleCoachMode={() => setCoachMode(prev => !prev)}
      aiVoiceMode={aiVoiceMode}
      onToggleAiVoiceMode={() => setAiVoiceMode(prev => !prev)}
      storyNarratorMode={storyNarratorMode}
      onToggleStoryNarratorMode={() => setStoryNarratorMode(prev => !prev)}
    />
    {/* V2 Mode/Persona selector on intro screen */}
    {showV2Selector && (
      <ModePersonaSelector
        game={introGameData || currentGame}
        legacyStatus={v2LegacyStatus}
        dailyChallenge={v2DailyChallenge}
        onConfirm={handleV2SelectorConfirm}
        onClose={() => setShowV2Selector(false)}
      />
    )}
    {/* Fix 6: Leaderboard Preview overlay on intro screen */}
    <AnimatePresence>
      {showLeaderboardPreview && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
        >
          <LeaderboardPreview
            gameId={gameId}
            onStartSpeedRun={() => {
              setSpeedRunMode(true);
              setShowLeaderboardPreview(false);
            }}
            onDismiss={() => setShowLeaderboardPreview(false)}
          />
        </motion.div>
      )}
    </AnimatePresence>
    </>
  );
}

  // Route to specialized renderers for non-round game types
  const gameType = currentGame?.game_type || 'rounds';

  // For round-based games, wait for currentRound; for board/minigame, only need currentGame
  if (gameStarted && !currentGame) {
    return (
      <>
        {moduleReturnBanner}
        <div
          className="min-h-screen flex items-center justify-center"
          style={{ backgroundColor: colors.background }}
        >
          <div className="text-center">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="text-5xl mb-6"
              style={{ color: colors.primary }}
            >
              <FaGamepad />
            </motion.div>
            <p className="text-lg" style={{ color: colors.text }}>
              Loading game content...
            </p>
          </div>
        </div>
      </>
    );
  }

  // For round-based games, also wait for currentRound
  if (gameStarted && gameType === 'rounds' && !currentRound) {
    return (
      <>
        {moduleReturnBanner}
        <div
          className="min-h-screen flex items-center justify-center"
          style={{ backgroundColor: colors.background }}
        >
          <div className="text-center">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="text-5xl mb-6"
              style={{ color: colors.primary }}
            >
              <FaGamepad />
            </motion.div>
            <p className="text-lg" style={{ color: colors.text }}>
              Loading rounds...
            </p>
          </div>
        </div>
      </>
    );
  }
  if (gameType !== 'rounds') {
    // Game-type-specific default instructions
    const gameTypeInstructions = {
      chess_strategy: ['Each piece has unique abilities based on the game theme', 'Click a piece to select it, then click a highlighted square to move', 'Use Action Points (AP) wisely — they refresh each turn', 'Capture the opponent\'s King piece or reach the valuation target to win', 'Hover over pieces to see their stats and special abilities'],
      go_territory: ['Click any intersection on the board to place your stone (Black)', 'Surround opponent\'s stones to capture them', 'Control more territory than the AI to win', 'Click "Pass" when you have no beneficial moves left', 'The game ends when both players pass consecutively'],
      reversi: ['Click a valid position (highlighted) to place your disc', 'Your disc must outflank opponent discs in a straight line', 'Outflanked discs flip to your color', 'The player with the most discs when the board is full wins', 'Corner positions are powerful — they can never be flipped'],
      tower_defense: ['Select a tower type from the sidebar, then click a highlighted cell to place it', 'Click "Start Wave" to send the next wave of enemies', 'Towers automatically attack enemies in range', 'Earn currency for each enemy defeated — use it to build more towers', 'Upgrade towers by clicking on them for increased damage and range'],
      puzzle_match: ['Click a tile to select it, then click an adjacent tile to swap', 'Match 3 or more identical tiles in a row or column to score', 'Chain combos for bonus points', 'Reach the target score before running out of moves to win'],
      board: ['Roll the dice to move across the board', 'Land on special tiles for events, shops, or challenges', 'Manage your resources carefully as you progress', 'Reach the final tile or achieve the highest score to win'],
      minigame: ['Read the challenge prompt carefully', 'Complete the task within the time limit if applicable', 'Score points for correct answers or actions', 'Try to achieve the highest score possible'],
      card: ['Play cards from your hand by clicking on them', 'Each card has attack, defense, or special abilities', 'Strategize your card order for maximum effect', 'Defeat the opponent by reducing their health to zero'],
      strategy: ['Build and manage your resources each turn', 'Make strategic decisions about expansion vs consolidation', 'Balance multiple competing priorities', 'The final score depends on how well you managed all aspects'],
      ai_arena: ['Read each scenario carefully before choosing', 'Your choices affect multiple resource bars — watch the tradeoffs', 'NPC competitors react to your decisions', 'There may be crisis events that require immediate attention', 'The AI adapts the story based on your play style'],
      story_branching: ['Read the story scene and consider the situation', 'Choose from the available options to shape the narrative', 'Each choice leads to different story paths and outcomes', 'There is no single "right" answer — explore different perspectives'],
      simulation: ['Monitor your city dashboard — subsystems are interconnected', 'Each decision ripples across multiple systems over time', 'Watch the news ticker for events and NPC reactions', 'Balance competing priorities under budget constraints', 'Random events will test your resilience — plan ahead!'],
      strategy_grid: ['Click a piece on your side (blue) to select it', 'Green dots show valid moves — click to move there', 'Red highlights indicate capturable enemy pieces', 'Use special abilities from the side panel or piece detail modal', 'Control objectives, gather resources, and capture the key piece to win'],
    };
    const helpSteps = Array.isArray(currentGame?.how_to_play)
      ? currentGame.how_to_play
      : currentGame?.how_to_play?.steps || gameTypeInstructions[gameType] || [
        'Interact with the game board or interface',
        'Make strategic decisions each turn',
        'Watch how your actions affect the outcome',
        'Complete the objective to win',
      ];
    return (
      <>
      {moduleReturnBanner}
      {moduleBannerSpacer}
      <ErrorBoundary variant="gameplay" key={runId}>
      <Suspense fallback={
        <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: colors.background }}>
          <div className="text-center">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }} className="text-5xl mb-6" style={{ color: colors.primary }}>
              <FaGamepad />
            </motion.div>
            <p className="text-lg" style={{ color: colors.text }}>Loading game...</p>
          </div>
        </div>
      }>
        {/* Round 13: Frustration support message */}
        {frustrationMsg && (
          <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[200] max-w-sm w-full mx-4 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 shadow-lg flex items-start gap-3">
            <span className="text-xl">💡</span>
            <div className="flex-1">
              <p className="text-xs text-amber-800 font-medium">{frustrationMsg}</p>
            </div>
            <button onClick={() => setFrustrationMsg(null)} className="text-amber-400 text-lg font-bold leading-none">×</button>
          </div>
        )}

        {/* Coaching nudge overlay */}
        <AnimatePresence>
          {coachingNudge && (
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              className="fixed top-16 left-1/2 -translate-x-1/2 z-[200] max-w-xs w-full mx-4"
              style={{ background: 'linear-gradient(135deg, #FFF8E7 0%, #FFF3D0 100%)', border: '1px solid #FFD166', borderRadius: '14px', padding: '14px 16px', boxShadow: '0 8px 24px rgba(255,209,102,0.25)' }}
            >
              <div className="flex items-center gap-3">
                <span style={{ fontSize: '24px' }}>🧠</span>
                <div className="flex-1">
                  <p style={{ fontSize: '13px', fontWeight: 700, color: '#92400E', margin: 0 }}>Coaching Moment</p>
                  <p style={{ fontSize: '11px', color: '#B45309', margin: '2px 0 0' }}>I noticed a pattern in your choices — want a quick coaching tip?</p>
                </div>
                <button onClick={() => setCoachingNudge(false)} style={{ color: '#D97706', fontSize: '18px', fontWeight: 'bold', lineHeight: 1, background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Adaptive difficulty message */}
        <AnimatePresence>
          {adaptHint && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              style={{ margin: '8px 0', padding: '10px 14px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '10px',
                background: adaptHint.difficulty_adjustment === 'harder' ? '#FFF7ED' : '#F0FDF4',
                border: `1px solid ${adaptHint.difficulty_adjustment === 'harder' ? '#FED7AA' : '#BBF7D0'}`,
                position: 'fixed', bottom: '96px', right: '16px', zIndex: 200, maxWidth: '280px',
              }}
            >
              <span style={{ fontSize: '20px' }}>{adaptHint.difficulty_adjustment === 'harder' ? '🎯' : '💪'}</span>
              <div>
                <p style={{ fontSize: '12px', fontWeight: 700, color: adaptHint.difficulty_adjustment === 'harder' ? '#C2410C' : '#166534', margin: 0 }}>
                  {adaptHint.difficulty_adjustment === 'harder' ? 'Challenge Mode!' : 'Building Confidence'}
                </p>
                <p style={{ fontSize: '11px', color: adaptHint.difficulty_adjustment === 'harder' ? '#EA580C' : '#15803D', margin: '2px 0 0' }}>
                  {adaptHint.hint || (adaptHint.difficulty_adjustment === 'harder' ? "You're doing great — the next decisions will be more nuanced to match your level." : "This one's a bit simpler — let's build your confidence here.")}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Round 15: Variable reward bonus chip */}
        <AnimatePresence>
          {rewardBonus && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10 }}
              className="fixed top-20 left-1/2 -translate-x-1/2 z-[200] bg-amber-400 text-gray-900 font-bold text-sm px-5 py-2 rounded-full shadow-lg pointer-events-none"
            >
              🎰 {rewardBonus >= 2 ? 'Bonus Reward!' : rewardBonus > 1 ? 'Boosted!' : 'Reduced Outcome'} ×{rewardBonus.toFixed(1)}
            </motion.div>
          )}
        </AnimatePresence>

        <GameTypeRouter
          gameType={gameType}
          currentGame={currentGame}
          gameState={gameState}
          runId={runId}
          defaultAiMode={storyNarratorMode}
          playerProfile={playerProfile}
          onGameEnd={async () => {
            try {
              await endGame();
            } catch (err) {
              console.error('Failed to fetch final report for minigame/board game:', err);
            }
          }}
          onBack={() => {
            // Round 13: log quit before navigating away
            if (runId && gameId) {
              logQuitSession({ runId, gameId, roundNumber: gameState?.round_index || 0 }).catch(() => {});
            }
            navigate('/games');
          }}
        />


        {/* Floating Help Button — visible for ALL game types */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setShowHelpModal(true)}
          className="fixed bottom-20 right-4 z-40 w-10 h-10 rounded-full shadow-lg flex items-center justify-center border"
          style={{ backgroundColor: '#118AB2', borderColor: '#0E7490', color: 'white' }}
          title="How to Play"
        >
          <FaQuestionCircle className="text-sm" />
        </motion.button>

        {/* Help Modal */}
        <AnimatePresence>
          {showHelpModal && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
              onClick={() => setShowHelpModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white text-gray-900 rounded-xl shadow-2xl max-w-md w-full max-h-[80vh] overflow-y-auto"
              >
                <div className="p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <FaQuestionCircle className="text-blue-500" />
                      <h3 className="font-bold text-base">How to Play</h3>
                    </div>
                    <button onClick={() => setShowHelpModal(false)} className="p-1.5 hover:bg-gray-100 rounded-lg">
                      <FaTimes className="text-gray-400 text-sm" />
                    </button>
                  </div>
                  <p className="text-sm mb-3 text-gray-500">
                    {currentGame?.description || 'Complete the game objective by making strategic decisions.'}
                  </p>
                  <div className="space-y-2 mb-4">
                    {helpSteps.map((step, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-600 text-[10px] font-bold flex items-center justify-center mt-0.5">{i + 1}</span>
                        <span className="text-xs text-gray-700 leading-relaxed">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Glossary Panel — floats over board/minigames */}
        {currentGame?.glossary_terms?.length > 0 && (
          <GlossaryPanel
            terms={currentGame.glossary_terms}
            colors={mergedColors}
          />
        )}
      </Suspense>
      </ErrorBoundary>
      </>
    );
  }

  const videoUrl = currentRound?.video?.url || null;

  // Determine if this is audio/voice round
  const isAudioRound =
    hasFeature("audio_negotiation") || currentRound.audio_negotiation;

  // Available features
  const features = [
    { id: "resources", label: "Stats", icon: <FaChartLine />, has: true },
    {
      id: "crafting",
      label: "Craft",
      icon: <FaHammer />,
      has: hasFeature("crafting"),
    },
    {
      id: "tech",
      label: "Tech",
      icon: <FaSitemap />,
      has: hasFeature("tech_tree"),
    },
    {
      id: "dialogue",
      label: "Chat",
      icon: <FaComments />,
      has: hasFeature("dialogue"),
    },
    { id: "audio", label: "Voice", icon: <FaMicrophone />, has: isAudioRound },
    {
      id: "rpg",
      label: "Battle",
      icon: <FaSkullCrossbones />,
      has: hasFeature("rpg"),
    },
  ].filter((f) => f.has);

  // Key stats for quick access — dynamic from game's initial_state
  const keyStats = (() => {
    if (!currentGame || !gameState) return [];

    const KNOWN_STATS = {
      energy: { label: "Energy", icon: <FaBolt />, color: "#FFD166" },
      health: { label: "Health", icon: <FaHeart />, color: "#EF476F" },
      experience: { label: "XP", icon: <FaStar />, color: "#06D6A0" },
      reputation: { label: "Reputation", icon: <FaCrown />, color: "#FF9B71" },
      cash_inr: { label: "Cash", icon: <FaCoins />, color: "#06D6A0" },
      mento_coins: { label: "Money", icon: <FaCoins />, color: "#06D6A0" },
      stress: { label: "Stress", icon: <FaBrain />, color: "#6B7280" },
      customers: { label: "Customers", icon: <FaStar />, color: "#8B5CF6" },
      total_revenue: { label: "Revenue", icon: <FaCoins />, color: "#06D6A0" },
      total_expenses: { label: "Expenses", icon: <FaCoins />, color: "#EF476F" },
      morale: { label: "Morale", icon: <FaHeart />, color: "#8B5CF6" },
      food: { label: "Food", icon: <FaStar />, color: "#06D6A0" },
      water: { label: "Water", icon: <FaGem />, color: "#118AB2" },
      shelter_quality: { label: "Shelter", icon: <FaHome />, color: "#FF9B71" },
      funds: { label: "Funds", icon: <FaCoins />, color: "#06D6A0" },
      money_inr: { label: "Money", icon: <FaCoins />, color: "#06D6A0" },
      savings: { label: "Savings", icon: <FaCoins />, color: "#06D6A0" },
    };
    const COLOR_CYCLE = ["#06D6A0", "#EF476F", "#FFD166", "#118AB2", "#8B5CF6", "#FF9B71"];
    const SKIP_KEYS = new Set(["round_index", "total_rounds", "game_over", "game_id", "run_id", "week_number"]);
    const psychIds = new Set(
      (currentGame.psychological_framework?.core_skills || []).map(s => s.id)
    );

    const initialState = currentGame.initial_state || {};
    const results = [];
    let colorIdx = 0;

    for (const k of Object.keys(initialState)) {
      if (SKIP_KEYS.has(k) || psychIds.has(k)) continue;
      const def = initialState[k];
      if (typeof def === "object" && def !== null) {
        const cat = def.category;
        if (cat === "psychological" || cat === "Story & Narrative") continue;
      }
      if (gameState[k] === undefined || typeof gameState[k] !== "number") continue;

      const known = KNOWN_STATS[k];
      if (known) {
        results.push({ key: k, ...known });
      } else {
        const label = k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
        results.push({ key: k, label, icon: <FaChartLine />, color: COLOR_CYCLE[colorIdx++ % COLOR_CYCLE.length] });
      }
      if (results.length >= 8) break;
    }
    return results;
  })();

  return (
    <>
    {moduleReturnBanner}
    {moduleBannerSpacer}
    <div
      className="gp-page h-screen flex flex-col"
      style={{ backgroundColor: mergedColors.background, fontFamily: currentGame?.layout_config?.theme?.font_family || 'inherit' }}
      data-reduced-motion={reducedMotion ? "true" : undefined}
      data-focus-mode={isFocusMode ? "true" : undefined}
    >
      {/* Module banner is rendered globally below — see ModuleReturnBanner JSX. */}

      {/* Module completion modal — replaces window.confirm with a styled experience */}
      <AnimatePresence>
        {showModuleCompleteModal && moduleContext && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
            <motion.div
              initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-3xl shadow-2xl max-w-md w-full overflow-hidden">
              <div className="p-6 text-center text-white"
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}>
                <div className="text-5xl mb-2">🎉</div>
                <div className="text-xl font-black">Lesson Complete!</div>
                <div className="text-sm opacity-90 mt-1">
                  {moduleContext.lessonIcon} {moduleContext.lessonTitle}
                </div>
              </div>
              <div className="p-5">
                <div className="rounded-2xl p-3 mb-4"
                  style={{ background: '#EEF2FF', border: '1.5px solid #c7d2fe' }}>
                  <div className="text-[11px] font-bold uppercase tracking-wider mb-1" style={{ color: '#4f46e5' }}>
                    💬 Mento says
                  </div>
                  <p className="text-sm" style={{ color: '#1e1b4b' }}>
                    Great work finishing the simulation! Bring what you noticed back to your module — the next lesson builds on this.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => setShowModuleCompleteModal(false)}
                    className="px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
                    style={{ background: '#f5f5f4', color: '#57534E' }}>
                    Stay in game
                  </button>
                  <button onClick={() => navigate(`/modules/${moduleId}`)}
                    className="px-4 py-2.5 rounded-xl text-sm font-bold text-white transition-transform hover:scale-105"
                    style={{ background: 'linear-gradient(90deg, #6366f1, #8b5cf6)' }}>
                    Return to Module →
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Session timer nudge — 45-minute break reminder */}
      {showTimerNudge && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-amber-500/95 backdrop-blur text-white px-5 py-3 rounded-2xl shadow-xl flex items-center gap-3 max-w-sm w-[calc(100%-2rem)]">
          <span className="text-xl flex-shrink-0">⏰</span>
          <div className="flex-1">
            <p className="font-semibold text-sm">Time for a break!</p>
            <p className="text-xs opacity-90">You've been playing for 45+ minutes. Rest helps your brain retain what you've learned.</p>
          </div>
          <button
            onClick={() => { setShowTimerNudge(false); nudgeDismissedRef.current = true; }}
            className="text-white/80 hover:text-white text-lg font-bold flex-shrink-0 ml-1"
            aria-label="Dismiss break reminder"
          >✕</button>
        </div>
      )}

      {/* Feature 3: 15-minute session checkpoint banner */}
      {showCheckpoint && !checkpointDismissed && (
        <SessionCheckpointBanner
          onContinue={() => { setCheckpointDismissed(true); setShowCheckpoint(false); }}
          onSaveAndReturn={() => { setCheckpointDismissed(true); setShowCheckpoint(false); navigate('/home/student'); }}
        />
      )}

      {/* Fix 6: Speed Run Timer */}
      <SpeedRunTimer active={speedRunMode && !!speedRunStart} startTime={speedRunStart} />

      {/* Assessment mode banner */}
      {assessMode && (
        <div className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-amber-700 bg-amber-50 border-b border-amber-200">
          <span>📋</span>
          <span>Assessment Mode — your choices are being analysed for skill profiling</span>
        </div>
      )}

      {/* F5: IP lock violation overlay */}
      {assessIpLocked && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-red-900/95">
          <div className="text-center px-8 max-w-sm">
            <div className="text-5xl mb-4">⛔</div>
            <h2 className="text-xl font-bold text-white mb-2">Session Locked</h2>
            <p className="text-red-200 text-sm">This assessment session is locked to a different device. Please continue on the device where you started.</p>
          </div>
        </div>
      )}

      {/* R1 — Live investor negotiation modal */}
      {liveInvestor && (
        <LiveInvestorModal
          runId={runId}
          round={liveInvestor.round}
          choice={liveInvestor.choice}
          onClose={() => setLiveInvestor(null)}
        />
      )}

      {/* R4 — Contrarian dissent juror modal (Ethics Tribunal) */}
      {dissentJuror && (
        <DissentJurorModal
          runId={runId}
          round={dissentJuror.round}
          choice={dissentJuror.choice}
          onClose={() => setDissentJuror(null)}
        />
      )}

      {/* R18 — Mento explains contextual coach (per-round) */}
      {runId && currentRound?.id && !gameEnded && (
        <MentoExplainPopover runId={runId} roundId={currentRound.id} />
      )}

      {/* R12 — Live boardroom debate (rounds with live_debate config) */}
      {runId && currentRound?.live_debate?.enabled && (
        <LiveBoardDebateModal
          isOpen={liveDebateOpen}
          onClose={() => setLiveDebateOpen(false)}
          runId={runId}
          roundId={currentRound.id}
          liveDebate={currentRound.live_debate}
        />
      )}

      {/* R13 — Live PvP launcher (rounds with pvp_mode config) */}
      {runId && currentRound?.pvp_mode?.enabled && (
        <PvpLauncherModal
          isOpen={pvpLauncherOpen}
          onClose={() => setPvpLauncherOpen(false)}
          runId={runId}
          roundId={currentRound.id}
          pvpConfig={currentRound.pvp_mode}
        />
      )}

      {/* F8: Demo save modal */}
      {showDemoSaveModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 px-4">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm text-center">
            <div className="text-4xl mb-3">🎉</div>
            <h2 className="text-lg font-bold text-gray-800 mb-1">Nice game!</h2>
            <p className="text-sm text-gray-500 mb-4">Create a free account to save your results, track your skills, and unlock 101+ more games.</p>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/login')}
                className="w-full py-3 rounded-xl font-bold text-sm bg-yellow-400 text-gray-900 hover:bg-yellow-500 transition-colors"
              >Create Free Account →</button>
              <button
                onClick={() => setShowDemoSaveModal(false)}
                className="w-full py-2 rounded-xl text-xs text-gray-400 hover:text-gray-600"
              >Continue without saving</button>
            </div>
          </div>
        </div>
      )}

      {/* Engagement overlays — hidden in assessment mode */}
      {!assessMode && <FloatingDeltaLayer floatingDeltas={engagement.floatingDeltas} />}
      {!assessMode && <StreakBanner streakCount={engagement.streakCount} streakMultiplier={engagement.streakMultiplier} />}


      {/* Sound Controls */}
      <Suspense fallback={null}><SoundControls /></Suspense>

      {/* Game Storybook Modal */}
      <Suspense fallback={null}>
        <GameStorybook
          gameData={currentGame}
          isOpen={showStorybook}
          onClose={() => setShowStorybook(false)}
        />
      </Suspense>

      {/* Game Mode Overlays */}
      <Suspense fallback={null}>
        {currentGame?.game_mode === 'video_intro' && gameState?.round_index === 0 && (
          <VideoIntroOverlay
            round={currentRound}
            onComplete={() => {}}
          />
        )}
        {currentGame?.game_mode === 'storybook' && (
          <StorybookOverlay
            round={currentRound}
            choices={currentRound?.choices}
            onChoiceSelect={handleChoiceSubmit}
            gameState={gameState}
            disabled={showOutcome || isSubmitting || isTransitioning}
          />
        )}
        {currentGame?.game_mode === 'trait_journey' && (
          <TraitJourneyOverlay
            gameState={gameState}
            currentRound={currentRound}
            onChoiceSelect={handleChoiceSubmit}
          />
        )}
        {currentGame?.game_mode === 'quiz' && (
          <QuizOverlay
            round={currentRound}
            gameState={gameState}
            onTimeUp={() => {
              if (currentRound?.choices?.[0]) {
                handleChoiceSubmit(currentRound.choices[0].id);
              }
            }}
          />
        )}
        {currentGame?.game_mode === 'trading' && (
          <TradingOverlay
            gameState={gameState}
            currentGame={currentGame}
            roundIndex={gameState?.round_index || 0}
          />
        )}
        {currentGame?.game_mode === 'survival' && (
          <SurvivalOverlay
            gameState={gameState}
            currentGame={currentGame}
            roundIndex={gameState?.round_index || 0}
          />
        )}
        {currentGame?.game_mode === 'city_builder' && (
          <CityBuilderOverlay
            gameState={gameState}
            currentGame={currentGame}
          />
        )}
      </Suspense>

      {/* Top Header - Clean Design */}
      <header
        className="border-b bg-white flex-shrink-0"
        style={{ borderColor: mergedColors.primaryLight }}
      >
        <div className="px-3 sm:px-6 py-2 sm:py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 sm:space-x-4 min-w-0">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate("/games")}
                className="flex items-center space-x-2 px-3 py-2 border"
                style={{
                  borderColor: mergedColors.primaryLight,
                  color: mergedColors.text,
                }}
              >
                <FaChevronLeft />
                <span className="hidden sm:inline text-sm font-medium">
                  Games
                </span>
              </motion.button>

              <div className="flex items-center space-x-3">
                <div
                  className="w-8 h-8 flex items-center justify-center border"
                  style={{
                    backgroundColor: mergedColors.primary,
                    borderColor: mergedColors.primaryDark,
                  }}
                >
                  <FaGamepad
                    className="text-sm"
                    style={{ color: mergedColors.text }}
                  />
                </div>
                <div>
                  <h1
                    className="font-bold text-sm"
                    style={{ color: mergedColors.text }}
                  >
                    {currentGame.title}
                  </h1>
                  <p className="text-xs" style={{ color: mergedColors.textLight }}>
                    Round{" "}
                    {currentGame.rounds?.findIndex(
                      (r) => r.id === currentRound.id,
                    ) + 1 || 1}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {currentGame.rounds && (
                <div className="hidden md:block w-56">
                  <GameTimeline
                    rounds={currentGame.rounds}
                    currentRoundId={currentRound?.id}
                    roundHistory={roundHistory}
                  />
                </div>
              )}

              <div className="flex items-center space-x-2">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => navigate("/games")}
                  className="p-2 border"
                  style={{
                    borderColor: mergedColors.primaryLight,
                    color: mergedColors.text,
                  }}
                >
                  <FaHome />
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => window.location.reload()}
                  className="p-2 border"
                  style={{
                    borderColor: mergedColors.primaryLight,
                    color: mergedColors.text,
                  }}
                >
                  <FaRedo />
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setShowStorybook(true)}
                  className="p-2 border"
                  style={{
                    borderColor: mergedColors.primaryLight,
                    color: mergedColors.text,
                  }}
                  title="Game Guide"
                >
                  <FaBookOpen />
                </motion.button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div role="main" className="gp-main flex-1 flex flex-col min-h-0">
        {/* Top section (3/5): video + story */}
        <div className="gp-top min-h-0">
          {/* Video column */}
          <div className="gp-video p-1 flex flex-col">
            <div
              className="gp-media bg-white border overflow-hidden"
              style={{ borderColor: mergedColors.primaryLight }}
            >
              {currentRound?.image_url ? (
                // Priority 1: explicit pre-cached image URL
                <img
                  src={currentRound.image_url}
                  alt="Round visual"
                  className="w-full h-full"
                />
              ) : videoUrl ? (
                // Priority 2: explicit video — shown only when present
                <video
                  src={videoUrl}
                  className="w-full h-full object-contain"
                  controls
                  autoPlay={!showOutcome}
                  playsInline
                  preload="metadata"
                  style={{ background: '#1a1a2e' }}
                  onError={(e) => console.error("Video failed to load:", videoUrl)}
                />
              ) : (
                // Priority 3: no video → always try to auto-generate an image.
                // Backend derives prompt from image_prompt → scenario/title if not explicit.
                <StoryImageLoader
                  gameId={currentGame?.game_id}
                  roundId={currentRound?.id}
                  imagePrompt={
                    currentRound?.image_prompt ||
                    currentRound?.situation ||
                    currentRound?.story ||
                    currentRound?.title
                  }
                  sceneHint={currentRound?.scene_hint || currentRound?.title}
                  borderColor={mergedColors.primaryLight}
                />
              )}
            </div>
          </div>

          {/* Story column (scrollable) */}
          <div className="gp-storyCol p-2 overflow-y-auto">
            {/* Feature 4a: "Previously on..." recap */}
            {previouslyOn && (
              <div style={{ margin: '0 0 12px', padding: '10px 14px', background: '#EFF6FF', borderRadius: '10px', border: '1px solid #BFDBFE', position: 'relative' }}>
                <button onClick={() => setPreviouslyOn(null)} style={{ position: 'absolute', top: '4px', right: '8px', background: 'none', border: 'none', color: '#93C5FD', cursor: 'pointer', fontSize: '14px' }}>&times;</button>
                <p style={{ fontSize: '12px', color: '#1E40AF', fontStyle: 'italic' }}>
                  {'\u{1F4D6}'} <strong>Previously...</strong> {previouslyOn}
                </p>
              </div>
            )}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-8"
            >
              <div
                className="bg-white p-4 border"
                style={{
                  borderColor: mergedColors.primary,
                  borderLeftWidth: "6px",
                  boxShadow: "0 2px 8px rgba(255, 209, 102, 0.1)",
                }}
              >
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <h2 className="text-2xl font-bold" style={{ color: mergedColors.text }}>
                    {tRound(currentGame, currentRound?.id, 'title', currentRound?.title) || "Chapter Continues"}
                  </h2>
                  {roundMode === 'tutorial' && (
                    <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold" style={{ background: '#06D6A020', color: '#06D6A0' }}>
                      Learning the ropes
                    </span>
                  )}
                  {roundMode === 'mastery' && (
                    <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold" style={{ background: '#EF476F20', color: '#EF476F' }}>
                      Mastery round
                    </span>
                  )}
                  {currentRound?.adaptive_difficulty?.calibrated && (
                    <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold" style={{ background: '#6366f120', color: '#6366f1' }}>
                      🎯 Calibrated to your skill level
                    </span>
                  )}
                  {currentRound?.variant_label && (
                    <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold" style={{ background: '#a855f720', color: '#a855f7' }} title="You're playing an alternate replay variant">
                      🔀 Variant: {currentRound.variant_label}
                    </span>
                  )}
                  {currentRound?.live_debate?.enabled && !gameEnded && (
                    <button
                      onClick={() => setLiveDebateOpen(true)}
                      className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-gradient-to-r from-slate-900 to-indigo-700 text-white hover:opacity-90 transition"
                      title="Cross-examine the AI before you choose"
                    >
                      🎙️ Live debate · {currentRound.live_debate.persona?.name || 'Board member'}
                    </button>
                  )}
                  {currentRound?.pvp_mode?.enabled && !gameEnded && (
                    <button
                      onClick={() => setPvpLauncherOpen(true)}
                      className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-gradient-to-r from-emerald-700 to-teal-700 text-white hover:opacity-90 transition"
                      title="Negotiate against another player live"
                    >
                      ⚔️ Live PvP
                    </button>
                  )}
                  {soundscape.enabled && (
                    <button
                      onClick={soundscape.toggleMute}
                      className="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition"
                      title={soundscape.muted ? "Unmute soundscape" : "Mute soundscape"}
                    >
                      {soundscape.muted ? "🔇" : "🔊"} Sound
                    </button>
                  )}
                </div>
                {/* Feature 4: Market Feed for finance/negotiation games */}
                {currentGame?.market_feed && runId && (
                  <MarketFeed runId={runId} round={currentRound?.id} />
                )}
                {/* R5 — Lemonade Empire bar-chart dashboard */}
                {currentGame?.game_id === 'lemonade_empire_v1' && (
                  <LemonadeDashboard
                    gameState={gameState}
                    runId={runId}
                    roundIndex={gameState?.round_index}
                  />
                )}
                {/* V2 floating chrome + inline rival ticker */}
                {!assessMode && (
                  <V2Panel
                    game={currentGame}
                    runId={runId}
                    round={currentRound}
                    roundIndex={gameState?.round_index}
                  />
                )}
                {/* Dynamic news strip — injected by backend based on game state conditions */}
                {currentRound?.dynamic_news?.length > 0 && (
                  <div className="mb-3 flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: 'none' }}>
                    {currentRound.dynamic_news.map((n, i) => (
                      <div key={i} className="flex-shrink-0 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 max-w-[220px]">
                        <p className="text-[11px] font-semibold text-amber-800 leading-tight">{n.headline}</p>
                        {n.source && <p className="text-[10px] text-amber-500 mt-0.5">{n.source}</p>}
                      </div>
                    ))}
                  </div>
                )}
                <div className="gp-story max-w-none text-[15px]" style={{ color: mergedColors.text }}>
                  <StoryDisplay
                    story={injectPlayerName(tRound(currentGame, currentRound?.id, 'story', tRound(currentGame, currentRound?.id, 'scenario', currentRound?.story)))}
                    title={tRound(currentGame, currentRound?.id, 'title', currentRound?.title)}
                    setting={injectPlayerName(currentRound?.setting)}
                    goal={injectPlayerName(currentRound?.goal)}
                    imageUrl={currentRound?.image_url}
                    videoUrl={currentRound?.video_url}
                    challenge={injectPlayerName(currentRound?.challenge)}
                    sceneHint={currentRound?.scene_hint}
                    characterInsights={currentRound?.character_insights}
                    competitor={currentRound?.competitor}
                    competitorMove={currentRound?.competitor_move}
                    event={currentRound?.event}
                    callbackReferences={currentRound?.callback_references}
                    sceneType={currentRound?.scene_type}
                    colors={mergedColors}
                    variant="embedded"
                  />
                </div>

                {/* Setting & Goal (if any) */}
                {(currentRound?.setting || currentRound?.goal) && (
                  <div className="mt-6 pt-4 border-t" style={{ borderColor: mergedColors.primaryLight }}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {currentRound.setting && (
                        <div className="flex">
                          <div
                            className="w-8 h-8 flex items-center justify-center mr-3 mt-1"
                            style={{ backgroundColor: mergedColors.primaryLight, color: mergedColors.text }}
                          >
                            <FaGem className="text-sm" />
                          </div>
                          <div>
                            <h4 className="font-bold text-sm mb-1" style={{ color: mergedColors.text }}>
                              Current Setting
                            </h4>
                            <p className="text-sm" style={{ color: mergedColors.textLight }}>
                              {currentRound.setting}
                            </p>
                          </div>
                        </div>
                      )}
                      {currentRound.goal && (
                        <div className="flex">
                          <div
                            className="w-8 h-8 flex items-center justify-center mr-3 mt-1"
                            style={{ backgroundColor: mergedColors.primaryLight, color: mergedColors.text }}
                          >
                            <FaFlag className="text-sm" />
                          </div>
                          <div>
                            <h4 className="font-bold text-sm mb-1" style={{ color: mergedColors.text }}>
                              Your Goal
                            </h4>
                            <p className="text-sm" style={{ color: mergedColors.textLight }}>
                              {currentRound.goal}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>

            {/* Feature-specific panels (dialogue, battle, etc.) - placed below story */}
            {hasFeature("dialogue") && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
                <div
                  className="bg-white p-4 border"
                  style={{ borderColor: mergedColors.success, borderLeftWidth: "6px" }}
                >
                  <div className="flex items-center mb-4">
                    <div
                      className="w-10 h-10 flex items-center justify-center mr-3"
                      style={{ backgroundColor: mergedColors.success, border: `2px solid ${mergedColors.success}` }}
                    >
                      <FaComments style={{ color: mergedColors.text }} />
                    </div>
                    <h3 className="text-lg font-bold" style={{ color: mergedColors.text }}>
                      Character Dialogue
                    </h3>
                  </div>
                  <DialoguePanel messages={conversationHistory} character={currentRound?.character} />
                </div>
              </motion.div>
            )}

            {hasFeature("rpg") && currentRound?.battle && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
                <div
                  className="bg-white p-4 border"
                  style={{ borderColor: mergedColors.error, borderLeftWidth: "6px" }}
                >
                  <div className="flex items-center mb-6">
                    <div
                      className="w-12 h-12 flex items-center justify-center mr-4"
                      style={{ backgroundColor: mergedColors.error, border: `2px solid ${mergedColors.error}` }}
                    >
                      <FaSkullCrossbones style={{ color: mergedColors.text }} />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold" style={{ color: mergedColors.text }}>
                        Battle Arena
                      </h3>
                      <p className="text-sm" style={{ color: mergedColors.textLight }}>
                        Strategic combat encounter
                      </p>
                    </div>
                  </div>
                  <RPGBattlePanel battle={currentRound.battle} onAction={(action) => {}} />
                </div>
              </motion.div>
            )}

            {/* Crafting / Tech panels can be added here if desired, but they are also in stats panel */}
          </div>
        </div>

        {/* Bottom section (2/5): decisions (4/5) + stats (1/5) */}
          <div className="gp-bottom border-t bg-white" style={{ borderColor: mergedColors.primaryLight }}>
          <div className="gp-bottomGrid min-h-0">
            <div className="gp-decisions h-full min-h-0 p-1">
              {/* Mobile compact resource bar — visible only on mobile where stats panel is hidden */}
              {keyStats.length > 0 && (
                <div className="md:hidden" style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(keyStats.length, 4)}, 1fr)`, gap: '4px', padding: '4px 4px 6px' }}>
                  {keyStats.slice(0, 4).map(stat => {
                    const val = getResourceValue(stat.key);
                    if (typeof val !== 'number') return null;
                    const sentiment = getResourceSentiment(val, stat.max || 100);
                    return (
                      <div key={stat.key} style={{
                        textAlign: 'center', padding: '3px 4px', borderRadius: '8px',
                        background: '#FFFDF7', border: '1px solid #E2E8F0',
                      }}>
                        <div style={{ fontSize: '14px', fontWeight: 900, color: '#2D3047' }}>{val}</div>
                        <div style={{ fontSize: '8px', fontWeight: 600, color: '#64748B', lineHeight: 1.2 }}>{stat.label}</div>
                        <div style={{ fontSize: '7px', color: sentiment.color, fontWeight: 700 }}>{sentiment.emoji} {sentiment.label}</div>
                      </div>
                    );
                  })}
                </div>
              )}
              {isAudioRound ? (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                  <div
                    className="bg-white p-4 border"
                    style={{ borderColor: mergedColors.warning, borderLeftWidth: "6px" }}
                  >
                    <div className="flex items-center mb-6">
                      <div
                        className="w-12 h-12 flex items-center justify-center mr-4"
                        style={{
                          backgroundColor: mergedColors.warning,
                          border: `2px solid ${mergedColors.warning}`,
                        }}
                      >
                        <FaMicrophone style={{ color: mergedColors.text }} />
                      </div>
                      <div>
                        <h3 className="text-lg font-bold" style={{ color: mergedColors.text }}>
                          Voice Challenge
                        </h3>
                        <p className="text-sm" style={{ color: mergedColors.textLight }}>
                          Speak your decision aloud
                        </p>
                      </div>
                    </div>
                    <VoiceInput
                      onTranscript={(text) => {}}
                      conversationHistory={conversationHistory}
                      compact
                      embedded
                    />
                  </div>
                </motion.div>
              ) : (
                currentRound?.choices && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="h-full min-h-0"
                  >
                    <div
                      className="bg-white p-2 border h-full min-h-0 flex flex-col"
                      style={{ borderColor: mergedColors.primary, borderLeftWidth: "6px" }}
                    >
                      <div className="flex items-center mb-6 flex-shrink-0">
                        <div
                          className="w-12 h-12 flex items-center justify-center mr-4"
                          style={{
                            backgroundColor: mergedColors.primary,
                            border: `2px solid ${mergedColors.primaryDark}`,
                          }}
                        >
                          <FaLightbulb style={{ color: mergedColors.text }} />
                        </div>
                        <div className="flex-1">
                          <h3 className="text-xl font-bold" style={{ color: mergedColors.text }}>
                            Decision Point
                          </h3>
                          <p className="text-sm" style={{ color: mergedColors.textLight }}>
                            Choose your next action carefully
                          </p>
                        </div>
                        {timerActive && timeRemaining !== null && (
                          <div
                            className="flex items-center gap-2 px-3 py-2 rounded-lg font-bold text-lg"
                            style={{
                              backgroundColor: timeRemaining < 10 ? '#FEE2E2' : timeRemaining < 20 ? '#FEF3C7' : '#F0F9FF',
                              color: timeRemaining < 10 ? '#EF4444' : timeRemaining < 20 ? '#F59E0B' : '#3B82F6',
                              animation: timeRemaining < 10 ? 'pulse 1s infinite' : 'none',
                            }}
                          >
                            <FaClock />
                            <span>{Math.floor(timeRemaining / 60)}:{String(timeRemaining % 60).padStart(2, '0')}</span>
                          </div>
                        )}
                      </div>
                      <div className="flex-1 min-h-0">
                        {INPUT_WIDGETS[currentRound?.input_type] ? (
                          (() => {
                            const InputWidget = INPUT_WIDGETS[currentRound.input_type];
                            return (
                              <InputWidget
                                config={currentRound}
                                onSubmit={handleChoiceSubmit}
                                disabled={showOutcome || isSubmitting || isTransitioning}
                                colors={mergedColors}
                              />
                            );
                          })()
                        ) : (
                          <ChoiceSelector
                            choices={currentRound.choices || []}
                            onSelect={trackAndSelect}
                            onSubmit={handleChoiceSubmit}
                            selectedChoice={selectedChoice}
                            disabled={showOutcome || isSubmitting || isTransitioning}
                            colors={mergedColors}
                            density="dense"
                            coachHints={currentRound?.coach_hints}
                            gameState={gameState}
                            inputType={currentRound?.input_type || 'multiple_choice'}
                            freeTextValue={freeTextValue}
                            onFreeTextChange={setFreeTextValue}
                            rubricHints={currentRound?.evaluation_rubric ? Object.values(currentRound.evaluation_rubric) : null}
                            minFreeTextLength={currentRound?.min_response_length || 20}
                            freeTextPlaceholder={currentRound?.free_text_placeholder || 'Share your thoughts and reasoning here...'}
                          />
                        )}
                        {/* Fix 7: FreetextInput for hybrid rounds with free_text_prompt */}
                        {(currentRound?.input_type === 'hybrid' || currentRound?.free_text_prompt) && !showOutcome && (
                          <FreetextInput
                            prompt={currentRound.free_text_prompt}
                            onSubmit={(text) => {
                              if (selectedChoice) {
                                handleChoiceSubmit(selectedChoice, { freeText: text });
                              } else {
                                handleChoiceSubmit(null, { freeText: text });
                              }
                            }}
                            disabled={isSubmitting || isTransitioning}
                          />
                        )}
                      </div>
                    </div>
                  </motion.div>
                )
              )}
            </div>

            <aside
              className="gp-stats h-full min-h-0 p-1"
              aria-label="Game statistics"
            >
              <div
                className="gp-statsCard  bg-white"
                style={{ borderColor: mergedColors.primaryLight }}
              >
                <div className="gp-statsHeader" style={{ color: mergedColors.text }}>
                  Stats
                </div>
                <div className="gp-compactStatsGrid">
                  {keyStats.map((stat) => (
                    <div
                      key={stat.key}
                      className="gp-compactStat"
                      style={{ borderColor: mergedColors.primaryLight }}
                      title={stat.label}
                    >
                      <div className="gp-compactStatTop">
                        <span className="gp-compactStatIcon" style={{ color: stat.color }}>
                          {stat.icon}
                        </span>
                        <span className="gp-compactStatLabel" style={{ color: mergedColors.textLight }}>
                          {stat.label}
                        </span>
                      </div>
                      <div className="gp-compactStatValue" style={{ color: mergedColors.text }}>
                        {getResourceValue(stat.key)}
                      </div>
                      {(() => {
                        const val = getResourceValue(stat.key);
                        if (typeof val !== 'number') return null;
                        const sentiment = getResourceSentiment(val, stat.max || 100);
                        return (
                          <span style={{ fontSize: '9px', color: sentiment.color, fontWeight: 600, display: 'block', textAlign: 'center' }}>
                            {sentiment.emoji} {sentiment.label}
                          </span>
                        );
                      })()}
                    </div>
                  ))}
                </div>

                <div className="gp-statsDash">
                  <LiveSkillRadar gameState={gameState} compact={true} />
                  {/* ResourceDashboard + PsychologyPanel hidden to reduce clutter — radar + stat grid are sufficient */}
                  {false && <ResourceDashboard
                    state={gameState}
                    game={currentGame}
                    compact={true}
                    colors={mergedColors}
                    density="dense"
                  />}
                  {false && <PsychologyPanel
                    gameState={gameState}
                    gameConfig={currentGame}
                    compact={true}
                  />}
                </div>
              </div>
            </aside>
          </div>
        </div>
      </div>

      {/* Reflection Modal (before outcome reveal) */}
      <AnimatePresence>
        {showReflectionModal && (
          <ReflectionModal
            prompt={showReflectionModal}
            onSubmit={handleReflectionSubmit}
          />
        )}
      </AnimatePresence>

      {/* Consequence Scene (after choice, before takeaway) */}
      <AnimatePresence>
        {showConsequenceScene && (
          <ConsequenceScene
            scene={showConsequenceScene}
            onDismiss={handleConsequenceSceneDismiss}
          />
        )}
      </AnimatePresence>

      {/* Halftime Checkpoint */}
      <AnimatePresence>
        {showHalftimeCheckpoint && (
          <HalftimeCheckpoint
            checkpoint={showHalftimeCheckpoint}
            onContinue={handleHalftimeContinue}
          />
        )}
      </AnimatePresence>

      {/* Teachable Moment Card (negative outcome education) */}
      <AnimatePresence>
        {teachableMoment && (
          <TeachableMomentCard
            moment={teachableMoment}
            onDismiss={handleTeachableMomentDismiss}
          />
        )}
      </AnimatePresence>

      {/* Post-Choice Reflection (after pivotal decisions) */}
      <AnimatePresence>
        {postChoiceReflection && (
          <PostChoiceReflection
            reflection={postChoiceReflection}
            onSubmit={handlePostChoiceReflectionSubmit}
          />
        )}
      </AnimatePresence>

      {/* Skill feedback: show ChoiceExplanation if deltas available (richer), else SkillCallout toast.
          Avoids rendering both for the same skill event. */}
      {choiceDeltas ? (
        <ChoiceExplanation
          skillCallout={skillCallout}
          deltas={choiceDeltas}
          skillExplanations={choiceSkillExplanation}
          onDismiss={() => {
            setChoiceDeltas(null);
            setChoiceSkillExplanation(null);
            setSkillCallout(null);
          }}
        />
      ) : (
        <SkillCallout
          callout={skillCallout}
          onDismiss={() => setSkillCallout(null)}
        />
      )}

      {/* Fix 7: LLMFeedbackCard — AI Coach feedback for free-text / hybrid responses */}
      <LLMFeedbackCard
        feedback={llmFeedback}
        onDismiss={() => setLLMFeedback(null)}
      />

      {/* Fix 1: SkillIntroCard — one-time skill introduction overlay */}
      <SkillIntroCard
        skill={currentSkillIntro}
        onDismiss={() => {
          setSkillIntroQueue(prev => {
            const remaining = prev.slice(1);
            if (remaining.length > 0) {
              setTimeout(() => setCurrentSkillIntro(remaining[0]), 300);
            } else {
              setCurrentSkillIntro(null);
            }
            return remaining;
          });
        }}
      />

      {/* D1: ReflectionPrompt — "Why did you make that choice?" modal.
          reflectionPrompt may be a string (legacy) or { text, kantian } (Kantian mode). */}
      <ReflectionPrompt
        prompt={typeof reflectionPrompt === 'string' ? reflectionPrompt : reflectionPrompt?.text}
        kantian={typeof reflectionPrompt === 'object' ? !!reflectionPrompt?.kantian : false}
        onSubmit={() => setReflectionPrompt(null)}
        onSkip={() => setReflectionPrompt(null)}
      />

      {/* D3: AchievementUnlock — mid-play achievement celebration */}
      <AchievementUnlock
        achievement={achievementUnlock}
        onDismiss={() => setAchievementUnlock(null)}
      />

      {/* Narrative bridge — brief transition scene after a choice */}
      {narrativeBridge && (
        <NarrativeBridge
          deltas={narrativeBridge.deltas}
          choiceLabel={narrativeBridge.choiceLabel}
          onDismiss={() => {
            const savedOutcome = narrativeBridge.outcomeObj;
            setNarrativeBridge(null);
            showNextPostChoiceStep(savedOutcome);
          }}
        />
      )}

      {/* MARKET SHOCK — exogenous event injected by backend simulation_config.market_shocks */}
      <AnimatePresence>
        {marketShock && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
            onClick={() => setMarketShock(null)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 30 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 30 }}
              onClick={(e) => e.stopPropagation()}
              className="rounded-2xl p-6 shadow-2xl border-2 max-w-md w-full"
              style={{ background: '#FFF8EA', borderColor: '#E0B96A' }}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full"
                      style={{ background: '#FF7B4D', color: 'white' }}>
                  ⚡ MARKET SHOCK
                </span>
                <button onClick={() => setMarketShock(null)} className="text-xs opacity-60 hover:opacity-100">✕</button>
              </div>
              <h3 className="text-lg font-extrabold mb-2" style={{ color: '#5B3A1E' }}>
                {marketShock.title}
              </h3>
              <p className="text-sm mb-4" style={{ color: '#5B3A1E' }}>
                {marketShock.body}
              </p>
              {Array.isArray(marketShock.response_choices) && marketShock.response_choices.length > 0 && (
                <div className="space-y-2">
                  {marketShock.response_choices.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => setMarketShock(null)}
                      className="w-full text-left px-3 py-2 rounded-lg border text-sm hover:scale-[1.01] transition"
                      style={{ borderColor: '#E0B96A', background: 'white', color: '#3A2A0F' }}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              )}
              <div className="text-[10px] mt-3 opacity-60 italic" style={{ color: '#5B3A1E' }}>
                You didn't ask for this. The world doesn't wait.
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ORG FRICTION — bottom-right toast for culture rot / span-of-control / comms overhead */}
      <AnimatePresence>
        {orgFriction && (
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-6 right-6 z-40 max-w-sm rounded-2xl shadow-2xl border-2 p-4"
            style={{ background: '#FFF1E6', borderColor: '#D88B5A', color: '#5B3A1E' }}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-extrabold uppercase tracking-wider"
                    style={{ color: '#D88B5A' }}>
                ⚠ Scaling friction
              </span>
              <button onClick={() => setOrgFriction(null)} className="text-xs opacity-60 hover:opacity-100">✕</button>
            </div>
            <h4 className="text-sm font-extrabold mb-1">{orgFriction.title}</h4>
            <p className="text-xs leading-relaxed">{orgFriction.body}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Fix 3: Round Timer — shown during core/mastery phases with timer_seconds */}
      {timerSeconds && !gameEnded && !pendingCheckpoint && (
        <RoundTimer
          seconds={timerSeconds}
          onExpire={handleTimerExpire}
          paused={!!showOutcome || !!pendingCheckpoint || !!showConsequenceScene}
        />
      )}

      {/* Fix 4: Checkpoint Quiz — knowledge gate between rounds */}
      <AnimatePresence>
        {pendingCheckpoint && (
          <CheckpointQuiz
            checkpoint={pendingCheckpoint}
            runId={runId}
            onPass={handleCheckpointPass}
          />
        )}
      </AnimatePresence>

      {/* Round takeaway modal */}
      <div aria-live="polite" aria-atomic="true">
        <RoundTakeawayModal
          isOpen={showOutcome}
          onClose={handleCloseOutcome}
          onContinue={handleNextRound}
          outcome={outcomeData}
          takeaway={takeawayData}
          choices={outcomeData?._roundChoices || currentRound?.choices}
          coachingMoment={outcomeData?.coaching_moment || currentRound?.coaching_moment}
        />
      </div>

      {/* Achievement popups */}
      <AnimatePresence>
        {achievements.map((achievement, index) => (
          <AchievementPopup
            key={achievement.id}
            achievement={achievement}
            onClose={() => setAchievements((prev) => prev.filter((a) => a.id !== achievement.id))}
            delay={index * 500}
          />
        ))}
      </AnimatePresence>

      <AnimatePresence>
  {(isSubmitting || isTransitioning) && (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-white/70 backdrop-blur-sm"
    >
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
        className="text-5xl"
        style={{ color: mergedColors.primary }}
      >
        <FaGamepad />
      </motion.div>
    </motion.div>
  )}
</AnimatePresence>

      {/* Error recovery overlay — shown mid-game when an API call fails */}
      <AnimatePresence>
        {error && currentGame && lastFailedAction && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white text-gray-900 rounded-2xl shadow-xl max-w-sm w-full p-6 text-center"
            >
              <div className="text-4xl mb-3">
                <FaGamepad style={{ color: mergedColors.error, margin: '0 auto' }} />
              </div>
              <h3 className="text-lg font-bold mb-2" style={{ color: mergedColors.text }}>
                Something went wrong
              </h3>
              <p className="text-sm mb-5" style={{ color: mergedColors.textLight }}>
                Don't worry — your progress is safe. You can retry or go back to the game list.
              </p>
              <div className="flex gap-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={retryLastAction}
                  className="flex-1 py-2.5 rounded-xl font-bold text-sm"
                  style={{ backgroundColor: mergedColors.primary, color: mergedColors.text }}
                >
                  <FaRedo className="inline mr-2" />
                  Retry
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => { clearError(); navigate('/games'); }}
                  className="flex-1 py-2.5 rounded-xl font-medium text-sm border border-gray-200 text-gray-600"
                >
                  <FaHome className="inline mr-2" />
                  Exit Game
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* "Did You Know?" fact card toast between rounds */}
      <AnimatePresence>
        {factCard && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            style={{
              position: 'fixed', bottom: '80px', left: '50%', transform: 'translateX(-50%)',
              padding: '12px 20px', paddingRight: '36px', background: '#1E293B', color: 'white', borderRadius: '12px',
              fontSize: '12px', maxWidth: '340px', textAlign: 'center', zIndex: 60,
              boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
            }}
          >
            <button onClick={() => setFactCard(null)}
              style={{ position: 'absolute', top: '6px', right: '8px', background: 'none', border: 'none', color: '#94A3B8', fontSize: '16px', cursor: 'pointer', lineHeight: 1 }}>
              &times;
            </button>
            <span style={{ fontWeight: 700, color: '#FFD166' }}>Did you know? {factCard.term}:</span>{' '}
            <span>{factCard.definition}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Glossary Panel */}
      {(currentGame?.glossary_terms?.length > 0 || currentGame?.glossary?.length > 0) && (
        <GlossaryPanel
          terms={currentGame.glossary_terms || currentGame.glossary || []}
          colors={mergedColors}
        />
      )}

      {/* Floating Help Button */}
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setShowHelpModal(true)}
        className="fixed bottom-20 right-4 z-40 w-10 h-10 rounded-full shadow-lg flex items-center justify-center border"
        style={{
          backgroundColor: '#118AB2',
          borderColor: '#0E7490',
          color: 'white',
        }}
        title="How to Play"
      >
        <FaQuestionCircle className="text-sm" />
      </motion.button>

      {/* Help Modal */}
      <AnimatePresence>
        {showHelpModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
            onClick={() => setShowHelpModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white text-gray-900 rounded-xl shadow-2xl max-w-md w-full max-h-[80vh] overflow-y-auto"
            >
              <div className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <FaQuestionCircle className="text-blue-500" />
                    <h3 className="font-bold text-base" style={{ color: mergedColors.text }}>
                      How to Play
                    </h3>
                  </div>
                  <button
                    onClick={() => setShowHelpModal(false)}
                    className="p-1.5 hover:bg-gray-100 rounded-lg"
                  >
                    <FaTimes className="text-gray-400 text-sm" />
                  </button>
                </div>

                <p className="text-sm mb-3" style={{ color: mergedColors.textLight }}>
                  {currentGame?.description || 'Complete each round by making strategic decisions.'}
                </p>

                <div className="space-y-2 mb-4">
                  {(Array.isArray(currentGame?.how_to_play)
                    ? currentGame.how_to_play
                    : currentGame?.how_to_play?.steps || [
                      'Read the scenario and understand the situation',
                      'Choose your action from the options below',
                      'Watch how your choice affects your resources',
                      'Manage resources wisely to get the best score',
                    ]
                  ).map((step, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-600 text-[10px] font-bold flex items-center justify-center mt-0.5">
                        {i + 1}
                      </span>
                      <span className="text-xs text-gray-700 leading-relaxed">{step}</span>
                    </div>
                  ))}
                </div>

                {/* Resource explanations */}
                {keyStats.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Your Resources
                    </h4>
                    <div className="grid grid-cols-2 gap-1.5">
                      {keyStats.map((stat) => (
                        <div key={stat.key} className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-gray-50">
                          <span style={{ color: stat.color }}>{stat.icon}</span>
                          <span className="text-xs text-gray-700 capitalize">{stat.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mento AI Coach — simulation (rounds) games only */}
      {gameStarted && !gameEnded && currentRound && (
        <MentoAgent
          runId={runId}
          currentRound={currentRound}
          choices={currentRound?.choices}
          onChoiceSelect={handleChoiceSubmit}
          showOutcome={showOutcome}
          showReflection={showReflectionModal}
          defaultAiMode={aiVoiceMode}
        />
      )}
    </div>
    </>
  );
};

export default GamePlayPage;
