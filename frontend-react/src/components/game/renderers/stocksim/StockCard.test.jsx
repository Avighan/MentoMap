import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StockCard from './StockCard';

const stock = { symbol: 'TECHV', name: 'TechVista', sector: 'IT' };

describe('StockCard', () => {
  it('shows star toggle and calls onStar', () => {
    const onStar = vi.fn();
    render(<StockCard stock={stock} quote={{ mid: 215 }} onOpen={() => {}} onStar={onStar} />);
    fireEvent.click(screen.getByTestId('star-TECHV'));
    expect(onStar).toHaveBeenCalledWith('TECHV');
  });

  it('shows "Why moving?" chip when last_reason set', () => {
    render(<StockCard stock={stock} quote={{ mid: 215, last_reason: 'big contract' }} onOpen={() => {}} onStar={() => {}} />);
    expect(screen.getByTestId('why-chip-TECHV').textContent).toMatch(/big contract/);
  });

  it('clicking card calls onOpen', () => {
    const onOpen = vi.fn();
    render(<StockCard stock={stock} quote={{ mid: 215 }} onOpen={onOpen} onStar={() => {}} />);
    fireEvent.click(screen.getByTestId('card-TECHV'));
    expect(onOpen).toHaveBeenCalledWith('TECHV');
  });
});
