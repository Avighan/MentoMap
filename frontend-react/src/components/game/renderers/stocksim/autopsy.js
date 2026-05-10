export function pickBestTrade(log) {
  if (!Array.isArray(log) || log.length === 0) return null;
  const closed = log.filter(t => typeof t.realized_pnl === 'number');
  if (closed.length === 0) return null;
  return closed.reduce((a, b) => (a.realized_pnl >= b.realized_pnl ? a : b));
}

export function pickWorstTrade(log) {
  if (!Array.isArray(log) || log.length === 0) return null;
  const closed = log.filter(t => typeof t.realized_pnl === 'number');
  if (closed.length === 0) return null;
  return closed.reduce((a, b) => (a.realized_pnl <= b.realized_pnl ? a : b));
}

export function whatWouldHaveBeenBetter(trade, marketCtx = []) {
  if (!trade) return '';
  if (trade.realized_pnl > 0) {
    return `Locked in \u20b9${trade.realized_pnl} on ${trade.symbol}. Could you have held longer? Check the news.`;
  }
  if (trade.realized_pnl < 0) {
    if ((trade.news_at_tick || []).length === 0) {
      return `Lost \u20b9${Math.abs(trade.realized_pnl)} on ${trade.symbol} with no news catalyst \u2014 likely chased noise.`;
    }
    return `Lost \u20b9${Math.abs(trade.realized_pnl)} on ${trade.symbol}. The news was already priced in by the time you bought.`;
  }
  return `Even trade on ${trade.symbol}. No conviction either way.`;
}
