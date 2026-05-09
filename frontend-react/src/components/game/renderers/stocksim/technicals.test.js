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

  it('crossover detects bullish/bearish/none', () => {
    expect(crossover([5, 6, 7], [4, 5, 6])).toBe('bullish'); // short above long, increasing
    expect(crossover([5, 5, 5], [6, 6, 6])).toBe('bearish');
    expect(crossover([5, 5], [5, 5])).toBe('none');
  });
});
