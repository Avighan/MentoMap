import { describe, it, expect } from 'vitest';
import {
  analystVerdict,
  journalistFlavor,
  brokerOnTrade,
  mentorCheckIn,
} from './npcDialog';

describe('npcDialog', () => {
  it('analystVerdict flags stretched valuation when pe > sector_pe + 10%', () => {
    const out = analystVerdict({ pe: 28.4, sector_pe: 24.0, roe: 22.1, debt_equity: 0.12 });
    expect(out.key).toBe('stocksim.npc.analyst.stretched');
    expect(out.props.premiumPct).toBe(18);
  });

  it('analystVerdict flags cheap when pe < sector_pe - 10%', () => {
    const out = analystVerdict({ pe: 18, sector_pe: 24, roe: 19, debt_equity: 0.5 });
    expect(out.key).toBe('stocksim.npc.analyst.cheap');
  });

  it('analystVerdict returns fair when within band', () => {
    const out = analystVerdict({ pe: 24, sector_pe: 24, roe: 18, debt_equity: 0.4 });
    expect(out.key).toBe('stocksim.npc.analyst.fair');
  });

  it('journalistFlavor returns key with headline + reason', () => {
    const out = journalistFlavor({
      tick: 4,
      headline: 'TechVista wins ₹500Cr cloud contract',
      reason: 'Large new contract → revenue visibility lifts price',
    });
    expect(out.key).toBe('stocksim.npc.journalist.flavor');
    expect(out.props.tick).toBe(4);
    expect(out.props.reason).toMatch(/revenue visibility/);
  });

  it('brokerOnTrade warns when riskPct > 20', () => {
    const out = brokerOnTrade({ side: 'buy', symbol: 'TECHV', qty: 100, price: 215 }, 25);
    expect(out.key).toBe('stocksim.npc.broker.high_risk');
    expect(out.props.riskPct).toBe(25);
  });

  it('brokerOnTrade is silent when riskPct < 5', () => {
    const out = brokerOnTrade({ side: 'buy', symbol: 'TECHV', qty: 1, price: 215 }, 2);
    expect(out).toBeNull();
  });

  it('mentorCheckIn keys off concentration in single sector', () => {
    const state = {
      positions: { TECHV: 50, INFOS: 30 },
      stocks_by_sector: { TECHV: 'IT', INFOS: 'IT' },
    };
    const out = mentorCheckIn(state);
    expect(out.key).toBe('stocksim.npc.mentor.concentrated');
    expect(out.props.sector).toBe('IT');
  });
});
