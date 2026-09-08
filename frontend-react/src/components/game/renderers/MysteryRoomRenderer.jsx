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
import HintButton from '../mystery/HintButton';

const MysteryRoomRenderer = ({
  gameData,
  gameState,         // initial snapshot from GamePlayPage (may be stale)
  runId,
  onComplete,
  onBack,
  playerProfile,     // eslint-disable-line no-unused-vars -- used by later tasks
}) => {
  const [runState, setRunState] = useState(gameState || null);
  const [loading, setLoading] = useState(!gameState);
  const [error, setError] = useState(null);

  // The climax modal's onChoose sets run_state.outcome_label on the backend
  // (see escape_room_engine.py's _climax_choose) but nothing here ever read
  // it back out — the case never actually "ended" from the page's point of
  // view. Fire onComplete exactly once when it first appears.
  const completedRef = React.useRef(false);
  useEffect(() => {
    if (runState?.outcome_label && !completedRef.current) {
      completedRef.current = true;
      onComplete?.(runState);
    }
  }, [runState?.outcome_label, onComplete]);

  // Puzzle modal state (Task 19)
  const [openPuzzleId, setOpenPuzzleId] = useState(null);
  const [lastPuzzleResult, setLastPuzzleResult] = useState(null);

  // Evidence board modal state (Task 20)
  const [boardOpen, setBoardOpen] = useState(false);
  const [boardResult, setBoardResult] = useState(null);

  // Climax modal state (Task 21)
  const [climaxOpen, setClimaxOpen] = useState(false);

  // Inventory drawer open state — lifted into the renderer so the global
  // keyboard handler (Task 25: I=toggle, Esc=close) can drive it.
  const [inventoryOpen, setInventoryOpen] = useState(false);

  // Mobile splash gate (Task 26). Mystery rooms rely on a 16:9 stage with
  // small tap-targets; on narrow phones we show a friendly "best on bigger
  // screen" interstitial instead.
  const [isNarrow, setIsNarrow] = useState(
    typeof window !== 'undefined' && window.innerWidth < 768
  );
  useEffect(() => {
    const onResize = () => setIsNarrow(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Hint ladder state (Task 23). Reset whenever the active puzzle changes
  // so a fresh puzzle starts at level 1.
  const [lastHint, setLastHint] = useState(null);
  useEffect(() => { setLastHint(null); }, [openPuzzleId]);

  // Soft auto-prompt (Task 24). After `auto_prompt_seconds` of inactivity
  // on an open puzzle, drop a level-0 nudge into `lastHint` once. The next
  // real hint (level 1+) replaces it.
  const [autoPromptShown, setAutoPromptShown] = useState({});
  const autoPromptSeconds = gameData?.hint_policy?.auto_prompt_seconds || 120;
  useEffect(() => {
    if (!openPuzzleId) return undefined;
    if (autoPromptShown[openPuzzleId]) return undefined;
    const timer = setTimeout(() => {
      setAutoPromptShown((p) => ({ ...p, [openPuzzleId]: true }));
      // Only nudge if no real hint has appeared in the meantime.
      setLastHint((prev) => prev || { level: 0, text: 'Need a hint? Try the 🤔 button.' });
    }, autoPromptSeconds * 1000);
    return () => clearTimeout(timer);
  }, [openPuzzleId, autoPromptShown, autoPromptSeconds]);

  // Page-level keyboard shortcuts (Task 25):
  //   - `I` / `i`   → toggle inventory
  //   - `Escape`    → close the topmost overlay (puzzle > board > climax > inventory)
  // Native <button> elements already support Tab focus + Enter activation,
  // which covers Tab navigation through hotspots and Enter to examine.
  useEffect(() => {
    const handler = (e) => {
      // Don't intercept while typing in form fields.
      const tag = e.target?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.target?.isContentEditable) return;

      if (e.key === 'i' || e.key === 'I') {
        setInventoryOpen((o) => !o);
        return;
      }
      if (e.key === 'Escape') {
        if (openPuzzleId) {
          setOpenPuzzleId(null);
          setLastPuzzleResult(null);
        } else if (boardOpen) {
          setBoardOpen(false);
        } else if (climaxOpen) {
          setClimaxOpen(false);
        } else if (inventoryOpen) {
          setInventoryOpen(false);
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [openPuzzleId, boardOpen, climaxOpen, inventoryOpen]);

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
  if (isNarrow) {
    return (
      <div className="max-w-md mx-auto my-8 p-8 text-center bg-stone-900 text-stone-100 rounded-2xl shadow-xl">
        <div className="text-5xl mb-3" aria-hidden>🖥️</div>
        <h2 className="text-xl font-semibold mb-3">Best on a bigger screen</h2>
        <p className="text-stone-300 mb-5">
          Mystery rooms work best on a tablet or laptop. Try this game when
          you&apos;re at a larger screen.
        </p>
        <button
          type="button"
          onClick={onBack || (() => window.history.back())}
          className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black rounded font-semibold"
        >
          Back
        </button>
      </div>
    );
  }

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

        {/* Hint ladder (Task 23) */}
        <HintButton
          activePuzzleId={openPuzzleId}
          lastHint={lastHint}
          onRequestHint={async () => {
            if (!openPuzzleId) return;
            const resp = await action({ action: 'request_hint', puzzle_id: openPuzzleId });
            const ev = (resp?.events || []).find((e) => e.type === 'hint');
            if (ev) setLastHint({ level: ev.level, text: ev.text });
          }}
        />

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
        open={inventoryOpen}
        onOpenChange={setInventoryOpen}
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
