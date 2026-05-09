/**
 * NewsTickerStrip — horizontal scrolling chips for stocksim news.
 *
 * Renders a strip of news chips for ticks in [currentTick - 3, currentTick].
 * Color-codes chips by severity: info (blue), warning (amber), crisis (red).
 * Animates new items in with framer-motion. Scrolls horizontally if the
 * strip overflows.
 *
 * Props:
 *   newsStrip    Array<{ tick: number, text: string, severity?: string }>
 *   currentTick  number
 */
import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const SEVERITY = {
  info: 'bg-blue-50 text-blue-700 border-blue-200',
  warning: 'bg-amber-50 text-amber-800 border-amber-200',
  crisis: 'bg-red-50 text-red-700 border-red-200',
};

const NewsTickerStrip = ({ newsStrip = [], currentTick = 0 }) => {
  const items = useMemo(() => {
    if (!Array.isArray(newsStrip)) return [];
    return newsStrip
      .filter(
        (n) =>
          typeof n?.tick === 'number' &&
          n.tick <= currentTick &&
          n.tick >= currentTick - 3,
      )
      .sort((a, b) => b.tick - a.tick);
  }, [newsStrip, currentTick]);

  if (items.length === 0) return null;

  return (
    <div
      data-testid="stocksim-news-strip"
      className="px-6 py-2 overflow-x-auto whitespace-nowrap flex gap-2 bg-white/60 border-b border-gray-100"
    >
      <AnimatePresence initial={false}>
        {items.map((item, idx) => {
          const cls = SEVERITY[item.severity] || SEVERITY.info;
          return (
            <motion.span
              key={`${item.tick}-${idx}`}
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.25 }}
              className={`inline-flex items-center text-xs font-medium px-3 py-1 rounded-full border ${cls}`}
            >
              <span className="mr-2 text-[10px] uppercase tracking-wider opacity-70">
                T{item.tick}
              </span>
              <span className="truncate max-w-[320px]">{item.text}</span>
            </motion.span>
          );
        })}
      </AnimatePresence>
    </div>
  );
};

export default NewsTickerStrip;
