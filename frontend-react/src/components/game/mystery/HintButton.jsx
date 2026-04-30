/**
 * HintButton — 3-step hint ladder for mystery_room puzzles.
 *
 * Behaviour:
 *   - Disabled when no puzzle is open.
 *   - Each click escalates one rung up the ladder (level 1 → 2 → 3).
 *   - Before revealing the level-3 solution, asks the player to confirm
 *     ("Reveal the solution? You'll learn more by trying first.").
 *   - The current `lastHint` (if any) is rendered below the button as an
 *     amber callout. Level 0 is reserved for the soft auto-prompt
 *     ("Need a hint? Try the 🤔 button.") which originates outside this
 *     component.
 *
 * Props:
 *   - activePuzzleId: string | null
 *   - onRequestHint:  () => void   (parent issues the action and updates lastHint)
 *   - lastHint:       { level: number, text: string } | null
 */
import React, { useState } from 'react';

const HintButton = ({ activePuzzleId, onRequestHint, lastHint }) => {
  const [confirmingSolution, setConfirmingSolution] = useState(false);

  const handleClick = () => {
    // If the player is about to escalate from level 2 → 3 (the solution
    // reveal), gate behind a confirmation step.
    if (lastHint && lastHint.level === 2 && !confirmingSolution) {
      setConfirmingSolution(true);
      return;
    }
    setConfirmingSolution(false);
    onRequestHint?.();
  };

  return (
    <div className="absolute top-3 left-3 z-30 flex flex-col items-start gap-2 max-w-sm pointer-events-none">
      <button
        type="button"
        disabled={!activePuzzleId}
        onClick={handleClick}
        className="pointer-events-auto px-3 py-1.5 rounded-full bg-amber-500 hover:bg-amber-400 text-black text-sm font-semibold shadow disabled:opacity-40 disabled:cursor-not-allowed"
        title={!activePuzzleId ? "Open a puzzle first" : 'Get a hint'}
        aria-label="I'm stuck — get a hint"
      >
        🤔 I'm stuck{lastHint && lastHint.level > 0 ? ` (${lastHint.level}/3)` : ''}
      </button>

      {confirmingSolution && (
        <div className="pointer-events-auto bg-stone-100 border border-amber-500 rounded p-3 text-sm text-stone-800 shadow-lg">
          <p className="mb-2">Reveal the solution? You'll learn more by trying first.</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { setConfirmingSolution(false); onRequestHint?.(); }}
              className="px-2 py-1 bg-amber-500 hover:bg-amber-400 text-black rounded font-semibold"
            >
              Yes, reveal
            </button>
            <button
              type="button"
              onClick={() => setConfirmingSolution(false)}
              className="px-2 py-1 bg-stone-200 hover:bg-stone-300 text-stone-800 rounded"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {lastHint && (
        <div
          className="pointer-events-auto bg-amber-100 border border-amber-300 rounded p-3 text-sm text-stone-800 shadow-lg"
          role="status"
          aria-live="polite"
        >
          {lastHint.text}
        </div>
      )}
    </div>
  );
};

export default HintButton;
