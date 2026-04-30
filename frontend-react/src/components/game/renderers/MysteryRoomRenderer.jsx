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

  // Will be wired in Task 19 (PuzzleModal). Tracked here so Task 17 / 18
  // can already point puzzles at it.
  // eslint-disable-next-line no-unused-vars
  const [openPuzzleId, setOpenPuzzleId] = useState(null);

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
    if (resp?.state) setRunState(resp.state);
    return resp;
  }, [runId]);

  // ── Derived: current room ──────────────────────────────────────────────
  const currentRoomId = runState?.current_room || gameData?.rooms?.[0]?.id;

  const room = useMemo(() => {
    const rooms = gameData?.rooms || [];
    return rooms.find(r => r.id === currentRoomId) || null;
  }, [gameData, currentRoomId]);

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

  // ── Hotspot callbacks ──────────────────────────────────────────────────
  const handleExamine = useCallback((spot) => {
    if (!spot) return;
    if (spot.yields_item) {
      action({ action: 'pickup', target: `hotspot:${spot.id}` });
    } else {
      action({ action: 'examine', target: `hotspot:${spot.id}` });
      if (spot.puzzle_id) setOpenPuzzleId(spot.puzzle_id);
    }
  }, [action]);

  const handleMoveTo = useCallback((to) => {
    if (!to) return;
    action({ action: 'move_to_room', target: to });
  }, [action]);

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

        {/* Hotspot + exit layer */}
        <HotspotLayer
          hotspots={room.hotspots || []}
          exits={room.exits || []}
          onExamine={handleExamine}
          onMoveTo={handleMoveTo}
        />
      </div>
    </div>
  );
};

export default MysteryRoomRenderer;
