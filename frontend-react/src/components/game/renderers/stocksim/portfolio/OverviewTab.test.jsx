import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import OverviewTab from './OverviewTab';

const fixture = {
  netWorth: 52000,
  startingCash: 50000,
  todayPnL: 500,
  cash: 30000,
  holdingsValue: 22000,
  realizedPnL: 800,
  unrealizedPnL: 1200,
  netWorthSeries: [50000, 50500, 51200, 52000],
  allocation: [{ label: 'IT', value: 60 }, { label: 'Pharma', value: 40 }],
  bestToday: { symbol: 'TECHV', delta: 320 },
  worstToday: { symbol: 'BHARATBANK', delta: -120 },
};

describe('OverviewTab', () => {
  it('renders net worth and total return', () => {
    render(<OverviewTab {...fixture} />);
    expect(screen.getByTestId('overview-networth').textContent).toContain('52,000');
    expect(screen.getByTestId('overview-total-return').textContent).toContain('4.00%');
  });

  it('renders best/worst symbols', () => {
    render(<OverviewTab {...fixture} />);
    expect(screen.getByTestId('overview-best').textContent).toContain('TECHV');
    expect(screen.getByTestId('overview-worst').textContent).toContain('BHARATBANK');
  });
});
