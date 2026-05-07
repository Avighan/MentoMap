// frontend-react/src/api/breakout.js
import apiClient from './client';

export async function sendBreakoutTurn(runId, sceneId, message) {
  const { data } = await apiClient.post(`/api/run/${runId}/breakout-chat`, {
    scene_id: sceneId,
    message,
  });
  return data;
}
