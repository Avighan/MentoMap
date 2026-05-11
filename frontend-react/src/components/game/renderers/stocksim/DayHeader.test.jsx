import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import DayHeader from './DayHeader';

describe('DayHeader', () => {
  it('renders day label and position', () => {
    render(<DayHeader day={{ id: 'wed', label: 'Wednesday', index: 2, of: 5 }} />);
    expect(screen.getByTestId('day-header').textContent).toContain('Wednesday');
    expect(screen.getByTestId('day-header').textContent).toContain('Day 3 of 5');
  });

  it('renders nothing when day is null', () => {
    const { container } = render(<DayHeader day={null} />);
    expect(container.querySelector('[data-testid="day-header"]')).toBeNull();
  });
});
