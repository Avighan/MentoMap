/**
 * ModulesCatalogPage — browse-all-modules grid. ModuleDetailPage.jsx and
 * HomePage.jsx both navigate to `/modules` (via `navigate('/modules')`) as
 * "back to catalog", so this fills that route.
 *
 * Real backend route: GET /api/modules -> { modules: [...], total } (backend/app.py
 * `api_modules_list`), via api/modules.js `listModules()`.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listModules } from '../api/modules';
import { LoadingState } from '../components/ui/LoadingSpinner';

export default function ModulesCatalogPage() {
  const navigate = useNavigate();
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    listModules()
      .then((res) => setModules(res.modules || []))
      .catch(() => setError('Could not load modules right now.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState label="Loading modules…" />;

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ fontSize: '1.6rem', color: '#2D3047', marginBottom: 4 }}>Learning Modules</h1>
      <p style={{ color: '#6D7286', marginBottom: 20 }}>Multi-week guided courses</p>
      {error && <div style={{ color: '#EF4444', marginBottom: 16 }}>{error}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
        {modules.map((m) => {
          const progress = m.my_progress;
          return (
            <button
              key={m.module_id}
              onClick={() => navigate(`/modules/${m.module_id}`)}
              style={{
                textAlign: 'left', border: '1px solid #E5E7EB', borderRadius: 16, padding: 16,
                background: m.cover_color ? `${m.cover_color}15` : '#fff', cursor: 'pointer',
              }}
            >
              <div style={{ fontSize: '1.8rem', marginBottom: 8 }}>{m.icon || '📘'}</div>
              <div style={{ fontWeight: 700, color: '#2D3047' }}>{m.title}</div>
              {m.subtitle && <div style={{ fontSize: '0.8rem', color: '#6D7286', marginTop: 2 }}>{m.subtitle}</div>}
              <div style={{ display: 'flex', gap: 10, marginTop: 10, fontSize: '0.72rem', color: '#9CA3AF' }}>
                {m.duration_weeks ? <span>{m.duration_weeks} weeks</span> : null}
                {m.total_lessons ? <span>· {m.total_lessons} lessons</span> : null}
              </div>
              {progress && (
                <div style={{ marginTop: 10, fontSize: '0.75rem', fontWeight: 700, color: '#06D6A0' }}>
                  {progress.completed_lesson_count || 0}/{progress.total_lesson_count || m.total_lessons || 0} complete
                </div>
              )}
            </button>
          );
        })}
        {!modules.length && !error && (
          <p style={{ color: '#9CA3AF' }}>No modules are assigned to you yet.</p>
        )}
      </div>
    </div>
  );
}
