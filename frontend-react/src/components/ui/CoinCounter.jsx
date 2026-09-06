/**
 * CoinCounter — small pill showing the current user's wallet balance.
 * Rendered by ModuleDetailPage.jsx as `<CoinCounter />` (no props).
 * Backed by GET /api/wallet -> { balance, lifetime_coins } (backend/wallet.py).
 */
import React, { useEffect, useState } from 'react';
import { getWallet } from '../../api/wallet';

export default function CoinCounter() {
  const [balance, setBalance] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getWallet()
      .then((w) => { if (!cancelled) setBalance(w.balance ?? 0); })
      .catch(() => { if (!cancelled) setBalance(null); });
    return () => { cancelled = true; };
  }, []);

  if (balance === null) return null;

  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '4px 12px', borderRadius: 999, background: '#FFF7E0',
        color: '#B8860B', fontWeight: 700, fontSize: '0.85rem',
      }}
      title="Your coin balance"
    >
      🪙 {balance.toLocaleString()}
    </span>
  );
}
