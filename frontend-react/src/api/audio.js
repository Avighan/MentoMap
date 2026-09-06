/**
 * Audio API client — speech-to-text / text-to-speech for voice-driven
 * features (negotiation games, module voice lessons). Routes confirmed in
 * backend/app.py:
 *   POST /api/audio/transcribe  multipart: audio, run_id?, format -> { success, transcription }
 *   POST /api/audio/speak       JSON: { text, run_id?, voice_id? } -> audio/mpeg binary
 */
import apiClient from './client';

export const speechToText = async (audioBlob, runId = null) => {
  const fd = new FormData();
  fd.append('audio', audioBlob, 'recording.webm');
  fd.append('format', 'webm');
  if (runId) fd.append('run_id', runId);
  const res = await apiClient.post('/api/audio/transcribe', fd);
  return res.data;
};

export const textToSpeech = async (text, runId = null, voiceId = null) => {
  const res = await apiClient.post(
    '/api/audio/speak',
    { text, run_id: runId, voice_id: voiceId },
    { responseType: 'blob' }
  );
  return res.data;
};
