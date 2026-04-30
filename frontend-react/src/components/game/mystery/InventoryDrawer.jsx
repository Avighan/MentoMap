/**
 * InventoryDrawer — sliding side panel listing the player's collected items.
 *
 * Props:
 *   - items:     Array<{ id, name, icon?, description?, puzzle_on_examine? }>
 *                Full item catalog from the game JSON.
 *   - inventory: string[]   IDs of items currently held (from runState.inventory).
 *   - onItemClick(item)
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const InventoryDrawer = ({ items = [], inventory = [], onItemClick }) => {
  const [open, setOpen] = useState(false);

  const heldItems = (inventory || [])
    .map((id) => items.find((it) => it.id === id))
    .filter(Boolean);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Toggle inventory (${heldItems.length} items)`}
        aria-expanded={open}
        className="fixed right-4 top-1/2 -translate-y-1/2 z-30 px-3 py-2 rounded-l-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold shadow-lg flex items-center gap-2"
      >
        <span aria-hidden>🎒</span>
        <span>{heldItems.length}</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.aside
            key="inv-drawer"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="fixed right-0 top-0 bottom-0 w-80 max-w-[85vw] z-40 bg-white shadow-2xl border-l border-gray-200 flex flex-col"
            role="dialog"
            aria-label="Inventory"
          >
            <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-amber-50">
              <h3 className="font-bold text-gray-800">🎒 Inventory</h3>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close inventory"
                className="text-gray-500 hover:text-gray-800 text-xl leading-none"
              >
                ×
              </button>
            </header>

            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {heldItems.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-8">
                  No items yet. Examine the room to find clues.
                </p>
              )}
              {heldItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onItemClick?.(item)}
                  className="w-full flex items-start gap-3 p-3 rounded-lg border border-gray-200 hover:border-amber-400 hover:bg-amber-50 transition-colors text-left"
                >
                  <span className="text-2xl shrink-0" aria-hidden>{item.icon || '📦'}</span>
                  <span className="flex-1 min-w-0">
                    <span className="block font-semibold text-gray-800 truncate">
                      {item.name || item.id}
                    </span>
                    {item.description && (
                      <span className="block text-xs text-gray-500 line-clamp-2">
                        {item.description}
                      </span>
                    )}
                  </span>
                </button>
              ))}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
};

export default InventoryDrawer;
