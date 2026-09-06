/**
 * LoginPage — sign in / register. No existing page in the repo covers auth
 * (RUNNING_LOCALLY.md flags this as a genuine gap), so this is new.
 *
 * Calls the real routes in backend/app.py:
 *   POST /api/auth/login    { username, password }              -> { user, token }
 *   POST /api/auth/register { username, password, role, org_id } -> { user, token }, 201
 * via contexts/AuthContext.jsx's login()/register(), which store the JWT
 * and populate `user` for the rest of the app.
 */
import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const colors = {
  primary: '#FFD166',
  background: '#FFFDF7',
  card: '#FFFFFF',
  text: '#2D3047',
  textLight: '#6D7286',
  danger: '#EF4444',
};

const ROLES = ['student', 'teacher', 'parent', 'trainer', 'hr'];

export default function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || '/';

  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password) {
      setError('Please enter a username and password.');
      return;
    }
    setSubmitting(true);
    try {
      if (mode === 'login') {
        await login(username.trim(), password);
      } else {
        await register(username.trim(), password, role, 'default');
      }
      navigate(from, { replace: true });
    } catch (err) {
      const status = err?.response?.status;
      const serverMessage = err?.response?.data?.error;
      if (status === 401) {
        setError(serverMessage || 'Incorrect username or password.');
      } else if (status === 409) {
        setError(serverMessage || 'That username is already taken.');
      } else {
        setError(serverMessage || 'Something went wrong. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: colors.background,
        padding: 16,
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 400,
          background: colors.card,
          borderRadius: 20,
          padding: '32px 28px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: '2.2rem' }}>🎮</div>
          <h1 style={{ margin: '8px 0 0', fontSize: '1.4rem', color: colors.text }}>MentoMap</h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: colors.textLight }}>
            {mode === 'login' ? 'Welcome back — sign in to keep playing.' : 'Create an account to get started.'}
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: colors.text, marginBottom: 4 }}>
              Username
            </label>
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={inputStyle}
              placeholder="e.g. alex_23"
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: colors.text, marginBottom: 4 }}>
              Password
            </label>
            <input
              type="password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={inputStyle}
              placeholder="••••••••"
            />
          </div>

          {mode === 'register' && (
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: colors.text, marginBottom: 4 }}>
                I am a...
              </label>
              <select value={role} onChange={(e) => setRole(e.target.value)} style={inputStyle}>
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                ))}
              </select>
            </div>
          )}

          {error && (
            <div style={{ color: colors.danger, fontSize: '0.85rem', background: '#FEF2F2', borderRadius: 8, padding: '8px 10px' }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            style={{
              marginTop: 4,
              padding: '12px 16px',
              borderRadius: 12,
              border: 'none',
              background: colors.primary,
              color: colors.text,
              fontWeight: 800,
              fontSize: '0.95rem',
              cursor: submitting ? 'not-allowed' : 'pointer',
              opacity: submitting ? 0.7 : 1,
            }}
          >
            {submitting ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 18, fontSize: '0.85rem', color: colors.textLight }}>
          {mode === 'login' ? (
            <>
              New here?{' '}
              <button onClick={() => { setMode('register'); setError(''); }} style={linkStyle}>
                Create an account
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button onClick={() => { setMode('login'); setError(''); }} style={linkStyle}>
                Log in
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid #E5E7EB',
  fontSize: '0.95rem',
  fontFamily: 'inherit',
  boxSizing: 'border-box',
};

const linkStyle = {
  border: 'none',
  background: 'transparent',
  color: '#6C5CE7',
  fontWeight: 700,
  cursor: 'pointer',
  padding: 0,
  font: 'inherit',
};
