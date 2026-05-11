import { describe, it, expect } from 'vitest';
import { rsi, ma, supportResistance, crossover } from './technicals';

describe('technicals', () => {
  it('ma returns simple moving average over the last N closes', () => {
    expect(ma([1, 2, 3, 4, 5], 3)).toBeCloseTo(4); // (3+4+5)/3
    expect(ma([10], 3)).toBeNull();
  });

  it('rsi returns 100 for monotonic up series', () => {
    const series = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15];
    expect(rsi(series, 14)).toBeCloseTo(100, 0);
  });

  it('rsi returns 0 for monotonic down series', () => {
    const series = [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1];
    expect(rsi(series, 14)).toBeCloseTo(0, 0);
  });

  it('supportResistance returns min/max over lookback window', () => {
    const out = supportResistance([10, 12, 8, 11, 14, 9, 13], 5);
    expect(out.support).toBe(8);
    expect(out.resistance).toBe(14);
  });

  it('crossover detects bullish event when short crosses above long', () => {
    // prev: short=5 ≤ long=6 ; last: short=7 > long=6 ⇒ bullish cross
    expect(crossover([4, 5, 7], [5, 6, 6])).toBe('bullish');
  });

  it('crossover detects bearish event when short crosses below long', () => {
    // prev: short=6 ≥ long=5 ; last: short=4 < long=5 ⇒ bearish cross
    expect(crossover([7, 6, 4], [4, 5, 5])).toBe('bearish');
  });

  it('crossover returns none when short stays above long (no cross event)', () => {
    // short above long for both prev and last — relative position, not a cross
    expect(crossover([7, 8, 9], [4, 5, 6])).toBe('none');
  });

  it('crossover returns none for equal-length arrays without crossing', () => {
    expect(crossover([5, 5, 5], [6, 6, 6])).toBe('none');
  });

  it('crossover returns none when arrays are too short', () => {
    expect(crossover([5], [5])).toBe('none');
    expect(crossover([], [])).toBe('none');
  });

  it('rsi returns null when prices length is exactly period (insufficient data)', () => {
    expect(rsi(new Array(14).fill(1), 14)).toBeNull();
  });

  it('supportResistance returns nulls when fewer than 2 prices', () => {
    expect(supportResistance([], 5)).toEqual({ support: null, resistance: null });
    expect(supportResistance([42], 5)).toEqual({ support: null, resistance: null });
  });
});
