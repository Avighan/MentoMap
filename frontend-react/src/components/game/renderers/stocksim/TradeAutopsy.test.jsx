import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TradeAutopsy from './TradeAutopsy';

describe('TradeAutopsy', () => {
  it('renders empty-state when no trades', () => {
    render(<TradeAutopsy final={{ trade_log_enriched: [] }} />);
    expect(screen.getByText(/No trades/i)).toBeInTheDocument();
  });

  it('renders best and worst with lesson lines', () => {
    const final = { trade_log_enriched: [
      { tick: 2, symbol: 'TECHV', side: 'sell', realized_pnl: 100, news_at_tick: [] },
      { tick: 6, symbol: 'BANKX', side: 'sell', realized_pnl: -200, news_at_tick: [] },
    ]};
    render(<TradeAutopsy final={final} />);
    expect(screen.getByTestId('autopsy-best').textContent).toMatch(/TECHV/);
    expect(screen.getByTestId('autopsy-worst').textContent).toMatch(/BANKX/);
  });
});
