/**
 * useEngagementSystem — streak/combo tracking + floating score-delta feed
 * for gameplay UI feedback (badges, streak banners, "+N"/"-N" popups).
 *
 * Call sites (GamePlayPage.jsx, StockMarketGame.jsx, StoryBranchingRenderer.jsx)
 * all do `const engagement = useEngagementSystem();` then:
 *   - engagement.recordChoice(delta)        — call once per scored choice/trade
 *   - engagement.floatingDeltas             — passed to <FloatingDeltaLayer>
 *   - engagement.streakCount / .streakMultiplier — passed to <StreakBanner>
 *   - engagement.triggerScreenShake         — gates a framer-motion shake animation
 *
 * Judgment call (no further spec in the codebase): streak increments on any
 * positive delta and resets on zero/negative; the multiplier steps up every
 * 3 in a row (1x -> 1.5x -> 2x ..., capped at 3x); a screen-shake pulse fires
 * on a strongly negative delta (<= -2) and clears itself after 600ms.
 */
import { useState, useCallback, useRef, useEffect } from 'react';

const SHAKE_THRESHOLD = -2;
const SHAKE_DURATION_MS = 600;
const FLOATING_DELTA_LIFETIME_MS = 1400;
const STREAK_STEP = 3;
const MAX_MULTIPLIER = 3;

let _deltaIdSeq = 0;

export default function useEngagementSystem() {
  const [floatingDeltas, setFloatingDeltas] = useState([]);
  const [streakCount, setStreakCount] = useState(0);
  const [triggerScreenShake, setTriggerScreenShake] = useState(false);
  const shakeTimerRef = useRef(null);
  const deltaTimersRef = useRef(new Set());

  useEffect(() => {
    return () => {
      if (shakeTimerRef.current) clearTimeout(shakeTimerRef.current);
      deltaTimersRef.current.forEach((t) => clearTimeout(t));
      deltaTimersRef.current.clear();
    };
  }, []);

  const recordChoice = useCallback((delta = 0) => {
    const numericDelta = Number(delta) || 0;

    // Floating "+N" / "-N" popup.
    const id = `delta-${Date.now()}-${_deltaIdSeq++}`;
    setFloatingDeltas((prev) => [...prev, { id, value: numericDelta }]);
    const removeTimer = setTimeout(() => {
      setFloatingDeltas((prev) => prev.filter((d) => d.id !== id));
      deltaTimersRef.current.delete(removeTimer);
    }, FLOATING_DELTA_LIFETIME_MS);
    deltaTimersRef.current.add(removeTimer);

    // Streak tracking.
    setStreakCount((prev) => (numericDelta > 0 ? prev + 1 : 0));

    // Screen-shake pulse on a sharply negative outcome.
    if (numericDelta <= SHAKE_THRESHOLD) {
      if (shakeTimerRef.current) clearTimeout(shakeTimerRef.current);
      setTriggerScreenShake(true);
      shakeTimerRef.current = setTimeout(() => setTriggerScreenShake(false), SHAKE_DURATION_MS);
    }
  }, []);

  const reset = useCallback(() => {
    setFloatingDeltas([]);
    setStreakCount(0);
    setTriggerScreenShake(false);
  }, []);

  const streakMultiplier = Math.min(
    MAX_MULTIPLIER,
    1 + Math.floor(streakCount / STREAK_STEP) * 0.5
  );

  return {
    recordChoice,
    reset,
    floatingDeltas,
    streakCount,
    streakMultiplier,
    triggerScreenShake,
  };
}
