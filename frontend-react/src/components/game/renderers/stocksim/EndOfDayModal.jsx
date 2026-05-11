// EndOfDayModal.jsx
import React from 'react';
import { THEME, gainLossColor } from './theme';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;
const pct = (p) => `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`;

export default function EndOfDayModal({
  open, day, todayPnL = { total: 0, realized: 0, unrealized: 0 },
  topMover, bottomMover, earningsRevealed = [], headlines = [], onContinue,
}) {
  if (!open || !day) return null;
  const isLastDay = day.index + 1 >= day.of;
  return (
    <div
      data-testid="eod-backdrop"
      style={{
        position: 'fixed', inset: 0, background: 'rgba(60,40,10,0.55)',
        zIndex: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div style={{ background: '#fff', borderRadius: 14, maxWidth: 520, width: '100%', padding: 20, border: `1px solid ${THEME.borderTile}` }}>
        <div style={{ fontSize: 12, color: THEME.textMuted }}>End of {day.label}</div>
        <div style={{ fontSize: 24, fontWeight: 800, color: THEME.textPrimary, marginBottom: 8 }}>
          Day {day.index + 1} closed
        </div>
        <div data-testid="eod-pnl" style={{ fontSize: 18, fontWeight: 800, color: gainLossColor(todayPnL.total) }}>
          {todayPnL.total >= 0 ? '▲' : '▼'} {fmt(todayPnL.total)} today
        </div>
        <div style={{ fontSize: 12, color: THEME.textMuted }}>
          Realized {fmt(todayPnL.realized)} · Unrealized {fmt(todayPnL.unrealized)}
        </div>

        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <Mover label="Top mover" mover={topMover} />
          <Mover label="Worst mover" mover={bottomMover} />
        </div>

        {earningsRevealed.length > 0 && (
          <div data-testid="eod-earnings" style={{ marginTop: 12, padding: 10, background: THEME.bgTile, borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: THEME.textMuted, marginBottom: 4 }}>Earnings revealed</div>
            {earningsRevealed.map((e) => (
              <div key={e.symbol} style={{ fontSize: 13 }}>
                <strong>{e.symbol}</strong>: {e.headline}{' '}
                <span style={{ color: gainLossColor(e.surprise) }}>({pct((e.surprise || 0) * 100)})</span>
              </div>
            ))}
          </div>
        )}

        {headlines.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 12, color: THEME.textMuted }}>
            {headlines.map((h, i) => <div key={i}>· {h}</div>)}
          </div>
        )}

        <button
          data-testid="eod-continue"
          onClick={onContinue}
          style={{
            marginTop: 16, padding: '10px 16px', width: '100%',
            background: THEME.accentWarm, color: '#fff', border: 'none',
            borderRadius: 8, fontWeight: 700, cursor: 'pointer',
          }}
        >{isLastDay ? 'Continue to weekend →' : 'Continue to next day →'}</button>
      </div>
    </div>
  );
}

function Mover({ label, mover }) {
  return (
    <div style={{ background: THEME.bgTile, padding: 8, borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted }}>{label}</div>
      {mover ? (
        <>
          <div style={{ fontWeight: 700 }}>{mover.symbol}</div>
          <div style={{ color: gainLossColor(mover.changePct) }}>{pct(mover.changePct)}</div>
        </>
      ) : (
        <div style={{ color: THEME.textMuted, fontSize: 12 }}>—</div>
      )}
    </div>
  );
}
