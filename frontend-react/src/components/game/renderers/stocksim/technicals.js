export function ma(prices, period) {
  if (!Array.isArray(prices) || prices.length < period) return null;
  const slice = prices.slice(-period);
  const sum = slice.reduce((a, b) => a + b, 0);
  return sum / period;
}

export function rsi(prices, period = 14) {
  if (!Array.isArray(prices) || prices.length <= period) return null;
  let gains = 0, losses = 0;
  for (let i = 1; i <= period; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff >= 0) gains += diff; else losses -= diff;
  }
  let avgGain = gains / period;
  let avgLoss = losses / period;
  for (let i = period + 1; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
  }
  if (avgLoss === 0) return 100;
  if (avgGain === 0) return 0;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

export function supportResistance(prices, lookback = 10) {
  if (!Array.isArray(prices) || prices.length < 2) return { support: null, resistance: null };
  const slice = prices.slice(-lookback);
  return { support: Math.min(...slice), resistance: Math.max(...slice) };
}

export function crossover(maShort, maLong) {
  if (!Array.isArray(maShort) || !Array.isArray(maLong)) return 'none';
  if (maShort.length < 2 || maLong.length < 2) return 'none';
  const lastShort = maShort[maShort.length - 1];
  const lastLong = maLong[maLong.length - 1];
  const prevShort = maShort[maShort.length - 2];
  const prevLong = maLong[maLong.length - 2];
  if (prevShort <= prevLong && lastShort > lastLong) return 'bullish';
  if (prevShort >= prevLong && lastShort < lastLong) return 'bearish';
  return 'none';
}
