/**
 * MysteryRoomRenderer — Frontend renderer for `mystery_room` game type.
 *
 * Backend lives in `backend/engines/escape_room_engine.py` and is wired through
 * the standard `/api/run/<id>/choose` endpoint. The engine accepts an action
 * payload like `{ action: "examine" | "pickup" | "move_to_room" | ... , target, ... }`
 * directly on the request body (see `backend/app.py` mystery_room dispatch).
 *
 * This file is the skeleton (Task 16). Hotspots, inventory, and puzzle modal
 * are wired in later tasks.
 */
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getRunState, submitMysteryAction } from '../../../api/games';
import HotspotLayer from '../mystery/HotspotLayer';
import InventoryDrawer from '../mystery/InventoryDrawer';
import PuzzleModal from '../mystery/PuzzleModal';
import EvidenceBoardModal from '../mystery/EvidenceBoardModal';
import ClimaxModal from '../mystery/ClimaxModal';

const MysteryRoomRenderer = ({
  gameData,
  gameState,         // initial snapshot from GamePlayPage (may be stale)
  runId,
  onComplete,        // eslint-disable-line no-unused-vars -- used by later tasks
  onBack,
  playerProfile,     // eslint-disable-line no-unused-vars -- used by later tasks
}) => {
  const [runState, setRunState] = useState(gameState || null);
  const [loading, setLoading] = useState(!gameState);
  const [error, setError] = useState(null);

  // Puzzle modal state (Task 19)
  const [openPuzzleId, setOpenPuzzleId] = useState(null);
  const [lastPuzzleResult, setLastPuzzleResult] = useState(null);

  // Evidence board modal state (Task 20)
  const [boardOpen, setBoardOpen] = useState(false);
  const [boardResult, setBoardResult] = useState(null);

  // Climax modal state (Task 21)
  const [climaxOpen, setClimaxOpen] = useState(false);

  // Stable label map for evidence items (used by EvidenceBoardModal).
  const evidenceLabels = useMemo(() => {
    const labels = {};
    (gameData?.items || []).forEach((it) => { labels[it.id] = it.name || it.label || it.id; });
    (gameData?.puzzles || []).forEach((p) => {
      if (p.evidence_id) labels[p.evidence_id] = (p.prompt || '').slice(0, 80) || p.evidence_id;
    });
    return labels;
  }, [gameData]);

  // ── Initial state fetch ────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    if (!runId) return;
    (async () => {
      try {
        const state = await getRunState(runId);
        if (!cancelled) {
          setRunState(state);
          setLoading(false);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e?.message || 'Failed to load mystery room state');
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [runId]);

  // ── Action helper — POSTs an arbitrary mystery_room payload and applies
  //    the returned state. Returns the full response so callers can read
  //    `events` / `climax_unlocked` / etc.
  const action = useCallback(async (payload) => {
    const resp = await submitMysteryAction(runId, payload);
    if (resp?.state) {
      // The backend returns `climax_unlocked` alongside `state` (it's
      // computed from gating_status, not stored on the run). Merge it in
      // so the renderer can read runState.climax_unlocked uniformly.
      const merged = { ...resp.state };
      if (Array.isArray(resp.climax_unlocked)) {
        merged.climax_unlocked = resp.climax_unlocked;
      }
      setRunState(merged);
    }
    return resp;
  }, [runId]);

  // ── Derived: current room ──────────────────────────────────────────────
  const currentRoomId = runState?.current_room || gameData?.rooms?.[0]?.id;

  const room = useMemo(() => {
    const rooms = gameData?.rooms || [];
    return rooms.find(r => r.id === currentRoomId) || null;
  }, [gameData, currentRoomId]);

  // ── Hotspot / inventory callbacks (declared before any early return so
  //    React's rules-of-hooks ordering is preserved). ─────────────────────
  const handleExamine = useCallback((spot) => {
    if (!spot) return;
    if (spot.yields_item) {
      action({ action: 'pickup', target: `hotspot:${spot.id}` });
    } else {
      action({ action: 'examine', target: `hotspot:${spot.id}` });
      if (spot.puzzle_id) setOpenPuzzleId(spot.puzzle_id);
    }
  }, [action]);

  // Climax trigger gating: when the player has visited every required room
  // and has not already chosen an outcome, the next move attempt opens the
  // climax modal instead of moving rooms.
  const visitedRooms = runState?.rooms_visited || [];
  const requiredVisits = gameData?.climax?.trigger?.must_visit || [];
  const canTriggerClimax =
    requiredVisits.length > 0 &&
    requiredVisits.every((r) => visitedRooms.includes(r)) &&
    !runState?.outcome_label;

  const handleMoveTo = useCallback((to) => {
    if (!to) return;
    if (canTriggerClimax) {
      setClimaxOpen(true);
      return;
    }
    action({ action: 'move_to_room', target: to });
  }, [action, canTriggerClimax]);

  // ── Inventory item click → log examine event server-side; if the item
  //    has a puzzle attached, queue it up for the puzzle modal (Task 19).
  const handleItemClick = useCallback((item) => {
    if (!item) return;
    if (item.puzzle_on_examine) setOpenPuzzleId(item.puzzle_on_examine);
    action({
      action: 'examine',
      target: `item:${item.id}`,
      openPuzzle: item.puzzle_on_examine || null,
    });
  }, [action]);

  // ── Render guards ──────────────────────────────────────────────────────
  if (loading && !room) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-gray-500">
        Loading mystery room…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
        <div className="text-5xl mb-4">⚠️</div>
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={onBack}
          className="px-5 py-2 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700"
        >
          Back to Games
        </button>
      </div>
    );
  }

  if (!room) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-gray-500">
        Loading mystery room…
      </div>
    );
  }

  // ── 16:9 stage with full-bleed room background ─────────────────────────
  return (
    <div className="relative w-full max-w-6xl mx-auto">
      <div
        className="relative w-full overflow-hidden rounded-2xl shadow-xl bg-gray-900"
        style={{ aspectRatio: '16 / 9' }}
      >
        {room.background_image ? (
          <img
            src={room.background_image}
            alt={room.name || room.id}
            className="absolute inset-0 w-full h-full object-cover"
            draggable={false}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400">
            {room.name || room.id}
          </div>
        )}

        {/* Stuck button (placeholder — real wiring in Task 23) */}
        <button
          type="button"
          className="absolute top-3 left-3 z-20 px-3 py-1.5 rounded-full bg-white/90 hover:bg-white text-sm font-semibold shadow"
          aria-label="I'm stuck — get a hint"
          onClick={() => { /* Task 23 */ }}
        >
          🤔 I'm stuck
        </button>

        {/* Evidence Board trigger (Task 20) */}
        <button
          type="button"
          onClick={() => setBoardOpen(true)}
          disabled={(runState?.evidence_collected || []).length < 3}
          className="absolute top-3 right-3 z-20 px-3 py-1.5 rounded-full bg-emerald-500 text-black text-sm font-semibold shadow hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed"
          title={
            (runState?.evidence_collected || []).length < 3
              ? 'Collect at least 3 pieces of evidence first'
              : 'Open the evidence board'
          }
          aria-label="Open evidence board"
        >
          📋 Evidence Board ({(runState?.evidence_collected || []).length})
        </button>

        {/* Hotspot + exit layer */}
        <HotspotLayer
          hotspots={room.hotspots || []}
          exits={room.exits || []}
          onExamine={handleExamine}
          onMoveTo={handleMoveTo}
        />
      </div>

      <InventoryDrawer
        items={gameData?.items || []}
        inventory={runState?.inventory || []}
        onItemClick={handleItemClick}
      />

      {/* Climax modal (Task 21) */}
      {climaxOpen && (
        <ClimaxModal
          climax={gameData?.climax}
          unlocked={runState?.climax_unlocked || []}
          onClose={() => setClimaxOpen(false)}
          onChoose={async (choice) => {
            await action({ action: 'climax_choose', choice });
            setClimaxOpen(false);
          }}
        />
      )}

      {/* Evidence board modal (Task 20) */}
      {boardOpen && (
        <EvidenceBoardModal
          board={gameData?.evidence_board}
          evidenceCollected={runState?.evidence_collected || []}
          evidenceLabels={evidenceLabels}
          lastResult={boardResult}
          onClose={() => setBoardOpen(false)}
          onSubmit={async (groupings) => {
            const resp = await action({ action: 'submit_synthesis', groupings });
            const ev = (resp?.events || []).find((e) => e.type === 'synthesis_result');
            if (ev) setBoardResult({ correct: ev.correct, accuracy: ev.accuracy });
          }}
        />
      )}

      {/* Puzzle modal (Task 19) */}
      {openPuzzleId && (() => {
        const puzzle = (gameData?.puzzles || []).find((p) => p.id === openPuzzleId);
        if (!puzzle) return null;
        return (
          <PuzzleModal
            puzzle={puzzle}
            lastResult={lastPuzzleResult}
            onClose={() => { setOpenPuzzleId(null); setLastPuzzleResult(null); }}
            onSubmit={async (pid, answer) => {
              const resp = await action({ action: 'solve_puzzle', puzzle_id: pid, answer });
              const ev = (resp?.events || []).find((e) => e.type === 'puzzle_result');
              if (ev) setLastPuzzleResult({ puzzle_id: pid, correct: ev.correct });
            }}
          />
        );
      })()}
    </div>
  );
};

export default MysteryRoomRenderer;
