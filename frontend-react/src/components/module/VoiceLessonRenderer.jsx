/**
 * VoiceLessonRenderer — public-speaking / voice-recording lesson type.
 * Rendered by ModuleDetailPage.jsx as:
 *   <VoiceLessonRenderer moduleId={moduleId} lessonId={activeLessonId}
 *     schema={activeLesson.schema} savedAnswers={answers}
 *     onAnswersChange={(a) => setAnswers(a || {})} />
 *
 * Backed by the real route in backend/app.py `api_module_voice_submit`:
 *   POST /api/modules/:id/lessons/:lid/voice-submit
 *   multipart: audio (file), duration_seconds, format -> { ok, transcript, ai_feedback }
 * sent via api/modules.js `submitVoiceLesson(moduleId, lessonId, formData)`.
 *
 * Recording uses the browser's native MediaRecorder (same approach as
 * contexts/AudioContext.jsx) — no extra dependency needed.
 */
import React, { useState, useRef, useCallback } from 'react';
import { submitVoiceLesson } from '../../api/modules';

export default function VoiceLessonRenderer({ moduleId, lessonId, schema, savedAnswers, onAnswersChange }) {
  const [recording, setRecording] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [durationSeconds, setDurationSeconds] = useState(0);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const startTimeRef = useRef(0);

  const transcript = savedAnswers?.transcript || '';
  const feedback = savedAnswers?.ai_feedback || null;

  const startRecording = useCallback(async () => {
    setError('');
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone is not supported in this browser.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      startTimeRef.current = Date.now();
      setRecording(true);
    } catch (err) {
      setError(
        err.name === 'NotAllowedError'
          ? 'Microphone access was denied.'
          : 'Could not start recording.'
      );
    }
  }, []);

  const stopAndSubmit = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === 'inactive') return;
    recorder.onstop = async () => {
      const durationSec = (Date.now() - startTimeRef.current) / 1000;
      setDurationSeconds(durationSec);
      recorder.stream.getTracks().forEach((t) => t.stop());
      setRecording(false);

      const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
      const fd = new FormData();
      fd.append('audio', blob, 'recording.webm');
      fd.append('format', 'webm');
      fd.append('duration_seconds', String(durationSec));

      setSubmitting(true);
      setError('');
      try {
        const res = await submitVoiceLesson(moduleId, lessonId, fd);
        if (res?.ok === false) {
          setError(res.error || 'Transcription failed. Please try again.');
        } else {
          onAnswersChange?.({
            ...savedAnswers,
            transcript: res.transcript || '',
            ai_feedback: res.ai_feedback || null,
            duration_seconds: durationSec,
          });
        }
      } catch (err) {
        setError(err?.response?.data?.error || 'Could not submit your recording.');
      } finally {
        setSubmitting(false);
      }
    };
    recorder.stop();
  }, [moduleId, lessonId, savedAnswers, onAnswersChange]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {schema?.brief && (
        <p style={{ fontSize: '0.9rem', color: '#6D7286', fontStyle: 'italic' }}>{schema.brief}</p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {!recording ? (
          <button
            onClick={startRecording}
            disabled={submitting}
            style={{
              padding: '10px 20px', borderRadius: 999, border: 'none',
              background: '#EF4444', color: '#fff', fontWeight: 700, cursor: 'pointer',
            }}
          >
            🎙️ Start recording
          </button>
        ) : (
          <button
            onClick={stopAndSubmit}
            style={{
              padding: '10px 20px', borderRadius: 999, border: 'none',
              background: '#2D3047', color: '#fff', fontWeight: 700, cursor: 'pointer',
            }}
          >
            ⏹ Stop &amp; submit
          </button>
        )}
        {recording && <span style={{ color: '#EF4444', fontSize: '0.85rem' }}>● Recording…</span>}
        {submitting && <span style={{ color: '#6D7286', fontSize: '0.85rem' }}>Transcribing…</span>}
      </div>

      {error && <div style={{ color: '#EF4444', fontSize: '0.85rem' }}>{error}</div>}

      {transcript && (
        <div style={{ background: '#F9FAFB', padding: 12, borderRadius: 10 }}>
          <div style={{ fontWeight: 700, fontSize: '0.8rem', marginBottom: 4 }}>Your transcript</div>
          <p style={{ fontSize: '0.9rem', margin: 0 }}>{transcript}</p>
          {durationSeconds > 0 && (
            <div style={{ fontSize: '0.75rem', color: '#9CA3AF', marginTop: 6 }}>
              {Math.round(durationSeconds)}s recorded
            </div>
          )}
        </div>
      )}

      {feedback && (
        <div style={{ background: '#EEF2FF', padding: 12, borderRadius: 10 }}>
          <div style={{ fontWeight: 700, fontSize: '0.8rem', marginBottom: 4 }}>Feedback</div>
          <p style={{ fontSize: '0.9rem', margin: 0, whiteSpace: 'pre-wrap' }}>
            {typeof feedback === 'string' ? feedback : JSON.stringify(feedback)}
          </p>
        </div>
      )}
    </div>
  );
}
