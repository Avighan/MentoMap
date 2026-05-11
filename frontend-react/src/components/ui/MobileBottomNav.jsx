/**
 * MobileBottomNav.jsx
 * Fixed bottom navigation bar — visible only on mobile (hidden md+).
 * Only renders when user is authenticated.
 */
import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FaHome, FaGamepad, FaRoute, FaUser, FaUserFriends, FaBriefcase, FaBook, FaMagic } from "react-icons/fa";
import { useAuth } from "../../contexts/AuthContext";
import { useTranslation } from "react-i18next";
import apiClient from "../../api/client";

const ACTIVE_COLOR = "#FFD166";
const INACTIVE_COLOR = "#9CA3AF"; // gray-400

const MobileBottomNav = () => {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [hasReviews, setHasReviews] = useState(false);

  useEffect(() => {
    if (!user || user.role === 'parent') return;
    apiClient.get('/api/spaced-repetition/due')
      .then(r => {
        const reviews = Array.isArray(r.data) ? r.data : r.data?.reviews || r.data?.due || [];
        setHasReviews(reviews.length > 0);
      })
      .catch(() => {});
  }, [user]);

  // Build tabs based on role
  const TABS = (() => {
    const role = user?.role;
    if (role === 'parent') {
      return [
        { labelKey: "nav.home",     icon: FaHome,        path: "/home/parent" },
        { labelKey: "nav.family",   icon: FaUserFriends, path: "/parent-dashboard" },
        { labelKey: "nav.profile",  icon: FaUser,        path: "/parent-dashboard" },
        { labelKey: "nav.settings", icon: FaRoute,       path: "/settings" },
      ];
    }
    if (role === 'teacher') {
      return [
        { labelKey: "nav.home",    icon: FaHome,        path: "/home/teacher" },
        { labelKey: "nav.classes", icon: FaUserFriends, path: "/teacher" },
        { labelKey: "nav.library", icon: FaGamepad,     path: "/discover" },
        { labelKey: "nav.profile", icon: FaUser,        path: "/profile" },
      ];
    }
    if (role === 'admin' || role === 'trainer' || role === 'school_admin') {
      return [
        { labelKey: "nav.admin",    icon: FaHome,        path: "/admin" },
        { labelKey: "nav.games",    icon: FaGamepad,     path: "/discover" },
        { labelKey: "nav.designer", icon: FaMagic,       path: "/designer/ai-studio" },
        { labelKey: "nav.profile",  icon: FaUser,        path: "/profile" },
      ];
    }
    if (role === 'hr') {
      return [
        { labelKey: "nav.home",     icon: FaHome,      path: "/home/hr" },
        { labelKey: "nav.assess",   icon: FaBriefcase, path: "/assessment-manager" },
        { labelKey: "nav.profile",  icon: FaUser,      path: "/profile" },
        { labelKey: "nav.settings", icon: FaRoute,     path: "/settings" },
      ];
    }
    // Default: student
    return [
      { labelKey: "nav.home",     icon: FaHome,        path: "/home/student" },
      { labelKey: "nav.games",    icon: FaGamepad,     path: "/discover" },
      { labelKey: "nav.modules",  icon: FaBook,        path: "/modules" },
      { labelKey: "nav.profile",  icon: FaUser,        path: "/profile" },
      { labelKey: "nav.social",   icon: FaUserFriends, path: "/social" },
    ];
  })();

  // Only render for authenticated users; hide during active gameplay
  if (!user) return null;
  if (location.pathname.startsWith('/play/')) return null;

  const isActive = (path) => {
    if (path === "/") return location.pathname === "/";
    // Exact match for home routes to avoid false positives (e.g. /home/student vs /home/teacher)
    if (path.startsWith('/home/')) return location.pathname === path;
    return location.pathname.startsWith(path);
  };

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-white border-t border-gray-200 shadow-[0_-2px_10px_rgba(0,0,0,0.06)]"
      style={{
        paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom))',
      }}
    >
      <div className="flex items-stretch">
        {TABS.map(({ labelKey, icon: Icon, path }) => {
          const active = isActive(path);
          const isPracticeTab = labelKey === 'nav.practice' || path === '/interview';
          return (
            <button
              key={path}
              onClick={() => navigate(path)}
              className="flex flex-col items-center py-2 px-3 flex-1 text-[10px] transition-colors duration-150 focus:outline-none active:scale-95"
              style={{
                color: active ? ACTIVE_COLOR : INACTIVE_COLOR,
                fontWeight: active ? "700" : "400",
              }}
              aria-label={t(labelKey)}
              aria-current={active ? "page" : undefined}
            >
              <div className="relative inline-flex">
                <Icon
                  style={{
                    fontSize: "1.25rem",
                    marginBottom: "2px",
                    color: active ? ACTIVE_COLOR : INACTIVE_COLOR,
                    transition: "color 0.15s",
                  }}
                />
                {isPracticeTab && hasReviews && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-red-500" />
                )}
              </div>
              <span>{t(labelKey)}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

export default MobileBottomNav;
