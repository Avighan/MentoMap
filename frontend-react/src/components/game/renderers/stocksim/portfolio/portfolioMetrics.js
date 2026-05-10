// portfolioMetrics.js
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
