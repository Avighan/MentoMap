/**
 * PortfolioPanel — holdings and recent trades for the stocksim sidebar.
 *
 * Renders each held symbol with qty, avg price, current price, and
 * unrealized P&L (color-coded). Below holdings, lists the last 6 trades
 * (timestamp, side, symbol, qty, price). Compact card style consistent
 * with the existing Holdings/Recent Trades sections (gray-50 bg, rounded-xl).
 *
 * Props:
 *   holdings      { [symbol]: { qty, avg_price } }
 *   quotes        { [symbol]: { mid, bid, ask, volume } }
 *   transactions  Array<{ ts?, side, symbol, qty, price, tick }>
 *   cash          number
 *   totalValue    number
 *   pnl           { total, realized, unrealized }
 */
import React from 'react';
import { THEME, gainLossColor } from './theme';

function fmt(n, digits = 2) {
  if (n === undefined || n === null || Number.isNaN(Number(n))) return '-';
  return Number(n).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

const PortfolioPanel = ({
  holdings = {},
  quotes = {},
  transactions = [],
  cash = 0,
  totalValue = 0,
  pnl = { total: 0, realized: 0, unrealized: 0 },
}) => {
  const heldSymbols = Object.keys(holdings).filter(
    (sym) => (holdings[sym]?.qty || 0) !== 0,
  );

  const recentTrades = (transactions || []).slice(-6).reverse();

  return (
    <div data-testid="stocksim-portfolio-panel" className="flex flex-col gap-3">
      {/* Summary */}
      <div
        className="rounded-xl p-4"
        style={{
          backgroundColor: THEME.bgTile,
          border: `1px solid ${THEME.borderTile}`,
        }}
      >
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <div
              className="text-[10px] uppercase tracking-wider"
              style={{ color: THEME.textMuted }}
            >
              Total
            </div>
            <div
              data-testid="stocksim-portfolio-value"
              className="text-sm font-bold"
              style={{ color: THEME.textPrimary }}
            >
              ₹{fmt(totalValue, 0)}
            </div>
          </div>
          <div>
            <div
              className="text-[10px] uppercase tracking-wider"
              style={{ color: THEME.textMuted }}
            >
              Cash
            </div>
            <div
              className="text-sm font-bold"
              style={{ color: THEME.textPrimary }}
            >
              ₹{fmt(cash, 0)}
            </div>
          </div>
          <div>
            <div
              className="text-[10px] uppercase tracking-wider"
              style={{ color: THEME.textMuted }}
            >
              P&L
            </div>
            <div
              data-testid="stocksim-pnl"
              className="text-sm font-bold"
              style={{ color: gainLossColor(pnl?.total || 0) }}
            >
              {(pnl?.total || 0) >= 0 ? '+' : ''}₹{fmt(pnl?.total || 0, 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Holdings */}
      <div
        className="rounded-xl p-4"
        style={{
          backgroundColor: THEME.bgTile,
          border: `1px solid ${THEME.borderTile}`,
        }}
      >
        <h4
          className="text-xs uppercase tracking-wider font-semibold mb-3"
          style={{ color: THEME.textMuted }}
        >
          Holdings
        </h4>
        {heldSymbols.length === 0 ? (
          <p
            className="text-xs text-center py-2"
            style={{ color: THEME.textMuted }}
          >
            No stocks held yet
          </p>
        ) : (
          <div className="space-y-2">
            {heldSymbols.map((sym) => {
              const h = holdings[sym] || {};
              const q = quotes[sym] || {};
              const cur = q.mid ?? h.avg_price ?? 0;
              const u = ((cur - (h.avg_price || 0)) * (h.qty || 0));
              const upct =
                h.avg_price && h.qty
                  ? (((cur - h.avg_price) / h.avg_price) * 100)
                  : 0;
              const pos = u >= 0;
              return (
                <div
                  key={sym}
                  className="flex items-center justify-between text-xs"
                >
                  <div className="flex flex-col">
                    <span
                      className="font-bold"
                      style={{ color: THEME.textPrimary }}
                    >
                      {sym}
                    </span>
                    <span
                      className="text-[10px]"
                      style={{ color: THEME.textMuted }}
                    >
                      {h.qty}× @ ₹{fmt(h.avg_price, 2)}
                    </span>
                  </div>
                  <div className="text-right">
                    <div style={{ color: THEME.textPrimary }}>
                      ₹{fmt(cur, 2)}
                    </div>
                    <div
                      className="text-[10px] font-bold"
                      style={{ color: gainLossColor(u) }}
                    >
                      {pos ? '+' : ''}₹{fmt(u, 0)} ({pos ? '+' : ''}
                      {upct.toFixed(1)}%)
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent trades */}
      {recentTrades.length > 0 && (
        <div
          className="rounded-xl p-4"
          style={{
            backgroundColor: THEME.bgTile,
            border: `1px solid ${THEME.borderTile}`,
          }}
        >
          <h4
            className="text-xs uppercase tracking-wider font-semibold mb-2"
            style={{ color: THEME.textMuted }}
          >
            Recent Trades
          </h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {recentTrades.map((t, i) => {
              const side = (t.side || t.type || '').toLowerCase();
              const isBuy = side === 'buy';
              return (
                <div
                  key={`${t.tick ?? 'x'}-${t.symbol ?? ''}-${t.side ?? ''}-${i}`}
                  className="flex items-center justify-between text-xs"
                >
                  <span style={{ color: isBuy ? THEME.gain : THEME.loss }}>
                    {isBuy ? '▲ Buy' : '▼ Sell'} {t.qty}× {t.symbol || t.stock}
                  </span>
                  <span style={{ color: THEME.textMuted }}>
                    @₹{fmt(t.price, 2)}
                    {t.tick !== undefined ? ` T${t.tick}` : ''}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default PortfolioPanel;
