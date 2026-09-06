/**
 * OrgContext — branding + scoring config for the current user's
 * organisation, from GET /api/org/config (backend/app.py `api_org_config`,
 * no auth required — unauthenticated users get the default org).
 *
 * Consumers (LeaderboardPage, PostGameInsights, StockMarketGame) read
 * `customDimensions` to know which of the 8 default skill dimensions (or an
 * org-specific subset) to render.
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';

const OrgContext = createContext(null);

export const useOrg = () => {
  const ctx = useContext(OrgContext);
  if (!ctx) {
    throw new Error('useOrg must be used within an OrgProvider');
  }
  return ctx;
};

const DEFAULT_ORG = {
  id: 'default',
  name: 'MentoMap',
  primary_color: '#6C5CE7',
  accent_color: '#00B894',
  logo_url: '',
  custom_dimensions: null,
  features: {},
};

export const OrgProvider = ({ children }) => {
  const [org, setOrg] = useState(DEFAULT_ORG);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    return apiClient
      .get('/api/org/config')
      .then((res) => setOrg({ ...DEFAULT_ORG, ...res.data }))
      .catch(() => setOrg(DEFAULT_ORG))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = {
    org,
    loading,
    customDimensions: org.custom_dimensions || null,
    primaryColor: org.primary_color,
    accentColor: org.accent_color,
    logoUrl: org.logo_url,
    features: org.features || {},
    refresh,
  };

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>;
};

export default OrgContext;
