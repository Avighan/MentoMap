import { useState, Suspense, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { GiMoneyStack, GiPuzzle, GiLemon } from "react-icons/gi";
import {
  FaGamepad,
  FaPlayCircle,
  FaChevronRight,
  FaUsers,
  FaStar,
  FaLemon,
  FaHeart,
  FaRocket,
  FaPuzzlePiece,
  FaGraduationCap,
  FaShieldAlt,
  FaBrain,
  FaClock,
  FaArrowRight,
  FaHandSparkles,
} from "react-icons/fa";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import NotificationCenter from "../components/ui/NotificationCenter";
import RobotGuide from "../assets/robo.png";
import { listGames } from "../api/games";
import { getWeeklyChallenge, getStudentAssignments, joinCohortByCode } from "../api/teacher";
import { getStudentSchedule } from "../api/curriculum";
import { getProfile, getGoalRecommendations } from "../api/profile";
import StreakWidget from "../components/home/StreakWidget";
import ReviewQueueWidget from "../components/home/ReviewQueueWidget";
import { Swiper, SwiperSlide } from "swiper/react";
import {
  Autoplay,
  Navigation,
  Pagination,
  EffectCards,
  EffectCoverflow,
} from "swiper/modules";
import "swiper/css";
import "swiper/css/navigation";
import "swiper/css/pagination";
import "swiper/css/effect-cards";
import "swiper/css/effect-coverflow";
import { useAuth } from "../contexts/AuthContext";
import DailyRewardsBanner from "../components/ui/DailyRewardsBanner";
import WellbeingConsentModal, { shouldShowWellbeingConsent } from "../components/WellbeingConsentModal";
import apiClient from '../api/client';

const colors = {
  primary: "#FFD166",
  primaryLight: "#FFE8A5",
  primaryDark: "#FFC145",
  background: "#FFFDF7",
  card: "#FFFFFF",
  text: "#2D3047",
  textLight: "#6D7286",
  dark: "#1A1F2C",

  business: "#4ECDC4",
  social: "#FF6B6B",
  puzzle: "#9B5DE5",
  adventure: "#118AB2",
  strategy: "#06D6A0",
  lemon: "#FFD93D",
  secondary: "#FF8E8E",
};

const themeConfig = {
  business: {
    color: colors.business,
    icon: <GiMoneyStack />,
    bgGradient: "linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%)",
  },
  social: {
    color: colors.social,
    icon: <FaHeart />,
    bgGradient: "linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%)",
  },
  puzzle: {
    color: colors.puzzle,
    icon: <GiPuzzle />,
    bgGradient: "linear-gradient(135deg, #9B5DE5 0%, #7C4DFF 100%)",
  },
  adventure: {
    color: colors.adventure,
    icon: <FaRocket />,
    bgGradient: "linear-gradient(135deg, #118AB2 0%, #06BEE1 100%)",
  },
  strategy: {
    color: colors.strategy,
    icon: <FaBrain />,
    bgGradient: "linear-gradient(135deg, #06D6A0 0%, #00CF8A 100%)",
  },
  lemon: {
    color: colors.lemon,
    icon: <GiLemon />,
    bgGradient: "linear-gradient(135deg, #FFD93D 0%, #FFB347 100%)",
  },
  default: {
    color: colors.primary,
    icon: <FaGamepad />,
    bgGradient: "linear-gradient(135deg, #FFD166 0%, #FFB347 100%)",
  },
};

const HomePage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [activeGame, setActiveGame] = useState(0);
  const [games, setGames] = useState([]);
  const [activeSlide, setActiveSlide] = useState(0);

  const [loadingGames, setLoadingGames] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();

  const [featuredGames, setFeaturedGames] = useState([]);
  const [weeklyChallenge, setWeeklyChallenge] = useState(null);
  const [studentAssignments, setStudentAssignments] = useState([]);
  const [streakDays, setStreakDays] = useState(0);
  const [dueReviews, setDueReviews] = useState([]);
  const [learningPathProgress, setLearningPathProgress] = useState(null);
  const [hasBaseline, setHasBaseline] = useState(true); // optimistic: assume done
  const [baselineGameId, setBaselineGameId] = useState(null);
  const [goalRecs, setGoalRecs] = useState([]);
  const [cohortMatches, setCohortMatches] = useState([]);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [joinCode, setJoinCode] = useState('');
  const [joinLoading, setJoinLoading] = useState(false);
  const [joinMsg, setJoinMsg] = useState({ text: '', ok: true });
  const [showWellbeingModal, setShowWellbeingModal] = useState(false);
  const [wellbeingProfile, setWellbeingProfile] = useState(null);
  const [showEscapismWarning, setShowEscapismWarning] = useState(false);
  const [curriculumSchedule, setCurriculumSchedule] = useState([]);

  const getGameConfig = (game) => {
    const theme = game.theme?.toLowerCase();
    return themeConfig[theme] || themeConfig.default;
  };

  const handleJoinClass = async () => {
    const code = joinCode.trim().toUpperCase();
    if (!code || code.length < 4) {
      setJoinMsg({ text: 'Enter a valid class code', ok: false });
      return;
    }
    setJoinLoading(true);
    setJoinMsg({ text: '', ok: true });
    try {
      const res = await joinCohortByCode(code);
      setJoinMsg({ text: `✓ Joined "${res.cohort_name}"!`, ok: true });
      setJoinCode('');
      setTimeout(() => { setShowJoinModal(false); setJoinMsg({ text: '', ok: true }); }, 2000);
    } catch (err) {
      setJoinMsg({ text: err?.response?.data?.error || 'Invalid code — check with your teacher', ok: false });
    } finally {
      setJoinLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    const loadGames = async () => {
      try {
        const res = await listGames();
        if (controller.signal.aborted) return;
        const rawGames = res.games || [];
        setGames(rawGames);
        // Reverse funnel — surface kids/teen content first, exec games behind a deliberate CTA.
        const _ageRank = (g) => {
          const ab = (g.age_band || g.age_category || "").toLowerCase();
          if (ab === "kids") return 0;
          if (ab === "teen" || ab === "teens") return 1;
          if (ab === "young_adult") return 2;
          if (ab === "adult" || ab === "adults") return 3;
          return 2; // unknown bands sit in the middle
        };
        const _sorted = [...rawGames].sort((a, b) => {
          const ra = _ageRank(a), rb = _ageRank(b);
          if (ra !== rb) return ra - rb;
          // Within the same band, premium-tier (deeper) sims come last so kids see fun first.
          const ta = a.tier === "premium" ? 1 : 0;
          const tb = b.tier === "premium" ? 1 : 0;
          return ta - tb;
        });
        setFeaturedGames(_sorted.map((game) => {
          const config = getGameConfig(game);
          return {
            id: game.game_id,
            title: game.title,
            category: game.theme || "Adventure",
            description: game.description || game.theme || "Interactive learning game",
            icon: config.icon,
            duration: game.duration_minutes || null,
            learningConcept: game.learning_concept || null,
            color: config.color,
            bgGradient: config.bgGradient,
            tier: game.tier || "standard",
            ageBand: game.age_band || game.age_category || null,
            domain: game.domain || null,
            ageGroup:
              game.age_category === "kids"
                ? "8+"
                : game.age_category === "teens"
                  ? "13+"
                  : game.age_category === "adults"
                    ? "18+"
                    : "All ages",
            isNew: game.featured || false,
          };
        }));
      } catch (err) {
        if (err.name !== 'AbortError') console.error("Failed to load games", err);
      } finally {
        if (!controller.signal.aborted) setLoadingGames(false);
      }
    };
    loadGames();
    return () => controller.abort();
  }, []);

  // Load weekly challenge + assignments + streak for logged-in users
  useEffect(() => {
    if (!user) return;
    getWeeklyChallenge().then(res => setWeeklyChallenge(res.challenge)).catch(() => {});
    getStudentAssignments().then(res => setStudentAssignments(res.assignments || [])).catch(() => {});
    getStudentSchedule().then(res => {
      const all = res.schedule || res.assignments || [];
      const active = all.filter(a => a.status === 'active' || a.status === 'overdue');
      setCurriculumSchedule(active);
    }).catch(() => {});
    getProfile().then(p => {
      setStreakDays(p.streak_days || 0);
      setHasBaseline(!!p.baseline_completed_at);
      setWellbeingProfile(p);
      if (shouldShowWellbeingConsent(p)) setShowWellbeingModal(true);
    }).catch(() => {});
    // Fetch the correct baseline game ID for this user's age/persona
    apiClient.get('/api/profile/baseline-game').then(r => {
      if (r.data?.game_id) setBaselineGameId(r.data.game_id);
    }).catch(() => {});
    // Load spaced repetition due reviews
    import('../api/client').then(m => m.default.get('/api/spaced-repetition/due')).then(r => setDueReviews(r.data.reviews || [])).catch(() => {});
    // Load first in-progress learning path
    import('../api/client').then(m => m.default.get('/api/learning-paths')).then(r => {
      const paths = r.data.paths || [];
      if (paths.length > 0) {
        import('../api/client').then(m => m.default.get('/api/learning-paths/' + paths[0].id + '/progress').then(prog => {
          setLearningPathProgress({ path: paths[0], progress: prog.data });
        }).catch(() => {}));
      }
    }).catch(() => {});
    // Load goal-based recommendations
    getGoalRecommendations().then(r => setGoalRecs(r.recommendations || [])).catch(() => {});
    // Load cohort matches
    import('../api/client').then(m => m.default.get('/api/student/cohort-matches')).then(r => {
      setCohortMatches(r.data.matches || []);
    }).catch(() => {});
    // Escapism risk check — student only, once per 24h
    if (user?.role === 'student') {
      const dismissed = localStorage.getItem('escapism_warning_dismissed');
      if (!dismissed || (Date.now() - parseInt(dismissed)) > 86400000) {
        getProfile().then(p => {
          const gad7 = p.wellbeing_responses?.gad7_score;
          const wb = p.wellbeing_responses?.overall_score;
          const history = p.recent_activity || [];
          const weekAgo = Date.now() - 7 * 86400000;
          const recentCount = history.filter(r => {
            try { return new Date(r.timestamp || r.completed_at || 0).getTime() >= weekAgo; } catch { return false; }
          }).length;
          const highDistress = (gad7 != null && gad7 >= 10) || (wb != null && wb < 40);
          if (highDistress && recentCount >= 10) setShowEscapismWarning(true);
        }).catch(() => {});
      }
    }
  }, [user]);

  const handleStartGame = (gameId = null) => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      navigate(gameId ? `/play/${gameId}` : "/games");
    }, 600);
  };

  return (
    <div
      className="min-h-screen overflow-x-hidden"
      style={{ backgroundColor: colors.background }}
    >
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-white focus:p-2 focus:rounded">
        Skip to main content
      </a>
      <header className="sticky top-0 z-40 bg-white/85 backdrop-blur-sm border-b shadow-sm">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-3 cursor-pointer"
              onClick={() => navigate("/")}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center shadow-md"
                style={{ backgroundColor: colors.primary }}
              >
                <FaGamepad className="text-white text-lg" />
              </div>
              <div>
                <h1
                  className="text-2xl font-bold tracking-tight"
                  style={{ color: colors.text }}
                >
                  Mento<span style={{ color: colors.primaryDark }}>Games</span>
                </h1>
                <p className="text-xs" style={{ color: colors.textLight }}>
                  Learn through play
                </p>
              </div>
            </motion.div>
            {/* Desktop nav */}
            <div className="hidden sm:flex items-center gap-2">
              {user ? (
                <>
                  {user.role !== 'parent' && streakDays >= 2 && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-50 border border-orange-200 text-orange-700 text-sm font-bold">
                      🔥 {streakDays} day streak
                    </div>
                  )}
                  <NotificationCenter />
                  <button
                    onClick={() => navigate("/profile")}
                    className="px-3 py-1.5 rounded-lg text-sm font-medium"
                    style={{ color: colors.text, background: '#F3F4F6' }}
                  >
                    Profile
                  </button>
                  {user.role === 'parent' && (
                    <button
                      onClick={() => navigate("/parent-dashboard")}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium"
                      style={{ color: colors.text, background: '#FFF7ED', border: '1px solid #FDE68A' }}
                    >
                      Parent Dashboard
                    </button>
                  )}
                  {(user.role === 'admin' || user.role === 'trainer' || user.role === 'school_admin') && (
                    <button
                      onClick={() => navigate("/admin")}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium"
                      style={{ color: colors.text, background: '#F3F4F6' }}
                    >
                      {user.role === 'trainer' ? 'Game Builder' : 'Admin Panel'}
                    </button>
                  )}
                  {user.role === 'teacher' && (
                    <button
                      onClick={() => navigate("/teacher")}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium"
                      style={{ color: colors.text, background: '#F3F4F6' }}
                    >
                      My Classes
                    </button>
                  )}
                  {user.role === 'hr' && (
                    <button
                      onClick={() => navigate("/assessment-manager")}
                      className="px-3 py-1.5 rounded-lg text-sm font-medium"
                      style={{ color: colors.text, background: '#F3F4F6' }}
                    >
                      Assessment Manager
                    </button>
                  )}
                  {(!user.role || user.role === 'student') && (
                    <>
                      <button
                        onClick={() => navigate("/skill-portfolio")}
                        className="px-3 py-1.5 rounded-lg text-sm font-medium"
                        style={{ color: colors.text, background: '#F3F4F6' }}
                      >
                        Skills
                      </button>
                      <button
                        onClick={() => navigate("/my-analytics")}
                        className="px-3 py-1.5 rounded-lg text-sm font-medium"
                        style={{ color: colors.text, background: '#F3F4F6' }}
                      >
                        Analytics
                      </button>
                      <button
                        onClick={() => navigate("/wallet")}
                        className="px-3 py-1.5 rounded-lg text-sm font-medium"
                        style={{ color: colors.text, background: '#F3F4F6' }}
                      >
                        Wallet
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => { logout(); navigate("/"); }}
                    className="px-3 py-1.5 rounded-lg text-sm font-medium bg-yellow-400 text-white"
                  >
                    Logout ({user.username})
                  </button>
                </>
              ) : (
                <button
                  onClick={() => navigate("/login")}
                  className="px-3 py-1 bg-yellow-400 text-white rounded"
                >
                  Login
                </button>
              )}
            </div>
            {/* Mobile hamburger */}
            <div className="sm:hidden">
              <button
                onClick={() => setMobileMenuOpen(prev => !prev)}
                className="p-2 rounded-lg"
                style={{ color: colors.text }}
                aria-label="Toggle menu"
              >
                <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  {mobileMenuOpen ? (
                    <><line x1="6" y1="6" x2="18" y2="18" /><line x1="6" y1="18" x2="18" y2="6" /></>
                  ) : (
                    <><line x1="4" y1="7" x2="20" y2="7" /><line x1="4" y1="12" x2="20" y2="12" /><line x1="4" y1="17" x2="20" y2="17" /></>
                  )}
                </svg>
              </button>
            </div>

            {user?.role !== 'parent' && (
              <motion.button
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate("/games")}
                className="hidden sm:inline-flex px-5 py-2.5 rounded-lg font-medium text-white shadow-lg"
                style={{ backgroundColor: colors.primaryDark }}
              >
                All Games ({featuredGames.length}+)
              </motion.button>
            )}
          </div>
          {/* Mobile dropdown menu */}
          {mobileMenuOpen && (
            <div className="sm:hidden border-t mt-2 pt-3 pb-1 flex flex-col gap-2">
              {user ? (
                <>
                  {user.role === 'parent' ? (
                    <>
                      <button onClick={() => { navigate("/parent-dashboard"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#FFF7ED' }}>Parent Dashboard</button>
                      <button onClick={() => { navigate("/profile"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Profile</button>
                      <button onClick={() => { navigate("/settings"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Settings</button>
                    </>
                  ) : (user.role === 'admin' || user.role === 'trainer' || user.role === 'school_admin') ? (
                    <>
                      <button onClick={() => { navigate("/admin"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>{user.role === 'trainer' ? 'Game Builder' : 'Admin Panel'}</button>
                      <button onClick={() => { navigate("/games"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Browse Games</button>
                      <button onClick={() => { navigate("/profile"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Profile</button>
                      <button onClick={() => { navigate("/settings"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Settings</button>
                    </>
                  ) : user.role === 'teacher' ? (
                    <>
                      <button onClick={() => { navigate("/teacher"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>My Classes</button>
                      <button onClick={() => { navigate("/games"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Browse Games</button>
                      <button onClick={() => { navigate("/profile"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Profile</button>
                      <button onClick={() => { navigate("/settings"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Settings</button>
                    </>
                  ) : user.role === 'hr' ? (
                    <>
                      <button onClick={() => { navigate("/assessment-manager"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Assessment Manager</button>
                      <button onClick={() => { navigate("/profile"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Profile</button>
                      <button onClick={() => { navigate("/settings"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Settings</button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => { navigate("/games"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>All Games</button>
                      <button onClick={() => { navigate("/profile"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Profile</button>
                      <button onClick={() => { navigate("/wallet"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Wallet</button>
                      <button onClick={() => { navigate("/leaderboard"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Leaderboard</button>
                      <button onClick={() => { navigate("/skill-portfolio"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Skill Portfolio</button>
                      <button onClick={() => { navigate("/learning-paths"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Learning Paths</button>
                      <button onClick={() => { navigate("/my-analytics"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>My Analytics</button>
                      <button onClick={() => { navigate("/settings"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium" style={{ color: colors.text, background: '#F3F4F6' }}>Settings</button>
                    </>
                  )}
                  <button onClick={() => { logout(); setMobileMenuOpen(false); navigate("/"); }} className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium bg-yellow-400 text-white">Logout ({user.username})</button>
                </>
              ) : (
                <button onClick={() => { navigate("/login"); setMobileMenuOpen(false); }} className="w-full text-left px-3 py-2 bg-yellow-400 text-white rounded-lg text-sm font-medium">Login / Register</button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Weekly Challenge Banner — student/teacher only */}
      {weeklyChallenge && (user?.role === 'student' || user?.role === 'teacher' || !user?.role) && (
        <div className="bg-gradient-to-r from-yellow-400 to-orange-400 text-white px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚡</span>
            <p className="text-sm font-bold">This Week's Challenge: <span className="underline">{weeklyChallenge.title || weeklyChallenge.game_id}</span></p>
          </div>
          <button
            onClick={() => navigate(`/play/${weeklyChallenge.game_id}`)}
            className="bg-white/20 hover:bg-white/30 text-white font-bold text-xs px-4 py-1.5 rounded-full transition-all flex-shrink-0"
          >
            Play Now →
          </button>
        </div>
      )}

      {/* Assignments Banner — student only */}
      {studentAssignments.length > 0 && (user?.role === 'student' || !user?.role) && (
        <div className="border-b px-4 py-2 flex items-center gap-2" style={{ backgroundColor: '#FFF9EB', borderColor: '#FFD166' }}>
          <span className="text-sm">📋</span>
          <p className="text-sm font-medium" style={{ color: '#2D3047' }}>
            You have <strong>{studentAssignments.length} assignment{studentAssignments.length > 1 ? 's' : ''}</strong> from your teacher.{' '}
            <button onClick={() => navigate('/play/' + studentAssignments[0].game_id)} className="underline font-bold" style={{ color: '#FFC145' }}>
              Start first
            </button>
          </p>
        </div>
      )}

      {/* Streak at risk banner — student only */}
      {user && (user.role === 'student' || !user.role) && streakDays >= 2 && (() => {
        const today = new Date().toISOString().split('T')[0];
        return (
          <div className="bg-orange-50 border-b border-orange-200 px-4 py-2 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span>🔥</span>
              <p className="text-sm text-orange-800 font-medium">
                {t('home.streak_risk_sub', { days: streakDays })}
              </p>
            </div>
            <button onClick={() => navigate('/games')} className="text-xs font-bold text-orange-700 underline flex-shrink-0">Play Now</button>
          </div>
        );
      })()}

      {/* Due reviews banner */}
      {user && dueReviews.length > 0 && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>🔄</span>
            <p className="text-sm text-amber-700 font-medium">
              {t('home.reviews_due', { count: dueReviews.length })}
            </p>
          </div>
          <button onClick={() => navigate('/spaced-repetition')} className="text-xs font-bold text-amber-700 underline flex-shrink-0">Review Now</button>
        </div>
      )}

      {/* Escapism risk — gentle wellbeing check-in */}
      {showEscapismWarning && (
        <div className="bg-violet-50 border-b border-violet-200 px-4 py-3 flex items-start gap-3">
          <span className="text-lg mt-0.5 flex-shrink-0">💜</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-violet-800">A gentle check-in</p>
            <p className="text-xs text-violet-700 mt-0.5">You've been spending a lot of time here — and that's okay. Remember to take breaks and talk to someone if you're feeling overwhelmed.</p>
            <div className="flex gap-3 mt-2">
              <a href="https://www.childline.in/" target="_blank" rel="noopener noreferrer" className="text-xs text-violet-600 underline">Talk to someone</a>
              <button onClick={() => { setShowEscapismWarning(false); localStorage.setItem('escapism_warning_dismissed', String(Date.now())); }} className="text-xs text-violet-400 hover:text-violet-600">Dismiss</button>
            </div>
          </div>
        </div>
      )}

      {/* Baseline assessment prompt — disabled, baseline is opt-in only */}
      {false && user && (user.role === 'student' || !user.role) && !hasBaseline && (
        <div className="bg-violet-50 border-b border-violet-200 px-4 py-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>📋</span>
            <p className="text-sm text-violet-800 font-medium">Take the 5-min Soft Skills Baseline — unlock your personalised score profile</p>
          </div>
          <button
            onClick={() => navigate(baselineGameId ? `/play/${baselineGameId}` : '/onboarding')}
            className="text-xs font-bold text-violet-700 underline flex-shrink-0 whitespace-nowrap"
          >
            Start Now →
          </button>
        </div>
      )}

      {/* Role-specific dashboard shortcut banner */}
      {user?.role === 'teacher' && (
        <div className="bg-emerald-50 border-b border-emerald-100 px-4 py-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>🏫</span>
            <p className="text-sm text-emerald-800 font-medium">Teacher dashboard — manage classes, gradebook & assignments</p>
          </div>
          <button onClick={() => navigate('/teacher')} className="text-xs font-bold text-emerald-700 underline flex-shrink-0 whitespace-nowrap">Open Dashboard →</button>
        </div>
      )}
      {user?.role === 'parent' && (
        <div className="bg-orange-50 border-b border-orange-100 px-4 py-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>👨‍👩‍👧</span>
            <p className="text-sm text-orange-800 font-medium">Monitor your child's learning progress and skill development</p>
          </div>
          <button onClick={() => navigate('/parent-dashboard')} className="text-xs font-bold text-orange-700 underline flex-shrink-0 whitespace-nowrap">Parent Dashboard →</button>
        </div>
      )}
      {(user?.role === 'admin' || user?.role === 'trainer' || user?.role === 'school_admin') && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>{user.role === 'trainer' ? '🔨' : user.role === 'school_admin' ? '🏢' : '⚙️'}</span>
            <p className="text-sm text-amber-800 font-medium">
              {user.role === 'trainer' ? 'Game Builder & AI Design Studio' : user.role === 'school_admin' ? 'School Admin Panel — manage your org' : 'Admin Panel'}
            </p>
          </div>
          <button onClick={() => navigate('/admin')} className="text-xs font-bold text-amber-700 underline flex-shrink-0 whitespace-nowrap">
            {user.role === 'trainer' ? 'Open Builder →' : 'Admin Panel →'}
          </button>
        </div>
      )}
      {(user?.role === 'admin' || user?.role === 'trainer') && (
        <div className="bg-blue-50 border-b border-blue-100 px-4 py-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>📊</span>
            <p className="text-sm text-blue-800 font-medium">Assessment Manager — create candidate batches, share links, track results</p>
          </div>
          <button onClick={() => navigate('/assessment-manager')} className="text-xs font-bold text-blue-700 underline flex-shrink-0 whitespace-nowrap">Open →</button>
        </div>
      )}
      {user?.role === 'hr' && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>💼</span>
            <p className="text-sm text-amber-800 font-medium">Assessment Manager — create candidate batches, share game links, benchmark results</p>
          </div>
          <button onClick={() => navigate('/assessment-manager')} className="text-xs font-bold text-amber-700 underline flex-shrink-0 whitespace-nowrap">Open →</button>
        </div>
      )}

      {/* Daily Rewards Banner — students and teachers */}
      {user && user.role !== 'parent' && <DailyRewardsBanner />}

      {/* Streak + Review widgets — card-style, non-parent users only */}
      {user && user.role !== 'parent' && (
        <div style={{ padding: '10px 16px' }}>
          <div className="container mx-auto" style={{ maxWidth: 900 }}>
            <div className="flex flex-col gap-3">
              <StreakWidget />
              <ReviewQueueWidget />
            </div>
          </div>
        </div>
      )}

      {/* Learning Modules entry-point — students */}
      {(user?.role === 'student' || !user?.role) && (
        <div style={{ padding: '14px 16px' }}>
          <div className="container mx-auto" style={{ maxWidth: 900 }}>
            <button
              onClick={() => navigate('/modules')}
              style={{
                width: '100%',
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                color: 'white',
                border: 'none',
                borderRadius: 16,
                padding: '14px 18px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                boxShadow: '0 4px 14px rgba(99,102,241,0.35)',
              }}
            >
              <div style={{ fontSize: 32 }}>🚀</div>
              <div style={{ textAlign: 'left', flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 15 }}>
                  Mento Entrepreneurship Workshop
                </div>
                <div style={{ fontSize: 12, opacity: 0.9 }}>
                  4-week guided journey · worksheets, games &amp; a final pitch simulation
                </div>
              </div>
              <FaChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Curriculum Schedule — active/overdue assigned games for students */}
      {curriculumSchedule.length > 0 && (user?.role === 'student' || !user?.role) && (
        <div style={{ background: '#F0FFF4', borderBottom: '1px solid #C8E6C9', padding: '12px 16px' }}>
          <div className="container mx-auto" style={{ maxWidth: 900 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 16 }}>📅</span>
                <span style={{ fontWeight: 700, fontSize: 14, color: '#2D3047' }}>
                  My Schedule — {curriculumSchedule.length} game{curriculumSchedule.length !== 1 ? 's' : ''} to play
                </span>
              </div>
              <button onClick={() => navigate('/my-schedule')}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#1565C0', fontWeight: 600, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
                View Calendar <FaChevronRight size={10} />
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
              {curriculumSchedule.slice(0, 5).map(a => {
                const isOverdue = a.status === 'overdue';
                const dueDate = a.due_date ? new Date(a.due_date + 'T00:00:00') : null;
                const today = new Date(); today.setHours(0,0,0,0);
                const daysLeft = dueDate ? Math.ceil((dueDate - today) / 86400000) : null;
                return (
                  <button key={a.game_id} onClick={() => navigate(`/play/${a.game_id}`)}
                    style={{
                      flex: '0 0 auto', background: '#fff', borderRadius: 10,
                      padding: '8px 14px', cursor: 'pointer', textAlign: 'left',
                      border: isOverdue ? '2px solid #F44336' : '1px solid #E0E0E0',
                      boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
                      minWidth: 160, maxWidth: 200,
                    }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#2D3047', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {a.game_title || a.title || a.game_id}
                    </div>
                    <div style={{ fontSize: 11, marginTop: 3, color: isOverdue ? '#F44336' : daysLeft <= 3 ? '#FF9800' : '#4CAF50', fontWeight: 600 }}>
                      {isOverdue ? 'Overdue!' : daysLeft <= 0 ? 'Due today!' : `${daysLeft}d left`}
                    </div>
                    <div style={{ fontSize: 10, marginTop: 2, color: '#9E9E9E' }}>
                      Due {dueDate ? dueDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—'}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <section id="main-content" className="pt-8 pb-12 md:pt-12 md:pb-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-5 gap-8 lg:gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="lg:col-span-3"
            >
              {user?.role === 'parent' ? (
                <>
                  <div className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium mb-6 shadow-sm" style={{ backgroundColor: '#FFF7ED', color: colors.text }}>
                    <span className="mr-2">👨‍👩‍👧</span> Your child's learning journey
                  </div>
                  <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
                    <span style={{ color: colors.text }}>Welcome,</span>
                    <br />
                    <span style={{ color: colors.primaryDark }}>Track & Support</span>
                  </h1>
                  <p className="text-lg md:text-xl mb-8 leading-relaxed" style={{ color: colors.textLight, maxWidth: "90%" }}>
                    See your child's skill scores, completed games, and learning streaks — all in one place.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-4 mb-10">
                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => navigate('/parent-dashboard')}
                      className="px-8 py-4 rounded-xl font-bold text-lg flex items-center justify-center shadow-xl"
                      style={{ backgroundColor: colors.primary, color: colors.text }}
                    >
                      <FaUsers className="mr-3 text-xl" />
                      Go to Parent Dashboard
                      <FaChevronRight className="ml-3" />
                    </motion.button>
                  </div>
                </>
              ) : user?.role === 'admin' || user?.role === 'trainer' || user?.role === 'school_admin' ? (
                <>
                  <div className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium mb-6 shadow-sm" style={{ backgroundColor: colors.primaryLight, color: colors.text }}>
                    <FaStar className="mr-2" /> {user.role === 'trainer' ? 'Game Designer Tools' : user.role === 'school_admin' ? 'School Management' : 'Platform Admin'}
                  </div>
                  <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
                    <span style={{ color: colors.text }}>Welcome back,</span>
                    <br />
                    <span style={{ color: colors.primaryDark }}>{user.username}</span>
                  </h1>
                  <p className="text-lg md:text-xl mb-8 leading-relaxed" style={{ color: colors.textLight, maxWidth: "90%" }}>
                    {user.role === 'trainer' ? 'Build, test, and publish AI-powered games. Your design tools are ready.' : user.role === 'school_admin' ? 'Manage your school cohorts, users, and analytics.' : 'Manage the platform, games, users, and analytics.'}
                  </p>
                  <div className="flex flex-col sm:flex-row gap-4 mb-10">
                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => navigate('/admin')}
                      className="px-8 py-4 rounded-xl font-bold text-lg flex items-center justify-center shadow-xl"
                      style={{ backgroundColor: colors.primary, color: colors.text }}
                    >
                      <FaRocket className="mr-3 text-xl" />
                      {user.role === 'trainer' ? 'Open Game Builder' : 'Open Admin Panel'}
                      <FaChevronRight className="ml-3" />
                    </motion.button>
                  </div>
                </>
              ) : user?.role === 'teacher' ? (
                <>
                  <div className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium mb-6 shadow-sm" style={{ backgroundColor: colors.primaryLight, color: colors.text }}>
                    <FaGraduationCap className="mr-2" /> Teacher Dashboard
                  </div>
                  <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
                    <span style={{ color: colors.text }}>Welcome back,</span>
                    <br />
                    <span style={{ color: colors.primaryDark }}>{user.username}</span>
                  </h1>
                  <p className="text-lg md:text-xl mb-8 leading-relaxed" style={{ color: colors.textLight, maxWidth: "90%" }}>
                    Manage your classes, track student progress, assign games, and view gradebooks.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-4 mb-10">
                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => navigate('/teacher')}
                      className="px-8 py-4 rounded-xl font-bold text-lg flex items-center justify-center shadow-xl"
                      style={{ backgroundColor: colors.primary, color: colors.text }}
                    >
                      <FaGraduationCap className="mr-3 text-xl" />
                      Go to Teacher Dashboard
                      <FaChevronRight className="ml-3" />
                    </motion.button>
                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => navigate('/games')}
                      className="px-8 py-4 rounded-xl font-bold text-lg flex items-center justify-center shadow-xl border-2"
                      style={{ borderColor: colors.primaryDark, color: colors.primaryDark, background: 'white' }}
                    >
                      <FaGamepad className="mr-3 text-xl" />
                      Browse Games
                    </motion.button>
                  </div>
                </>
              ) : user?.role === 'hr' ? (
                <>
                  <div className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium mb-6 shadow-sm" style={{ backgroundColor: '#EEF2FF', color: '#4338CA' }}>
                    💼 HR Assessment Manager
                  </div>
                  <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
                    <span style={{ color: colors.text }}>Welcome back,</span>
                    <br />
                    <span style={{ color: '#4F46E5' }}>{user.username}</span>
                  </h1>
                  <p className="text-lg md:text-xl mb-8 leading-relaxed" style={{ color: colors.textLight, maxWidth: "90%" }}>
                    Create assessment batches, share game links with candidates, and benchmark performance across your team.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-4 mb-10">
                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => navigate('/assessment-manager')}
                      className="px-8 py-4 rounded-xl font-bold text-lg flex items-center justify-center shadow-xl"
                      style={{ backgroundColor: '#4F46E5', color: 'white' }}
                    >
                      📊 Open Assessment Manager
                      <FaChevronRight className="ml-3" />
                    </motion.button>
                  </div>
                </>
              ) : (
                <>
                  <div
                    className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium mb-6 shadow-sm"
                    style={{
                      backgroundColor: colors.primaryLight,
                      color: colors.text,
                    }}
                  >
                    <FaStar className="mr-2" /> New adventures added weekly!
                  </div>

                  <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
                    <span style={{ color: colors.text }}>Hey Explorer,</span>
                    <br />
                    <span style={{ color: colors.primaryDark }}>
                      Ready to Play?
                    </span>
                  </h1>

                  <p
                    className="text-lg md:text-xl mb-8 leading-relaxed"
                    style={{ color: colors.textLight, maxWidth: "90%" }}
                  >
                    Dive into games where you run businesses, solve puzzles, and
                    tell stories. Your next adventure is one click away!
                  </p>

                  <div className="flex flex-col sm:flex-row gap-4 mb-10">
                    <motion.button
                      whileHover={{
                        scale: 1.03,
                        boxShadow: `0 10px 25px ${colors.primary}50`,
                      }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => handleStartGame()}
                      disabled={isLoading}
                      className="px-8 py-4 rounded-xl font-bold text-lg flex items-center justify-center shadow-xl relative overflow-hidden"
                      style={{
                        backgroundColor: colors.primary,
                        color: colors.text,
                      }}
                    >
                      {isLoading ? (
                        <LoadingSpinner size="small" color="currentColor" />
                      ) : (
                        <>
                          <FaPlayCircle className="mr-3 text-xl" />
                          Start Your First Game
                          <FaChevronRight className="ml-3" />
                        </>
                      )}
                    </motion.button>
                  </div>
                </>
              )}

              <div className="flex flex-wrap gap-6">
                {[
                  { icon: <FaGamepad />, value: String(games.length || 12), label: "Unique Games" },
                  { icon: <FaUsers />, value: "4", label: "Game Types" },
                  { icon: <FaStar />, value: "Free", label: "To Play" },
                ].map((stat, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + idx * 0.1 }}
                    className="flex items-center space-x-3"
                  >
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center shadow"
                      style={{ backgroundColor: colors.card }}
                    >
                      <div style={{ color: colors.primaryDark }}>
                        {stat.icon}
                      </div>
                    </div>
                    <div>
                      <div
                        className="text-2xl font-bold"
                        style={{ color: colors.text }}
                      >
                        {stat.value}
                      </div>
                      <div
                        className="text-sm"
                        style={{ color: colors.textLight }}
                      >
                        {stat.label}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {user?.role !== 'parent' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="lg:col-span-2"
            >
              <div
                className="relative bg-gradient-to-br from-white to-blue-50 rounded-2xl p-6 shadow-2xl border"
                style={{ borderColor: colors.primaryLight }}
              >
                <div className="relative h-64 mb-6 rounded-xl overflow-hidden bg-gradient-to-b from-blue-100/30 to-yellow-100/20">
                  <motion.img
                    src={RobotGuide}
                    alt="Mento Robot Guide"
                    className="absolute right-0 bottom-0 w-48 md:w-56 lg:w-64 drop-shadow-xl"
                    animate={{
                      y: [0, -10, 0],
                      scaleX: -1,
                    }}
                  />

                  <motion.div
                    initial={{ opacity: 0, scale: 0.8, y: 10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{ delay: 0.8 }}
                    className="absolute top-4 left-4 bg-white p-3 rounded-2xl rounded-bl-none shadow-lg max-w-[70%]"
                  >
                    <p
                      className="text-sm font-medium"
                      style={{ color: colors.text }}
                    >
                      Hi! I'm{" "}
                      <span
                        className="font-bold"
                        style={{ color: colors.primaryDark }}
                      >
                        Mento
                      </span>
                      . Pick a game to start!
                    </p>
                    <div className="absolute -bottom-2 left-0 w-4 h-4 bg-white transform rotate-45" />
                  </motion.div>
                </div>
                <div>
                  <h3
                    className="text-xl font-bold mb-4 flex items-center"
                    style={{ color: colors.text }}
                  >
                    <FaGamepad
                      className="mr-2"
                      style={{ color: colors.primaryDark }}
                    />
                    What do you want to try?
                  </h3>
                  <div className="space-y-3">
                    {featuredGames.slice(0, 3).map((game, idx) => (
                      <motion.div
                        key={game.id}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.5 + idx * 0.1 }}
                        whileHover={{
                          x: 5,
                          backgroundColor: colors.primaryLight + "30",
                        }}
                        className={`p-3 rounded-xl cursor-pointer border transition-all ${activeGame === idx ? "ring-2" : ""}`}
                        style={{
                          borderColor:
                            activeGame === idx
                              ? game.color
                              : colors.primaryLight,
                          backgroundColor: colors.card,
                        }}
                        onClick={() => {
                          setActiveGame(idx);
                          handleStartGame(game.id);
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            <div
                              className="w-10 h-10 rounded-lg flex items-center justify-center mr-3 shadow-sm"
                              style={{ backgroundColor: game.color + "20" }}
                            >
                              <div style={{ color: game.color }}>
                                {game.icon}
                              </div>
                            </div>
                            <div>
                              <h4
                                className="font-bold text-sm"
                                style={{ color: colors.text }}
                              >
                                {game.title}
                              </h4>
                              <p
                                className="text-xs"
                                style={{ color: colors.textLight }}
                              >
                                {game.category}
                              </p>
                            </div>
                          </div>
                          <div
                            className="text-xs font-bold px-2 py-1 rounded-full"
                            style={{
                              backgroundColor: colors.primaryLight,
                              color: colors.text,
                            }}
                          >
                            {game.ageGroup}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => navigate("/games")}
                    className="w-full mt-4 py-3 rounded-lg font-medium flex items-center justify-center shadow"
                    style={{
                      backgroundColor: colors.card,
                      color: colors.text,
                      border: `2px dashed ${colors.primaryLight}`,
                    }}
                  >
                    See all {featuredGames.length}+ games
                    <FaChevronRight className="ml-2 text-sm" />
                  </motion.button>
                </div>
              </div>
            </motion.div>
            )}
          </div>
        </div>
      </section>
      {user?.role !== 'parent' && (
      <section
        className="py-12 md:py-16"
        style={{ backgroundColor: colors.card }}
      >
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-10"
          >
            <h2
              className="text-3xl md:text-4xl font-bold mb-4"
              style={{ color: colors.text }}
            >
              Popular{" "}
              <span style={{ color: colors.primaryDark }}>
                Learning Adventures
              </span>
            </h2>
            <p className="text-lg" style={{ color: colors.textLight }}>
              Each game builds real-world soft skills through play
            </p>
          </motion.div>
          <Swiper
            modules={[Autoplay, Navigation, Pagination, EffectCoverflow]}
            spaceBetween={30}
            slidesPerView={1}
            centeredSlides={true}
            loop={featuredGames.length > 3}
            speed={600}
            autoplay={{
              delay: 3000,
              disableOnInteraction: false,
              pauseOnMouseEnter: true,
            }}
            navigation={{
              nextEl: ".game-carousel-next",
              prevEl: ".game-carousel-prev",
              disabledClass: "opacity-30 cursor-not-allowed",
            }}
            pagination={{
              clickable: true,
              dynamicBullets: true,
              renderBullet: function (index, className) {
                return `<span class="${className}" style="background: ${colors.textLight}40"></span>`;
              },
            }}
            effect="coverflow"
            coverflowEffect={{
              rotate: 15,
              stretch: 0,
              depth: 80,
              modifier: 1,
              slideShadows: true,
              scale: 0.85,
            }}
            breakpoints={{
              640: {
                slidesPerView: 1.2,
                spaceBetween: 20,
                coverflowEffect: {
                  rotate: 20,
                  stretch: 0,
                  depth: 50,
                  modifier: 1,
                },
              },
              768: {
                slidesPerView: 2,
                spaceBetween: 25,
                coverflowEffect: {
                  rotate: 15,
                  stretch: 0,
                  depth: 60,
                  modifier: 1,
                },
              },
              1024: {
                slidesPerView: 2.5,
                spaceBetween: 30,
                coverflowEffect: {
                  rotate: 10,
                  stretch: 0,
                  depth: 40,
                  modifier: 1,
                },
              },
              1280: {
                slidesPerView: 3,
                spaceBetween: 35,
                coverflowEffect: {
                  rotate: 8,
                  stretch: 0,
                  depth: 30,
                  modifier: 1,
                },
              },
            }}
            onSlideChange={(swiper) => {
              setActiveSlide(swiper.realIndex);
            }}
            className="pb-16"
          >
            {featuredGames.map((game, index) => (
              <SwiperSlide key={game.id}>
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{
                    y: -20,
                    scale: 1.05,
                    transition: {
                      type: "spring",
                      stiffness: 300,
                      damping: 15,
                    },
                  }}
                  className="relative group cursor-pointer"
                >
                  <div className="bg-white rounded-3xl shadow-2xl overflow-hidden border-2 border-white/20 backdrop-blur-sm transform transition-all duration-300 hover:shadow-3xl">
                    <div
                      className="h-48 relative overflow-hidden"
                      style={{ background: game.bgGradient }}
                    >
                      <div className="absolute inset-0 opacity-20">
                        <div
                          className="absolute top-4 right-4 w-32 h-32 rounded-full bg-white/30 blur-xl animate-pulse"
                          style={{ animationDelay: `${index * 0.5}s` }}
                        ></div>
                        <div
                          className="absolute bottom-4 left-4 w-24 h-24 rounded-full bg-white/20 blur-xl animate-pulse"
                          style={{ animationDelay: `${index * 0.3}s` }}
                        ></div>
                      </div>
                      {game.isNew && (
                        <div className="absolute top-4 left-4 z-10">
                          <div className="flex items-center px-3 py-1.5 rounded-full bg-white/90 backdrop-blur-sm shadow-lg">
                            <FaHandSparkles className="text-yellow-500 mr-1.5 text-sm" />
                            <span
                              className="text-xs font-bold"
                              style={{ color: colors.dark }}
                            >
                              Featured
                            </span>
                          </div>
                        </div>
                      )}
                      {game.tier === "premium" && (
                        <div className="absolute top-4 right-4 z-10">
                          <div
                            className="flex items-center px-3 py-1.5 rounded-full shadow-lg"
                            style={{
                              background: "linear-gradient(135deg, #FFD700 0%, #FFA500 100%)",
                              color: "#3A2A0F",
                            }}
                          >
                            <span className="text-xs mr-1">👑</span>
                            <span className="text-[11px] font-extrabold tracking-wide">PREMIUM</span>
                          </div>
                        </div>
                      )}
                      <motion.div
                        className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
                        animate={{
                          y: [0, -5, 0],
                          rotate: [0, 5, -5, 0],
                        }}
                        transition={{
                          duration: 4,
                          repeat: Infinity,
                          ease: "easeInOut",
                        }}
                      >
                        <div className="w-20 h-20 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-2xl group-hover:scale-110 transition-transform duration-300">
                          <div className="text-4xl" style={{ color: "white" }}>
                            {game.icon}
                          </div>
                        </div>
                      </motion.div>

                      {/* Duration badge */}
                      <div className="absolute bottom-4 right-4">
                        <div className="flex items-center px-3 py-1.5 rounded-full bg-black/20 backdrop-blur-sm">
                          <FaClock className="text-white text-sm mr-1.5" />
                          <span className="text-xs font-bold text-white">
                            {game.duration ? `${game.duration} min` : 'Quick play'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Game Content */}
                    <div className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <h3
                            className="text-xl font-bold mb-2 line-clamp-1"
                            style={{ color: colors.text }}
                          >
                            {game.title}
                          </h3>
                          <div className="flex items-center space-x-3 mb-3">
                            <span
                              className="text-xs font-semibold px-3 py-1 rounded-full"
                              style={{
                                backgroundColor: game.color + "20",
                                color: game.color,
                              }}
                            >
                              {game.category}
                            </span>
                            <span
                              className="text-xs flex items-center"
                              style={{ color: colors.textLight }}
                            >
                              <FaClock className="mr-1" /> {game.duration}min
                            </span>
                          </div>
                          <p
                            className="text-sm line-clamp-2"
                            style={{ color: colors.textLight }}
                          >
                            {game.description}
                          </p>
                        </div>
                      </div>

                      {/* Learning concept & Age */}
                      <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center min-w-0 flex-1 mr-2">
                          {game.learningConcept ? (
                            <span className="text-xs text-gray-500 truncate flex items-center gap-1">
                              <FaBrain className="flex-shrink-0 text-amber-400" size={10} />
                              {game.learningConcept}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400 flex items-center gap-1">
                              <FaGraduationCap className="flex-shrink-0" size={10} />
                              Soft Skills
                            </span>
                          )}
                        </div>
                        <div
                          className="text-xs font-semibold px-3 py-1 rounded-full flex-shrink-0"
                          style={{
                            backgroundColor: colors.primaryLight,
                            color: colors.text,
                          }}
                        >
                          {game.ageGroup}
                        </div>
                      </div>

                      {/* Play Button */}
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handleStartGame(game.id)}
                        className="w-full py-3 rounded-xl font-bold flex items-center justify-center shadow-lg relative overflow-hidden group"
                        style={{
                          backgroundColor: game.color,
                          color: colors.text,
                        }}
                      >
                        <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-20 transition-opacity duration-300" />
                        <FaPlayCircle className="mr-3 text-lg" />
                        Play Now
                        <FaArrowRight className="ml-2 group-hover:translate-x-1 transition-transform" />
                      </motion.button>
                    </div>
                  </div>

                  {/* Glow Effect */}
                  <div className="absolute inset-0 rounded-3xl bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-500 -z-10"></div>
                </motion.div>
              </SwiperSlide>
            ))}
          </Swiper>

          {/* Progress Indicator */}
          <div className="flex justify-center items-center space-x-2 mt-8">
            {featuredGames
              .slice(0, Math.min(5, featuredGames.length))
              .map((_, index) => (
                <button
                  key={index}
                  onClick={() => {
                    const swiper = document.querySelector(".swiper")?.swiper;
                    if (swiper) {
                      swiper.slideToLoop(index);
                    }
                  }}
                  className={`w-3 h-3 rounded-full transition-all duration-300 ${activeSlide === index ? "w-8" : ""}`}
                  style={{
                    backgroundColor:
                      activeSlide === index
                        ? colors.primary
                        : colors.textLight + "40",
                  }}
                />
              ))}
          </div>
        </div>

        {/* View All Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mt-12"
        >
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate("/games")}
            className="px-8 py-4 rounded-xl font-bold text-lg border-2 shadow-xl flex items-center justify-center mx-auto group"
            style={{
              borderColor: colors.primary,
              color: colors.text,
              backgroundColor: colors.card,
            }}
          >
            <FaGamepad className="mr-3 group-hover:rotate-12 transition-transform" />
            Explore All {games.length} Games
            <FaHandSparkles className="ml-3 text-yellow-500" />
          </motion.button>
        </motion.div>
      </section>
      )}

      {/* Live AI Practice Sessions — student/teacher */}
      {user && user.role !== 'parent' && (
        <section className="py-8 bg-gradient-to-r from-amber-50 to-yellow-50">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xl font-bold text-gray-800">Live AI Practice</h3>
                <p className="text-sm text-gray-500">Real-time conversational skill sessions with AI</p>
              </div>
              <button onClick={() => navigate('/interview')} className="text-xs font-bold text-amber-600 underline">See all →</button>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2" style={{ scrollbarWidth: 'none' }}>
              {[
                { icon: '💼', label: 'Job Interview', path: '/interview', color: '#6366f1' },
                { icon: '⚖️', label: 'Debate', path: '/debate', color: '#8b5cf6' },
                { icon: '🤝', label: 'Negotiation', path: '/negotiation', color: '#06b6d4' },
                { icon: '👥', label: 'Group Discussion', path: '/gd', color: '#10b981' },
                { icon: '🎤', label: 'Pitch', path: '/pitch', color: '#f59e0b' },
                { icon: '🗣️', label: 'Public Speaking', path: '/public-speaking', color: '#ef4444' },
              ].map(({ icon, label, path, color }) => (
                <motion.button
                  key={path}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => navigate(path)}
                  className="flex-shrink-0 flex flex-col items-center gap-1.5 px-4 py-3 rounded-xl bg-white border shadow-sm min-w-[90px]"
                  style={{ borderColor: color + '30' }}
                >
                  <span className="text-2xl">{icon}</span>
                  <span className="text-[11px] font-semibold text-gray-700 text-center leading-tight">{label}</span>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full text-white" style={{ background: color }}>Live AI</span>
                </motion.button>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Learning Path Progress Widget — student/teacher only */}
      {user && learningPathProgress && user.role !== 'parent' && (
        <section className="py-6">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div
              className="rounded-2xl p-5 border cursor-pointer hover:shadow-md transition-all"
              style={{ background: 'linear-gradient(135deg, #E0F2FE 0%, #F0FDF4 100%)', borderColor: '#BAE6FD' }}
              onClick={() => navigate('/learning-paths')}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{learningPathProgress.path.icon || '🛤️'}</span>
                  <div>
                    <p className="font-bold text-gray-800 text-sm">{learningPathProgress.path.title}</p>
                    <p className="text-xs text-gray-500">Active Learning Path</p>
                  </div>
                </div>
                <span className="text-xs font-bold text-teal-700 bg-teal-50 px-2 py-1 rounded-full">
                  {learningPathProgress.progress?.progress_pct || 0}% done
                </span>
              </div>
              <div className="w-full bg-white/60 rounded-full h-2">
                <div
                  className="h-2 bg-teal-500 rounded-full transition-all"
                  style={{ width: `${learningPathProgress.progress?.progress_pct || 0}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-2">
                {learningPathProgress.progress?.completed_count || 0} / {learningPathProgress.progress?.total_games || learningPathProgress.path?.games?.length || 0} games completed →
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Goal-based recommendations — students only */}
      {user && goalRecs.length > 0 && (
        <section className="py-4">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-6">
              <h2 className="text-base font-bold text-gray-800 mb-3">🎯 Recommended for your goals</h2>
              <div className="flex gap-3 overflow-x-auto pb-1 -mx-1 px-1">
                {goalRecs.slice(0, 3).map((rec) => (
                  <motion.div
                    key={rec.game_id}
                    whileHover={{ y: -2 }}
                    className="flex-shrink-0 w-40 bg-white rounded-xl border border-gray-200 p-3 shadow-sm cursor-pointer"
                    onClick={() => navigate(`/play/${rec.game_id}`)}
                  >
                    <div className="text-2xl mb-1">{rec.icon || "🎮"}</div>
                    <p className="font-bold text-xs text-gray-800 line-clamp-2">{rec.title}</p>
                    {rec.target_dimensions?.length > 0 && (
                      <p className="text-[10px] text-amber-500 mt-1">{rec.target_dimensions[0]}</p>
                    )}
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Cohort matches — play with a classmate */}
      {user && cohortMatches.length > 0 && (
        <section className="py-4">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-6">
              <h2 className="text-base font-bold text-gray-800 mb-3">👥 Play with a Classmate</h2>
              <motion.div
                whileHover={{ y: -2 }}
                className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm cursor-pointer inline-flex items-center gap-3"
                onClick={() => navigate('/multiplayer')}
              >
                <div className="text-2xl">🎮</div>
                <div>
                  <p className="font-bold text-sm text-gray-800">{cohortMatches[0].name || 'Your Classmate'}</p>
                  <p className="text-xs text-amber-500">Challenge them to a game →</p>
                </div>
              </motion.div>
            </div>
          </div>
        </section>
      )}

      {/* Join a Class — students only */}
      {user && user.role === 'student' && (
        <section className="py-3">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
              whileHover={{ y: -1 }}
              className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between gap-4 cursor-pointer"
              onClick={() => setShowJoinModal(true)}
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">🏫</span>
                <div>
                  <p className="font-bold text-sm text-amber-800">Join a Class</p>
                  <p className="text-xs text-amber-500">Got a code from your teacher? Enter it here.</p>
                </div>
              </div>
              <span className="text-xs font-bold text-amber-600 bg-amber-100 px-3 py-1.5 rounded-full flex-shrink-0">Enter Code →</span>
            </motion.div>
          </div>
        </section>
      )}

      {/* Join Class Modal */}
      {showJoinModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" onClick={() => setShowJoinModal(false)}>
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="font-bold text-lg text-gray-800 mb-1">🏫 Join a Class</h3>
            <p className="text-xs text-gray-500 mb-4">Ask your teacher for the 6-character class code.</p>
            <input
              autoFocus
              value={joinCode}
              onChange={e => { setJoinCode(e.target.value.toUpperCase()); setJoinMsg({ text: '', ok: true }); }}
              onKeyDown={e => e.key === 'Enter' && handleJoinClass()}
              placeholder="e.g. ABC123"
              maxLength={8}
              className="w-full border rounded-xl px-4 py-3 text-center text-2xl font-mono font-bold tracking-widest focus:outline-none focus:ring-2 focus:ring-amber-300 mb-3"
              style={{ borderColor: joinMsg.ok ? '#E5E7EB' : '#EF4444' }}
            />
            {joinMsg.text && (
              <p className={`text-sm text-center mb-3 font-medium ${joinMsg.ok ? 'text-green-600' : 'text-red-500'}`}>{joinMsg.text}</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => { setShowJoinModal(false); setJoinCode(''); setJoinMsg({ text: '', ok: true }); }}
                className="flex-1 py-2.5 rounded-xl text-sm font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >Cancel</button>
              <button
                onClick={handleJoinClass}
                disabled={joinLoading}
                className="flex-1 py-2.5 rounded-xl text-sm font-bold text-gray-800 transition-colors disabled:opacity-60"
                style={{ backgroundColor: colors.primary }}
              >{joinLoading ? 'Joining...' : 'Join Class'}</button>
            </div>
          </motion.div>
        </div>
      )}

      <section className="py-12 md:py-16">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h2
                className="text-3xl md:text-4xl font-bold mb-8"
                style={{ color: colors.text }}
              >
                More Than{" "}
                <span style={{ color: colors.primaryDark }}>Just Games</span>
              </h2>

              <div className="space-y-6">
                {[
                  {
                    icon: <FaGraduationCap />,
                    title: "Real Skills",
                    desc: "Learn business, communication, and problem-solving.",
                  },
                  {
                    icon: <FaLemon />,
                    title: "Safe Environment",
                    desc: "No ads, no pressure. Just learning and fun.",
                  },
                  {
                    icon: <FaShieldAlt />,
                    title: "Designed for You",
                    desc: "Content made specifically for 8-15 year olds.",
                  },
                ].map((item, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: idx * 0.1 }}
                    className="flex items-start p-4 rounded-xl border border-gray-100 hover:shadow-md transition-shadow"
                    style={{ backgroundColor: colors.card }}
                  >
                    <div
                      className="w-12 h-12 rounded-lg flex items-center justify-center mr-4 shadow-sm"
                      style={{ backgroundColor: colors.primaryLight }}
                    >
                      <div style={{ color: colors.primaryDark }}>
                        {item.icon}
                      </div>
                    </div>
                    <div>
                      <h4
                        className="font-bold text-lg mb-1"
                        style={{ color: colors.text }}
                      >
                        {item.title}
                      </h4>
                      <p
                        className="text-sm"
                        style={{ color: colors.textLight }}
                      >
                        {item.desc}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="bg-gradient-to-br rounded-2xl p-8 shadow-xl"
              style={{
                background: `linear-gradient(135deg, ${colors.primaryLight} 0%, ${colors.secondary}20 100%)`,
              }}
            >
              <h3
                className="text-2xl font-bold mb-6"
                style={{ color: colors.text }}
              >
                Perfect for{" "}
                <span style={{ color: colors.primaryDark }}>
                  Your Age Group
                </span>
              </h3>

              <div className="space-y-4 mb-8">
                {[
                  {
                    range: "8-10 Years",
                    focus: "Simple business games, basic puzzles",
                  },
                  {
                    range: "11-13 Years",
                    focus: "Social stories, strategy challenges",
                  },
                  {
                    range: "14-15 Years",
                    focus: "Complex simulations, advanced logic",
                  },
                ].map((age, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-lg"
                    style={{ backgroundColor: "rgba(255, 255, 255, 0.7)" }}
                  >
                    <div
                      className="font-bold text-lg mb-1"
                      style={{ color: colors.text }}
                    >
                      {age.range}
                    </div>
                    <div
                      className="text-sm"
                      style={{ color: colors.textLight }}
                    >
                      {age.focus}
                    </div>
                  </div>
                ))}
              </div>

              <p className="text-sm italic" style={{ color: colors.textLight }}>
                All games adapt to your skill level, getting more challenging as
                you learn!
              </p>
            </motion.div>
          </div>
        </div>
      </section>
      <section
        className="py-16"
        style={{ backgroundColor: colors.primaryLight }}
      >
        <div className="max-w-4xl mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2
              className="text-4xl md:text-5xl font-bold mb-6"
              style={{ color: colors.text }}
            >
              Your Adventure{" "}
              <span style={{ color: colors.primaryDark }}>Awaits!</span>
            </h2>
            <p
              className="text-xl mb-10 max-w-2xl mx-auto"
              style={{ color: colors.textLight }}
            >
              No sign-up needed for your first game. Just click and play!
            </p>

            <div className="flex flex-col sm:flex-row gap-6 justify-center">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() =>
                  featuredGames[0] && handleStartGame(featuredGames[0].id)
                }
                className="px-10 py-5 rounded-xl font-bold text-xl shadow-2xl flex items-center justify-center"
                style={{
                  backgroundColor: colors.primary,
                  color: colors.text,
                }}
              >
                <FaPlayCircle className="mr-3 text-2xl" />
                Play Lemonade Empire (Free)
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate("/games")}
                className="px-10 py-5 rounded-xl font-bold text-xl shadow-xl border-2"
                style={{
                  borderColor: colors.primaryDark,
                  color: colors.text,
                  backgroundColor: colors.card,
                }}
              >
                Browse All Games
              </motion.button>
            </div>
          </motion.div>
        </div>
      </section>
      <footer
        className="py-8 border-t"
        style={{
          borderColor: colors.primaryLight,
          backgroundColor: colors.card,
        }}
      >
        <div className="container mx-auto px-4 text-center">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center justify-center md:justify-start space-x-3 mb-4 md:mb-0">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: colors.primary }}
              >
                <FaGamepad className="text-white text-sm" />
              </div>
              <span
                className="text-lg font-bold"
                style={{ color: colors.text }}
              >
                MentoGames
              </span>
            </div>
            <p className="text-sm" style={{ color: colors.textLight }}>
              Made for curious minds aged 8-15 • Play, Learn, Grow
            </p>
          </div>
        </div>
      </footer>

      {showWellbeingModal && (
        <WellbeingConsentModal
          profile={wellbeingProfile}
          onClose={() => setShowWellbeingModal(false)}
          onConsent={(status) => setWellbeingProfile(p => p ? { ...p, wellbeing_consent: status } : p)}
        />
      )}
    </div>
  );
};

export default HomePage;
