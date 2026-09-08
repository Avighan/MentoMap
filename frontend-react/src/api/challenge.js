/**
 * Peer "challenge a friend" API client (backend/app.py /api/challenge/*).
 */
import apiClient from './client';

export const createChallenge = async (runId, message = '') => {
  const response = await apiClient.post('/api/challenge/create', { run_id: runId, message });
  return response.data;
};
