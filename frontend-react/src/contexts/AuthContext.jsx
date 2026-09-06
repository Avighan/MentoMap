/**
 * AuthContext — session state for the whole app.
 *
 * Consumers across the codebase (HomePage, LeaderboardPage, SettingsPage,
 * ModuleDetailPage, StudentHomePage, GamePlayPage, MobileBottomNav,
 * PostGameInsights) do `const { user, logout } = useAuth()` and some also
 * read `isAuthenticated`. `user` matches backend/auth.py's `_public_user`
 * shape: { id, username, role, org_id }.
 */
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import apiClient, { getStoredToken, setStoredToken } from '../api/client';

const AuthContext = createContext(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};

const USER_CACHE_KEY = 'mentomap_user';

const readCachedUser = () => {
  try {
    const raw = localStorage.getItem(USER_CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const writeCachedUser = (user) => {
  try {
    if (user) localStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_CACHE_KEY);
  } catch {
    // ignore — user just won't survive a hard refresh this time.
  }
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => (getStoredToken() ? readCachedUser() : null));
  const [loading, setLoading] = useState(true);

  // Validate the stored token against the backend on first load (it may have
  // expired or been revoked server-side since the last visit).
  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }
    apiClient
      .get('/api/auth/me')
      .then((res) => {
        setUser(res.data.user);
        writeCachedUser(res.data.user);
      })
      .catch(() => {
        setStoredToken(null);
        writeCachedUser(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username, password) => {
    const res = await apiClient.post('/api/auth/login', { username, password });
    const { user: loggedInUser, token } = res.data;
    setStoredToken(token);
    writeCachedUser(loggedInUser);
    setUser(loggedInUser);
    return loggedInUser;
  }, []);

  const register = useCallback(async (username, password, role = 'student', orgId = 'default') => {
    const res = await apiClient.post('/api/auth/register', {
      username,
      password,
      role,
      org_id: orgId,
    });
    const { user: newUser, token } = res.data;
    setStoredToken(token);
    writeCachedUser(newUser);
    setUser(newUser);
    return newUser;
  }, []);

  const logout = useCallback(() => {
    // Best-effort server-side token revocation; auth state clears regardless.
    apiClient.post('/api/auth/logout').catch(() => {});
    setStoredToken(null);
    writeCachedUser(null);
    setUser(null);
  }, []);

  const value = {
    user,
    isAuthenticated: !!user,
    loading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
