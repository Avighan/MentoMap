/**
 * LeaderboardPage - Player-facing leaderboard with coins, XP, and game rankings.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FaArrowLeft,
  FaCoins,
  FaTrophy,
  FaMedal,
  FaStar,
  FaGamepad,
  FaCrown,
  FaChevronDown,
} from 'react-icons/fa';
import { getGlobalLeaderboard } from '../api/wallet';
import { getXPLeaderboard, getSkillHistory } from '../api/profile';
import { getLeaderboard } from '../api/games';
import { useAuth } from '../contexts/AuthContext';
import { useOrg } from '../contexts/OrgContext';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';

const colors = {
  primary: '#FFD166',
  text: '#2D3047',
  textLight: '#6B7280',
  success: '#06D6A0',
  gold: '#FFB300',
  silver: '#9E9E9E',
  bronze: '#CD7F32',
};

const MEDAL_COLORS = ['#FFB300', '#C0C0C0', '#CD7F32'];
const MEDAL_ICONS = [FaCrown, FaMedal, FaMedal];

const _ALL_DIM_LABELS = {
  strategic_thinking: 'Strategic Thinking',
  risk_tolerance: 'Risk Tolerance',
  delayed_gratification: 'Delayed Gratification',
  adaptability: 'Adaptability',
  resilience: 'Resilience',
  empathy: 'Empathy',
  ethical_reasoning: 'Ethical Reasoning',
  creativity: 'Creativity',
  capital_allocation: 'Capital Allocation',
  vision_setting: 'Vision Setting',
  governance_judgment: 'Governance Judgment',
  talent_strategy: 'Talent Strategy',
  commercial_acumen: 'Commercial Acumen',
  systems_thinking: 'Systems Thinking',
  narrative_persuasion: 'Narrative Persuasion',
  decision_quality: 'Decision Quality',
};
const _DEFAULT_DIMS = ['strategic_thinking','risk_tolerance','delayed_gratification','adaptability','resilience','empathy','ethical_reasoning','creativity'];

const LeaderboardPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const { customDimensions } = useOrg();
  const { t } = useTranslation();
  const dimIds = customDimensions && customDimensions.length > 0 ? customDimensions : _DEFAULT_DIMS;
  const SKILL_DIMENSIONS = dimIds.map(id => ({ id, label: _ALL_DIM_LABELS[id] || id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }));
  const [activeTab, setActiveTab] = useState('coins');
  const [coinLeaderboard, setCoinLeaderboard] = useState([]);
  const [xpLeaderboard, setXpLeaderboard] = useState([]);
  const [gameLeaderboard, setGameLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [skillDimension, setSkillDimension] = useState('strategic_thinking');
  const [skillLeaderboard, setSkillLeaderboard] = useState([]);
  const [skillLoading, setSkillLoading] = useState(false);
  const [skillTrend, setSkillTrend] = useState([]);
  // R19 — cohort scoping for skills leaderboard
  const [skillCohort, setSkillCohort] = useState('global'); // 'global' | 'org' | 'cohort'
  const [skillCohortMeta, setSkillCohortMeta] = useState(null); // { cohort_size, org_id, suppressed, reason, k }
  // Privacy suppression state for non-skills tabs
  const [coinSuppressed, setCoinSuppressed] = useState(null);   // { suppressed, reason, k }
  const [xpSuppressed, setXpSuppressed] = useState(null);
  const [gameSuppressed, setGameSuppressed] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [coins, xp, games] = await Promise.all([
          getGlobalLeaderboard(50).catch(() => ({})),
          getXPLeaderboard(50).catch(() => ({ leaderboard: [] })),
          getLeaderboard().catch(() => ({ leaderboard: [] })),
        ]);
        // coins: may be array (legacy) or { rows/entries, suppressed, reason, k }
        if (Array.isArray(coins)) {
          setCoinLeaderboard(coins);
        } else {
          setCoinLeaderboard(coins?.rows || coins?.entries || []);
          if (coins?.suppressed != null) {
            setCoinSuppressed({ suppressed: coins.suppressed, reason: coins.reason, k: coins.k });
          }
        }
        // xp
        setXpLeaderboard(xp?.rows || xp?.leaderboard || []);
        if (xp?.suppressed != null) {
          setXpSuppressed({ suppressed: xp.suppressed, reason: xp.reason, k: xp.k });
        }
        // games
        setGameLeaderboard(games?.rows || games?.leaderboard || []);
        if (games?.suppressed != null) {
          setGameSuppressed({ suppressed: games.suppressed, reason: games.reason, k: games.k });
        }
      } catch (err) {
        console.error('Failed to load leaderboards:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    if (activeTab !== 'skills') return;
    const loadSkills = async () => {
      setSkillLoading(true);
      try {
        const res = await apiClient.get(
          `/api/leaderboard/skills?dimension=${skillDimension}&scope=${skillCohort}`
        );
        setSkillLeaderboard(res.data?.rows || res.data?.leaderboard || res.data?.entries || []);
        setSkillCohortMeta({
          org_id: res.data?.org_id,
          cohort_size: res.data?.cohort_size,
          caller_role: res.data?.caller_role,
          suppressed: res.data?.suppressed,
          reason: res.data?.reason,
          k: res.data?.k,
        });
      } catch (err) {
        console.error('Failed to load skills leaderboard:', err);
        setSkillLeaderboard([]);
        setSkillCohortMeta(null);
      } finally {
        setSkillLoading(false);
      }
    };
    loadSkills();
  }, [activeTab, skillDimension, skillCohort]);

  useEffect(() => {
    if (activeTab !== 'skills') return;
    getSkillHistory().then(data => {
      const entries = data?.history || data?.entries || data || [];
      const filtered = Array.isArray(entries)
        ? entries.filter(e => !skillDimension || e.dimension === skillDimension || !e.dimension)
        : [];
      setSkillTrend(filtered.slice(-5));
    }).catch(() => setSkillTrend([]));
  }, [activeTab, skillDimension]);

  const tabs = [
    { id: 'coins', label: t('leaderboard.tab_coins'), icon: <FaCoins className="text-yellow-400" /> },
    { id: 'xp', label: t('leaderboard.tab_xp'), icon: <FaStar className="text-purple-400" /> },
    { id: 'games', label: t('leaderboard.tab_games'), icon: <FaGamepad className="text-blue-400" /> },
    { id: 'skills', label: `🧠 ${t('leaderboard.tab_skills')}`, icon: null },
  ];

  // Resolve the display name for a leaderboard row, honouring the privacy schema:
  // - is_self rows: show display_name (real name)
  // - peer rows: show peer_label (e.g. "Peer 1") or fall back to display_name / user_id
  const resolveRowName = (e) => {
    if (e.is_self) return e.display_name || e.user_id || 'You';
    return e.peer_label || e.display_name || e.name || e.user_id || e.username || 'Peer';
  };

  const getActiveData = () => {
    switch (activeTab) {
      case 'coins':
        return coinLeaderboard.map(e => ({
          id: e.user_id,
          name: resolveRowName(e),
          isSelf: !!e.is_self,
          primary: (e.lifetime_earned || 0).toLocaleString(),
          primaryLabel: 'coins earned',
          secondary: `${e.games_completed || 0} games`,
        }));
      case 'xp':
        return xpLeaderboard.map(e => ({
          id: e.user_id,
          name: resolveRowName(e),
          isSelf: !!e.is_self,
          primary: (e.xp || e.total_xp || 0).toLocaleString(),
          primaryLabel: 'XP',
          secondary: `Level ${e.level || Math.floor((e.xp || 0) / 100) + 1}`,
        }));
      case 'games':
        return gameLeaderboard.map(e => ({
          id: e.user_id || e.username,
          name: resolveRowName(e),
          isSelf: !!e.is_self,
          primary: (e.score || e.mento_score || 0).toLocaleString(),
          primaryLabel: 'Mento Score',
          secondary: e.game_title || e.game_id || '',
          // P0 Task 20: surface 90% CI on the score so learners see how
          // tight or wide their performance estimate is. Keys come straight
          // from /api/leaderboard/<game_id> entries (Task 9 backend).
          ciLow:  typeof e.ci_low  === 'number' ? Math.round(e.ci_low)  : null,
          ciHigh: typeof e.ci_high === 'number' ? Math.round(e.ci_high) : null,
        }));
      default:
        return [];
    }
  };

  // Suppression data for the currently-active non-skills tab
  const activeTabSuppression = activeTab === 'coins' ? coinSuppressed
    : activeTab === 'xp' ? xpSuppressed
    : activeTab === 'games' ? gameSuppressed
    : null;

  const data = activeTab === 'skills' ? [] : getActiveData();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          className="text-4xl text-yellow-400"
        >
          <FaTrophy />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/games')}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <FaArrowLeft className="text-gray-500 text-sm" />
          </button>
          <div>
            <h1 className="text-lg font-bold" style={{ color: colors.text }}>
              Leaderboard
            </h1>
            <p className="text-xs text-gray-400">
              See how you rank against other players
            </p>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {/* Tab Switcher */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-white shadow-sm text-gray-800'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.icon} <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Skills Tab Content */}
        {activeTab === 'skills' && (
          <div className="space-y-4">
            {/* Dimension Filter Buttons */}
            <div className="flex flex-wrap gap-2">
              {SKILL_DIMENSIONS.map((dim) => (
                <button
                  key={dim.id}
                  onClick={() => setSkillDimension(dim.id)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                    skillDimension === dim.id
                      ? 'bg-amber-400 border-amber-400 text-gray-900 shadow-sm'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-amber-400 hover:text-amber-600'
                  }`}
                >
                  {dim.label}
                </button>
              ))}
            </div>

            {/* R19 — Cohort scope toggle */}
            {isAuthenticated && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Scope</span>
                {[
                  { value: 'global', label: '🌍 Global' },
                  { value: 'org', label: '🏫 My School' },
                  { value: 'cohort', label: '👥 My Cohort' },
                ].map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => setSkillCohort(value)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                      skillCohort === value
                        ? 'bg-indigo-100 border-indigo-300 text-indigo-700'
                        : 'bg-white border-gray-200 text-gray-500 hover:border-indigo-300'
                    }`}
                  >
                    {label}
                  </button>
                ))}
                {skillCohort !== 'global' && skillCohortMeta?.cohort_size != null && (
                  <span className="text-xs text-gray-500">
                    {skillCohortMeta.cohort_size} {skillCohortMeta.cohort_size === 1 ? 'classmate' : 'classmates'}
                    {skillCohortMeta.org_id ? ` · ${skillCohortMeta.org_id}` : ''}
                  </span>
                )}
              </div>
            )}

            {/* k-anonymity suppression banner for skills tab */}
            {skillCohortMeta?.suppressed && (
              <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900 mb-3">
                {skillCohortMeta.reason || `Need at least ${skillCohortMeta.k || 5} participants in this group to show a leaderboard. This protects everyone's privacy.`}
              </div>
            )}

            {/* My Trend Sparkline */}
            {(() => {
              const SparkLine = ({ data }) => {
                if (!data || data.length < 2) return null;
                const vals = data.map(d => d.score || d.value || 50);
                const min = Math.min(...vals), max = Math.max(...vals);
                const range = max - min || 1;
                const w = 80, h = 24;
                const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * w},${h - ((v - min) / range) * h}`).join(' ');
                const first = vals[0], last = vals[vals.length - 1];
                const color = last >= first ? '#22c55e' : '#ef4444';
                const delta = last - first;
                return (
                  <span className="inline-flex items-center gap-2">
                    <svg width={w} height={h} className="overflow-visible">
                      <polyline points={pts} fill="none" stroke={color} strokeWidth="2"/>
                      {vals.map((v, i) => (
                        <circle key={i} cx={(i / (vals.length - 1)) * w} cy={h - ((v - min) / range) * h} r="3" fill={color}/>
                      ))}
                    </svg>
                    <span className={`text-xs font-semibold ${delta >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                      {delta >= 0 ? '+' : ''}{delta} pts
                    </span>
                  </span>
                );
              };
              if (skillTrend.length < 2) return null;
              return (
                <div className="bg-white rounded-xl border border-gray-100 px-4 py-3 flex items-center gap-4">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">My Trend</span>
                  <SparkLine data={skillTrend} />
                </div>
              );
            })()}

            {/* Skills Leaderboard Table */}
            {skillLoading ? (
              <div className="flex justify-center py-10">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                  className="text-3xl text-amber-400"
                >
                  <FaTrophy />
                </motion.div>
              </div>
            ) : skillLeaderboard.length === 0 ? (
              <div className="text-center py-12 text-gray-400 text-sm bg-white rounded-xl border border-gray-100">
                <FaTrophy className="text-3xl mx-auto mb-3 opacity-40" />
                <p>No skill rankings yet for this dimension.</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <div className="grid grid-cols-12 text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 py-2 bg-gray-50 border-b border-gray-100">
                  <span className="col-span-1">{t('leaderboard.col_rank')}</span>
                  <span className="col-span-5">{t('leaderboard.col_player')}</span>
                  <span className="col-span-4">{t('leaderboard.col_score')}</span>
                  <span className="col-span-2 text-right">{t('leaderboard.col_games')}</span>
                </div>
                <div className="divide-y divide-gray-50">
                  {skillLeaderboard.map((entry, i) => {
                    const isMe = entry.is_self || entry.user_id === user?.username || entry.user_id === user?.id;
                    const displayName = isMe
                      ? (entry.display_name || entry.user_id || 'You')
                      : (entry.peer_label || entry.display_name || entry.user_id || entry.username || 'Peer');
                    const score = entry.score ?? entry.dimension_score ?? 0;
                    const games = entry.games_played ?? entry.games_completed ?? 0;
                    return (
                      <motion.div
                        key={`${entry.user_id}-${i}`}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: Math.min(i * 0.03, 0.5) }}
                        className={`grid grid-cols-12 items-center px-4 py-3 ${
                          isMe
                            ? 'bg-yellow-50 border-l-4 border-yellow-300 ring-2 ring-blue-300'
                            : ''
                        }`}
                      >
                        <span className="col-span-1">
                          <div
                            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                            style={{
                              backgroundColor: i < 3 ? `${MEDAL_COLORS[i]}20` : '#F3F4F6',
                              color: i < 3 ? MEDAL_COLORS[i] : '#9CA3AF',
                            }}
                          >
                            {i + 1}
                          </div>
                        </span>
                        <span className="col-span-5 text-sm font-semibold truncate" style={{ color: colors.text }}>
                          {displayName} {isMe ? '(You)' : ''}
                        </span>
                        <span className="col-span-4 pr-4">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-gray-100 rounded-full h-2">
                              <div
                                className="h-2 rounded-full transition-all"
                                style={{
                                  width: `${Math.min(score, 100)}%`,
                                  background: 'linear-gradient(90deg, #FFD166, #FFB300)',
                                }}
                              />
                            </div>
                            <span className="text-xs font-bold text-amber-600 w-8 text-right">{Math.round(score)}</span>
                          </div>
                        </span>
                        <span className="col-span-2 text-right text-xs text-gray-400">{games}</span>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Suppression banner — shown for coins/xp/games tabs when k-anonymity is active */}
        {activeTab !== 'skills' && activeTabSuppression?.suppressed && (
          <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900 mb-3">
            {activeTabSuppression.reason || `Need at least ${activeTabSuppression.k || 5} participants in this group to show a leaderboard. This protects everyone's privacy.`}
          </div>
        )}

        {/* Top 3 Podium */}
        {activeTab !== 'skills' && data.length >= 3 && (
          <div className="flex items-end justify-center gap-3 pt-4 pb-2">
            {[1, 0, 2].map((rank) => {
              const entry = data[rank];
              if (!entry) return null;
              const isMe = entry.isSelf || entry.id === user?.username || entry.id === user?.id;
              const heights = ['h-28', 'h-20', 'h-16'];
              const MedalIcon = MEDAL_ICONS[rank];
              return (
                <motion.div
                  key={rank}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: rank * 0.15 }}
                  className="flex flex-col items-center"
                >
                  <div
                    className="w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center mb-1"
                    style={{ backgroundColor: `${MEDAL_COLORS[rank]}20`, color: MEDAL_COLORS[rank] }}
                  >
                    <MedalIcon className="text-lg" />
                  </div>
                  <p className="text-xs font-bold truncate max-w-[80px] text-center" style={{ color: colors.text }}>
                    {entry.name} {isMe ? '(You)' : ''}
                  </p>
                  <p className="text-xs text-gray-400">{entry.primary}</p>
                  <div
                    className={`w-16 sm:w-20 ${heights[rank]} rounded-t-xl mt-2`}
                    style={{
                      background: `linear-gradient(180deg, ${MEDAL_COLORS[rank]}40 0%, ${MEDAL_COLORS[rank]}15 100%)`,
                      borderTop: `3px solid ${MEDAL_COLORS[rank]}`,
                    }}
                  >
                    <p className="text-center pt-2 text-lg font-black" style={{ color: MEDAL_COLORS[rank] }}>
                      {rank + 1}
                    </p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* Full Rankings List */}
        {activeTab !== 'skills' && (
        <div>
          <h2 className="text-xs uppercase tracking-wider font-semibold mb-3" style={{ color: colors.textLight }}>
            {t('leaderboard.full_rankings')}
          </h2>
          {data.length === 0 ? (
            <div className="text-center py-12 text-gray-400 text-sm">
              <FaTrophy className="text-3xl mx-auto mb-3 opacity-40" />
              <p>{t('leaderboard.no_players')}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {data.map((entry, i) => {
                const isMe = entry.isSelf || entry.id === user?.username || entry.id === user?.id;
                return (
                  <motion.div
                    key={`${entry.id}-${i}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: Math.min(i * 0.03, 0.5) }}
                    className={`flex items-center gap-3 p-3 rounded-lg border ${
                      isMe
                        ? 'border-yellow-200 bg-yellow-50 ring-2 ring-blue-300'
                        : 'border-gray-100 bg-white'
                    }`}
                  >
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
                      style={{
                        backgroundColor: i < 3 ? `${MEDAL_COLORS[i]}20` : '#F3F4F6',
                        color: i < 3 ? MEDAL_COLORS[i] : '#9CA3AF',
                      }}
                    >
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold truncate" style={{ color: colors.text }}>
                        {entry.name} {isMe ? '(You)' : ''}
                      </p>
                      <p className="text-xs text-gray-400">{entry.secondary}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p
                        className="text-sm font-bold"
                        style={{ color: colors.text }}
                        title={
                          entry.ciLow != null && entry.ciHigh != null
                            ? `90% confidence interval: ${entry.ciLow}–${entry.ciHigh}`
                            : undefined
                        }
                      >
                        {entry.primary}
                        {entry.ciLow != null && entry.ciHigh != null && (
                          <span className="ml-1 text-[10px] font-normal text-gray-400">
                            ±{Math.round((entry.ciHigh - entry.ciLow) / 2)}
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-gray-400">{entry.primaryLabel}</p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
        )}
      </div>
    </div>
  );
};

export default LeaderboardPage;
