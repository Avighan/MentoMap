/**
 * DepthLadder — purely visual 5-level bid/ask ladder for the stocksim.
 *
 * Backend currently exposes only top-of-book bid/ask/mid/volume. To give
 * students an authentic Zerodha/Groww-style depth feel, this component
 * synthesises 5 stylised levels above and below by stepping outward in
 * 1 basis-point increments and tapering displayed sizes. No real depth
 * data is implied — fills always happen at the server-quoted top-of-book.
 *
 * Props:
 *   bid     number  current best bid
 *   ask     number  current best ask
 *   mid     number  mid price
 *   volume  number  current tick volume (used to taper synthesised sizes)
 */
import React, { useMemo } from 'react';
import { THEME } from './theme';

function buildLadder(bid, ask, mid, volume) {
  const safeMid = Number(mid) || Number(bid) || 0;
  const tick = Math.max(0.01, safeMid * 0.0001); // ~1 basis point
  const baseSize = Math.max(50, Math.round((Number(volume) || 1000) / 6));

  const asks = [];
  const bids = [];
  for (let i = 0; i < 5; i++) {
    const askPx = (Number(ask) || safeMid) + tick * i;
    const bidPx = Math.max(0.01, (Number(bid) || safeMid) - tick * i);
    const taper = 1 - i * 0.15;
    asks.push({
      px: askPx,
      qty: Math.max(10, Math.round(baseSize * taper)),
    });
    bids.push({
      px: bidPx,
      qty: Math.max(10, Math.round(baseSize * taper)),
    });
  }
  // Asks descend from highest to lowest (closest to mid at the bottom).
  asks.reverse();
  return { asks, bids };
}

const DepthLadder = ({ bid, ask, mid, volume }) => {
  const { asks, bids } = useMemo(
    () => buildLadder(bid, ask, mid, volume),
    [bid, ask, mid, volume],
  );
  const safeMid = Number(mid) || Number(bid) || 0;

  return (
    <div
      data-testid="stocksim-depth-ladder"
      className="rounded-xl p-2 text-[11px] font-mono"
      style={{
        width: 160,
        backgroundColor: THEME.bgTile,
        border: `1px solid ${THEME.borderTile}`,
      }}
    >
      <div
        className="flex justify-between text-[9px] uppercase tracking-wider px-1 pb-1"
        style={{
          color: THEME.textMuted,
          borderBottom: `1px solid ${THEME.borderTile}`,
        }}
      >
        <span>Price</span>
        <span>Qty</span>
      </div>

      {/* Ask side (loss) */}
      <div className="py-1">
        {asks.map((row, idx) => (
          <div
            key={`a-${idx}`}
            className="flex justify-between items-center px-1 py-0.5 rounded"
            style={{ backgroundColor: `rgba(163, 45, 45, ${0.05 + idx * 0.02})` }}
          >
            <span style={{ color: THEME.loss }}>{row.px.toFixed(2)}</span>
            <span style={{ color: THEME.textMuted }}>{row.qty}</span>
          </div>
        ))}
      </div>

      {/* Mid */}
      <div
        className="my-1 py-1 text-center rounded"
        style={{
          backgroundColor: THEME.bgPage,
          border: `1px dashed ${THEME.borderTile}`,
        }}
      >
        <span
          className="text-[10px] uppercase mr-1"
          style={{ color: THEME.textMuted }}
        >
          Mid
        </span>
        <span className="font-bold" style={{ color: THEME.textPrimary }}>
          ₹{safeMid.toFixed(2)}
        </span>
      </div>

      {/* Bid side (gain) */}
      <div className="py-1">
        {bids.map((row, idx) => (
          <div
            key={`b-${idx}`}
            className="flex justify-between items-center px-1 py-0.5 rounded"
            style={{ backgroundColor: `rgba(15, 110, 86, ${0.05 + idx * 0.02})` }}
          >
            <span style={{ color: THEME.gain }}>{row.px.toFixed(2)}</span>
            <span style={{ color: THEME.textMuted }}>{row.qty}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DepthLadder;
