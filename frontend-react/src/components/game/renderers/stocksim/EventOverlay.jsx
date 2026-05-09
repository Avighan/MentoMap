/**
 * EventOverlay — full-width event banner for the stocksim.
 *
 * Replaces the older inline activeEvent banner. Renders a richer overlay
 * with severity-based gradient (info → purple/indigo, warning → amber/orange,
 * crisis → red/rose), framer-motion entrance, and auto-dismiss after 4s.
 *
 * Props:
 *   event      { title, description, severity?, icon? } | null
 *   onDismiss  () => void
 */
import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const GRADIENTS = {
  info: 'from-purple-600 to-indigo-600',
  warning: 'from-amber-500 to-orange-600',
  crisis: 'from-red-600 to-rose-700',
};

const TEXT_TINT = {
  info: 'text-purple-100',
  warning: 'text-amber-100',
  crisis: 'text-rose-100',
};

const DEFAULT_ICONS = {
  info: '📊',
  warning: '⚠️',
  crisis: '🚨',
};

const EventOverlay = ({ event, onDismiss }) => {
  useEffect(() => {
    if (!event) return undefined;
    const t = setTimeout(() => onDismiss?.(), 4000);
    return () => clearTimeout(t);
  }, [event, onDismiss]);

  return (
    <AnimatePresence>
      {event && (
        <motion.div
          data-testid="stocksim-event-overlay"
          initial={{ opacity: 0, y: -24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -24 }}
          transition={{ duration: 0.3 }}
          className={`mx-6 mt-3 bg-gradient-to-r ${
            GRADIENTS[event.severity] || GRADIENTS.info
          } text-white rounded-xl p-4 shadow-lg`}
        >
          <div className="flex items-center gap-3">
            <span className="text-3xl" aria-hidden="true">
              {event.icon || DEFAULT_ICONS[event.severity] || '📊'}
            </span>
            <div className="flex-1">
              <h3 className="font-bold text-lg">
                {event.title || 'Market Event'}
              </h3>
              {event.description && (
                <p
                  className={`text-sm ${
                    TEXT_TINT[event.severity] || TEXT_TINT.info
                  }`}
                >
                  {event.description}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => onDismiss?.()}
              className="ml-2 text-white/80 hover:text-white text-lg leading-none"
              aria-label="Dismiss event"
            >
              ×
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default EventOverlay;
