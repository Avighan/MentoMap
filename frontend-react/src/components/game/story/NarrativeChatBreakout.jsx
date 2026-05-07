// frontend-react/src/components/game/story/NarrativeChatBreakout.jsx
import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaPaperPlane, FaMicrophone, FaStop, FaVolumeUp, FaVolumeMute } from 'react-icons/fa';
import { useAudio } from '../../../contexts/AudioContext';
import { sendBreakoutTurn } from '../../../api/breakout';

/**
 * Renders a chat_breakout scene inline within story flow.
 * Props:
 *   runId, scene (with chat_breakout block), onComplete({ outcome, next_scene_id, state_delta })
 */
export default function NarrativeChatBreakout({ runId, scene, onComplete }) {
  const cb = scene.chat_breakout || {};
  const persona = cb.ai_persona || {};
  const [messages, setMessages] = useState([
    { speaker: 'ai', text: cb.opening_message || '' },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [turn, setTurn] = useState(0);
  const [score, setScore] = useState(0);
  const [error, setError] = useState(null);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const endRef = useRef(null);

  const {
    isRecording, isPlaying, playingMessageId, audioLevel, error: audioError,
    startRecording, stopRecording, transcribeAudio, speak, stopSpeaking,
  } = useAudio();

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, sending]);

  const handleSend = async (overrideText) => {
    const text = (overrideText ?? input).trim();
    if (!text || sending) return;
    setError(null);
    setSending(true);
    setMessages((m) => [...m, { speaker: 'student', text }]);
    setInput('');
    try {
      const res = await sendBreakoutTurn(runId, scene.scene_id, text);
      setMessages((m) => [...m, { speaker: 'ai', text: res.ai_message || '' }]);
      setTurn(res.turn);
      setScore(res.score);
      if (res.closed) {
        setTimeout(() => {
          onComplete({
            outcome: res.outcome,
            outcome_label: res.outcome_label,
            next_scene_id: res.next_scene_id,
            state_delta: res.state_delta || {},
            score: res.score,
          });
        }, 1800);
      }
    } catch (e) {
      setError(e?.response?.data?.error || 'Could not reach the AI. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const handleVoiceToggle = async () => {
    if (isRecording) {
      const blob = await stopRecording();
      if (blob) {
        setIsTranscribing(true);
        try {
          const result = await transcribeAudio(blob, runId);
          const t = result?.transcription || result;
          if (t && typeof t === 'string' && t.trim()) await handleSend(t.trim());
        } finally {
          setIsTranscribing(false);
        }
      }
    } else {
      await startRecording();
    }
  };

  const handlePlayAudio = async (text, msgIndex) => {
    if (isPlaying && playingMessageId === msgIndex) { stopSpeaking(); return; }
    try { await speak(text, runId, null, msgIndex); } catch { /* ignore TTS unavailable */ }
  };

  const maxTurns = cb.max_turns || 5;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-md flex flex-col" style={{ minHeight: 480 }}>
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-full bg-purple-100 flex items-center justify-center text-lg">
            {persona.avatar || '🤖'}
          </div>
          <div>
            <div className="font-bold text-sm text-gray-900">{persona.name || 'AI'}</div>
            <div className="text-[11px] text-gray-500">{persona.personality || 'Live conversation'}</div>
          </div>
        </div>
        <div className="text-[11px] text-gray-500">Turn {turn}/{maxTurns}</div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <AnimatePresence>
          {messages.map((m, i) => {
            const isUser = m.speaker === 'student';
            return (
              <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] ${isUser ? '' : ''}`}>
                  <div className="px-3 py-2 rounded-2xl text-sm leading-relaxed"
                    style={isUser
                      ? { backgroundColor: '#FFD166', color: '#2D3047', borderBottomRightRadius: 4 }
                      : { backgroundColor: '#F3F4F6', color: '#2D3047', borderBottomLeftRadius: 4 }}>
                    {m.text}
                  </div>
                  {!isUser && (
                    <button
                      onClick={() => handlePlayAudio(m.text, i)}
                      className={`mt-1 text-[10px] flex items-center gap-1 ${isPlaying && playingMessageId === i ? 'text-purple-600 font-semibold' : 'text-gray-400 hover:text-gray-600'}`}>
                      {isPlaying && playingMessageId === i ? (<><FaVolumeMute /> Playing...</>) : (<><FaVolumeUp /> Listen</>)}
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {sending && <div className="text-xs text-gray-400">{persona.name || 'AI'} is thinking…</div>}
        <div ref={endRef} />
      </div>

      <div className="border-t border-gray-100 p-3">
        {error && <div className="mb-2 px-3 py-1.5 rounded bg-red-50 text-red-600 text-xs">{error}</div>}
        {audioError && <div className="mb-2 px-3 py-1.5 rounded bg-red-50 text-red-600 text-xs">{audioError}</div>}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsVoiceMode(!isVoiceMode)}
            className={`p-2 rounded-lg ${isVoiceMode ? 'bg-purple-100 text-purple-600' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}
            title={isVoiceMode ? 'Switch to text' : 'Switch to voice'}>
            <FaMicrophone className="text-sm" />
          </button>
          {isVoiceMode ? (
            <button onClick={handleVoiceToggle} disabled={sending || isTranscribing}
              className={`flex-1 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center ${isRecording ? 'bg-red-500 text-white' : isTranscribing ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {isRecording ? (<><FaStop className="mr-2" /> Stop Recording</>)
                : isTranscribing ? 'Transcribing…'
                : (<><FaMicrophone className="mr-2" /> Tap to Speak</>)}
            </button>
          ) : (
            <>
              <input
                type="text" value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                placeholder="Your reply..."
                disabled={sending}
                className="flex-1 px-3 py-2 rounded-xl bg-gray-100 text-sm border-none outline-none focus:ring-2 focus:ring-blue-200"
              />
              <button onClick={() => handleSend()} disabled={!input.trim() || sending}
                className="p-2 rounded-lg disabled:opacity-30" style={{ backgroundColor: '#FFD166', color: '#2D3047' }}>
                <FaPaperPlane className="text-sm" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
