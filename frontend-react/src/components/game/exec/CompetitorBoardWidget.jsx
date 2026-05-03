/**
 * CompetitorBoardWidget — 3-firm reactive AI competitor board for HBR sims.
 *
 * Renders `payload.ux_executive.competitor_board` (built by
 * backend/engines/competitor_ai_engine.build_competitor_payload).
 *
 * Shape:
 *   {
 *     competitors: [{id, name, persona, market_share, price,
 *                    marketing_spend, r_and_d_alloc, ...}],
 *     player: {market_share, price, marketing_spend, r_and_d_alloc},
 *     moves:  [{id, rationale, action_summary}],
 *     personas_in_play: [...]
 *   }
 *
 * Returns null when payload is null (no competitor_ai config on game).
 */
import React from 'react';

const PERSONA_BADGE = {
  aggressive_rd: {
    label: 'Aggressive R&D',
    bg: 'bg-fuchsia-900/40 text-fuchsia-300 border-fuchsia-700/40',
    icon: '🚀',
  },
  defensive_cost_leader: {
    label: 'Cost Leader',
    bg: 'bg-amber-900/40 text-amber-300 border-amber-700/40',
    icon: '🛡️',
  },
  fast_follower: {
    label: 'Fast Follower',
    bg: 'bg-cyan-900/40 text-cyan-300 border-cyan-700/40',
    icon: '🔄',
  },
  neutral: {
    label: 'Neutral',
    bg: 'bg-gray-700 text-gray-300 border-gray-600',
    icon: '○',
  },
};

const fmtMoney = (n) => {
  if (n === null || n === undefined || isNaN(n)) return '—';
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${Number(n).toFixed(0)}`;
};
const fmtPct = (n) => (n === null || n === undefined || isNaN(n) ? '—' : `${(n * 100).toFixed(1)}%`);
const fmtPctRaw = (n) => (n === null || n === undefined || isNaN(n) ? '—' : `${(n * 100).toFixed(0)}%`);

function FirmCard({ firm, isPlayer = false, lastMove = null }) {
  const persona = PERSONA_BADGE[firm.persona] || PERSONA_BADGE.neutral;
  return (
    <div
      className={`rounded-xl p-4 border ${
        isPlayer
          ? 'bg-emerald-900/20 border-emerald-700/40'
          : 'bg-gray-800/60 border-gray-700/60'
      }`}
      data-testid={`firm-card-${firm.id || (isPlayer ? 'player' : 'unknown')}`}
    >
      <div className="flex items-center justify-between mb-2 gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-white truncate">
            {isPlayer ? '🎯 You' : firm.name || firm.id}
          </div>
          {!isPlayer && (
            <span className={`inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider border ${persona.bg}`}>
              {persona.icon} {persona.label}
            </span>
          )}
        </div>
        <div className="text-right">
          <div className="text-2xl font-extrabold text-white tabular-nums">
            {fmtPct(firm.market_share)}
          </div>
          <div className="text-[10px] text-gray-400 uppercase tracking-wider">share</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs mt-2">
        <div className="bg-gray-900/50 rounded px-2 py-1.5">
          <div className="text-gray-500 text-[10px] uppercase">Price</div>
          <div className="text-gray-100 font-mono tabular-nums">${Number(firm.price || 0).toFixed(0)}</div>
        </div>
        <div className="bg-gray-900/50 rounded px-2 py-1.5">
          <div className="text-gray-500 text-[10px] uppercase">Mkt</div>
          <div className="text-gray-100 font-mono tabular-nums">{fmtMoney(firm.marketing_spend)}</div>
        </div>
        <div className="bg-gray-900/50 rounded px-2 py-1.5">
          <div className="text-gray-500 text-[10px] uppercase">R&D</div>
          <div className="text-gray-100 font-mono tabular-nums">{fmtPctRaw(firm.r_and_d_alloc)}</div>
        </div>
      </div>

      {lastMove && (lastMove.rationale || lastMove.action_summary) && (
        <div className="mt-2 text-[11px] text-gray-300 italic border-l-2 border-gray-600 pl-2">
          “{lastMove.rationale || lastMove.action_summary}”
        </div>
      )}
    </div>
  );
}

export default function CompetitorBoardWidget({ payload, className = '' }) {
  if (!payload || typeof payload !== 'object') return null;
  const competitors = payload.competitors || [];
  if (competitors.length === 0) return null;

  const movesById = {};
  (payload.moves || []).forEach((m) => {
    if (m && m.id) movesById[m.id] = m;
  });

  return (
    <div className={`bg-gray-900/60 border border-gray-700 rounded-xl p-5 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-white">⚔️ Competitor Board</h3>
        {payload.personas_in_play?.length > 0 && (
          <span className="text-xs text-gray-400">
            {payload.personas_in_play.length} persona{payload.personas_in_play.length > 1 ? 's' : ''} active
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-3">
        {payload.player && Object.keys(payload.player).length > 0 && (
          <FirmCard firm={payload.player} isPlayer={true} />
        )}
        {competitors.map((c) => (
          <FirmCard
            key={c.id || c.name}
            firm={c}
            lastMove={c.id ? movesById[c.id] : null}
          />
        ))}
      </div>

      {payload.moves?.length === 0 && (
        <p className="mt-3 text-[11px] text-gray-500 italic">
          Make a decision this round — competitors will respond on the next tick.
        </p>
      )}
    </div>
  );
}
