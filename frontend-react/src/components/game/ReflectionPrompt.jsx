/**
 * D1: ReflectionPrompt — Post-choice modal asking "Why did you make that choice?"
 * Props: { prompt, kantian, runId, roundId, choiceId, onSubmit, onSkip }
 *
 * When `kantian` is true (ethics-tagged choices, kantian games, or duty mode on),
 * the modal foregrounds the categorical-imperative question: would you will the
 * rule behind your choice as a universal law?
 *
 * Task 12 (P0): when `runId` is present, the rationale is sent to
 * POST /api/run/<runId>/reflection for LLM grading and a feedback toast
 * shows the per-dimension signal deltas before closing.
 */
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { submitReflection } from '../../api/profile';

const ReflectionPrompt = ({
  prompt,
  kantian = false,
  runId = null,
  roundId = null,
  choiceId = null,
  onSubmit,
  onSkip,
}) => {
  const { t } = useTranslation();
  const [answer, setAnswer] = useState('');
  const [universalAnswer, setUniversalAnswer] = useState('');
  const [visible, setVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null); // { dim_signals, score, strengths }

  useEffect(() => {
    if (prompt) {
      setAnswer('');
      setUniversalAnswer('');
      setFeedback(null);
      setVisible(true);
    }
  }, [prompt]);

  const handleSubmit = async () => {
    const trimmed = answer.trim();
    const trimmedUniversal = universalAnswer.trim();
    if (trimmed || trimmedUniversal) {
      try {
        const key = `reflection_${Date.now()}`;
        localStorage.setItem(
          key,
          JSON.stringify({
            prompt,
            kantian,
            answer: trimmed,
            universal_answer: trimmedUniversal,
            ts: Date.now(),
          })
        );
      } catch (_) {}
    }

    // Task 12: grade rationale via backend if runId is provided and we have text
    if (runId && trimmed) {
      setSubmitting(true);
      try {
        const result = await submitReflection(runId, {
          round_id: roundId,
          choice_id: choiceId,
          rationale: trimmed,
        });
        setFeedback(result);
        setSubmitting(false);
        // Hold the toast visible briefly, then close
        setTimeout(() => {
          setVisible(false);
          setTimeout(() => onSubmit?.(trimmed), 300);
        }, 3500);
        return;
      } catch (_) {
        setSubmitting(false);
        // Fall through to default close behavior on grading failure
      }
    }

    setVisible(false);
    setTimeout(() => onSubmit?.(trimmed), 300);
  };

  const handleSkip = () => {
    setVisible(false);
    setTimeout(() => onSkip?.(), 300);
  };

  if (!prompt) return null;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="reflection-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
        >
          <motion.div
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ type: 'spring', damping: 22, stiffness: 260 }}
            className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
          >
            {/* Header (amber/cream palette to match simulation games) */}
            <div
              className="px-6 py-4"
              style={{
                background: kantian
                  ? 'linear-gradient(135deg, #4F46E5 0%, #312E81 100%)'
                  : 'linear-gradient(135deg, #EF9F27 0%, #BA7517 100%)',
                fontFamily: "'Poppins', sans-serif",
              }}
            >
              <div className="flex items-center gap-2">
                <span className="text-2xl">{kantian ? '⚖️' : '🤔'}</span>
                <h3 className="font-bold text-lg" style={{ color: '#FFFFFF' }}>
                  {kantian ? 'Universalize your choice' : 'Reflect on your choice'}
                </h3>
              </div>
              <p className="text-xs mt-1" style={{ color: kantian ? '#E0E7FF' : '#FFF3DC' }}>
                {kantian
                  ? 'Kant: act only on a maxim you could will to be universal law.'
                  : 'Take a moment to think about why you decided this way'}
              </p>
            </div>

            {/* Body */}
            <div
              className="px-6 py-5"
              style={{
                background: kantian ? '#EEF2FF' : '#FFF9EE',
                fontFamily: "'Poppins', sans-serif",
              }}
            >
              <p
                className="font-medium text-sm mb-3 leading-relaxed"
                style={{ color: kantian ? '#1E1B4B' : '#412402' }}
              >
                {prompt}
              </p>
              <textarea
                className="w-full rounded-xl p-3 text-sm resize-none focus:outline-none"
                rows={kantian ? 3 : 4}
                placeholder="Type your thoughts here... (optional)"
                value={answer}
                onChange={e => setAnswer(e.target.value)}
                autoFocus
                style={{
                  border: kantian ? '1px solid #C7D2FE' : '1px solid #F0E6D2',
                  background: kantian ? '#FFFFFF' : '#FFFDF7',
                  color: kantian ? '#1E1B4B' : '#412402',
                  boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.04)',
                }}
              />

              {kantian && (
                <div className="mt-4">
                  <p
                    className="text-xs font-bold uppercase tracking-wider mb-1"
                    style={{ color: '#4338CA' }}
                  >
                    Universalization test
                  </p>
                  <p
                    className="text-sm mb-2 leading-relaxed"
                    style={{ color: '#1E1B4B' }}
                  >
                    If <em>everyone</em> in this situation made the same choice,
                    what kind of world would that create — and could you will it
                    even if you were on the receiving end?
                  </p>
                  <textarea
                    className="w-full rounded-xl p-3 text-sm resize-none focus:outline-none"
                    rows={3}
                    placeholder="Imagine the rule behind your choice as a universal law..."
                    value={universalAnswer}
                    onChange={e => setUniversalAnswer(e.target.value)}
                    style={{
                      border: '1px solid #C7D2FE',
                      background: '#FFFFFF',
                      color: '#1E1B4B',
                      boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.04)',
                    }}
                  />
                </div>
              )}

              {/* Task 12: feedback toast — dim_signal deltas after grading */}
              {feedback && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 rounded-xl px-4 py-3"
                  style={{
                    background: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                  }}
                >
                  <p
                    className="text-xs font-bold uppercase tracking-wider mb-1"
                    style={{ color: kantian ? '#4338CA' : '#854F0B' }}
                  >
                    {t('reflection.feedback_title', 'Reflection captured')}
                  </p>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {Object.entries(feedback.dim_signals || {}).map(([dim, delta]) => {
                      const sign = delta >= 0 ? '+' : '';
                      const label = t('reflection.feedback_dim_delta', {
                        dim: dim.replace(/_/g, ' '),
                        sign,
                        delta,
                        defaultValue: `${dim.replace(/_/g, ' ')} ${sign}${delta}`,
                      });
                      return (
                        <span
                          key={dim}
                          className="text-xs font-semibold px-2 py-1 rounded-md capitalize"
                          style={{
                            background: delta >= 0 ? '#ECFDF5' : '#FEF2F2',
                            color: delta >= 0 ? '#065F46' : '#991B1B',
                          }}
                        >
                          {label}
                        </span>
                      );
                    })}
                  </div>
                  {Array.isArray(feedback.strengths) && feedback.strengths.length > 0 && (
                    <p className="text-xs mt-2" style={{ color: '#374151' }}>
                      {feedback.strengths[0]}
                    </p>
                  )}
                </motion.div>
              )}
            </div>

            {/* Footer */}
            <div
              className="px-6 pb-5 pt-3 flex justify-end gap-3"
              style={{
                background: kantian ? '#E0E7FF' : '#FAEEDA',
                borderTop: kantian ? '1px solid #C7D2FE' : '1px solid #F0E6D2',
              }}
            >
              <button
                onClick={handleSkip}
                className="px-4 py-2 text-sm font-medium transition"
                style={{ color: kantian ? '#3730A3' : '#854F0B' }}
              >
                Skip
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting || !!feedback}
                className="px-5 py-2 text-sm font-semibold rounded-xl transition shadow disabled:opacity-60"
                style={{
                  background: kantian ? '#4F46E5' : '#EF9F27',
                  color: '#FFFFFF',
                }}
              >
                {submitting ? '…' : 'Submit reflection'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default ReflectionPrompt;
