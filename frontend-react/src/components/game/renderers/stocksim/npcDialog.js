// Pure functions: NPC signal + data → { key, props } for i18n.
// Returning { key, props } lets the consumer call t(key, props).
// Returning null means "no line at this signal".

export function analystVerdict({ pe, sector_pe, roe, debt_equity }) {
  if (pe == null || sector_pe == null) {
    return { key: 'stocksim.npc.analyst.fair', props: {} };
  }
  const premiumPct = Math.round(((pe - sector_pe) / sector_pe) * 100);
  if (premiumPct >= 10) {
    return { key: 'stocksim.npc.analyst.stretched', props: { premiumPct, pe, sectorPe: sector_pe } };
  }
  if (premiumPct <= -10) {
    return { key: 'stocksim.npc.analyst.cheap', props: { discountPct: -premiumPct, pe, sectorPe: sector_pe } };
  }
  return { key: 'stocksim.npc.analyst.fair', props: { pe, sectorPe: sector_pe, roe, debtEquity: debt_equity } };
}

export function journalistFlavor(newsItem) {
  if (!newsItem) return null;
  return {
    key: 'stocksim.npc.journalist.flavor',
    props: {
      tick: newsItem.tick,
      headline: newsItem.headline,
      reason: newsItem.reason || '',
    },
  };
}

export function brokerOnTrade(order, riskPct) {
  if (riskPct == null) return null;
  if (riskPct >= 20) {
    return { key: 'stocksim.npc.broker.high_risk', props: { riskPct: Math.round(riskPct), symbol: order.symbol } };
  }
  if (riskPct >= 10) {
    return { key: 'stocksim.npc.broker.moderate', props: { riskPct: Math.round(riskPct), symbol: order.symbol } };
  }
  return null;
}

export function mentorCheckIn(state) {
  const positions = state?.positions || {};
  const sectors = state?.stocks_by_sector || {};
  const sectorTotals = {};
  let total = 0;
  for (const [sym, qty] of Object.entries(positions)) {
    const sec = sectors[sym] || 'Other';
    sectorTotals[sec] = (sectorTotals[sec] || 0) + Math.abs(qty);
    total += Math.abs(qty);
  }
  if (total === 0) {
    return { key: 'stocksim.npc.mentor.no_trades', props: {} };
  }
  const dominant = Object.entries(sectorTotals).sort((a, b) => b[1] - a[1])[0];
  if (dominant && dominant[1] / total >= 0.7) {
    return { key: 'stocksim.npc.mentor.concentrated', props: { sector: dominant[0], pct: Math.round((dominant[1] / total) * 100) } };
  }
  return { key: 'stocksim.npc.mentor.diversified', props: {} };
}
