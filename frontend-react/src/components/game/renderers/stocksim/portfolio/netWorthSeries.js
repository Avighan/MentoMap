// netWorthSeries.js
// Replays transactions over the price history to compute net worth at each tick.
// transactions: Array<{ tick, symbol, side: 'buy'|'sell', qty, price, charges? }>
// priceHistory: { [symbol]: number[] }   // index = tick
// startingCash: number
// currentTick: number   // inclusive — produces currentTick+1 points
// Returns: number[] of length currentTick+1
export function netWorthSeries(transactions, priceHistory, startingCash, currentTick) {
  const sorted = [...(transactions || [])].sort((a, b) => (a.tick ?? 0) - (b.tick ?? 0));
  const holdings = {};
  let cash = startingCash;
  let txIdx = 0;
  const out = [];

  for (let t = 0; t <= currentTick; t++) {
    while (txIdx < sorted.length && (sorted[txIdx].tick ?? 0) <= t) {
      const tx = sorted[txIdx++];
      const charges = tx.charges ?? 0;
      const cost = tx.qty * tx.price;
      if (tx.side === 'buy') {
        cash -= cost + charges;
        holdings[tx.symbol] = (holdings[tx.symbol] ?? 0) + tx.qty;
      } else {
        cash += cost - charges;
        holdings[tx.symbol] = (holdings[tx.symbol] ?? 0) - tx.qty;
      }
    }
    let mv = 0;
    for (const sym of Object.keys(holdings)) {
      const qty = holdings[sym];
      if (!qty) continue;
      const series = priceHistory?.[sym] ?? [];
      const price = series[t] ?? series[series.length - 1] ?? 0;
      mv += qty * price;
    }
    out.push(cash + mv);
  }
  return out;
}
