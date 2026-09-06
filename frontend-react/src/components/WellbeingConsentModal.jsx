/**
 * WellbeingConsentModal — DPDP-style consent prompt for wellbeing/behavioral
 * monitoring. Rendered by HomePage.jsx as:
 *   <WellbeingConsentModal profile={wellbeingProfile} onClose={...} onConsent={(status) => ...} />
 * and gated by the exported `shouldShowWellbeingConsent(profile)`.
 *
 * Backed by the real route in backend/app.py `update_wellbeing_consent_endpoint`:
 *   PATCH /api/profile/wellbeing-consent  body: { consent: 'given'|'withdrawn' }
 * via api/profile.js `updateWellbeingConsent(consent)`.
 *
 * Judgment call: shown once, only while the profile has never recorded a
 * decision (`wellbeing_consent` is unset) — once a user has explicitly
 * given or withdrawn consent, this doesn't re-prompt them.
 */
import React, { useState } from 'react';
import { updateWellbeingConsent } from '../api/profile';

export const shouldShowWellbeingConsent = (profile) => {
  if (!profile) return false;
  return profile.wellbeing_consent == null;
};

export default function WellbeingConsentModal({ profile, onClose, onConsent }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const respond = async (consent) => {
    setSubmitting(true);
    setError('');
    try {
      const res = await updateWellbeingConsent(consent);
      onConsent?.(res.wellbeing_consent || consent);
      onClose?.();
    } catch {
      setError('Could not save your choice. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 200,
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div style={{ background: '#fff', borderRadius: 16, padding: 24, maxWidth: 440, width: '100%' }}>
        <h2 style={{ margin: '0 0 12px', fontSize: '1.1rem', color: '#2D3047' }}>
          Help us look out for {profile?.username || 'you'}
        </h2>
        <p style={{ fontSize: '0.9rem', color: '#6D7286', lineHeight: 1.5 }}>
          MentoMap can watch for signs of frustration or disengagement while you play
          (e.g. rage-quitting, long pauses) to gently check in and help teachers/parents
          support you. This is optional and you can change your mind anytime in Settings.
        </p>
        {error && <div style={{ color: '#EF4444', fontSize: '0.85rem', marginBottom: 8 }}>{error}</div>}
        <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
          <button
            onClick={() => respond('given')}
            disabled={submitting}
            style={{
              flex: 1, padding: '10px 16px', borderRadius: 10, border: 'none',
              background: '#6C5CE7', color: '#fff', fontWeight: 700, cursor: 'pointer',
            }}
          >
            Yes, keep an eye out
          </button>
          <button
            onClick={() => respond('withdrawn')}
            disabled={submitting}
            style={{
              flex: 1, padding: '10px 16px', borderRadius: 10, border: '1px solid #E5E7EB',
              background: '#fff', color: '#2D3047', fontWeight: 700, cursor: 'pointer',
            }}
          >
            No thanks
          </button>
        </div>
      </div>
    </div>
  );
}
