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

/**
 * Per-tick sector market-value distribution computed by replaying
 * transactions over the price history.
 *
 * Returns one object per tick (length = `currentTick + 1`) of shape
 * `{ total: number, [sectorName]: percent }`. Symbols with no `sectorBySymbol`
 * entry are bucketed into `'Other'`. When `total <= 0` (no positions, or net
 * short positions dominating), every sector percent is forced to 0 but the
 * `total` field reflects the raw signed market value — a negative `total`
 * therefore signals a caller data issue (the function expects long-only
 * positions). The internal `cash` variable tracks running cash for symmetry
 * with `netWorthSeries`; it is not emitted, since this view is equity-only.
 *
 * @param {Array<{ tick: number, symbol: string, side: 'buy'|'sell', qty: number, price: number, charges?: number }>} transactions
 * @param {Record<string, number[]>} priceHistory
 * @param {Record<string, string>} sectorBySymbol
 * @param {number} startingCash
 * @param {number} currentTick
 * @returns {Array<Record<string, number>>}
 */
export function sectorExposureSeries(transactions, priceHistory, sectorBySymbol, startingCash, currentTick) {
  const sorted = [...(transactions || [])].sort((a, b) => (a.tick ?? 0) - (b.tick ?? 0));
  const holdings = {};
  let cash = startingCash;
  let i = 0;
  const out = [];
  for (let t = 0; t <= currentTick; t++) {
    while (i < sorted.length && (sorted[i].tick ?? 0) <= t) {
      const tx = sorted[i++];
      const cost = tx.qty * tx.price;
      const charges = tx.charges ?? 0;
      if (tx.side === 'buy') {
        cash -= cost + charges;
        holdings[tx.symbol] = (holdings[tx.symbol] ?? 0) + tx.qty;
      } else {
        cash += cost - charges;
        holdings[tx.symbol] = (holdings[tx.symbol] ?? 0) - tx.qty;
      }
    }
    const sectors = {};
    let total = 0;
    for (const sym of Object.keys(holdings)) {
      const qty = holdings[sym];
      if (!qty) continue;
      const series = priceHistory?.[sym] ?? [];
      const px = series[t] ?? series[series.length - 1] ?? 0;
      const mv = qty * px;
      total += mv;
      const sec = sectorBySymbol?.[sym] ?? 'Other';
      sectors[sec] = (sectors[sec] ?? 0) + mv;
    }
    const pcts = { total };
    for (const sec of Object.keys(sectors)) {
      pcts[sec] = total > 0 ? (sectors[sec] / total) * 100 : 0;
    }
    out.push(pcts);
  }
  return out;
}

/**
 * Equal-weight cumulative return percent across all symbols in
 * `priceHistory`, evaluated at every tick from 0 to `currentTick` inclusive.
 *
 * Symbols whose tick-0 price is `0`, `null`, or `undefined` are excluded
 * from the average to avoid division-by-zero — the caller is responsible
 * for ensuring opening prices are positive when those symbols should
 * participate in the benchmark.
 *
 * @param {Record<string, number[]>} priceHistory
 * @param {number} currentTick
 * @returns {number[]} cumulative return percent per tick
 */
export function benchmarkSeries(priceHistory, currentTick) {
  const symbols = Object.keys(priceHistory || {});
  if (symbols.length === 0) return [];
  const out = [];
  for (let t = 0; t <= currentTick; t++) {
    let sum = 0;
    let n = 0;
    for (const sym of symbols) {
      const arr = priceHistory[sym] ?? [];
      const start = arr[0];
      const cur = arr[t] ?? arr[arr.length - 1];
      if (start && cur != null) {
        sum += (cur - start) / start;
        n += 1;
      }
    }
    out.push(n ? (sum / n) * 100 : 0);
  }
  return out;
}

/**
 * Sums realized P&L per day window, grouping `sell`-side transactions that
 * carry a numeric `realized_pnl` field. Day window k owns ticks in the
 * half-open range `[sum(days[0..k-1].ticks), sum(days[0..k].ticks))`.
 * Transactions whose tick falls outside every window are silently dropped.
 *
 * @param {Array<{ tick?: number, side: string, realized_pnl?: number }>} transactions
 * @param {Array<{ id: string, label: string, ticks: number }>} days
 * @returns {Array<{ dayId: string, label: string, pnl: number }>}
 */
export function dayPnL(transactions, days) {
  const out = (days || []).map((d) => ({ dayId: d.id, label: d.label, pnl: 0 }));
  let cumulative = 0;
  const ranges = (days || []).map((d) => {
    const range = { start: cumulative, end: cumulative + d.ticks };
    cumulative = range.end;
    return range;
  });
  for (const tx of transactions || []) {
    if (tx.side !== 'sell' || typeof tx.realized_pnl !== 'number') continue;
    const tick = tx.tick ?? 0;
    const idx = ranges.findIndex((r) => tick >= r.start && tick < r.end);
    if (idx >= 0) out[idx].pnl += tx.realized_pnl;
  }
  return out;
}
