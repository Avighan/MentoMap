/**
 * NotificationCenter — bell icon + dropdown of recent notifications.
 * Rendered by HomePage.jsx and ModuleDetailPage.jsx as `<NotificationCenter />`
 * (no props). Backed by real routes in backend/app.py (see `notifications`
 * module): GET /api/notifications, POST /api/notifications/:id/read,
 * POST /api/notifications/read-all. Calls apiClient directly rather than
 * through a dedicated api/*.js file, matching the existing precedent in
 * components/ui/MobileBottomNav.jsx.
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import apiClient from '../../api/client';

export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const rootRef = useRef(null);

  const load = useCallback(() => {
    apiClient
      .get('/api/notifications', { params: { limit: 20 } })
      .then((res) => {
        setNotifications(res.data?.notifications || []);
        setUnreadCount(res.data?.unread_count || 0);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [open]);

  const markAllRead = () => {
    apiClient.post('/api/notifications/read-all').then(() => {
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    }).catch(() => {});
  };

  const markOneRead = (id) => {
    apiClient.post(`/api/notifications/${id}/read`).then(() => {
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      setUnreadCount((c) => Math.max(0, c - 1));
    }).catch(() => {});
  };

  return (
    <div ref={rootRef} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        style={{
          position: 'relative', border: 'none', background: 'transparent',
          cursor: 'pointer', fontSize: '1.2rem', lineHeight: 1, padding: 6,
        }}
      >
        🔔
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute', top: 0, right: 0, minWidth: 16, height: 16,
              borderRadius: 999, background: '#EF4444', color: '#fff',
              fontSize: '0.6rem', fontWeight: 700, display: 'flex',
              alignItems: 'center', justifyContent: 'center', padding: '0 3px',
            }}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          style={{
            position: 'absolute', right: 0, top: '110%', width: 320, maxHeight: 400,
            overflowY: 'auto', background: '#fff', borderRadius: 12,
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)', zIndex: 100, padding: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px' }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                style={{ border: 'none', background: 'transparent', color: '#6C5CE7', fontSize: '0.75rem', cursor: 'pointer' }}
              >
                Mark all read
              </button>
            )}
          </div>
          {notifications.length === 0 ? (
            <div style={{ padding: '16px 8px', color: '#9CA3AF', fontSize: '0.85rem', textAlign: 'center' }}>
              You're all caught up.
            </div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                onClick={() => !n.read && markOneRead(n.id)}
                style={{
                  padding: '10px 8px', borderRadius: 8, cursor: n.read ? 'default' : 'pointer',
                  background: n.read ? 'transparent' : '#F5F3FF', marginBottom: 4,
                }}
              >
                <div style={{ fontSize: '0.85rem', fontWeight: n.read ? 400 : 700 }}>{n.title || n.message}</div>
                {n.title && n.message && (
                  <div style={{ fontSize: '0.78rem', color: '#6D7286', marginTop: 2 }}>{n.message}</div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
