import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TradesTab from './TradesTab';

const trades = [
  { tick: 1, dayLabel: 'Mon', symbol: 'TECHV', side: 'buy',  qty: 10, price: 100, charges: 5, realized_pnl: 0 },
  { tick: 5, dayLabel: 'Tue', symbol: 'TECHV', side: 'sell', qty: 10, price: 130, charges: 5, realized_pnl: 290 },
  { tick: 6, dayLabel: 'Tue', symbol: 'BHARATBANK', side: 'buy', qty: 5, price: 600, charges: 3 },
];

describe('TradesTab', () => {
  it('renders one row per trade and footer summary', () => {
    render(<TradesTab trades={trades} />);
    expect(screen.getAllByTestId(/^trade-row-/)).toHaveLength(3);
    expect(screen.getByTestId('trades-summary').textContent).toContain('Win rate');
  });

  it('filters by side', () => {
    render(<TradesTab trades={trades} />);
    fireEvent.click(screen.getByTestId('trades-filter-buy'));
    expect(screen.getAllByTestId(/^trade-row-/)).toHaveLength(2);
  });
});
