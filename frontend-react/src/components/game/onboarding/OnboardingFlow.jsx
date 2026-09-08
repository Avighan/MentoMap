/**
 * OnboardingFlow — a minimal welcome overlay for the v1 (legacy) stock
 * market UI. StockMarketGame.jsx only mounts this when v2 is disabled
 * (org.flags.stocksim_v2_ui === false or ?stocksim_v2=0) — the default v2
 * path never renders it. Kept intentionally small since it's a fallback
 * path, not the primary experience.
 */
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const OnboardingFlow = ({ gameData, phase, setPhase }) => {
  if (phase !== 'story') return null;
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 text-center"
        >
          <div className="text-4xl mb-3">{gameData?.icon || '📈'}</div>
          <h2 className="text-lg font-bold text-gray-800 mb-2">{gameData?.title || 'Stock Market Simulator'}</h2>
          <p className="text-sm text-gray-500 mb-5">{gameData?.description || 'Trade a simulated market and see how your decisions play out.'}</p>
          <button
            onClick={() => setPhase('playing')}
            className="w-full py-3 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
          >
            Start Trading
          </button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default OnboardingFlow;
