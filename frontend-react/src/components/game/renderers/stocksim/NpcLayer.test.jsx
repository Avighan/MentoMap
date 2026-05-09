import { describe, it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { NpcLayerProvider, useNpc } from './NpcLayer';

function Probe() {
  const npc = useNpc();
  return (
    <div>
      <button onClick={() => npc.say('broker', { key: 'stocksim.npc.broker.high_risk', props: { riskPct: 30, symbol: 'TECHV' } })}>broker</button>
      <button onClick={() => npc.say('journalist', { key: 'stocksim.npc.journalist.flavor', props: { tick: 4, headline: 'h', reason: 'r' } })}>journalist</button>
    </div>
  );
}

describe('NpcLayer', () => {
  it('renders only one NPC chip at a time', () => {
    render(
      <NpcLayerProvider currentTick={1}>
        <Probe />
      </NpcLayerProvider>
    );
    act(() => { screen.getByText('broker').click(); });
    expect(screen.getAllByTestId('npc-chip').length).toBe(1);
    act(() => { screen.getByText('journalist').click(); });
    // newest wins: still one chip
    expect(screen.getAllByTestId('npc-chip').length).toBe(1);
  });

  it('honors broker cooldown (4 ticks)', () => {
    const { rerender } = render(
      <NpcLayerProvider currentTick={1}>
        <Probe />
      </NpcLayerProvider>
    );
    act(() => { screen.getByText('broker').click(); });
    expect(screen.queryByTestId('npc-chip')).not.toBeNull();

    // Advance ticks to 3 (still within 4-tick cooldown). New broker call should be suppressed.
    rerender(
      <NpcLayerProvider currentTick={3}>
        <Probe />
      </NpcLayerProvider>
    );
    act(() => { screen.getByText('broker').click(); });
    // Still showing earliest; not duplicated
    expect(screen.getAllByTestId('npc-chip').length).toBe(1);
  });

  it('honors mentor one-shot semantics (cooldown Infinity)', () => {
    function MentorProbe() {
      const npc = useNpc();
      return <button onClick={() => npc.say('mentor', { key: 'stocksim.npc.mentor.diversified', props: {} })}>mentor</button>;
    }
    const { rerender } = render(
      <NpcLayerProvider currentTick={1}>
        <MentorProbe />
      </NpcLayerProvider>
    );
    act(() => { screen.getByText('mentor').click(); });
    expect(screen.getAllByTestId('npc-chip').length).toBe(1);
    // Advance many ticks; mentor should still be suppressed (one-shot).
    rerender(
      <NpcLayerProvider currentTick={9999}>
        <MentorProbe />
      </NpcLayerProvider>
    );
    act(() => { screen.getByText('mentor').click(); });
    expect(screen.getAllByTestId('npc-chip').length).toBe(1);
  });
});
