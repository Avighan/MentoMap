/**
 * StockMarketGame.test.jsx — vitest suite for the Tier-2 realtime stocksim
 * renderer, now reachable at /play/:gameId via StockMarketPlayPage.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';
import { OrgProvider } from '../contexts/OrgContext';
import StockMarketGame from '../components/game/renderers/StockMarketGame';
import * as stocksimApi from '../api/stocksim';

vi.mock('../api/stocksim');

function renderGame(props) {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <OrgProvider>
          <StockMarketGame {...props} />
        </OrgProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

const mockStart = {
  seed: 12345,
  profile: 'day_trader',
  config: {
    tick_count: 22,
    tick_interval_ms: 8000,
    starting_capital: 100000,
    stocks: [
      {
        symbol: 'INFY',
        name: 'Infosys',
        sector: 'IT',
        starting_price: 1500,
        volatility: 0.02,
      },
      {
        symbol: 'TCS',
        name: 'TCS',
        sector: 'IT',
        starting_price: 3500,
        volatility: 0.018,
      },
    ],
    charges: { brokerage_bps: 3, stt_sell_bps: 10, gst_pct: 18 },
    circuit_breaker_pct: [5],
  },
  state: {
    seed: 12345,
    cash: 100000,
    holdings: {},
    pending_orders: [],
    current_tick: 0,
    completed: false,
    realized_pnl: 0,
    trade_log: [],
  },
  news_strip: [{ tick: 1, text: 'Market opens flat', severity: 'info' }],
};

const mockState = {
  state: { ...mockStart.state, current_tick: 1 },
  quotes: {
    INFY: { mid: 1502, bid: 1501.5, ask: 1502.5, volume: 11000 },
    TCS: { mid: 3505, bid: 3504, ask: 3506, volume: 9000 },
  },
  pnl: { total: 0, realized: 0, unrealized: 0 },
  halted_symbols: {},
  event: null,
};

describe('StockMarketGame', () => {
  beforeEach(() => {
    stocksimApi.startStocksim.mockResolvedValue(mockStart);
    stocksimApi.getStocksimState.mockResolvedValue(mockState);
    stocksimApi.placeStocksimTrade.mockResolvedValue({
      status: 'filled',
      fill: { price: 1502.5, qty: 10 },
      new_cash: 84975,
      new_holdings: { INFY: { qty: 10, avg_price: 1502.5 } },
    });
    stocksimApi.completeStocksim.mockResolvedValue({
      pnl: { total: 1500, realized: 1500, unrealized: 0 },
      dimensions: {
        risk_tolerance: 70,
        delayed_gratification: 60,
        strategic_thinking: 65,
        financial_literacy: 75,
      },
      recap_messages: ['Solid day-trading session.'],
      xp_awarded: 250,
      completed: true,
    });
  });

  it('mounts and starts a stocksim session', async () => {
    renderGame({ runId: 'r1', gameData: { title: 'Stock Market' }, config: {} });
    await waitFor(() =>
      expect(stocksimApi.startStocksim).toHaveBeenCalledWith(
        'r1',
        expect.objectContaining({ profile: expect.any(String) }),
      ),
    );
  });

  it('renders net worth, P&L, and depth ladder', async () => {
    // v2 UI (the default — see StockMarketGame's v2Enabled check) shows net
    // worth/P&L in the sticky PersistentStrip rather than the legacy
    // stocksim-cash element, which only renders when v2 is disabled.
    renderGame({ runId: 'r1', gameData: {}, config: {} });
    await waitFor(() => expect(screen.getByText('NET WORTH')).toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getByTestId('persistent-pnl')).toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByTestId('stocksim-depth-ladder')).toBeInTheDocument(),
    );
  });

  it('places a buy order via placeStocksimTrade', async () => {
    renderGame({ runId: 'r1', gameData: {}, config: {} });
    await waitFor(() => screen.getByTestId('stocksim-buy-btn'));
    fireEvent.click(screen.getByTestId('stocksim-buy-btn'));
    await waitFor(() =>
      expect(stocksimApi.placeStocksimTrade).toHaveBeenCalledWith(
        'r1',
        expect.objectContaining({
          side: 'buy',
          order_type: expect.any(String),
        }),
      ),
    );
  });

  it('shows recap on complete', async () => {
    const onComplete = vi.fn();
    // Force final-tick state so the renderer auto-calls completeStocksim.
    stocksimApi.getStocksimState.mockResolvedValue({
      ...mockState,
      state: { ...mockStart.state, current_tick: 21, completed: true },
    });
    renderGame({ runId: 'r1', gameData: {}, config: {}, onComplete });
    await waitFor(() =>
      expect(stocksimApi.completeStocksim).toHaveBeenCalledWith('r1'),
    );
    await waitFor(() =>
      expect(screen.getByText(/Market Closed/i)).toBeInTheDocument(),
    );
  });
});
