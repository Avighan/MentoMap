// portfolioMetrics.test.js
import { describe, it, expect } from 'vitest';
import { maxDrawdown, concentration, hitRatio } from './portfolioMetrics';

describe('maxDrawdown', () => {
  it('returns 0 for monotonically rising series', () => {
    expect(maxDrawdown([100, 110, 120, 130])).toBe(0);
  });
  it('computes percent drop from peak', () => {
    expect(maxDrawdown([100, 120, 90, 110])).toBeCloseTo(25, 5); // 120 → 90
  });
  it('returns 0 for empty/single', () => {
    expect(maxDrawdown([])).toBe(0);
    expect(maxDrawdown([100])).toBe(0);
  });
});

describe('concentration', () => {
  it('returns largest position by market value as pct of total', () => {
    const holdings = { A: { qty: 10 }, B: { qty: 5 } };
    const prices = { A: 200, B: 100 };  // A=2000, B=500, total=2500
    const result = concentration(holdings, prices);
    expect(result.symbol).toBe('A');
    expect(result.pct).toBeCloseTo(80, 1);
  });
  it('returns null on empty holdings', () => {
    expect(concentration({}, {})).toBeNull();
  });
});

describe('hitRatio', () => {
  it('counts winning closed trades vs total closed', () => {
    const txs = [
      { side: 'sell', realized_pnl: 500 },
      { side: 'sell', realized_pnl: -200 },
      { side: 'sell', realized_pnl: 300 },
      { side: 'buy', realized_pnl: 0 },        // open: not counted
    ];
    const r = hitRatio(txs);
    expect(r.totalClosed).toBe(3);
    expect(r.winRate).toBeCloseTo(2 / 3, 3);
    expect(r.avgWin).toBeCloseTo(400);
    expect(r.avgLoss).toBeCloseTo(-200);
  });
  it('handles no closed trades', () => {
    expect(hitRatio([])).toEqual({ winRate: 0, avgWin: 0, avgLoss: 0, totalClosed: 0 });
  });
});
