import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoadingSpinner from './components/ui/LoadingSpinner';

import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import GamesCatalogPage from './pages/GamesCatalogPage';
import PilotGamePlayPage from './pages/PilotGamePlayPage';
import ModulesCatalogPage from './pages/ModulesCatalogPage';
import ModuleDetailPage from './pages/ModuleDetailPage';
import ModuleReportPage from './pages/ModuleReportPage';
import LeaderboardPage from './pages/LeaderboardPage';
import SettingsPage from './pages/SettingsPage';

// Every product route needs a logged-in user (backend routes behind
// @require_auth reject an unauthenticated request with 401 anyway) —
// this just keeps the app from rendering pages that would immediately
// error out, and sends the visitor to /login instead.
function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingSpinner />;
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
      <Route path="/games" element={<RequireAuth><GamesCatalogPage /></RequireAuth>} />
      <Route path="/play/:gameId" element={<RequireAuth><PilotGamePlayPage /></RequireAuth>} />
      <Route path="/modules" element={<RequireAuth><ModulesCatalogPage /></RequireAuth>} />
      <Route path="/modules/:moduleId" element={<RequireAuth><ModuleDetailPage /></RequireAuth>} />
      <Route path="/modules/:moduleId/report" element={<RequireAuth><ModuleReportPage /></RequireAuth>} />
      <Route path="/leaderboard" element={<RequireAuth><LeaderboardPage /></RequireAuth>} />
      <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
