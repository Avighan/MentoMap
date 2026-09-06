/**
 * Duty Mode — a purely client-side preference (no backend route: it only
 * changes how the local UI presents rewards, see SettingsPage.jsx's
 * description). Persisted to localStorage; `setDutyMode` is called directly
 * from event handlers (not as a hook return value), so it broadcasts a
 * custom event that every `useDutyMode()` subscriber re-renders on —
 * including in other components/tabs open at the same time.
 */
import { useState, useEffect } from 'react';

const STORAGE_KEY = 'mentomap_duty_mode';
const EVENT_NAME = 'mentomap:duty-mode-change';

const readStored = () => {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
};

export const setDutyMode = (enabled) => {
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0');
  } catch {
    // ignore — the in-memory event still fires for this tab.
  }
  window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: !!enabled }));
};

export const useDutyMode = () => {
  const [enabled, setEnabled] = useState(readStored);

  useEffect(() => {
    const onChange = (e) => setEnabled(!!e.detail);
    const onStorage = (e) => {
      if (e.key === STORAGE_KEY) setEnabled(e.newValue === '1');
    };
    window.addEventListener(EVENT_NAME, onChange);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(EVENT_NAME, onChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  return enabled;
};
