import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PerformanceTab from './PerformanceTab';

describe('PerformanceTab', () => {
  it('renders day P&L bars and metrics card', () => {
    render(
      <PerformanceTab
        dayPnL={[{ dayId: 'mon', label: 'Mon', pnl: 200 }, { dayId: 'tue', label: 'Tue', pnl: -100 }]}
        portfolioReturnSeries={[0, 1, 2, 3]}
        benchmarkReturnSeries={[0, 0.5, 1, 1.5]}
        maxDD={4.2}
        topConcentration={{ symbol: 'TECHV', pct: 35 }}
        hitRatio={{ winRate: 0.66, totalClosed: 3, avgWin: 200, avgLoss: -50 }}
      />
    );
    expect(screen.getByTestId('perf-day-mon')).toBeTruthy();
    expect(screen.getByTestId('perf-day-tue')).toBeTruthy();
    expect(screen.getByTestId('perf-max-dd').textContent).toContain('4.2');
  });

  it('handles empty dayPnL gracefully', () => {
    render(<PerformanceTab />);
    expect(screen.getByText('P&L by day')).toBeTruthy();
  });

  it('renders zero-pnl bars without divide-by-zero', () => {
    render(
      <PerformanceTab
        dayPnL={[{ dayId: 'mon', label: 'Mon', pnl: 0 }]}
      />
    );
    expect(screen.getByTestId('perf-day-mon')).toBeTruthy();
  });

  it('shows dash sentinel when topConcentration is absent', () => {
    render(<PerformanceTab />);
    const tiles = screen.getAllByText('—');
    expect(tiles.length).toBeGreaterThanOrEqual(2);
  });

  it('omits return-lines svg when both series are empty', () => {
    const { container } = render(<PerformanceTab />);
    expect(container.querySelector('svg[aria-label="return-lines"]')).toBeNull();
  });

  it('uses default maxDD of 0.0% when omitted', () => {
    render(<PerformanceTab />);
    expect(screen.getByTestId('perf-max-dd').textContent).toContain('0.0%');
  });
});
