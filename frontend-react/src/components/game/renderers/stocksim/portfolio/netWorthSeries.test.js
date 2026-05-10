// netWorthSeries.test.js
import { describe, it, expect } from 'vitest';
import { netWorthSeries } from './netWorthSeries';

describe('netWorthSeries', () => {
  it('returns startingCash for tick 0 with no trades', () => {
    const series = netWorthSeries([], { TECHV: [100, 110, 120] }, 50000, 0);
    expect(series).toEqual([50000]);
  });

  it('replays a buy and tracks holdings value across ticks', () => {
    // Buy 10 TECHV at tick 1 for ₹110/share = ₹1,100 spent
    const txs = [{ tick: 1, symbol: 'TECHV', side: 'buy', qty: 10, price: 110 }];
    const prices = { TECHV: [100, 110, 120, 130] };
    const series = netWorthSeries(txs, prices, 50000, 3);
    expect(series).toHaveLength(4);
    expect(series[0]).toBe(50000);                 // before trade
    expect(series[1]).toBe(50000 - 1100 + 10*110); // cash drops, holdings worth same
    expect(series[2]).toBe(50000 - 1100 + 10*120);
    expect(series[3]).toBe(50000 - 1100 + 10*130);
  });

  it('handles a sell after a buy (realizes pnl)', () => {
    const txs = [
      { tick: 1, symbol: 'TECHV', side: 'buy',  qty: 10, price: 100 },
      { tick: 3, symbol: 'TECHV', side: 'sell', qty: 10, price: 130 },
    ];
    const prices = { TECHV: [100, 100, 100, 130, 140] };
    const series = netWorthSeries(txs, prices, 10000, 4);
    expect(series[0]).toBe(10000);
    expect(series[1]).toBe(10000 - 1000 + 10*100); // 10000
    expect(series[3]).toBe(10000 - 1000 + 1300);   // 10300 (cash up after sell)
    expect(series[4]).toBe(10300);                  // no holdings, just cash
  });
});
