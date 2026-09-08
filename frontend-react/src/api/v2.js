/**
 * v2 engine API client — post-game share cards and legacy-reward
 * recording for games flagged as "v2" (engines/v2_engine.py). Both
 * endpoints return {v2: false} for non-v2 games, so callers can await
 * them unconditionally.
 */
import apiClient from './client';

export const getV2ShareCard = async (runId) => {
  const response = await apiClient.get(`/api/v2/run/${runId}/share-card`);
  return response.data;
};

export const completeV2Run = async (runId) => {
  const response = await apiClient.post(`/api/v2/run/${runId}/complete`);
  return response.data;
};
