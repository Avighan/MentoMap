import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PersistentStrip from './PersistentStrip';

describe('PersistentStrip', () => {
  const baseProps = {
    cash: 98925,
    holdingsValue: 1075,
    netWorth: 100000,
    pnl: 0.25,
    currentTick: 4,
    tickCount: 22,
  };

  it('renders all 5 cells with formatted values', () => {
    render(<PersistentStrip {...baseProps} />);
    expect(screen.getByText(/CASH/i)).toBeInTheDocument();
    expect(screen.getByText(/₹98,925/)).toBeInTheDocument();
    expect(screen.getByText(/HOLDINGS/i)).toBeInTheDocument();
    expect(screen.getByText(/₹1,075/)).toBeInTheDocument();
    expect(screen.getByText(/NET WORTH/i)).toBeInTheDocument();
    expect(screen.getByText(/₹1,00,000/)).toBeInTheDocument();
    expect(screen.getByText(/4 \/ 22/)).toBeInTheDocument();
  });

  it('formats negative P&L with red color and minus sign', () => {
    render(<PersistentStrip {...baseProps} pnl={-247.5} />);
    const pnlEl = screen.getByTestId('persistent-pnl');
    expect(pnlEl.textContent).toMatch(/-₹247\.50/);
    expect(pnlEl).toHaveStyle({ color: '#A32D2D' });
  });

  it('formats positive P&L with green color and plus sign', () => {
    render(<PersistentStrip {...baseProps} pnl={123.45} />);
    const pnlEl = screen.getByTestId('persistent-pnl');
    expect(pnlEl.textContent).toMatch(/\+₹123\.45/);
    expect(pnlEl).toHaveStyle({ color: '#0F6E56' });
  });
});
