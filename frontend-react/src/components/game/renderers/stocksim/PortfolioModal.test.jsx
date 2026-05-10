import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PortfolioModal from './PortfolioModal';

const baseProps = {
  open: true,
  onClose: vi.fn(),
  cash: 30000,
  startingCash: 50000,
  netWorth: 52000,
  todayPnL: 500,
  pnl: { realized: 800, unrealized: 1200 },
  holdings: { TECHV: { qty: 10, avg_price: 1100 } },
  quotes: { TECHV: { mid: 1180 } },
  transactions: [],
  priceHistory: { TECHV: [1100, 1150, 1180] },
  currentTick: 2,
  stocks: [{ symbol: 'TECHV', sector: 'IT', name: 'TechVista' }],
  days: [{ id: 'mon', label: 'Monday', ticks: 4 }],
};

describe('PortfolioModal', () => {
  it('renders backdrop with testid when open', () => {
    render(<PortfolioModal {...baseProps} />);
    expect(screen.getByTestId('portfolio-backdrop')).toBeTruthy();
  });

  it('does not render when closed', () => {
    render(<PortfolioModal {...baseProps} open={false} />);
    expect(screen.queryByTestId('portfolio-backdrop')).toBeNull();
  });

  it('switches tabs', () => {
    render(<PortfolioModal {...baseProps} />);
    fireEvent.click(screen.getByTestId('portfolio-tab-holdings'));
    expect(screen.getByTestId('portfolio-tab-holdings').getAttribute('data-active')).toBe('true');
  });

  it('closes on backdrop click', () => {
    const onClose = vi.fn();
    render(<PortfolioModal {...baseProps} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('portfolio-backdrop'));
    expect(onClose).toHaveBeenCalled();
  });
});
