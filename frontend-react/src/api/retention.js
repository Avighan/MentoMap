/**
 * Retention API — wraps the audit-followup retention/UX endpoints.
 *
 * Endpoints (all behind /api/...):
 *   weekly-challenges, weekly-challenges/:id/claim
 *   game-requests (POST/GET), game-requests/:id/upvote
 *   reflection-prompts?age=N&choice_index=I
 *   parent/daily-summary?child_id=X&date=YYYY-MM-DD
 *   offline-activities, offline-activities/match
 */
import apiClient from './client';

// ---- Weekly challenges ----
export async function listWeeklyChallenges() {
  const r = await apiClient.get('/api/weekly-challenges');
  return r.data?.challenges || [];
}
export async function claimWeeklyChallenge(challengeId) {
  const r = await apiClient.post(`/api/weekly-challenges/${challengeId}/claim`);
  return r.data;
}

// ---- Game requests ----
export async function createGameRequest({ title, topic, game_type_hint, audience }) {
  const r = await apiClient.post('/api/game-requests', { title, topic, game_type_hint, audience });
  return r.data?.request;
}
export async function listGameRequests({ status, limit = 50 } = {}) {
  const params = {};
  if (status) params.status = status;
  if (limit) params.limit = limit;
  const r = await apiClient.get('/api/game-requests', { params });
  return r.data?.requests || [];
}
export async function upvoteGameRequest(requestId) {
  const r = await apiClient.post(`/api/game-requests/${requestId}/upvote`);
  return r.data?.request;
}

// ---- Reflection prompts ----
export async function getReflectionPrompts(age, choiceIndex) {
  const params = { age };
  if (choiceIndex !== undefined && choiceIndex !== null) params.choice_index = choiceIndex;
  const r = await apiClient.get('/api/reflection-prompts', { params });
  return r.data;
}

// ---- Parent daily summary ----
export async function getParentDailySummary({ childId, date } = {}) {
  const params = {};
  if (childId) params.child_id = childId;
  if (date) params.date = date;
  const r = await apiClient.get('/api/parent/daily-summary', { params });
  return r.data;
}

// ---- Offline activity cards ----
export async function listOfflineActivities({ dim, age } = {}) {
  const params = {};
  if (dim) params.dim = dim;
  if (age !== undefined) params.age = age;
  const r = await apiClient.get('/api/offline-activities', { params });
  return r.data;
}
export async function matchOfflineActivity({ dim, age }) {
  const r = await apiClient.get('/api/offline-activities/match', { params: { dim, age } });
  return r.data?.card;
}
