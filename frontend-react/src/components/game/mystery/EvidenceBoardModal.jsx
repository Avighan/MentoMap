/**
 * EvidenceBoardModal — synthesis grouping UI for the mystery_room game type
 * (Task 20 of mystery-room plan).
 *
 * The player drags each collected evidence item into one of the buckets
 * defined by `gameData.evidence_board.buckets`. On submit, the renderer
 * dispatches `submit_synthesis` to the backend.
 *
 * Props:
 *   board               — gameData.evidence_board (prompt, buckets[]).
 *   evidenceCollected   — IDs of evidence the player has gathered so far.
 *   evidenceLabels      — { [evidenceId]: humanLabel }.
 *   onSubmit(groupings) — async, dispatches submit_synthesis.
 *   onClose()           — close handler.
 *   lastResult          — { correct, accuracy } from the most recent synthesis_result event.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function EvidenceBoardModal({
  board,
  evidenceCollected,
  evidenceLabels,
  onSubmit,
  onClose,
  lastResult,
}) {
  const [groupings, setGroupings] = useState({});
  if (!board) return null;

  const setBucket = (itemId, bucketId) =>
    setGroupings((g) => ({ ...g, [itemId]: bucketId }));

  const allAssigned =
    evidenceCollected.length > 0 &&
    Object.keys(groupings).length >= evidenceCollected.length;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-board-title"
      >
        <motion.div
          className="bg-stone-100 rounded-lg max-w-4xl w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto"
          initial={{ scale: 0.95 }}
          animate={{ scale: 1 }}
        >
          <h2 id="evidence-board-title" className="text-xl font-semibold mb-2 text-stone-900">
            {board.prompt || 'Evidence Board'}
          </h2>
          <p className="text-sm text-stone-600 mb-4">
            For each piece of evidence, click the bucket where it belongs.
          </p>

          {evidenceCollected.length === 0 ? (
            <p className="text-sm text-stone-500 italic">
              You haven't collected any evidence yet.
            </p>
          ) : (
            <div className="space-y-3">
              {evidenceCollected.map((eid) => (
                <div
                  key={eid}
                  className="flex flex-wrap items-center gap-3 p-2 bg-white rounded border border-stone-200"
                >
                  <span className="flex-1 min-w-[180px] font-medium text-stone-800">
                    {evidenceLabels[eid] || eid}
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {(board.buckets || []).map((b) => {
                      const bid = typeof b === 'string' ? b : b.id;
                      const blabel = typeof b === 'string' ? b : b.label || b.id;
                      return (
                        <button
                          key={bid}
                          onClick={() => setBucket(eid, bid)}
                          className={`px-3 py-1 rounded text-xs transition-colors ${
                            groupings[eid] === bid
                              ? 'bg-amber-500 text-black font-semibold'
                              : 'bg-stone-200 text-stone-700 hover:bg-stone-300'
                          }`}
                        >
                          {blabel}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {lastResult && (
            <div
              className={`mt-4 p-3 rounded ${
                lastResult.correct ? 'bg-emerald-100' : 'bg-rose-100'
              }`}
            >
              {lastResult.correct ? (
                <p className="text-sm text-stone-800">
                  Correct synthesis. The Whistleblower ending is now unlocked.
                </p>
              ) : (
                <p className="text-sm text-stone-800">
                  Not quite — accuracy {Math.round((lastResult.accuracy || 0) * 100)}%.
                  Try rearranging.
                </p>
              )}
            </div>
          )}

          <div className="mt-5 flex gap-3 justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded text-stone-700 hover:bg-stone-200"
            >
              Close
            </button>
            <button
              disabled={!allAssigned}
              onClick={() => onSubmit(groupings)}
              className="px-4 py-2 rounded bg-emerald-600 text-white disabled:opacity-50 hover:bg-emerald-700"
            >
              Submit
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
