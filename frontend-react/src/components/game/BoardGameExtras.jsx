/**
 * BoardGameExtras — small gameplay-feedback overlays shared across game
 * renderers (GamePlayPage.jsx, StockMarketGame.jsx, StoryBranchingRenderer.jsx),
 * fed by useEngagementSystem()'s `floatingDeltas` / `streakCount` /
 * `streakMultiplier`. Plain CSS animation (framer-motion is already a
 * dependency and used everywhere else in these renderers, so it's used here
 * too rather than hand-rolled keyframes).
 *
 * Judgment call (no visual spec exists elsewhere in the repo): green/red
 * pill for score deltas floating upward and fading; a compact banner that
 * only appears once a streak is "hot" (>=3), colored by the multiplier.
 */
import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';

export function FloatingDeltaLayer({ floatingDeltas = [] }) {
  if (!floatingDeltas.length) return null;
  return (
    <div
      style={{
        position: 'fixed',
        top: '30%',
        left: '50%',
        pointerEvents: 'none',
        zIndex: 60,
      }}
    >
      <AnimatePresence>
        {floatingDeltas.map((d, i) => {
          const positive = d.value > 0;
          return (
            <motion.div
              key={d.id}
              initial={{ opacity: 0, y: 0, x: '-50%', scale: 0.8 }}
              animate={{ opacity: 1, y: -60 - i * 6, x: '-50%', scale: 1 }}
              exit={{ opacity: 0, y: -90 - i * 6, x: '-50%' }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
              style={{
                position: 'absolute',
                whiteSpace: 'nowrap',
                fontWeight: 800,
                fontSize: '1.5rem',
                color: positive ? '#06D6A0' : '#EF4444',
                textShadow: '0 2px 8px rgba(0,0,0,0.25)',
              }}
            >
              {positive ? '+' : ''}
              {d.value}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export function StreakBanner({ streakCount = 0, streakMultiplier = 1 }) {
  const isHot = streakCount >= 3;
  return (
    <AnimatePresence>
      {isHot && (
        <motion.div
          key="streak-banner"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          style={{
            position: 'fixed',
            top: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 60,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 18px',
            borderRadius: 999,
            fontWeight: 700,
            fontSize: '0.9rem',
            color: '#fff',
            background: 'linear-gradient(135deg, #FF6B6B 0%, #FFD166 100%)',
            boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
          }}
        >
          <span role="img" aria-label="fire">🔥</span>
          {streakCount}-streak
          {streakMultiplier > 1 && (
            <span style={{ opacity: 0.9 }}>· {streakMultiplier}x</span>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default { FloatingDeltaLayer, StreakBanner };
