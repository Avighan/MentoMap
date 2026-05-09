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
import { THEME } from './theme';

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
          className="mx-6 mt-3 rounded-xl p-4 shadow-lg"
          style={{
            backgroundColor: THEME.bgTile,
            borderLeft: `3px solid ${THEME.accentWarm}`,
          }}
        >
          <div className="flex items-center gap-3">
            <span className="text-3xl" aria-hidden="true">
              {event.icon || DEFAULT_ICONS[event.severity] || '📊'}
            </span>
            <div className="flex-1">
              <h3
                className="font-bold text-lg"
                style={{ color: THEME.textPrimary }}
              >
                {event.title || 'Market Event'}
              </h3>
              {event.description && (
                <p className="text-sm" style={{ color: THEME.textMuted }}>
                  {event.description}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => onDismiss?.()}
              className="ml-2 text-lg leading-none"
              style={{ color: THEME.textMuted }}
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
