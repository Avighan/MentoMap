/**
 * stocksimPricing.js — JS port of backend deterministic pricing for the
 * realtime stock market simulator. Used ONLY for chart smoothing between
 * server state polls; the server is authoritative for trades, fills, P&L,
 * and end-of-game scoring.
 *
 * The backend (backend/engines/stocksim/pricing.py) uses SHA-256 + Box-Muller.
 * This port uses FNV-1a + mulberry32 + Box-Muller for performance reasons.
 * The two implementations therefore produce DIFFERENT numeric sequences —
 * this is intentional and documented in the backend pricing module's
 * docstring. Cross-language parity is NOT a goal; the JS sequence only
 * needs to look plausible at chart scale until the next state poll
 * snaps back to authoritative server values.
 *
 * Mirrors the backend's interface:
 *   priceFromSeed(seed, symbol, tick, stockCfg) -> { mid, bid, ask, volume }
 *
 * Stock cfg keys mirror the backend stock_cfg shape:
 *   - starting_price (number, required)
 *   - volatility    (number, default 0.02)
 *
 * Drift is hardcoded at 0.0002 per tick to match the backend.
 */

// FNV-1a 32-bit hash for short strings. Returns unsigned 32-bit int.
function _fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    // 32-bit FNV prime multiply via shifts (avoid float precision)
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
  }
  return h >>> 0;
}

// mulberry32 — small fast deterministic PRNG seeded from a 32-bit int.
function _mulberry32(seed) {
  let s = seed >>> 0;
  return function next() {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Deterministic 32-bit hash from (seed, symbol, tick, channel).
 * Exposed for tests; mirrors the role of the SHA-256 digest on the backend.
 */
export function hashSeed(seed, symbol, tick, channel = 'ret') {
  return _fnv1a(`${seed}|${symbol}|${tick}|${channel}`);
}

// Box-Muller normal from a deterministic seed. Returns ~ N(0, 1).
function _seededNormal(seed, symbol, tick, channel = 'ret') {
  const h = hashSeed(seed, symbol, tick, channel);
  const rng = _mulberry32(h);
  let u1 = rng();
  const u2 = rng();
  if (u1 < 1e-12) u1 = 1e-12; // avoid log(0)
  return Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
}

// Sum of log-returns from tick 1..tick. Tick 0 returns 0 (starting price).
function _accumulateLogReturn(seed, symbol, tick, vol) {
  let total = 0.0;
  for (let t = 1; t <= tick; t++) {
    const z = _seededNormal(seed, symbol, t, 'ret');
    // Tiny mean drift (~0.0002 per tick), volatility scales noise — matches
    // backend pricing.py:_accumulate_log_return.
    total += 0.0002 + vol * z;
  }
  return total;
}

function _round2(x) {
  return Math.round(x * 100) / 100;
}

/**
 * Quote dict {mid, bid, ask, volume} for (seed, symbol, tick, stockCfg).
 *
 * Pure function: identical inputs always return identical output.
 * Mirrors backend price_from_seed shape and clamping behavior.
 */
export function priceFromSeed(seed, symbol, tick, stockCfg) {
  const starting = Number(stockCfg.starting_price);
  const vol =
    stockCfg.volatility === undefined || stockCfg.volatility === null
      ? 0.02
      : Number(stockCfg.volatility);

  let mid;
  if (tick === 0) {
    mid = starting;
  } else {
    let logRet = _accumulateLogReturn(seed, symbol, tick, vol);
    // Clamp log-return to ±4 to prevent numerical overflow (matches backend).
    if (logRet > 4.0) logRet = 4.0;
    if (logRet < -4.0) logRet = -4.0;
    mid = starting * Math.exp(logRet);
  }

  // Hard clamps — mid bounded to [0.01, 10× starting].
  mid = Math.max(0.01, Math.min(mid, starting * 10.0));

  // Spread widens with volatility. 5bps base + vol-scaled.
  const spreadBps = 5.0 + vol * 200.0;
  let halfSpread = (mid * (spreadBps / 10000.0)) / 2.0;
  halfSpread = Math.max(halfSpread, 0.01);
  const bid = Math.max(0.01, mid - halfSpread);
  const ask = mid + halfSpread;

  // Volume — deterministic, scales with volatility.
  const volZ = _seededNormal(seed, symbol, tick, 'vol');
  const baseVol = 10000 * (1.0 + vol * 5.0);
  const volume = Math.max(0, Math.round(baseVol * (1.0 + 0.3 * volZ)));

  return {
    mid: _round2(mid),
    bid: _round2(bid),
    ask: _round2(ask),
    volume,
  };
}

export default { priceFromSeed, hashSeed };
