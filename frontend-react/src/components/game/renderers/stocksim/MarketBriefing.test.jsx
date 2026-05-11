import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MarketBriefing from './MarketBriefing';

describe('MarketBriefing', () => {
  const briefing = {
    macro_tone: 'RBI policy day. IT and banks in focus.',
    sector_mood: { IT: 'positive', Banking: 'neutral' },
    headline: '8 stocks. 22 ticks.',
    sub: 'Each tick = ~8 seconds.',
  };
  const stocks = [
    { symbol: 'TECHV', name: 'TechVista', sector: 'IT', starting_price: 215 },
    { symbol: 'BANKX', name: 'BankX', sector: 'Banking', starting_price: 320 },
  ];

  it('renders headline, sub, sector chips and stock peek', () => {
    render(<MarketBriefing briefing={briefing} stocks={stocks} onBegin={() => {}} />);
    expect(screen.getByText(briefing.headline)).toBeInTheDocument();
    expect(screen.getByText(briefing.sub)).toBeInTheDocument();
    expect(screen.getByText(/IT · positive/)).toBeInTheDocument();
    expect(screen.getByText(/TECHV/)).toBeInTheDocument();
  });

  it('Begin button calls onBegin', () => {
    const onBegin = vi.fn();
    render(<MarketBriefing briefing={briefing} stocks={stocks} onBegin={onBegin} />);
    fireEvent.click(screen.getByRole('button', { name: /Begin/i }));
    expect(onBegin).toHaveBeenCalled();
  });

  it('renders earnings day chip when stock has scheduled earnings', () => {
    render(
      <MarketBriefing
        briefing={{ headline: 'X', sub: 'Y', macro_tone: 'neutral', sector_mood: {} }}
        stocks={[{ symbol: 'TECHV', name: 'TechVista', sector: 'IT' }]}
        earningsByDay={{ TECHV: { day: 'tue', label: 'Tuesday' } }}
        onBegin={() => {}}
      />
    );
    expect(screen.getByTestId('briefing-earnings-TECHV').textContent).toContain('Earnings: Tue');
  });
});
