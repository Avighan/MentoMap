/**
 * AudioContext - Manages voice input/output for audio negotiation games
 */

import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import * as audioAPI from '../api/audio';

const AudioContext = createContext();

export const useAudio = () => {
  const context = useContext(AudioContext);
  if (!context) {
    throw new Error('useAudio must be used within AudioProvider');
  }
  return context;
};

export const AudioProvider = ({ children }) => {
  // State
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playingMessageId, setPlayingMessageId] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [transcript, setTranscript] = useState('');
  const [conversationHistory, setConversationHistory] = useState([]);
  const [error, setError] = useState(null);

  // Refs
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioElementRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);
  const recognitionRef = useRef(null);
  const browserTranscriptRef = useRef('');

  // Mic level monitor for visual feedback
  const startLevelMonitor = useCallback((stream) => {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = { analyser, audioCtx };

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        setAudioLevel(Math.min(avg / 128, 1)); // 0..1
        animFrameRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      // AudioContext not available — visual level stays 0
    }
  }, []);

  const stopLevelMonitor = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (analyserRef.current?.audioCtx) {
      analyserRef.current.audioCtx.close().catch(() => {});
      analyserRef.current = null;
    }
    setAudioLevel(0);
  }, []);

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      setError(null);

      // Microphone API requires HTTPS (secure context)
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const isHTTP = window.location.protocol === 'http:' && window.location.hostname !== 'localhost';
        setError(
          isHTTP
            ? 'Microphone requires HTTPS. Voice input is not available on HTTP connections. Please use text input instead.'
            : 'Microphone is not supported in this browser. Please use text input instead.'
        );
        return false;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      startLevelMonitor(stream);

      // Start browser SpeechRecognition in parallel as a fallback transcript
      browserTranscriptRef.current = '';
      try {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = false;
          recognition.lang = 'en-US';
          recognition.onresult = (event) => {
            let text = '';
            for (let i = 0; i < event.results.length; i++) {
              if (event.results[i].isFinal) {
                text += event.results[i][0].transcript + ' ';
              }
            }
            browserTranscriptRef.current = text.trim();
          };
          recognition.onerror = () => {}; // Silently fail — this is just a fallback
          recognition.onend = () => { recognitionRef.current = null; };
          recognition.start();
          recognitionRef.current = recognition;
        }
      } catch {
        // Browser SpeechRecognition not available — no fallback
      }

      return true;
    } catch (err) {
      const msg = err.name === 'NotAllowedError'
        ? 'Microphone access denied. Please allow microphone access in your browser settings.'
        : err.name === 'NotFoundError'
          ? 'No microphone found. Please connect a microphone and try again.'
          : err.message || 'Failed to start recording';
      setError(msg);
      return false;
    }
  }, [startLevelMonitor]);

  // Stop recording
  const stopRecording = useCallback(() => {
    stopLevelMonitor();
    // Stop browser SpeechRecognition if running
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
    }
    return new Promise((resolve) => {
      if (!mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') {
        setIsRecording(false);
        resolve(null);
        return;
      }

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

        // Stop all tracks
        if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
          mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }

        setIsRecording(false);
        resolve(audioBlob);
      };

      mediaRecorderRef.current.stop();
    });
  }, [stopLevelMonitor]);

  // Transcribe audio — tries server Whisper first, falls back to browser SpeechRecognition captured during recording
  const transcribeAudio = useCallback(async (audioBlob, runId = null) => {
    try {
      setError(null);

      try {
        const response = await audioAPI.speechToText(audioBlob, runId);
        const transcribedText = response.transcription || response.text || response.transcript || '';
        if (transcribedText) {
          setTranscript(transcribedText);
          return transcribedText;
        }
        throw new Error('Empty transcription from server');
      } catch (serverErr) {
        // Server STT failed — use browser transcript captured during recording
        console.warn('Server STT failed, checking browser fallback:', serverErr.message);
        const browserText = browserTranscriptRef.current || '';
        if (browserText) {
          // Using browser SpeechRecognition fallback
          setTranscript(browserText);
          return browserText;
        }
        setError('Could not transcribe audio. Please try again or use text input.');
        throw new Error('Transcription failed — no server or browser result');
      }
    } catch (err) {
      if (!error) setError(err.message || 'Failed to transcribe audio');
      throw err;
    }
  }, [error]);

  // Browser-native TTS fallback using speechSynthesis
  const browserSpeak = useCallback((text) => {
    return new Promise((resolve, reject) => {
      if (!window.speechSynthesis) {
        reject(new Error('Browser speech synthesis not available'));
        return;
      }
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1;
      utterance.onend = () => resolve(true);
      utterance.onerror = (e) => reject(e);
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    });
  }, []);

  // Play text as speech — tries server TTS first, falls back to browser
  // messageId is an optional identifier so components can track *which* message is playing
  const speak = useCallback(async (text, runId = null, voiceId = null, messageId = null) => {
    try {
      setError(null);

      // If already playing this message, stop it (toggle behavior)
      if (isPlaying && playingMessageId === messageId && messageId != null) {
        stopSpeakingInner();
        return false;
      }

      // Stop any current playback first
      stopSpeakingInner();

      setIsPlaying(true);
      setPlayingMessageId(messageId);

      try {
        const audioBlob = await audioAPI.textToSpeech(text, runId, voiceId);
        const audioUrl = URL.createObjectURL(audioBlob);

        const audio = new Audio(audioUrl);
        audioElementRef.current = audio;

        audio.onended = () => {
          setIsPlaying(false);
          setPlayingMessageId(null);
          URL.revokeObjectURL(audioUrl);
        };
        audio.onerror = () => {
          setIsPlaying(false);
          setPlayingMessageId(null);
          URL.revokeObjectURL(audioUrl);
        };

        await audio.play();
        return true;
      } catch (serverErr) {
        // Server TTS failed — fall back to browser speechSynthesis
        console.warn('Server TTS failed, using browser fallback:', serverErr.message);
        await browserSpeak(text);
        setIsPlaying(false);
        setPlayingMessageId(null);
        return true;
      }
    } catch (err) {
      setError(err.message || 'Failed to play audio');
      setIsPlaying(false);
      setPlayingMessageId(null);
      return false;
    }
  }, [browserSpeak, isPlaying, playingMessageId]);

  // Inner helper (no deps) to stop current audio
  const stopSpeakingInner = useCallback(() => {
    if (audioElementRef.current) {
      audioElementRef.current.pause();
      audioElementRef.current.currentTime = 0;
      audioElementRef.current = null;
    }
    window.speechSynthesis?.cancel();
    setIsPlaying(false);
    setPlayingMessageId(null);
  }, []);

  // Public stop
  const stopSpeaking = stopSpeakingInner;

  // Add message to conversation history
  const addMessage = useCallback((message) => {
    setConversationHistory(prev => [...prev, {
      ...message,
      timestamp: Date.now(),
    }]);
  }, []);

  // Clear conversation history
  const clearHistory = useCallback(() => {
    setConversationHistory([]);
    setTranscript('');
  }, []);

  // Complete voice turn (record + transcribe)
  const recordAndTranscribe = useCallback(async () => {
    try {
      await startRecording();
      
      // Wait for user to stop recording manually
      return new Promise((resolve) => {
        // Caller will call stopRecording when ready
        resolve();
      });
    } catch (err) {
      setError(err.message || 'Failed to record');
      throw err;
    }
  }, [startRecording]);

  const value = {
    // State
    isRecording,
    isPlaying,
    playingMessageId,
    audioLevel,
    transcript,
    conversationHistory,
    error,

    // Actions
    startRecording,
    stopRecording,
    transcribeAudio,
    speak,
    stopSpeaking,
    addMessage,
    clearHistory,
    recordAndTranscribe,
  };

  return (
    <AudioContext.Provider value={value}>
      {children}
    </AudioContext.Provider>
  );
};
