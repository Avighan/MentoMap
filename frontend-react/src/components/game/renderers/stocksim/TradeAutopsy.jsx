import React from 'react';
import { THEME, gainLossColor } from './theme';
import { pickBestTrade, pickWorstTrade, whatWouldHaveBeenBetter } from './autopsy';

function TradeRow({ trade, label, testId }) {
  if (!trade) return null;
  return (
    <div data-testid={testId} style={{ background: THEME.bgTile, borderRadius: 8, padding: 10, marginBottom: 8 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted, fontWeight: 700 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 800, color: THEME.textPrimary }}>
        {trade.symbol} · {trade.side} · tick {trade.tick}
      </div>
      <div style={{ fontSize: 12, color: gainLossColor(trade.realized_pnl), fontWeight: 700 }}>
        ₹{trade.realized_pnl}
      </div>
      <div style={{ fontSize: 11, color: THEME.textMuted, marginTop: 4 }}>
        {whatWouldHaveBeenBetter(trade, trade.news_at_tick || [])}
      </div>
    </div>
  );
}

export default function TradeAutopsy({ final }) {
  const log = final?.trade_log_enriched || [];
  const best = pickBestTrade(log);
  const worst = pickWorstTrade(log);
  if (!best && !worst) {
    return <div style={{ padding: 12, color: THEME.textMuted, fontSize: 12 }}>No trades to autopsy.</div>;
  }
  return (
    <div style={{ background: '#fff', border: `1px solid ${THEME.borderTile}`, borderRadius: 12, padding: 14, margin: '12px 0' }}>
      <div style={{ fontSize: 11, color: THEME.textMuted, fontWeight: 700, marginBottom: 8 }}>🔬 TRADE AUTOPSY</div>
      <TradeRow trade={best} label="BEST TRADE" testId="autopsy-best" />
      <TradeRow trade={worst} label="WORST TRADE" testId="autopsy-worst" />
    </div>
  );
}
