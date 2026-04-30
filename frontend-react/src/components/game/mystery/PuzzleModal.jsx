/**
 * PuzzleModal — modal for factual, interpretive, and ordering puzzles
 * (Task 19 of mystery-room plan).
 *
 * Props:
 *   puzzle      — the puzzle object from `gameData.puzzles[]`. Supports:
 *                   • type: "factual" with `options` + `correct` index
 *                   • type: "factual" with `ordering_items` (drag/order list)
 *                   • type: "interpretive" with `options` + `skill_tags_per_option`
 *   onSubmit(puzzleId, answer)  — async callback. `answer` is an option index for
 *                                 multiple-choice puzzles, or an array of item IDs
 *                                 for ordering puzzles.
 *   onClose()   — close handler.
 *   lastResult  — { puzzle_id, correct } from the most recent solve_puzzle response.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function PuzzleModal({ puzzle, onSubmit, onClose, lastResult }) {
  const [selected, setSelected] = useState(null);
  if (!puzzle) return null;
  const isOrdering = !!puzzle.ordering_items;
  const showExplanation = lastResult && lastResult.puzzle_id === puzzle.id;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="puzzle-title"
      >
        <motion.div
          className="bg-stone-100 rounded-lg max-w-2xl w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto"
          initial={{ scale: 0.95 }}
          animate={{ scale: 1 }}
        >
          <h2 id="puzzle-title" className="text-xl font-semibold mb-3 text-stone-900">
            {puzzle.prompt}
          </h2>

          {puzzle.audio_clips && puzzle.audio_clips.length > 0 && (
            <div className="mb-4 space-y-2">
              {puzzle.audio_clips.map((src, i) => (
                <audio
                  key={i}
                  controls
                  src={src}
                  className="w-full"
                  aria-label={`Voicemail ${i + 1}`}
                />
              ))}
            </div>
          )}

          {!isOrdering && puzzle.options && (
            <ol className="space-y-2">
              {puzzle.options.map((opt, i) => (
                <li key={i}>
                  <button
                    onClick={() => setSelected(i)}
                    className={`w-full text-left px-4 py-3 rounded border transition-colors ${
                      selected === i
                        ? 'bg-amber-200 border-amber-500'
                        : 'bg-white border-stone-300 hover:bg-stone-50'
                    }`}
                  >
                    {opt}
                  </button>
                </li>
              ))}
            </ol>
          )}

          {isOrdering && (
            <OrderingPuzzle
              items={puzzle.ordering_items}
              onChange={setSelected}
              value={selected}
            />
          )}

          {showExplanation && (
            <div
              className={`mt-4 p-3 rounded ${
                lastResult.correct ? 'bg-emerald-100' : 'bg-rose-100'
              }`}
            >
              <p className="text-sm text-stone-800">
                {lastResult.correct
                  ? puzzle.explanation_correct ||
                    'Correct! Nicely reasoned.'
                  : puzzle.explanation_wrong || 'Not quite — try again.'}
              </p>
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
              disabled={selected === null}
              onClick={() => onSubmit(puzzle.id, selected)}
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

function OrderingPuzzle({ items, onChange, value }) {
  const initial = Array.isArray(value) ? value : items.map((it) => it.id);
  const [order, setOrder] = useState(initial);

  const move = (idx, dir) => {
    const newOrder = [...order];
    const target = idx + dir;
    if (target < 0 || target >= newOrder.length) return;
    [newOrder[idx], newOrder[target]] = [newOrder[target], newOrder[idx]];
    setOrder(newOrder);
    onChange(newOrder);
  };

  return (
    <ol className="space-y-2">
      {order.map((id, idx) => {
        const item = items.find((it) => it.id === id);
        if (!item) return null;
        return (
          <li
            key={id}
            className="flex items-center gap-2 px-3 py-2 bg-white border border-stone-300 rounded"
          >
            <span className="w-6 font-mono text-stone-500">{idx + 1}.</span>
            <span className="flex-1 text-stone-800">{item.label}</span>
            <button
              onClick={() => move(idx, -1)}
              aria-label="Move up"
              disabled={idx === 0}
              className="px-2 py-1 rounded hover:bg-stone-100 disabled:opacity-30"
            >
              ↑
            </button>
            <button
              onClick={() => move(idx, 1)}
              aria-label="Move down"
              disabled={idx === order.length - 1}
              className="px-2 py-1 rounded hover:bg-stone-100 disabled:opacity-30"
            >
              ↓
            </button>
          </li>
        );
      })}
    </ol>
  );
}
