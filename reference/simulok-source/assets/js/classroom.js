/* ==========================================================================
   Simulok.ai — classroom session client (confidence layer)
   --------------------------------------------------------------------------
   Talks to tools/classroom-session.gs (Apps Script web app).
   POST JSON as text/plain to avoid CORS preflight. Judge success on the
   response BODY (success === "true"), not HTTP status alone.
   ========================================================================== */
(function (global) {
  'use strict';

  /** Apps Script web-app /exec URL (Simulok Classroom Sheet). */
  var ENDPOINT = 'https://script.google.com/macros/s/AKfycbyA4W6sVkRcBRShBY8g_EhdPFUwDvn_vXrFIZOOjjmTc_XIjea4gh2GWNrHIxl5NA3W/exec';

  var STORAGE_KEY = 'simulok_classroom';
  var CLASSROOM_SIMS = {
    mumbai: { title: 'The Mumbai Manufacturer', kind: 'platform' },
    zara: { title: 'Zara — The Fast-Fashion Reckoning', kind: 'platform' },
    'zara-new': { title: 'Zara — Business Model & Globalization', kind: 'platform' },
    zenith: {
      title: 'Zenith Appliances — The Annual Budget War Room',
      kind: 'standalone',
      path: 'cost-accounting/zenith-appliances.html'
    }
  };

  function configured() {
    return !!(ENDPOINT && String(ENDPOINT).indexOf('http') === 0);
  }

  /** localStorage so refresh / new dashboard tab keep the instructor signed in. */
  function storage() {
    try { return global.localStorage; } catch (e) { return null; }
  }

  function loadSession() {
    try {
      var store = storage();
      if (!store) return null;
      var raw = store.getItem(STORAGE_KEY);
      // Migrate older sessionStorage logins (tab-only) into localStorage once.
      if (!raw) {
        try {
          raw = global.sessionStorage.getItem(STORAGE_KEY);
          if (raw) {
            store.setItem(STORAGE_KEY, raw);
            global.sessionStorage.removeItem(STORAGE_KEY);
          }
        } catch (e2) { /* ignore */ }
      }
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveSession(obj) {
    try {
      var store = storage();
      if (!store) return;
      if (!obj) store.removeItem(STORAGE_KEY);
      else store.setItem(STORAGE_KEY, JSON.stringify(obj));
      try { global.sessionStorage.removeItem(STORAGE_KEY); } catch (e2) { /* ignore */ }
    } catch (e) { /* ignore */ }
  }

  function clearSession() {
    saveSession(null);
  }

  function post(payload) {
    if (!configured()) {
      return Promise.resolve({ success: 'false', message: 'Classroom endpoint not configured' });
    }
    var controller = null;
    var timer = null;
    try {
      if (typeof AbortController !== 'undefined') {
        controller = new AbortController();
        timer = setTimeout(function () {
          try { controller.abort(); } catch (e) { /* ignore */ }
        }, 20000);
      }
    } catch (e) { /* ignore */ }

    var opts = {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify(payload)
    };
    if (controller) opts.signal = controller.signal;

    return fetch(ENDPOINT, opts).then(function (res) {
      return res.text().then(function (text) {
        var data;
        try { data = JSON.parse(text); }
        catch (err) {
          return { success: 'false', message: 'Bad response from classroom backend' };
        }
        if (!data || (data.success !== 'true' && data.success !== true)) {
          return {
            success: 'false',
            message: (data && data.message) || 'Request refused',
            session: data && data.session,
            run_status: data && data.run_status
          };
        }
        data.success = 'true';
        return data;
      });
    }).catch(function (err) {
      var msg = String(err && err.message ? err.message : err);
      if (err && err.name === 'AbortError') msg = 'Classroom server timed out — try again';
      return { success: 'false', message: msg };
    }).then(function (data) {
      if (timer) clearTimeout(timer);
      return data;
    });
  }

  function login(studentId, password, displayName) {
    var payload = {
      action: 'login',
      student_id: String(studentId || '').trim(),
      password: String(password || '')
    };
    var name = String(displayName || '').trim();
    if (name) payload.display_name = name;
    return post(payload).then(function (data) {
      if (data.success === 'true') {
        saveSession({
          student_id: data.student_id,
          name: data.name || name || data.student_id,
          role: data.role === 'instructor' ? 'instructor' : 'student',
          password: String(password || ''),
          session: data.session || null,
          run_status: data.run_status || 'none'
        });
      }
      return data;
    });
  }

  function openSession(simId) {
    var auth = loadSession();
    if (!auth || auth.role !== 'instructor') {
      return Promise.resolve({ success: 'false', message: 'Sign in as instructor first' });
    }
    return post({
      action: 'open_session',
      student_id: auth.student_id,
      password: auth.password,
      sim_id: simId
    }).then(function (data) {
      if (data.success === 'true' && data.session) {
        auth.session = data.session;
        saveSession(auth);
      }
      return data;
    });
  }

  function closeSession() {
    var auth = loadSession();
    if (!auth || auth.role !== 'instructor') {
      return Promise.resolve({ success: 'false', message: 'Sign in as instructor first' });
    }
    return post({
      action: 'close_session',
      student_id: auth.student_id,
      password: auth.password
    }).then(function (data) {
      if (data.success === 'true') {
        auth.session = null;
        saveSession(auth);
      }
      return data;
    });
  }

  function refreshStatus() {
    return post({ action: 'session_status' }).then(function (data) {
      var auth = loadSession();
      if (auth && data.success === 'true') {
        auth.session = data.session || null;
        saveSession(auth);
      }
      return data;
    });
  }

  function logRound(fields) {
    var auth = loadSession();
    if (!auth || !auth.student_id || auth.role === 'instructor') {
      return Promise.resolve({ success: 'false', message: 'no student session' });
    }
    if (!auth.session || !auth.session.session_id) {
      return Promise.resolve({ success: 'false', message: 'no open classroom session' });
    }
    var payload = {
      action: 'log_round',
      student_id: auth.student_id,
      password: auth.password || '',
      display_name: auth.name || '',
      session_id: auth.session.session_id,
      sim_id: fields.sim_id || auth.session.sim_id,
      round: fields.round,
      choice_label: fields.choice_label || '',
      score: fields.score,
      timestamp: fields.timestamp || new Date().toISOString(),
      extra: fields.extra || {}
    };

    function attempt(left) {
      return post(payload).then(function (data) {
        if (data.success === 'true') return data;
        if (left <= 0) return data;
        return new Promise(function (resolve) {
          setTimeout(function () { resolve(attempt(left - 1)); }, 800);
        });
      });
    }
    return attempt(1);
  }

  function completeRun(report) {
    var auth = loadSession();
    if (!auth || !auth.student_id || auth.role === 'instructor') {
      return Promise.resolve({ success: 'false', message: 'no student session' });
    }
    if (!auth.session || !auth.session.session_id) {
      return Promise.resolve({ success: 'false', message: 'no open classroom session' });
    }
    return post({
      action: 'complete_run',
      student_id: auth.student_id,
      password: auth.password || '',
      display_name: auth.name || '',
      session_id: auth.session.session_id,
      sim_id: (report && report.sim_id) || auth.session.sim_id,
      timestamp: new Date().toISOString(),
      score: report && report.total,
      report: report || {}
    }).then(function (data) {
      if (data.success === 'true') {
        auth.run_status = 'completed';
        saveSession(auth);
      }
      return data;
    });
  }

  function fetchDashboard(sessionId) {
    var auth = loadSession();
    if (!auth || auth.role !== 'instructor') {
      return Promise.resolve({ success: 'false', message: 'Sign in as instructor first' });
    }
    return post({
      action: 'dashboard',
      student_id: auth.student_id,
      password: auth.password,
      session_id: sessionId || (auth.session && auth.session.session_id) || ''
    });
  }

  function listSessions() {
    var auth = loadSession();
    if (!auth || auth.role !== 'instructor') {
      return Promise.resolve({ success: 'false', message: 'Sign in as instructor first' });
    }
    return post({
      action: 'list_sessions',
      student_id: auth.student_id,
      password: auth.password
    });
  }

  function resetRuns(sessionId) {
    var auth = loadSession();
    if (!auth || auth.role !== 'instructor') {
      return Promise.resolve({ success: 'false', message: 'Sign in as instructor first' });
    }
    return post({
      action: 'reset_runs',
      student_id: auth.student_id,
      password: auth.password,
      session_id: sessionId || (auth.session && auth.session.session_id) || ''
    });
  }

  function assignedSimId() {
    var auth = loadSession();
    return auth && auth.session ? auth.session.sim_id : null;
  }

  function isClassroomStudent() {
    var auth = loadSession();
    return !!(auth && auth.role === 'student' && auth.session);
  }

  function platformBase() {
    try {
      var path = (global.location && global.location.pathname) || '';
      if (path.indexOf('/platform') >= 0) {
        var idx = path.indexOf('/platform');
        return path.slice(0, idx + '/platform'.length) + '/';
      }
      if (/index\.html$/i.test(path)) return path.replace(/index\.html$/i, '');
      if (path.endsWith('/')) return path;
      return '';
    } catch (e) {
      return '';
    }
  }

  function zenithUrl() {
    return platformBase() + 'cost-accounting/zenith-appliances.html';
  }

  function dashboardUrl(sessionId) {
    var base = platformBase() + 'classroom/dashboard.html';
    if (sessionId) {
      return base + '?session=' + encodeURIComponent(sessionId);
    }
    return base;
  }

  global.SimulokClassroom = {
    ENDPOINT: ENDPOINT,
    CLASSROOM_SIMS: CLASSROOM_SIMS,
    configured: configured,
    loadSession: loadSession,
    saveSession: saveSession,
    clearSession: clearSession,
    login: login,
    openSession: openSession,
    closeSession: closeSession,
    refreshStatus: refreshStatus,
    logRound: logRound,
    completeRun: completeRun,
    fetchDashboard: fetchDashboard,
    listSessions: listSessions,
    resetRuns: resetRuns,
    assignedSimId: assignedSimId,
    isClassroomStudent: isClassroomStudent,
    zenithUrl: zenithUrl,
    dashboardUrl: dashboardUrl
  };
})(typeof window !== 'undefined' ? window : this);
