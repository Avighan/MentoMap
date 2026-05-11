import { describe, it, expect } from 'vitest';
import { priceFromSeed, hashSeed } from '../utils/stocksimPricing';

describe('stocksimPricing', () => {
  it('hashSeed is deterministic', () => {
    const a = hashSeed(12345, 'TECHV', 5);
    const b = hashSeed(12345, 'TECHV', 5);
    const c = hashSeed(12345, 'TECHV', 6);
    expect(a).toBe(b);
    expect(a).not.toBe(c);
  });

  it('priceFromSeed returns identical quote for identical inputs', () => {
    const cfg = { starting_price: 100, volatility: 0.02 };
    const a = priceFromSeed(12345, 'TECHV', 5, cfg);
    const b = priceFromSeed(12345, 'TECHV', 5, cfg);
    expect(a).toEqual(b);
  });

  it('priceFromSeed returns mid/bid/ask/volume shape', () => {
    const cfg = { starting_price: 100, volatility: 0.02 };
    const q = priceFromSeed(12345, 'TECHV', 5, cfg);
    expect(typeof q.mid).toBe('number');
    expect(q.bid).toBeLessThan(q.mid);
    expect(q.ask).toBeGreaterThan(q.mid);
    expect(typeof q.volume).toBe('number');
    expect(q.volume).toBeGreaterThanOrEqual(0);
  });

  it('priceFromSeed clamps mid to [0.01, 10x starting]', () => {
    const cfg = { starting_price: 100, volatility: 5.0 }; // huge vol -> would blow up
    for (let t = 0; t < 50; t++) {
      const q = priceFromSeed(12345, 'TECHV', t, cfg);
      expect(q.mid).toBeGreaterThanOrEqual(0.01);
      expect(q.mid).toBeLessThanOrEqual(1000);
    }
  });

  it('tick 0 returns the starting price exactly', () => {
    const cfg = { starting_price: 100, volatility: 0.02 };
    const q = priceFromSeed(12345, 'TECHV', 0, cfg);
    expect(q.mid).toBe(100);
  });
});
