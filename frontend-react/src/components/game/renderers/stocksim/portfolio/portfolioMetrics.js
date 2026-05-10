// portfolioMetrics.js
/**
 * Pure portfolio analytics helpers consumed by the portfolio modal.
 *
 * All functions are pure and accept the shapes produced by the stocksim
 * client component (transactions, holdings keyed by symbol, prices keyed by
 * symbol). They tolerate `null`/`undefined` inputs by returning a neutral
 * value rather than throwing.
 */

/**
 * Maximum peak-to-trough percent decline across a value series.
 *
 * Precondition: series values are expected to be positive (e.g. net worth
 * with non-zero starting cash). When the running peak is non-positive the
 * percent formula is undefined; this function returns 0 in that branch.
 *
 * @param {number[]} series
 * @returns {number} drawdown percent in [0, 100]
 */
export function maxDrawdown(series) {
  if (!series || series.length < 2) return 0;
  let peak = series[0];
  let maxDD = 0;
  for (const v of series) {
    if (v > peak) peak = v;
    if (peak > 0) {
      const dd = ((peak - v) / peak) * 100;
      if (dd > maxDD) maxDD = dd;
    }
  }
  return maxDD;
}

/**
 * Largest position by market value as a percent of total portfolio market
 * value.
 *
 * Holdings with `qty === 0` are skipped. Holdings with a missing price are
 * valued at 0 and contribute 0 to the total — they cannot become `best`
 * unless every other position is also zero-valued.
 *
 * @param {Record<string, { qty: number }>} holdings
 * @param {Record<string, number>} prices
 * @returns {{ symbol: string, pct: number } | null}
 */
export function concentration(holdings, prices) {
  let total = 0;
  let best = null;
  for (const sym of Object.keys(holdings || {})) {
    const qty = holdings[sym]?.qty ?? 0;
    if (!qty) continue;
    const px = prices?.[sym] ?? 0;
    const mv = qty * px;
    total += mv;
    if (!best || mv > best.mv) best = { symbol: sym, mv };
  }
  if (!best || total <= 0) return null;
  return { symbol: best.symbol, pct: (best.mv / total) * 100 };
}

/**
 * Win/loss statistics over closed (sell-side) trades that carry a numeric
 * `realized_pnl` field. Sells without that field are silently excluded.
 *
 * @param {Array<{ side: string, realized_pnl?: number }>} transactions
 * @returns {{ winRate: number, avgWin: number, avgLoss: number, totalClosed: number }}
 */
export function hitRatio(transactions) {
  const closed = (transactions || []).filter(
    (t) => t.side === 'sell' && typeof t.realized_pnl === 'number'
  );
  if (closed.length === 0) return { winRate: 0, avgWin: 0, avgLoss: 0, totalClosed: 0 };
  const wins = closed.filter((t) => t.realized_pnl > 0);
  const losses = closed.filter((t) => t.realized_pnl < 0);
  const sum = (a) => a.reduce((s, t) => s + t.realized_pnl, 0);
  return {
    totalClosed: closed.length,
    winRate: wins.length / closed.length,
    avgWin: wins.length ? sum(wins) / wins.length : 0,
    avgLoss: losses.length ? sum(losses) / losses.length : 0,
  };
}
