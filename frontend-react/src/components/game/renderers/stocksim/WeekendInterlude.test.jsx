import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import WeekendInterlude from './WeekendInterlude';

const event = {
  type: 'saturday_news',
  title: 'Saturday Headlines',
  items: [
    { scope: 'macro', text: 'RBI keeps repo rate unchanged' },
    { scope: 'stock', symbol: 'GREENX', text: 'Govt approves new solar tariff' },
  ],
};

describe('WeekendInterlude', () => {
  it('renders title and items', () => {
    render(<WeekendInterlude open event={event} onAdvance={() => {}} />);
    expect(screen.getByTestId('weekend-title').textContent).toContain('Saturday Headlines');
    expect(screen.getAllByTestId(/^weekend-item-/)).toHaveLength(2);
  });

  it('skip button is disabled for first 3s, then enabled', async () => {
    vi.useFakeTimers();
    render(<WeekendInterlude open event={event} onAdvance={() => {}} />);
    const btn = screen.getByTestId('weekend-skip');
    expect(btn.disabled).toBe(true);
    await act(async () => { vi.advanceTimersByTime(3100); });
    expect(btn.disabled).toBe(false);
    vi.useRealTimers();
  });

  it('auto-advances after 10s', async () => {
    vi.useFakeTimers();
    const onAdvance = vi.fn();
    render(<WeekendInterlude open event={event} onAdvance={onAdvance} />);
    await act(async () => { vi.advanceTimersByTime(10100); });
    expect(onAdvance).toHaveBeenCalled();
    vi.useRealTimers();
  });
});
