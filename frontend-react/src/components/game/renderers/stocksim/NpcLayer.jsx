import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { THEME } from './theme';

const NpcContext = createContext(null);

const COOLDOWNS = {
  broker: 4,
  journalist: 0,
  analyst: 0,
  mentor: Infinity, // mentor handled separately (one-shot)
};

export function NpcLayerProvider({ currentTick = 0, children }) {
  const lastTickByPersona = useRef({});
  const [active, setActive] = useState(null);

  const say = useCallback((persona, payload) => {
    if (!payload) return;
    const last = lastTickByPersona.current[persona];
    const cooldown = COOLDOWNS[persona] ?? 0;
    if (last != null && currentTick - last < cooldown) return;
    lastTickByPersona.current[persona] = currentTick;
    setActive({ persona, payload, ts: Date.now() });
  }, [currentTick]);

  const dismiss = useCallback(() => setActive(null), []);

  const value = { say, dismiss, active };
  return (
    <NpcContext.Provider value={value}>
      {children}
      {active && <NpcChip persona={active.persona} payload={active.payload} onDismiss={dismiss} />}
    </NpcContext.Provider>
  );
}

export function useNpc() {
  const ctx = useContext(NpcContext);
  if (!ctx) throw new Error('useNpc must be used inside NpcLayerProvider');
  return ctx;
}

const PERSONA_ICON = { broker: '💼', journalist: '📰', analyst: '🤖', mentor: '🧭' };

function NpcChip({ persona, payload, onDismiss }) {
  const { t } = useTranslation();
  const text = t(payload.key, payload.props || {});
  return (
    <div
      data-testid="npc-chip"
      role="status"
      style={{
        position: 'fixed',
        bottom: 16,
        left: '50%',
        transform: 'translateX(-50%)',
        background: THEME.bgTile,
        border: `1px solid ${THEME.borderTile}`,
        borderLeft: `3px solid ${THEME.accentWarm}`,
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 12,
        color: THEME.textPrimary,
        maxWidth: 480,
        zIndex: 90,
        cursor: 'pointer',
        boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
      }}
      onClick={onDismiss}
    >
      <strong style={{ color: THEME.textMuted }}>{PERSONA_ICON[persona] || ''} {persona}:</strong> {text}
    </div>
  );
}
