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

  it('closes on Escape key', () => {
    const onClose = vi.fn();
    render(<PortfolioModal {...baseProps} onClose={onClose} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('does not register Escape handler when closed', () => {
    const onClose = vi.fn();
    render(<PortfolioModal {...baseProps} open={false} onClose={onClose} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).not.toHaveBeenCalled();
  });

  it('renders without crashing in empty state', () => {
    render(
      <PortfolioModal
        open
        onClose={() => {}}
        holdings={{}}
        quotes={{}}
        transactions={[]}
        priceHistory={{}}
        stocks={[]}
        days={[]}
      />
    );
    expect(screen.getByTestId('portfolio-backdrop')).toBeTruthy();
    // Switch through every tab and confirm no crash + the tab becomes active
    for (const id of ['holdings', 'trades', 'performance', 'overview']) {
      fireEvent.click(screen.getByTestId(`portfolio-tab-${id}`));
      expect(screen.getByTestId(`portfolio-tab-${id}`).getAttribute('data-active')).toBe('true');
    }
  });

  it('does not close when inner panel is clicked', () => {
    const onClose = vi.fn();
    render(<PortfolioModal {...baseProps} onClose={onClose} />);
    // Click the active tab button (inside inner panel) — must not bubble to backdrop
    fireEvent.click(screen.getByTestId('portfolio-tab-overview'));
    expect(onClose).not.toHaveBeenCalled();
  });

  it('default `overview` tab is active on first render', () => {
    render(<PortfolioModal {...baseProps} />);
    expect(screen.getByTestId('portfolio-tab-overview').getAttribute('data-active')).toBe('true');
    expect(screen.getByTestId('portfolio-tab-holdings').getAttribute('data-active')).toBe('false');
  });
});
