import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  FaStar,
  FaRedoAlt,
  FaHome,
  FaTrophy,
  FaBrain,
  FaFileAlt,
  FaCertificate,
  FaShareAlt,
  FaChartLine,
} from 'react-icons/fa';
import RobotGuide from '../../assets/robo.png';
import RichText from '../ui/RichText';
import MentoScoreBreakdown from './MentoScoreBreakdown';
import PsychometricProfile from './PsychometricProfile';
import LearningOutcomes from './LearningOutcomes';
import SkillRadarChart from './SkillRadarChart';
import DNACard from './DNACard';
import StarRating from './StarRating';
import PostGameQuiz from './PostGameQuiz';
import PostGameInsights from './PostGameInsights';
import CharacterCard from './CharacterCard';
import BrainVisualization from './BrainVisualization';
import { rateGame, getCertificate } from '../../api/games';
import { FaCoins } from 'react-icons/fa';
import MovieRecap from './MovieRecap';
import PostGameChoiceReview from './PostGameChoiceReview';
import ChallengeButton from './ChallengeButton';

const colors = {
  primary: '#FFD166',
  primaryLight: '#FFE8A5',
  primaryDark: '#FFC145',
  background: '#FFFDF7',
  card: '#FFFFFF',
  text: '#2D3047',
  textLight: '#6D7286',
  dark: '#1A1F2C',
  secondary: '#FF8E8E',
};

