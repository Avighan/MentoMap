/**
 * OfflineActivityCard — renders a single offline (printable) activity card.
 *
 * Two modes:
 *   - <OfflineActivityCard card={card} />          render directly
 *   - <OfflineActivityCard dim="empathy" age={8} /> fetch best-fit card
 */
import React, { useEffect, useState } from 'react';
import { matchOfflineActivity } from '../../api/retention';

export default function OfflineActivityCard({ card: providedCard, dim, age }) {
  const [card, setCard] = useState(providedCard || null);
  const [loading, setLoading] = useState(!providedCard && Boolean(dim));

  useEffect(() => {
    if (providedCard) {
      setCard(providedCard);
      setLoading(false);
      return;
    }
    if (!dim) return;
    let cancelled = false;
    setLoading(true);
    matchOfflineActivity({ dim, age: age ?? 10 })
      .then((c) => { if (!cancelled) setCard(c || null); })
      .catch(() => { if (!cancelled) setCard(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [providedCard, dim, age]);

  if (loading) return <div style={{ color: '#9CA3AF', padding: 12 }}>Finding an activity…</div>;
  if (!card) return null;

  return (
    <div style={{ background: '#1F2937', border: '1px solid #374151',
                  borderRadius: 12, padding: 16, color: '#F9FAFB',
                  marginBottom: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 22 }}>{card.emoji || '🎲'}</span>
        <div style={{ fontWeight: 800, fontSize: 15 }}>{card.title}</div>
      </div>
      {card.subtitle && (
        <div style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 8 }}>{card.subtitle}</div>
      )}
      {card.description && (
        <p style={{ fontSize: 13, color: '#D1D5DB', marginBottom: 8 }}>{card.description}</p>
      )}
      {Array.isArray(card.steps) && card.steps.length > 0 && (
        <ol style={{ paddingLeft: 18, fontSize: 13, color: '#D1D5DB',
                     marginBottom: 8 }}>
          {card.steps.map((step, i) => (
            <li key={i} style={{ marginBottom: 4 }}>{step}</li>
          ))}
        </ol>
      )}
      {card.materials && (
        <div style={{ fontSize: 12, color: '#9CA3AF' }}>
          <strong>Materials:</strong> {Array.isArray(card.materials) ? card.materials.join(', ') : card.materials}
        </div>
      )}
      {card.duration_minutes && (
        <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>
          ⏱ ~{card.duration_minutes} min
        </div>
      )}
    </div>
  );
}
