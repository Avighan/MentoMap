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
      className="bg-white rounded-xl border border-gray-100 p-2 text-[11px] font-mono"
      style={{ width: 160 }}
    >
      <div className="flex justify-between text-[9px] uppercase tracking-wider text-gray-400 px-1 pb-1 border-b border-gray-100">
        <span>Price</span>
        <span>Qty</span>
      </div>

      {/* Ask side (red) */}
      <div className="py-1">
        {asks.map((row, idx) => (
          <div
            key={`a-${idx}`}
            className="flex justify-between items-center px-1 py-0.5 rounded"
            style={{ backgroundColor: `rgba(239, 68, 68, ${0.05 + idx * 0.02})` }}
          >
            <span className="text-red-600">{row.px.toFixed(2)}</span>
            <span className="text-gray-500">{row.qty}</span>
          </div>
        ))}
      </div>

      {/* Mid */}
      <div className="my-1 py-1 text-center bg-gray-50 rounded border border-dashed border-gray-200">
        <span className="text-[10px] uppercase text-gray-400 mr-1">Mid</span>
        <span className="font-bold text-gray-800">₹{safeMid.toFixed(2)}</span>
      </div>

      {/* Bid side (green) */}
      <div className="py-1">
        {bids.map((row, idx) => (
          <div
            key={`b-${idx}`}
            className="flex justify-between items-center px-1 py-0.5 rounded"
            style={{ backgroundColor: `rgba(34, 197, 94, ${0.05 + idx * 0.02})` }}
          >
            <span className="text-green-600">{row.px.toFixed(2)}</span>
            <span className="text-gray-500">{row.qty}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DepthLadder;