const GameOverScreen = ({ finalReport, onPlayAgain, onBackToMenu, runId, epilogueSlot = null }) => {
  const navigate = useNavigate();
  const [showSpeech, setShowSpeech] = useState(false);
  const [userRating, setUserRating] = useState(0);
  const [ratingFeedback, setRatingFeedback] = useState('');
  const [hasRated, setHasRated] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  const [showRecap, setShowRecap] = useState(true);
  const [showChoiceReview, setShowChoiceReview] = useState(true);

  const reportCore = finalReport?.report_core || finalReport || {};
  const narrative = finalReport?.narrative || {};
  const adaptive = finalReport?.adaptive || {};

  const score =
    reportCore?.final_score ??
    finalReport?.final_score ??
    finalReport?.score ??
    null;
  const hasScore = score !== null && score !== undefined;

  const psychologicalSummary =
    reportCore?.psychological_focus_summary ||
    finalReport?.psychological_focus_summary ||
    null;
  const psychologicalScore = psychologicalSummary?.psychological_score ?? null;
  const psychologicalSkills = psychologicalSummary?.skills || [];
  const badges = narrative?.badges || reportCore?.badges || finalReport?.badges || [];
  const summary =
    narrative?.kid_summary ||
    narrative?.summary ||
    finalReport?.summary ||
    finalReport?.report ||
    '';

  // Mento Score (from state endpoint, may be in finalReport)
  const mentoScore = finalReport?.mento_score || reportCore?.mento_score || null;

  // Wallet reward
  const walletReward = finalReport?.wallet_reward || null;

  // Psychometric data
  const finalState = reportCore?.final_state || {};
  const dimensionScores = finalState?.dimension_scores || {};
  const memoryTags = finalState?.memory_tags || [];

  // Learning data
  const learningOutcomes = finalState?.learning_outcomes || {};
  const nepTags = reportCore?.nep_tags_seen || [];

  // Behavioral analytics
  const behavioralIndicators = reportCore?.behavioral_indicators || null;
  const timingStats = reportCore?.timing_stats || null;

  const getRobotMessage = () => {
    if (score >= 90) return "\u{1F31F} Incredible! You're a superstar!";
    if (score >= 70) return "\u{1F389} Great job! You rocked it!";
    if (score >= 50) return "\u{1F44D} Good effort! Keep going!";
    return "\u{1F4AA} Nice try! Want to play again?";
  };

  useEffect(() => {
    const timer = setTimeout(() => setShowSpeech(true), 500);
    return () => clearTimeout(timer);
  }, []);

  const handlePlayAgain = () => {
    if (onPlayAgain) onPlayAgain();
    else navigate(0);
  };

  const handleBackToMenu = () => {
    if (onBackToMenu) onBackToMenu();
    else navigate('/');
  };

  const handleRateGame = async (rating) => {
    setUserRating(rating);
    try {
      await rateGame(runId, rating, ratingFeedback);
      setHasRated(true);
    } catch (err) {
      console.error('Failed to submit rating:', err);
      setHasRated(true); // Still show "thanks" to not block the UI
    }
  };

  // Movie Recap — cinematic text animation before showing results
  const choiceHistory = finalState?.choice_history || reportCore?.round_history || [];
  if (showRecap && choiceHistory.length > 0) {
    return (
      <MovieRecap
        choiceHistory={choiceHistory}
        dimensionScores={dimensionScores}
        gameTitle={reportCore?.game?.title || finalReport?.game_title}
        playerName={finalReport?.player_name || finalReport?.username}
        onComplete={() => setShowRecap(false)}
      />
    );
  }

  // Choice Replay — reflection layer between recap and final score
  if (showChoiceReview && choiceHistory.length > 0) {
    const hasTaggedChoices = choiceHistory.some(
      (c) => Array.isArray(c?.skill_tags) && c.skill_tags.length > 0
    );
    if (hasTaggedChoices) {
      return (
        <PostGameChoiceReview
          choiceHistory={choiceHistory}
          onComplete={() => setShowChoiceReview(false)}
        />
      );
    }
  }

  return (
    <div
      className="h-screen flex items-center justify-center p-2 sm:p-4"
      style={{ backgroundColor: colors.background }}
    >
      <div className="w-full max-w-7xl h-full flex items-center justify-center">
        <div className="grid lg:grid-cols-[30%_70%] gap-4 lg:gap-8 w-full h-full max-h-[calc(100vh-2rem)]">
          {/* Robot Column */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="relative flex items-center justify-center lg:justify-end"
          >
            <div className="relative w-48 h-48 lg:w-64 lg:h-64">
              <motion.img
                src={RobotGuide}
                alt="Mento Robot"
                className="w-full h-full object-contain drop-shadow-xl"
                style={{ transform: 'scaleX(-1)' }}
                animate={{ y: [0, -6, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              />
              {showSpeech && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8, y: 10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ type: 'spring', stiffness: 200, delay: 0.6 }}
                  className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-white px-4 py-2 rounded-2xl rounded-bl-none shadow-xl"
                >
                  <p className="text-xs sm:text-sm font-medium whitespace-nowrap" style={{ color: colors.text }}>
                    {getRobotMessage()}
                  </p>
                  <div className="absolute -bottom-2 left-4 w-4 h-4 bg-white transform rotate-45" />
                </motion.div>
              )}
            </div>
          </motion.div>

          {/* Results Card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="bg-white rounded-3xl shadow-xl border border-gray-100 overflow-hidden flex flex-col h-full max-h-full"
          >
            {/* Header - fixed */}
            <div className="px-4 sm:px-6 pt-6 pb-2 flex-shrink-0">
              <div className="flex items-center justify-between">
                <h1 className="text-xl sm:text-2xl font-bold" style={{ color: colors.text }}>
                  Game Complete
                </h1>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <FaTrophy className="text-yellow-500 text-sm" />
                    <span className="text-xs font-semibold" style={{ color: colors.textLight }}>
                      Score
                    </span>
                  </div>
                  {psychologicalScore !== null && (
                    <div className="flex items-center gap-1">
                      <FaBrain className="text-gray-500 text-sm" />
                      <span className="text-xs font-semibold" style={{ color: colors.textLight }}>
                        Psych
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Score Display - fixed */}
            <div className="px-4 sm:px-6 pb-4 flex-shrink-0">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-xl border border-gray-100 bg-gray-50/30 p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <FaTrophy className="text-yellow-500 text-xs" />
                    <div className="text-xs uppercase tracking-wider font-semibold" style={{ color: colors.textLight }}>
                      Final Score
                    </div>
                  </div>
                  <div className="flex items-baseline gap-2">
                    {hasScore ? (
                      <span className="text-4xl font-bold" style={{ color: colors.primaryDark }}>
                        {score}
                      </span>
                    ) : (
                      <span className="text-2xl opacity-40">Calculating…</span>
                    )}
                    <span className="text-xs" style={{ color: colors.textLight }}>
                      / 100
                    </span>
                  </div>
                  {hasScore && (
                    <div className="mt-2 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.primaryLight }}>
                      <div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, score))}%`, backgroundColor: colors.primaryDark }} />
                    </div>
                  )}
                </div>

                {psychologicalScore !== null && (
                  <div className="rounded-xl border border-gray-100 bg-gray-50/30 p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <FaBrain className="text-gray-500 text-xs" />
                      <div className="text-xs uppercase tracking-wider font-semibold" style={{ color: colors.textLight }}>
                        Psychological Score
                      </div>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-4xl font-bold" style={{ color: colors.text }}>
                        {psychologicalScore}
                      </span>
                      <span className="text-xs" style={{ color: colors.textLight }}>
                        / 100
                      </span>
                    </div>
                    <div className="mt-2 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.primaryLight }}>
                      <div
                        className="h-full"
                        style={{
                          width: `${Math.max(0, Math.min(100, Number(psychologicalScore)))}%`,
                          backgroundColor: colors.primary,
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Scrollable content area */}
            <div className="flex-1 overflow-y-auto px-4 sm:px-6 pb-4 space-y-4 min-h-0">
              {/* Mento Score Breakdown */}
              {mentoScore && (
                <div className="rounded-xl border border-gray-100 bg-gray-50/30 p-3">
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-3" style={{ color: colors.textLight }}>
                    Mento Score
                  </h2>
                  <MentoScoreBreakdown mentoScore={mentoScore} />
                </div>
              )}

              {/* Wallet Reward */}
              {walletReward && walletReward.coins_earned > 0 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.5 }}
                  className="rounded-xl border p-4 text-center"
                  style={{ backgroundColor: '#FFD16610', borderColor: '#FFD16630' }}
                >
                  <FaCoins className="text-yellow-400 text-2xl mx-auto mb-1" />
                  <p className="text-2xl font-bold" style={{ color: colors.text }}>
                    +{walletReward.coins_earned}
                  </p>
                  <p className="text-xs text-gray-500 mb-2">Mento Coins earned</p>
                  {walletReward.breakdown && walletReward.breakdown.length > 0 && (
                    <div className="flex flex-wrap justify-center gap-1.5">
                      {walletReward.breakdown.map((b, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-white border border-gray-100 text-gray-600">
                          +{b.amount} {b.reason}
                        </span>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}

              {/* Badges */}
              {badges.length > 0 && (
                <div>
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-3" style={{ color: colors.textLight }}>
                    Badges Earned
                  </h2>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {badges.map((badge, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.8 + index * 0.1 }}
                        className="flex flex-col items-center p-2 rounded-xl bg-gray-50 border border-gray-100"
                      >
                        <span className="text-2xl mb-1">{badge.icon || '🏅'}</span>
                        <span className="text-xs font-medium text-center truncate w-full" style={{ color: colors.text }}>
                          {badge.name || badge}
                        </span>
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* Skill Radar Chart */}
              {psychologicalSkills.length > 0 && (
                <div>
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-3" style={{ color: colors.textLight }}>
                    Skill Radar
                  </h2>
                  <div className="bg-gray-50/50 rounded-xl border border-gray-100 p-2">
                    <SkillRadarChart skills={psychologicalSkills} showInitialOverlay={true} size="md" />
                  </div>
                </div>
              )}

              {/* Brain Map */}
              {psychologicalSkills.length > 0 && (
                <div>
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-3" style={{ color: colors.textLight }}>
                    Brain Map
                  </h2>
                  <div className="bg-gray-50/50 rounded-xl border border-gray-100 p-3">
                    <BrainVisualization skills={psychologicalSkills} />
                  </div>
                </div>
              )}

              {/* Psychological Skills */}
              {psychologicalSkills.length > 0 && (
                <div>
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-3" style={{ color: colors.textLight }}>
                    Psychological Focus
                  </h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {psychologicalSkills.map((s) => {
                      const delta = Number(s.change || 0);
                      const isPositive = delta >= 0;
                      const finalVal = Number(s.final || 0);
                      const finalPct = Math.max(0, Math.min(100, finalVal));
                      return (
                        <div
                          key={s.id}
                          className="p-3 rounded-xl bg-gray-50 border border-gray-100"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="text-lg">{s.icon || '🧠'}</span>
                              <div className="min-w-0">
                                <div className="text-sm font-semibold truncate" style={{ color: colors.text }}>
                                  {s.name || s.id}
                                </div>
                                <div className="text-xs" style={{ color: colors.textLight }}>
                                  {s.focus_count || 0} rounds
                                </div>
                              </div>
                            </div>
                            <div
                              className="text-xs font-bold px-1.5 py-0.5 rounded-full"
                              style={{
                                backgroundColor: isPositive ? 'rgba(6, 214, 160, 0.12)' : 'rgba(239, 71, 111, 0.12)',
                                color: isPositive ? '#06D6A0' : '#EF476F',
                              }}
                            >
                              {isPositive ? '+' : ''}{delta}
                            </div>
                          </div>
                          <div className="mt-2">
                            <div className="flex items-center justify-between text-xs mb-1" style={{ color: colors.textLight }}>
                              <span>Final</span>
                              <span className="font-semibold" style={{ color: colors.text }}>
                                {finalVal}/100
                              </span>
                            </div>
                            <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.primaryLight }}>
                              <div
                                className="h-full"
                                style={{
                                  width: `${finalPct}%`,
                                  backgroundColor: colors.primary,
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Behavioral Insights */}
              {(behavioralIndicators || timingStats) && (
                <div className="bg-gray-50/50 rounded-xl p-3">
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-3" style={{ color: colors.textLight }}>
                    Behavioral Insights
                  </h2>
                  {behavioralIndicators && (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
                      {Object.entries(behavioralIndicators).map(([key, val]) => {
                        const pct = Math.round((typeof val === 'number' ? val : 0) * 100);
                        const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                        return (
                          <div key={key} className="p-2 rounded-lg bg-white border border-gray-100">
                            <div className="text-xs font-medium truncate" style={{ color: colors.text }}>{label}</div>
                            <div className="flex items-center gap-2 mt-1">
                              <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.primaryLight }}>
                                <div className="h-full rounded-full" style={{ width: `${Math.min(100, pct)}%`, backgroundColor: pct > 60 ? '#10B981' : pct > 30 ? colors.primary : '#F59E0B' }} />
                              </div>
                              <span className="text-xs font-semibold" style={{ color: colors.textLight }}>{pct}%</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {timingStats && (
                    <div className="flex flex-wrap gap-3 text-xs" style={{ color: colors.textLight }}>
                      {timingStats.mean_ms != null && (
                        <span>Avg decision: <strong style={{ color: colors.text }}>{(timingStats.mean_ms / 1000).toFixed(1)}s</strong></span>
                      )}
                      {timingStats.fast_decisions_count != null && (
                        <span>Fast decisions: <strong style={{ color: colors.text }}>{timingStats.fast_decisions_count}</strong></span>
                      )}
                      {timingStats.slow_decisions_count != null && (
                        <span>Deliberate decisions: <strong style={{ color: colors.text }}>{timingStats.slow_decisions_count}</strong></span>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Psychometric Profile */}
              {(Object.keys(dimensionScores).length > 0 || memoryTags.length > 0) && (
                <PsychometricProfile
                  dimensionScores={dimensionScores}
                  memoryTags={memoryTags}
                />
              )}

              {/* Soft Skill Insights (SkillDashboard, Skill Report, Mento Breakdown, Debrief) */}
              <PostGameInsights
                summary={{ ...(narrative || {}), meta_debrief: finalReport?.meta_debrief }}
                state={finalState}
                gameType={reportCore?.game?.game_type || 'rounds'}
                won={score >= 70}
                reportCore={reportCore}
                runId={runId}
                recommendations={adaptive?.recommended_next || []}
                mentoPercentile={reportCore?.mento_score?.percentile ?? null}
                uxExecutive={finalReport?.ux_executive || null}
                execActionsLog={finalReport?.exec_actions_log || []}
                currency={reportCore?.game?.llm_config?.currency || 'USD'}
                epilogueSlot={epilogueSlot}
              />

              {/* Learning Outcomes */}
              <LearningOutcomes
                learningOutcomes={learningOutcomes}
                nepTags={nepTags}
              />

              {/* Concept Mastery (Board Games) */}
              {reportCore?.concept_mastery && Object.keys(reportCore.concept_mastery).length > 0 && (
                <div className="bg-gray-50/50 rounded-xl p-3">
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-2" style={{ color: colors.textLight }}>
                    Concept Mastery
                  </h2>
                  <div className="space-y-2">
                    {Object.entries(reportCore.concept_mastery).map(([term, data]) => {
                      const pct = typeof data === 'object' ? (data.mastery_pct || 0) : (typeof data === 'number' ? data : 0);
                      const encounters = typeof data === 'object' ? (data.encounters || 0) : 0;
                      return (
                        <div key={term} className="flex items-center gap-3">
                          <span className="text-xs font-medium capitalize flex-shrink-0 w-28 truncate" style={{ color: colors.text }}>
                            {term.replace(/_/g, ' ')}
                          </span>
                          <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: colors.primaryLight }}>
                            <div className="h-full rounded-full" style={{ width: `${Math.min(100, pct)}%`, backgroundColor: pct >= 80 ? '#10B981' : pct >= 50 ? colors.primary : '#F59E0B' }} />
                          </div>
                          <span className="text-xs" style={{ color: colors.textLight }}>{Math.round(pct)}%</span>
                          {encounters > 0 && <span className="text-xs" style={{ color: colors.textLight }}>({encounters}x)</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Decision Journal (Board Games) */}
              {reportCore?.decision_journal && reportCore.decision_journal.length > 0 && (
                <div className="bg-gray-50/50 rounded-xl p-3">
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-2" style={{ color: colors.textLight }}>
                    Decision Journal
                  </h2>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {reportCore.decision_journal.map((entry, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs py-1 border-b border-gray-100">
                        <span className="text-gray-400 w-8 flex-shrink-0">T{entry.turn || idx + 1}</span>
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium flex-shrink-0 ${entry.type === 'boss' ? 'bg-purple-100 text-purple-700' : entry.type === 'shop' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                          {entry.type || 'event'}
                        </span>
                        <span className="flex-1 truncate" style={{ color: colors.text }}>{entry.choice || entry.choice_label || '-'}</span>
                        {entry.correct !== undefined && (
                          <span className={entry.correct ? 'text-green-500' : 'text-red-400'}>{entry.correct ? '✓' : '✗'}</span>
                        )}
                        {entry.skill_tags && entry.skill_tags.length > 0 && (
                          <span className="text-xs text-indigo-400">{entry.skill_tags[0]}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Board Learned Terms */}
              {reportCore?.board_learned_terms && reportCore.board_learned_terms.length > 0 && (
                <div className="bg-gray-50/50 rounded-xl p-3">
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-2" style={{ color: colors.textLight }}>
                    Terms Learned
                  </h2>
                  <div className="flex flex-wrap gap-1">
                    {reportCore.board_learned_terms.map((term, idx) => (
                      <span key={idx} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium">
                        {term}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Decision DNA Card */}
              {reportCore?.dna_card && (
                <DNACard
                  dnaCard={reportCore.dna_card}
                  gameTitle={reportCore?.game?.title || finalReport?.game_title}
                />
              )}

              {/* Character Card */}
              {Object.keys(dimensionScores).length > 0 && (
                <div style={{ margin: '16px 0' }}>
                  <CharacterCard
                    dimensionScores={dimensionScores}
                    gameTitle={reportCore?.game?.title || finalReport?.game_title}
                    playerName={finalReport?.player_name || finalReport?.username}
                    mentoScore={mentoScore?.score}
                  />
                </div>
              )}

              {/* Summary */}
              {summary && (
                <div className="bg-gray-50/50 rounded-xl p-3">
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-2" style={{ color: colors.textLight }}>
                    Summary
                  </h2>
                  <RichText className="text-xs leading-relaxed" style={{ color: colors.text }}>
                    {summary}
                  </RichText>
                </div>
              )}

              {/* Game Rating */}
              {runId && (
                <div className="bg-gray-50/50 rounded-xl p-4 text-center">
                  <h2 className="text-xs uppercase tracking-wider font-semibold mb-3" style={{ color: colors.textLight }}>
                    How was this game?
                  </h2>
                  <div style={{ display: 'flex', justifyContent: 'center' }}>
                    <StarRating
                      rating={userRating}
                      onRate={handleRateGame}
                      interactive={!hasRated}
                      size="lg"
                    />
                  </div>
                  {!hasRated && (
                    <textarea
                      value={ratingFeedback}
                      onChange={(e) => setRatingFeedback(e.target.value)}
                      placeholder="Any feedback? (optional)"
                      className="mt-3 w-full p-2 rounded-lg border border-gray-200 text-sm resize-none"
                      rows={2}
                      style={{ fontSize: 12 }}
                    />
                  )}
                  {hasRated && (
                    <p className="text-xs mt-2" style={{ color: '#06D6A0', fontWeight: 600 }}>
                      Thanks for rating!
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Friendly nudge to rate (does not block actions) */}
            {!hasRated && runId && (
              <div className="px-4 sm:px-6 pt-2 flex-shrink-0">
                <div className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium">
                  <FaStar className="text-amber-400" />
                  Tap the stars above to rate this game (optional)
                </div>
              </div>
            )}

            {/* Action Buttons - fixed */}
            <div className="px-4 sm:px-6 py-4 flex-shrink-0 flex flex-col sm:flex-row gap-2 border-t border-gray-100">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handlePlayAgain}
                className="flex-1 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center shadow-sm border"
                style={{
                  backgroundColor: colors.primary,
                  borderColor: colors.primaryDark,
                  color: colors.text,
                }}
              >
                <FaRedoAlt className="mr-2 text-xs" />
                Play Again
              </motion.button>
              {runId && (
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => navigate(`/report/${runId}`)}
                  className="flex-1 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center shadow-sm border"
                  style={{
                    borderColor: '#118AB2',
                    color: '#118AB2',
                    backgroundColor: 'white',
                  }}
                >
                  <FaFileAlt className="mr-2 text-xs" />
                  Report Card
                </motion.button>
              )}
              {runId && (
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setShowQuiz(true)}
                  className="flex-1 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center shadow-sm border"
                  style={{
                    borderColor: '#06D6A0',
                    color: '#06D6A0',
                    backgroundColor: 'white',
                  }}
                >
                  <FaBrain className="mr-2 text-xs" />
                  Take Quiz
                </motion.button>
              )}
              {runId && (
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={async () => {
                    try {
                      const html = await getCertificate(runId);
                      const blob = new Blob([html], { type: 'text/html' });
                      const url = URL.createObjectURL(blob);
                      const win = window.open(url, '_blank');
                      if (win) win.focus();
                    } catch (err) {
                      console.error('Certificate error:', err);
                    }
                  }}
                  className="flex-1 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center shadow-sm border"
                  style={{
                    borderColor: '#9B5DE5',
                    color: '#9B5DE5',
                    backgroundColor: 'white',
                  }}
                >
                  <FaCertificate className="mr-2 text-xs" />
                  Certificate
                </motion.button>
              )}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  const text = `I scored ${score} on ${finalReport?.game_title || 'a game'} on Mento! Can you beat my score?`;
                  if (navigator.share) {
                    navigator.share({ title: 'My Mento Score', text }).catch(() => {});
                  } else {
                    navigator.clipboard.writeText(text);
                    alert('Score copied to clipboard!');
                  }
                }}
                className="flex-1 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center shadow-sm border"
                style={{ borderColor: '#6366F1', color: '#6366F1', backgroundColor: 'white' }}
              >
                <FaShareAlt className="mr-2 text-xs" />
                Share
              </motion.button>
              {runId && <ChallengeButton runId={runId} />}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => navigate('/my-analytics')}
                className="flex-1 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center shadow-sm border"
                style={{ borderColor: '#3B82F6', color: '#3B82F6', backgroundColor: 'white' }}
              >
                <FaChartLine className="mr-2 text-xs" />
                My Analytics
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => navigate('/discover')}
                className="flex-1 py-2.5 rounded-xl font-bold text-sm flex items-center justify-center shadow-sm border-2"
                style={{
                  borderColor: colors.primary,
                  color: colors.text,
                  backgroundColor: 'white',
                }}
              >
                <FaHome className="mr-2 text-xs" />
                Go Home
              </motion.button>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Quiz Modal */}
      {showQuiz && <PostGameQuiz runId={runId} onClose={() => setShowQuiz(false)} />}
    </div>
  );
};

export default GameOverScreen;
