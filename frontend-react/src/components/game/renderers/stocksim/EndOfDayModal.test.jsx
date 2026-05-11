import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import EndOfDayModal from './EndOfDayModal';

const props = {
  open: true,
  day: { id: 'wed', label: 'Wednesday', index: 2, of: 5 },
  todayPnL: { total: 320, realized: 200, unrealized: 120 },
  topMover: { symbol: 'TECHV', changePct: 4.2 },
  bottomMover: { symbol: 'BHARATBANK', changePct: -2.1 },
  earningsRevealed: [{ symbol: 'BHARATBANK', headline: 'BharatBank misses on NPAs', surprise: -0.03 }],
  onContinue: vi.fn(),
};

describe('EndOfDayModal', () => {
  it('renders today P&L and continue button', () => {
    render(<EndOfDayModal {...props} />);
    expect(screen.getByTestId('eod-pnl').textContent).toContain('320');
    expect(screen.getByTestId('eod-continue')).toBeTruthy();
  });
  it('renders earnings reveal block when present', () => {
    render(<EndOfDayModal {...props} />);
    expect(screen.getByTestId('eod-earnings').textContent).toContain('BharatBank');
  });
  it('calls onContinue when button clicked', () => {
    const onContinue = vi.fn();
    render(<EndOfDayModal {...props} onContinue={onContinue} />);
    fireEvent.click(screen.getByTestId('eod-continue'));
    expect(onContinue).toHaveBeenCalled();
  });
});
