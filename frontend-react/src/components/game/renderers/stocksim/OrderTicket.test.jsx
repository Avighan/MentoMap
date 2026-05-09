import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../../i18n';
import OrderTicket from './OrderTicket';
import { NpcLayerProvider } from './NpcLayer';

const wrap = (ui) => (
  <I18nextProvider i18n={i18n}>
    <NpcLayerProvider currentTick={0}>{ui}</NpcLayerProvider>
  </I18nextProvider>
);

const STOCKS = [{ symbol: 'TECHV', name: 'TechVista', sector: 'IT', starting_price: 215 }];

describe('OrderTicket v2 additions', () => {
  it('shows position sizer line with total cost and risk %', () => {
    render(wrap(
      <OrderTicket
        stocks={STOCKS}
        selectedSymbol="TECHV"
        currentQuote={{ mid: 215, ask: 215, bid: 214.95 }}
        cashAvailable={10000}
        onSubmit={() => {}}
      />
    ));
    fireEvent.change(screen.getByTestId('order-qty'), { target: { value: '10' } });
    expect(screen.getByTestId('order-sizer').textContent).toMatch(/₹2,150/);
    expect(screen.getByTestId('order-sizer').textContent).toMatch(/21\.5%/);
  });

  it('toggles Target/Stop chips and includes them in submitted payload', () => {
    const onSubmit = vi.fn();
    render(wrap(
      <OrderTicket
        stocks={STOCKS}
        selectedSymbol="TECHV"
        currentQuote={{ mid: 215, ask: 215, bid: 214.95 }}
        cashAvailable={10000}
        onSubmit={onSubmit}
      />
    ));
    fireEvent.change(screen.getByTestId('order-qty'), { target: { value: '5' } });
    fireEvent.click(screen.getByTestId('chip-target'));
    fireEvent.click(screen.getByTestId('chip-stop'));
    fireEvent.click(screen.getByTestId('stocksim-buy-btn'));
    expect(onSubmit).toHaveBeenCalled();
    const payload = onSubmit.mock.calls[0][0];
    expect(payload.target_pct).toBe(5);
    expect(payload.stop_pct).toBe(-3);
  });
});
