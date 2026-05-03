/**
 * Player Profile API client
 */
import apiClient from './client';

export const getProfile = async () => {
  const response = await apiClient.get('/api/profile');
  return response.data;
};

// Task 12 (P0): submit a reflection rationale for LLM grading.
// Returns: { ok, score, dim_signals, strengths, improvements }
export const submitReflection = async (runId, payload) => {
  const response = await apiClient.post(`/api/run/${runId}/reflection`, payload);
  return response.data;
};

export const getBadges = async () => {
  const response = await apiClient.get('/api/profile/badges');
  return response.data;
};

export const getXPLeaderboard = async (limit = 20) => {
  const response = await apiClient.get(`/api/profile/leaderboard?limit=${limit}`);
  return response.data;
};

export const getProfileProgress = async () => {
  const response = await apiClient.get('/api/profile/progress');
  return response.data;
};

export const getProfileSkills = async () => {
  const response = await apiClient.get('/api/profile/skills');
  return response.data;
};

export const getSkillTree = async () => {
  const response = await apiClient.get('/api/profile/skill-tree');
  return response.data;
};

export const updateProfile = async (data) => {
  const response = await apiClient.put('/api/profile', data);
  return response.data;
};

export const setupProfile = (data) =>
  apiClient.patch('/api/profile/setup', data).then(r => r.data);

export const getReportHistory = async () => {
  const response = await apiClient.get('/api/profile/reports');
  return response.data;
};

export const getHistoricalReport = async (runId) => {
  const response = await apiClient.get(`/api/report/${runId}`);
  return response.data;
};

// --- Skill Portfolio (Item 31) ---
export const getSkillPortfolio = async () => {
  const response = await apiClient.get('/api/profile/skill-portfolio');
  return response.data;
};

// --- Recommendations (Item 32) ---
export const getRecommendations = async () => {
  const response = await apiClient.get('/api/profile/recommendations');
  return response.data;
};

// --- Skill Achievements (Item 34) ---
export const getSkillAchievements = async () => {
  const response = await apiClient.get('/api/profile/skill-achievements');
  return response.data;
};

// --- Learning Paths (Item 33) ---
export const getLearningPaths = async () => {
  const response = await apiClient.get('/api/learning-paths');
  return response.data;
};

export const getLearningPathDetail = async (pathId) => {
  const response = await apiClient.get(`/api/learning-paths/${pathId}`);
  return response.data;
};

export const getLearningPathProgress = async (pathId) => {
  const response = await apiClient.get(`/api/learning-paths/${pathId}/progress`);
  return response.data;
};

// --- Transfer Exercises (Item 35) ---
export const getTransferExercises = async (runId) => {
  const response = await apiClient.get(`/api/run/${runId}/transfer-exercises`);
  return response.data;
};

// --- Parent Dashboard ---
export const getParentDashboard = async () => {
  const response = await apiClient.get('/api/analytics/dashboard');
  return response.data;
};

// --- Skill History (longitudinal trends) ---
export const getSkillHistory = async () => {
  const response = await apiClient.get('/api/profile/skill-history');
  return response.data;
};

// --- Goals System ---
export const getSkillGoals = async () => {
  const response = await apiClient.get('/api/profile/goals');
  return response.data;
};

export const setSkillGoals = async (goals) => {
  const response = await apiClient.put('/api/profile/goals', { goals });
  return response.data;
};

// --- Certificates ---
export const getCertificates = async () => {
  const response = await apiClient.get('/api/profile/certificates');
  return response.data;
};

// --- Quit Session / Frustration Detection ---
export const logQuitSession = async ({ runId, gameId, roundNumber = 0, reason = '' }) => {
  const response = await apiClient.post('/api/profile/quit-session', {
    run_id: runId, game_id: gameId, round_number: roundNumber, reason,
  });
  return response.data;
};

export const getFrustrationCheck = async (gameId) => {
  const response = await apiClient.get(`/api/profile/frustration-check?game_id=${gameId}`);
  return response.data;
};

// --- Goal-Based Recommendations ---
export const getGoalRecommendations = async () => {
  const response = await apiClient.get('/api/profile/goals/recommendations');
  return response.data;
};

// --- Daily Rewards ---
export const getDailyRewardsStatus = async () => {
  const response = await apiClient.get('/api/daily-rewards/status');
  return response.data;
};

export const claimDailyReward = async () => {
  const response = await apiClient.post('/api/daily-rewards/claim');
  return response.data;
};

export const getDailyRewardsConfig = async () => {
  const response = await apiClient.get('/api/daily-rewards/config');
  return response.data;
};

// --- Next Game Recommendation ---
export const getNextGameRecommendation = async () => {
  const response = await apiClient.get('/api/profile/next-game');
  return response.data;
};

// --- Behavioral Intelligence (Round 15) ---
export const getBaselineImageUrl = (bust = '') =>
  `/api/profile/baseline-image${bust ? `?t=${bust}` : ''}`;

export const getChildBaselineImageUrl = (childId, bust = '') =>
  `/api/family/children/${childId}/baseline-image${bust ? `?t=${bust}` : ''}`;

export const getBehavioralSignature = async () => {
  const response = await apiClient.get('/api/profile/behavioral-signature');
  return response.data;
};

export const getBehavioralSignals = async () => {
  const response = await apiClient.get('/api/profile/behavioral-signals');
  return response.data;
};

export const updateWellbeingConsent = async (consent, childId = null) => {
  const body = { consent };
  if (childId) body.child_id = childId;
  const response = await apiClient.patch('/api/profile/wellbeing-consent', body);
  return response.data;
};

export const getWellbeingHistory = async () => {
  const response = await apiClient.get('/api/wellbeing/history');
  return response.data;
};

export const getWellbeingSurveys = async () => {
  const response = await apiClient.get('/api/wellbeing/surveys');
  return response.data;
};

export const deleteWellbeingData = async () => {
  const response = await apiClient.delete('/api/profile/wellbeing-data');
  return response.data;
};

export const getWellbeingAlerts = async () => {
  const response = await apiClient.get('/api/teacher/wellbeing-alerts');
  return response.data;
};

export const markWellbeingCheckin = async (studentId) => {
  const response = await apiClient.post(`/api/teacher/wellbeing-alerts/${studentId}/check-in`);
  return response.data;
};

export const getLeaderboardPercentile = async (dimension, period = 'all') => {
  const response = await apiClient.get(`/api/leaderboard/percentile?dimension=${dimension}&period=${period}`);
  return response.data;
};
