import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../../../i18n';
import ChartTab from './ChartTab';
import FundamentalsTab from './FundamentalsTab';
import TechnicalsTab from './TechnicalsTab';
import NewsTab from './NewsTab';
import PeersTab from './PeersTab';
import AboutTab from './AboutTab';

const wrap = (ui) => <I18nextProvider i18n={i18n}>{ui}</I18nextProvider>;

describe('Drill-down tabs render with empty/minimal data', () => {
  it('ChartTab renders with empty priceHistory', () => {
    expect(() => render(wrap(<ChartTab priceHistory={[]} indicators={{}} />))).not.toThrow();
  });
  it('FundamentalsTab renders with no fundamentals', () => {
    expect(() => render(wrap(<FundamentalsTab fundamentals={null} />))).not.toThrow();
  });
  it('TechnicalsTab renders with empty priceHistory', () => {
    expect(() => render(wrap(<TechnicalsTab priceHistory={[]} stockCfg={{ symbol: 'X' }} />))).not.toThrow();
  });
  it('NewsTab renders with empty news', () => {
    expect(() => render(wrap(<NewsTab news={[]} symbol="X" currentTick={0} />))).not.toThrow();
  });
  it('PeersTab renders with no peers', () => {
    expect(() => render(wrap(<PeersTab peers={[]} stockCfg={{ symbol: 'X', fundamentals: {} }} />))).not.toThrow();
  });
  it('AboutTab renders with no about block', () => {
    expect(() => render(wrap(<AboutTab about={null} imageUrl={null} />))).not.toThrow();
  });
});
