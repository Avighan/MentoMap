/**
 * ClimaxModal — gated 4-option fork at the climax of a mystery_room game
 * (Task 21 of mystery-room plan).
 *
 * Displays the climax's narrative text and four options. Options the
 * player has not yet unlocked (per `gameData.climax.options[].gating` /
 * `runState.climax_unlocked` / engine.gating_status) are shown locked
 * with a tooltip-style gating message.
 *
 * Props:
 *   climax    — gameData.climax ({ modal_text, options: [{ id, label, gating_message }] }).
 *   unlocked  — array of option IDs that are unlocked.
 *   onChoose(optionId) — invoked when the player commits to an option.
 *   onClose()          — invoked when the player dismisses the modal.
 */
import { motion, AnimatePresence } from 'framer-motion';

export default function ClimaxModal({ climax, unlocked = [], onChoose, onClose }) {
  if (!climax) return null;
  const options = climax.options || [];

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="climax-title"
      >
        <motion.div
          className="bg-stone-900 text-stone-100 rounded-lg max-w-2xl w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto"
          initial={{ scale: 0.95 }}
          animate={{ scale: 1 }}
        >
          <h2 id="climax-title" className="sr-only">Climax decision</h2>
          <p className="text-base mb-5 italic text-stone-200">{climax.modal_text}</p>

          <ul className="space-y-3">
            {options.map((opt) => {
              const isUnlocked = unlocked.includes(opt.id);
              return (
                <li key={opt.id}>
                  <button
                    onClick={() => isUnlocked && onChoose(opt.id)}
                    disabled={!isUnlocked}
                    className={`w-full text-left px-4 py-3 rounded border transition-colors ${
                      isUnlocked
                        ? 'bg-stone-800 hover:bg-stone-700 border-stone-700'
                        : 'bg-stone-950 border-stone-800 opacity-40 cursor-not-allowed'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span>{opt.label}</span>
                      {!isUnlocked && (
                        <span className="text-xs text-stone-500 flex-shrink-0">
                          🔒 {opt.gating_message || 'Locked'}
                        </span>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="mt-4 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-stone-400 hover:text-stone-200"
            >
              Wait — let me look around more
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
