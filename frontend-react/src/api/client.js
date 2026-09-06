/**
 * Shared axios instance for every api/*.js client.
 *
 * Every existing api client in this directory (games.js, modules.js,
 * profile.js, retention.js, stocksim.js, breakout.js) already does
 * `import apiClient from './client'` and calls relative paths like
 * '/api/games' — no VITE_API_* base URL is read anywhere in src/, so the
 * convention is: relative paths, proxied to the backend in dev (see
 * vite.config.js) and same-origin in production.
 *
 * This also owns auth: LoginPage stores the JWT returned by
 * POST /api/auth/login /register in localStorage, and every subsequent
 * request here attaches it as `Authorization: Bearer <token>` (see
 * backend/auth.py's get_token_from_request, which reads that header).
 *
 * The storage key is plain `'token'` — several already-existing components
 * (PostGameInsights.jsx, MusicGameRenderer.jsx, TitrationLabRenderer.jsx,
 * StudentHomePage.jsx, renderers/_graderSubmit.js) already read
 * `localStorage.getItem('token')` directly for raw fetch() calls, so this
 * is the real existing convention, not a new one.
 */
import axios from 'axios';

export const AUTH_TOKEN_KEY = 'token';

export const getStoredToken = () => {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setStoredToken = (token) => {
  try {
    if (token) localStorage.setItem(AUTH_TOKEN_KEY, token);
    else localStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {
    // localStorage unavailable (private mode, etc.) — auth just won't persist.
  }
};

const apiClient = axios.create({
  baseURL: '/',
});

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On a 401 from an authenticated request, the stored token is stale/expired —
// drop it so the UI falls back to a logged-out state instead of looping.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      setStoredToken(null);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
