/**
 * MentoScoreBreakdown - Displays the 7-dimension Mento Score with rank badge.
 * Shown on the GameOverScreen after a game completes.
 *
 * P0 Task 19 — Reconciled with PostGameInsights taxonomy: when a backend
 * doesn't supply the legacy 7-bucket `breakdown`, we now derive each bucket
 * as the mean of the corresponding PostGameInsights dimensions
 * (`AGGREGATE_FROM_DIMS`). This keeps the rank badge meaningful even after
 * runs that only emit the 14-dim v2 vector.
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FaChevronDown, FaChevronUp } from 'react-icons/fa';

// Mapping from the 7 legacy aggregate buckets to the 14 PostGameInsights
// dimensions. Used when the backend ships only the dimensional vector.
const AGGREGATE_FROM_DIMS = {
  resource_optimization:   ['capital_allocation', 'commercial_acumen'],
  decision_quality:        ['decision_quality', 'strategic_thinking'],
  achievement_progress:    ['delayed_gratification', 'resilience'],
  competitive_performance: ['risk_tolerance', 'narrative_persuasion'],
  learning_engagement:     ['adaptability', 'creativity'],
  speed_efficiency:        ['decision_quality'], // proxy when no decision_time signal
  risk_management:         ['risk_tolerance', 'governance_judgment'],
};

/**
 * Derive the 7 aggregate scores from the 14-dim PostGameInsights vector.
 * Returns {} when no dimension scores are available so the caller can fall
 * back to the legacy `breakdown` map.
 */
function deriveAggregates(dimensionScores) {
  if (!dimensionScores || typeof dimensionScores !== 'object') return {};
  const out = {};
  for (const [aggKey, srcDims] of Object.entries(AGGREGATE_FROM_DIMS)) {
    const vals = srcDims
      .map((d) => dimensionScores[d])
      .filter((v) => typeof v === 'number' && !Number.isNaN(v));
    if (vals.length > 0) {
      out[aggKey] = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
    }
  }
  return out;
}

const DIMENSION_META = {
  resource_optimization: { label: 'Resource Optimization', icon: '📊', color: '#06D6A0', weight: '20%' },
  decision_quality: { label: 'Decision Quality', icon: '🎯', color: '#FFD166', weight: '20%' },
  achievement_progress: { label: 'Achievement Progress', icon: '🏆', color: '#FF9B71', weight: '15%' },
  competitive_performance: { label: 'Competitive Performance', icon: '⚔️', color: '#EF476F', weight: '15%' },
  learning_engagement: { label: 'Learning Engagement', icon: '📚', color: '#118AB2', weight: '10%' },
  speed_efficiency: { label: 'Speed Efficiency', icon: '⚡', color: '#7B2FBE', weight: '10%' },
  risk_management: { label: 'Risk Management', icon: '🛡️', color: '#073B4C', weight: '10%' },
};

const RANK_STYLES = {
  S: { bg: 'linear-gradient(135deg, #FFD700, #FFA500)', text: '#000', glow: '#FFD700' },
  A: { bg: 'linear-gradient(135deg, #C0C0C0, #E8E8E8)', text: '#333', glow: '#C0C0C0' },
  B: { bg: 'linear-gradient(135deg, #CD7F32, #D4A574)', text: '#FFF', glow: '#CD7F32' },
  C: { bg: 'linear-gradient(135deg, #4A9EAF, #6BB8C9)', text: '#FFF', glow: '#4A9EAF' },
  D: { bg: 'linear-gradient(135deg, #7B8794, #9CA8B5)', text: '#FFF', glow: '#7B8794' },
  F: { bg: 'linear-gradient(135deg, #E74C3C, #F1948A)', text: '#FFF', glow: '#E74C3C' },
};

const MentoScoreBreakdown = ({ mentoScore, dimensionScores = null }) => {
  const [expanded, setExpanded] = useState(false);

  if (!mentoScore || typeof mentoScore.score !== 'number') return null;

  const { score, breakdown = {}, rank = '', percentile = 50 } = mentoScore;
  const rankLetter = (rank || 'C').charAt(0).toUpperCase();
  const rankStyle = RANK_STYLES[rankLetter] || RANK_STYLES.C;

  // P0 Task 19: prefer the legacy backend-supplied `breakdown`, but for any
  // bucket the backend left empty (or for entirely v2 runs that only emit
  // the 14-dim PostGameInsights vector), derive the aggregate from those
  // dimensions instead of showing 0.
  const derived = deriveAggregates(dimensionScores);
  const merged = { ...derived, ...breakdown };

  const dimensions = Object.entries(DIMENSION_META).map(([key, meta]) => ({
    key,
    ...meta,
    score: Math.round(merged[key] ?? 0),
  }));

  // Sort by score descending
  dimensions.sort((a, b) => b.score - a.score);

  return (
    <div>
      {/* Compact header: score + rank + percentile */}
      <div className="flex items-center gap-3 mb-3">
        {/* Rank Badge */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, delay: 0.3 }}
          className="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg flex-shrink-0"
          style={{ background: rankStyle.bg, boxShadow: `0 4px 15px ${rankStyle.glow}40` }}
        >
          <span className="text-xl font-black" style={{ color: rankStyle.text }}>
            {rankLetter}
          </span>
        </motion.div>

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <motion.span
              className="text-3xl font-bold text-gray-900"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              {score}
            </motion.span>
            <span className="text-xs text-gray-400">/100</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500">{rank}</span>
            {percentile > 0 && (
              <span className="text-[10px] text-gray-400">
                Top {100 - percentile}%
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-2 rounded-full bg-gray-100 overflow-hidden mb-2">
        <motion.div
          className="h-full rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(0, Math.min(100, score))}%` }}
          transition={{ duration: 1, delay: 0.4, ease: 'easeOut' }}
          style={{
            background: `linear-gradient(90deg, ${rankStyle.glow}, ${rankStyle.glow}CC)`,
          }}
        />
      </div>

      {/* Expand toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-center gap-1 text-[10px] text-gray-400 hover:text-gray-600 py-1 transition-colors"
      >
        <span>{expanded ? 'Hide' : 'Show'} breakdown</span>
        {expanded ? <FaChevronUp /> : <FaChevronDown />}
      </button>

      {/* Dimension breakdown */}
      {expanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="space-y-2 mt-2"
        >
          {dimensions.map((dim, i) => (
            <motion.div
              key={dim.key}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <div className="flex items-center justify-between mb-0.5">
                <div className="flex items-center gap-1">
                  <span className="text-xs">{dim.icon}</span>
                  <span className="text-[10px] text-gray-600">{dim.label}</span>
                  <span className="text-[9px] text-gray-300">({dim.weight})</span>
                </div>
                <span className="text-[10px] font-semibold text-gray-800">{dim.score}</span>
              </div>
              <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${dim.score}%` }}
                  transition={{ duration: 0.6, delay: 0.1 + i * 0.05 }}
                  style={{ backgroundColor: dim.color }}
                />
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
};

export default MentoScoreBreakdown;
