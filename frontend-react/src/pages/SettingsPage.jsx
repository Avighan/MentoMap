/**
 * SettingsPage - User preferences (notification toggles).
 *
 * Phase D adds an opt-in toggle for the 28-day Mento Entrepreneur daily
 * dispatch. The toggle defaults to ON (matches dispatcher default) and is
 * stored on the user's profile under preferences.module_daily_dispatch.
 */
import React, { useEffect, useState } from 'react';
import { getProfile, updateProfile } from '../api/profile';

export default function SettingsPage() {
  const [prefs, setPrefs] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getProfile()
      .then((p) => {
        if (cancelled) return;
        setPrefs((p && p.preferences) || {});
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message || 'Could not load preferences');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const updatePref = async (key, value) => {
    const next = { ...prefs, [key]: value };
    setPrefs(next);
    setSaving(true);
    setError(null);
    try {
      await updateProfile({ preferences: next });
      setSavedAt(Date.now());
    } catch (e) {
      setError(e?.message || 'Could not save preference');
      // Revert UI on failure
      setPrefs(prefs);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 text-sm text-gray-500">Loading settings…</div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-1">Settings</h1>
      <p className="text-sm text-gray-500 mb-6">
        Notification preferences for Mento learning content.
      </p>

      <section className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h2 className="text-base font-semibold mb-3">Notifications</h2>

        <label className="flex items-start gap-3 text-sm py-2 cursor-pointer">
          <input
            type="checkbox"
            checked={prefs.module_daily_dispatch !== false}
            onChange={(e) => updatePref('module_daily_dispatch', e.target.checked)}
            className="mt-1"
          />
          <span>
            <span className="block font-medium">
              Daily Mento workshop tips (during the 4-week module)
            </span>
            <span className="block text-gray-500 text-xs">
              We'll send one short tip a day at 6 PM IST while you're inside
              the Entrepreneur Workshop. Turn this off any time.
            </span>
          </span>
        </label>
      </section>

      {error && (
        <p className="text-sm text-red-600 mb-3">{error}</p>
      )}
      {saving && (
        <p className="text-sm text-gray-500">Saving…</p>
      )}
      {!saving && savedAt && (
        <p className="text-sm text-green-600">Saved.</p>
      )}
    </div>
  );
}
