import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StockListFilters from './StockListFilters';

describe('StockListFilters', () => {
  const counts = { all: 8, gainers: 3, losers: 2, mine: 1, starred: 2 };

  it('renders 5 filter chips with counts', () => {
    render(<StockListFilters mode="all" counts={counts} setMode={() => {}} />);
    expect(screen.getByText(/All/)).toBeInTheDocument();
    expect(screen.getByText(/Gainers/)).toBeInTheDocument();
    expect(screen.getByText(/Losers/)).toBeInTheDocument();
    expect(screen.getByText(/Mine/)).toBeInTheDocument();
    expect(screen.getByText(/⭐/)).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('marks the active chip', () => {
    render(<StockListFilters mode="gainers" counts={counts} setMode={() => {}} />);
    const chip = screen.getByTestId('filter-gainers');
    expect(chip).toHaveAttribute('data-active', 'true');
  });

  it('calls setMode when chip clicked', () => {
    const setMode = vi.fn();
    render(<StockListFilters mode="all" counts={counts} setMode={setMode} />);
    fireEvent.click(screen.getByTestId('filter-losers'));
    expect(setMode).toHaveBeenCalledWith('losers');
  });
});
