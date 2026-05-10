import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import HoldingsTab from './HoldingsTab';

const rows = [
  { symbol: 'TECHV', sector: 'IT', qty: 10, avgCost: 1100, ltp: 1180, pnlAbs: 800, pnlPct: 7.27, dayDelta: 60 },
  { symbol: 'BHARATBANK', sector: 'Fin', qty: 5, avgCost: 600, ltp: 580, pnlAbs: -100, pnlPct: -3.3, dayDelta: -25 },
];

describe('HoldingsTab', () => {
  it('renders one row per holding', () => {
    render(<HoldingsTab rows={rows} />);
    expect(screen.getByTestId('holding-row-TECHV')).toBeTruthy();
    expect(screen.getByTestId('holding-row-BHARATBANK')).toBeTruthy();
  });

  it('opens drilldown on row click', () => {
    const onOpen = vi.fn();
    render(<HoldingsTab rows={rows} onOpenSymbol={onOpen} />);
    fireEvent.click(screen.getByTestId('holding-row-TECHV'));
    expect(onOpen).toHaveBeenCalledWith('TECHV');
  });

  it('filters by Profit chip', () => {
    render(<HoldingsTab rows={rows} />);
    fireEvent.click(screen.getByTestId('holdings-filter-profit'));
    expect(screen.getByTestId('holding-row-TECHV')).toBeTruthy();
    expect(screen.queryByTestId('holding-row-BHARATBANK')).toBeNull();
  });
});
