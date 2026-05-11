import { describe, it, expect } from 'vitest';
import { pickBestTrade, pickWorstTrade, whatWouldHaveBeenBetter } from './autopsy';

describe('autopsy', () => {
  const log = [
    { tick: 2, symbol: 'TECHV', side: 'buy', qty: 5, price: 200, realized_pnl: 0, news_at_tick: [] },
    { tick: 8, symbol: 'TECHV', side: 'sell', qty: 5, price: 220, realized_pnl: 100, news_at_tick: [{ headline: 'cloud win', reason: 'r' }] },
    { tick: 10, symbol: 'BANKX', side: 'buy', qty: 10, price: 300, realized_pnl: 0, news_at_tick: [] },
    { tick: 14, symbol: 'BANKX', side: 'sell', qty: 10, price: 280, realized_pnl: -200, news_at_tick: [] },
  ];

  it('pickBestTrade returns the highest realized P&L', () => {
    const best = pickBestTrade(log);
    expect(best.symbol).toBe('TECHV');
    expect(best.realized_pnl).toBe(100);
  });

  it('pickWorstTrade returns the lowest realized P&L', () => {
    const worst = pickWorstTrade(log);
    expect(worst.symbol).toBe('BANKX');
    expect(worst.realized_pnl).toBe(-200);
  });

  it('whatWouldHaveBeenBetter returns a lesson string keyed off side and outcome', () => {
    const lesson = whatWouldHaveBeenBetter({ symbol: 'BANKX', side: 'buy', realized_pnl: -200 }, []);
    expect(typeof lesson).toBe('string');
    expect(lesson.length).toBeGreaterThan(0);
  });

  it('returns null on empty log', () => {
    expect(pickBestTrade([])).toBeNull();
    expect(pickWorstTrade([])).toBeNull();
  });

  it('pickBestTrade ignores NaN realized_pnl', () => {
    const log = [
      { realized_pnl: 100, symbol: 'A' },
      { realized_pnl: NaN, symbol: 'B' },
      { realized_pnl: 50, symbol: 'C' },
    ];
    expect(pickBestTrade(log)).toEqual({ realized_pnl: 100, symbol: 'A' });
  });

  it('pickWorstTrade ignores NaN realized_pnl', () => {
    const log = [
      { realized_pnl: -100, symbol: 'A' },
      { realized_pnl: NaN, symbol: 'B' },
      { realized_pnl: -50, symbol: 'C' },
    ];
    expect(pickWorstTrade(log)).toEqual({ realized_pnl: -100, symbol: 'A' });
  });
});
