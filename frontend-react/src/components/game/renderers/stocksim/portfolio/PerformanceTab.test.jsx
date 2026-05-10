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
});
