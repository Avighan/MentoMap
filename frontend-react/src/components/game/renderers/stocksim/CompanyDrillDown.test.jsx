import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../../i18n';
import CompanyDrillDown from './CompanyDrillDown';

const stock = {
  symbol: 'TECHV', name: 'TechVista', sector: 'IT',
  fundamentals: { pe: 28.4, sector_pe: 24, roe: 22, debt_equity: 0.12 },
  peers: [], about: { description: 'd' }, image_prompt: 'p',
};
const quote = { mid: 215, bid: 214.95, ask: 215.05, volume: 100 };

const wrap = (ui) => <I18nextProvider i18n={i18n}>{ui}</I18nextProvider>;

describe('CompanyDrillDown', () => {
  it('renders with Chart tab active by default', () => {
    render(wrap(<CompanyDrillDown stock={stock} quote={quote} priceHistory={[{ mid: 210 }, { mid: 215 }]} news={[]} imageUrl={null} onClose={() => {}} />));
    expect(screen.getByTestId('drilldown-tab-chart')).toHaveAttribute('data-active', 'true');
  });

  it('switches to Fundamentals when clicked', () => {
    render(wrap(<CompanyDrillDown stock={stock} quote={quote} priceHistory={[{ mid: 210 }, { mid: 215 }]} news={[]} imageUrl={null} onClose={() => {}} />));
    fireEvent.click(screen.getByTestId('drilldown-tab-fundamentals'));
    expect(screen.getByTestId('drilldown-tab-fundamentals')).toHaveAttribute('data-active', 'true');
    expect(screen.getByText(/VALUATION/)).toBeInTheDocument();
    expect(screen.queryByText(/MA-20/)).toBeNull();
  });

  it('calls onClose when backdrop clicked', () => {
    const onClose = vi.fn();
    render(wrap(<CompanyDrillDown stock={stock} quote={quote} priceHistory={[]} news={[]} imageUrl={null} onClose={onClose} />));
    fireEvent.click(screen.getByTestId('drilldown-backdrop'));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when Escape key pressed', () => {
    const onClose = vi.fn();
    render(wrap(<CompanyDrillDown stock={stock} quote={quote} priceHistory={[]} news={[]} imageUrl={null} onClose={onClose} />));
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
