import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Polyfill localStorage for jsdom environments where --localstorage-file
// flag causes the native jsdom localStorage to be initialized without
// getItem/setItem methods (affects module-level imports like i18n.js).
if (typeof localStorage === 'undefined' || typeof localStorage.getItem !== 'function') {
  const store = {};
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (k) => store[k] ?? null,
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
      clear: () => { Object.keys(store).forEach(k => delete store[k]); },
    },
  });
}

afterEach(() => {
  cleanup();
});
