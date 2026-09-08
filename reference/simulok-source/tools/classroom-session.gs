/**
 * Simulok.ai — classroom session backend (Google Apps Script)
 * ---------------------------------------------------------------------------
 * Roster login + one Sheet tab per sitting + completion / dashboard.
 * Bound to a spreadsheet with tabs:
 *   Roster   — student_id, name, password, role, active
 *   Sessions — session_id, sim_id, opened_at, status, tab_name
 *   Sess_A1… — round rows + one __COMPLETE__ row per student when finished
 *
 * Client actions (POST JSON as text/plain):
 *   login | open_session | close_session | log_round | complete_run
 *   | session_status | list_sessions | dashboard | reset_runs
 *
 * One run per student per session: after __COMPLETE__, login/play is refused
 * until faculty runs reset_runs on that sitting (or opens a new Sess_*).
 *
 * Students may send display_name on login so Sheet rows / dashboards show a real name.
 *
 * Redeploy: Manage deployments → edit → New version (keep same /exec URL).
 */

var ROSTER_TAB = 'Roster';
var SESSIONS_TAB = 'Sessions';
var ALLOWED_SIMS = ['mumbai', 'zara', 'zara-new', 'zenith'];
var COMPLETE_ROUND = '__COMPLETE__';

var RUN_FIELDS = [
  'timestamp', 'session_id', 'student_id', 'name', 'sim_id',
  'round', 'choice_label', 'score', 'extra_json'
];

var SESSION_FIELDS = [
  'session_id', 'sim_id', 'opened_at', 'status', 'tab_name'
];

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return json_({ success: 'false', message: 'empty request' });
    }
    var d = JSON.parse(e.postData.contents);
    var action = String(d.action || '').toLowerCase();

    if (action === 'login') return login_(d);
    if (action === 'open_session') return openSession_(d);
    if (action === 'close_session') return closeSession_(d);
    if (action === 'log_round') return logRound_(d);
    if (action === 'complete_run') return completeRun_(d);
    if (action === 'session_status') return sessionStatus_(d);
    if (action === 'list_sessions') return listSessions_(d);
    if (action === 'dashboard') return dashboard_(d);
    if (action === 'reset_runs') return resetRuns_(d);

    return json_({ success: 'false', message: 'unknown action' });
  } catch (err) {
    return json_({ success: 'false', message: String(err) });
  }
}

function doGet() {
  return json_({ success: 'true', message: 'Simulok.ai classroom endpoint is live' });
}

/* ── login ──────────────────────────────────────────────────────────────── */

function login_(d) {
  var studentId = String(d.student_id || d.email || '').trim();
  var password = String(d.password || '');
  if (!studentId || !password) {
    return json_({ success: 'false', message: 'student_id and password are required' });
  }

  var row = findRoster_(studentId);
  if (!row) {
    return json_({
      success: 'false',
      message: 'Unknown ID "' + studentId + '". Check the Roster tab has columns student_id,name,password,role,active and a FACULTY row.'
    });
  }
  if (String(row.active || 'yes').toLowerCase() === 'no') {
    return json_({ success: 'false', message: 'This ID is inactive' });
  }
  if (String(row.password) !== password) {
    return json_({ success: 'false', message: 'Incorrect password' });
  }

  var role = String(row.role || 'student').toLowerCase();
  if (role === 'faculty' || role === 'admin') role = 'instructor';
  if (role !== 'instructor') role = 'student';

  var displayName = resolveDisplayName_(d, row);
  if (role === 'student' && displayName && displayName !== row.name) {
    updateRosterName_(row.student_id, displayName);
    row.name = displayName;
  }

  var open = getOpenSession_();
  var runStatus = 'none';
  if (open && role === 'student') {
    runStatus = studentRunStatus_(open.tab_name, row.student_id);
    if (runStatus === 'completed') {
      return json_({
        success: 'false',
        message: 'You already completed this session (' + open.session_id + '). Each student may run once.',
        run_status: 'completed',
        session: open
      });
    }
  }

  return json_({
    success: 'true',
    message: 'ok',
    student_id: row.student_id,
    name: displayName || row.name || row.student_id,
    role: role,
    run_status: runStatus,
    session: open ? {
      session_id: open.session_id,
      sim_id: open.sim_id,
      tab_name: open.tab_name,
      status: open.status
    } : null
  });
}

/* ── sessions ───────────────────────────────────────────────────────────── */

function openSession_(d) {
  var auth = requireInstructor_(d);
  if (auth.error) return json_({ success: 'false', message: auth.error });

  var simId = String(d.sim_id || '').trim();
  if (ALLOWED_SIMS.indexOf(simId) < 0) {
    return json_({ success: 'false', message: 'sim_id must be one of: ' + ALLOWED_SIMS.join(', ') });
  }

  var lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    var existing = getOpenSession_();
    if (existing) {
      return json_({
        success: 'false',
        message: 'A session is already open (' + existing.session_id + '). Close it first.',
        session: existing
      });
    }

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    ensureSessionsSheet_(ss);
    var tabName = nextSessionTabName_(ss);
    var sessionId = tabName;
    var openedAt = new Date().toISOString();

    var runSheet = ss.insertSheet(tabName);
    runSheet.appendRow(RUN_FIELDS);
    runSheet.getRange(1, 1, 1, RUN_FIELDS.length).setFontWeight('bold');
    runSheet.setFrozenRows(1);

    var sess = findSheet_(ss, SESSIONS_TAB);
    sess.appendRow([sessionId, simId, openedAt, 'open', tabName]);

    return json_({
      success: 'true',
      message: 'session opened',
      session: {
        session_id: sessionId,
        sim_id: simId,
        opened_at: openedAt,
        status: 'open',
        tab_name: tabName
      }
    });
  } finally {
    lock.releaseLock();
  }
}

function closeSession_(d) {
  var auth = requireInstructor_(d);
  if (auth.error) return json_({ success: 'false', message: auth.error });

  var lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    var open = getOpenSession_();
    if (!open) return json_({ success: 'false', message: 'No open session' });

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = findSheet_(ss, SESSIONS_TAB);
    var data = sh.getDataRange().getValues();
    for (var i = 1; i < data.length; i++) {
      if (String(data[i][0]) === open.session_id && String(data[i][3]).toLowerCase() === 'open') {
        sh.getRange(i + 1, 4).setValue('closed');
        break;
      }
    }
    open.status = 'closed';
    return json_({ success: 'true', message: 'session closed', session: open });
  } finally {
    lock.releaseLock();
  }
}

function sessionStatus_(d) {
  var open = getOpenSession_();
  return json_({
    success: 'true',
    message: 'ok',
    session: open || null
  });
}

/* ── list all sittings (open + closed history) ──────────────────────────── */

function listSessions_(d) {
  var auth = requireInstructor_(d);
  if (auth.error) return json_({ success: 'false', message: auth.error });

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureSessionsSheet_(ss);
  var sh = findSheet_(ss, SESSIONS_TAB);
  var sessions = [];
  if (sh && sh.getLastRow() >= 2) {
    var data = sh.getDataRange().getValues();
    var headers = data[0].map(function (h) { return String(h).toLowerCase().trim(); });
    var idIdx = headers.indexOf('session_id'); if (idIdx < 0) idIdx = 0;
    var simIdx = headers.indexOf('sim_id'); if (simIdx < 0) simIdx = 1;
    var openedIdx = headers.indexOf('opened_at'); if (openedIdx < 0) openedIdx = 2;
    var statusIdx = headers.indexOf('status'); if (statusIdx < 0) statusIdx = 3;
    var tabIdx = headers.indexOf('tab_name'); if (tabIdx < 0) tabIdx = 4;

    var simMeta = {
      mumbai: 'The Mumbai Manufacturer',
      zara: 'Zara — The Fast-Fashion Reckoning',
      'zara-new': 'Zara — Business Model & Globalization',
      zenith: 'Zenith Appliances — The Annual Budget War Room'
    };

    for (var i = 1; i < data.length; i++) {
      var sid = String(data[i][idIdx] || '').trim();
      if (!sid) continue;
      var simId = String(data[i][simIdx] || '');
      var tabName = String(data[i][tabIdx] || sid);
      // Keep list_sessions fast — counts come from dashboard when a session is opened.
      sessions.push({
        session_id: sid,
        sim_id: simId,
        sim_title: simMeta[simId] || simId,
        opened_at: String(data[i][openedIdx] || ''),
        status: String(data[i][statusIdx] || '').toLowerCase() || 'closed',
        tab_name: tabName,
        completed: null,
        in_progress: null,
        rows: null
      });
    }
  }

  sessions.reverse(); // newest first (append order)
  return json_({
    success: 'true',
    message: 'ok',
    sessions: sessions,
    open_session_id: (getOpenSession_() || {}).session_id || ''
  });
}

function sessionQuickCounts_(ss, tabName) {
  var out = { completed: 0, in_progress: 0, rows: 0 };
  var sh = ss.getSheetByName(tabName) || findSheet_(ss, tabName);
  if (!sh || sh.getLastRow() < 2) return out;
  var data = sh.getDataRange().getValues();
  var headers = data[0].map(function (h) { return String(h).toLowerCase().trim(); });
  var roundIdx = headers.indexOf('round');
  var sidIdx = headers.indexOf('student_id');
  if (roundIdx < 0) roundIdx = 5;
  if (sidIdx < 0) sidIdx = 2;
  var by = {};
  for (var i = 1; i < data.length; i++) {
    var sid = String(data[i][sidIdx] || '').trim();
    if (!sid) continue;
    out.rows += 1;
    if (!by[sid]) by[sid] = 'in_progress';
    if (String(data[i][roundIdx]) === COMPLETE_ROUND) by[sid] = 'completed';
  }
  Object.keys(by).forEach(function (k) {
    if (by[k] === 'completed') out.completed += 1;
    else out.in_progress += 1;
  });
  return out;
}

/* ── reset runs (allow students another single attempt) ─────────────────── */

function resetRuns_(d) {
  var auth = requireInstructor_(d);
  if (auth.error) return json_({ success: 'false', message: auth.error });

  var open = getOpenSession_();
  var sessionId = String(d.session_id || (open ? open.session_id : '')).trim();
  var session = null;
  if (open && (!sessionId || sessionId === open.session_id)) session = open;
  else if (sessionId) session = findSessionById_(sessionId);
  else session = open;

  if (!session) {
    return json_({ success: 'false', message: 'Pick a session first (or open one), then reset runs.' });
  }

  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName(session.tab_name) || findSheet_(ss, session.tab_name);
    if (!sh) {
      return json_({ success: 'false', message: 'Session tab missing: ' + session.tab_name });
    }

    var lastRow = sh.getLastRow();
    var cleared = 0;
    if (lastRow >= 2) {
      cleared = lastRow - 1;
      sh.deleteRows(2, cleared);
    }

    return json_({
      success: 'true',
      message: 'Runs cleared — each student may complete once again on ' + session.session_id,
      session: session,
      rows_cleared: cleared
    });
  } finally {
    lock.releaseLock();
  }
}

/* ── log round ──────────────────────────────────────────────────────────── */

function logRound_(d) {
  var studentId = String(d.student_id || '').trim();
  var password = String(d.password || '');
  if (!studentId) return json_({ success: 'false', message: 'student_id required' });

  var row = findRoster_(studentId);
  if (!row) return json_({ success: 'false', message: 'Unknown student ID' });
  if (password && String(row.password) !== password) {
    return json_({ success: 'false', message: 'Incorrect password' });
  }

  var open = getOpenSession_();
  if (!open) return json_({ success: 'false', message: 'No open classroom session' });

  var sessionId = String(d.session_id || open.session_id);
  if (sessionId !== open.session_id) {
    return json_({ success: 'false', message: 'Session mismatch — ask faculty to confirm the open sitting' });
  }

  if (studentRunStatus_(open.tab_name, row.student_id) === 'completed') {
    return json_({ success: 'false', message: 'Run already completed — one attempt per session' });
  }

  var simId = String(d.sim_id || open.sim_id);
  if (ALLOWED_SIMS.indexOf(simId) < 0) simId = open.sim_id;

  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName(open.tab_name) || findSheet_(ss, open.tab_name);
    if (!sh) return json_({ success: 'false', message: 'Session tab missing: ' + open.tab_name });
    ensureRunHeader_(sh);

    var displayName = resolveDisplayName_(d, row);

    var record = {
      timestamp: d.timestamp || new Date().toISOString(),
      session_id: open.session_id,
      student_id: row.student_id,
      name: displayName,
      sim_id: simId,
      round: d.round === undefined || d.round === null ? '' : String(d.round),
      choice_label: d.choice_label === undefined ? '' : String(d.choice_label),
      score: d.score === undefined || d.score === null ? '' : String(d.score),
      extra_json: stringifyExtra_(d)
    };

    sh.appendRow(RUN_FIELDS.map(function (k) {
      return record[k] === undefined ? '' : record[k];
    }));

    return json_({ success: 'true', message: 'logged', session_id: open.session_id });
  } finally {
    lock.releaseLock();
  }
}

/* ── complete run (report card) ─────────────────────────────────────────── */

function completeRun_(d) {
  var studentId = String(d.student_id || '').trim();
  var password = String(d.password || '');
  if (!studentId) return json_({ success: 'false', message: 'student_id required' });

  var row = findRoster_(studentId);
  if (!row) return json_({ success: 'false', message: 'Unknown student ID' });
  if (password && String(row.password) !== password) {
    return json_({ success: 'false', message: 'Incorrect password' });
  }

  var open = getOpenSession_();
  if (!open) return json_({ success: 'false', message: 'No open classroom session' });
  if (String(d.session_id || open.session_id) !== open.session_id) {
    return json_({ success: 'false', message: 'Session mismatch' });
  }

  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    if (studentRunStatus_(open.tab_name, row.student_id) === 'completed') {
      return json_({ success: 'false', message: 'Already completed — one attempt per session' });
    }

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName(open.tab_name) || findSheet_(ss, open.tab_name);
    if (!sh) return json_({ success: 'false', message: 'Session tab missing: ' + open.tab_name });
    ensureRunHeader_(sh);

    var simId = String(d.sim_id || open.sim_id);
    var report = d.report && typeof d.report === 'object' ? d.report : {};
    var total = report.total !== undefined ? report.total : d.score;
    var grade = report.grade || '';
    var label = report.label || '';

    var extra = {
      kind: 'complete',
      report: report,
      grade: grade,
      label: label,
      profileName: report.profileName || '',
      profileBlurb: report.profileBlurb || '',
      display: report.display || {},
      highlights: report.highlights || []
    };

    var displayName = resolveDisplayName_(d, row);

    sh.appendRow([
      d.timestamp || new Date().toISOString(),
      open.session_id,
      row.student_id,
      displayName,
      simId,
      COMPLETE_ROUND,
      label || 'Completed',
      total === undefined || total === null ? '' : String(total),
      JSON.stringify(extra)
    ]);

    return json_({
      success: 'true',
      message: 'completed',
      session_id: open.session_id,
      total: total,
      grade: grade
    });
  } finally {
    lock.releaseLock();
  }
}

/* ── instructor dashboard ───────────────────────────────────────────────── */

function dashboard_(d) {
  var auth = requireInstructor_(d);
  if (auth.error) return json_({ success: 'false', message: auth.error });

  var open = getOpenSession_();
  var sessionId = String(d.session_id || (open ? open.session_id : '')).trim();
  var session = null;

  if (open && (!sessionId || sessionId === open.session_id)) {
    session = open;
  } else if (sessionId) {
    session = findSessionById_(sessionId);
  } else {
    session = open;
  }

  if (!session) {
    return json_({ success: 'false', message: 'No session to show — open a classroom sitting first.' });
  }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(session.tab_name) || findSheet_(ss, session.tab_name);
  var byStudent = {};
  var rosterStudents = listStudentRoster_();

  rosterStudents.forEach(function (s) {
    byStudent[s.student_id] = emptyStudentEntry_(s.student_id, s.name);
  });

  if (sh && sh.getLastRow() >= 2) {
    var data = sh.getDataRange().getValues();
    var headers = data[0].map(function (h) { return String(h).toLowerCase().trim(); });
    var idx = {
      timestamp: headers.indexOf('timestamp'),
      student_id: headers.indexOf('student_id'),
      name: headers.indexOf('name'),
      round: headers.indexOf('round'),
      choice_label: headers.indexOf('choice_label'),
      score: headers.indexOf('score'),
      extra_json: headers.indexOf('extra_json'),
      sim_id: headers.indexOf('sim_id')
    };
    if (idx.student_id < 0) idx.student_id = 2;

    for (var i = 1; i < data.length; i++) {
      var sid = String(data[i][idx.student_id]).trim();
      if (!sid) continue;
      if (!byStudent[sid]) {
        byStudent[sid] = emptyStudentEntry_(
          sid,
          String(idx.name >= 0 ? data[i][idx.name] : sid)
        );
      }
      var entry = byStudent[sid];
      var round = String(idx.round >= 0 ? data[i][idx.round] : '');
      var ts = String(idx.timestamp >= 0 ? data[i][idx.timestamp] : '');
      var choiceLabel = String(idx.choice_label >= 0 ? data[i][idx.choice_label] : '');
      var scoreCell = idx.score >= 0 ? data[i][idx.score] : '';
      var extra = parseExtra_(idx.extra_json >= 0 ? data[i][idx.extra_json] : '');

      if (round === COMPLETE_ROUND) {
        entry.status = 'completed';
        entry.completed_at = ts;
        var totalNum = parseFloat(scoreCell);
        entry.total = isNaN(totalNum) ? null : totalNum;
        var report = (extra && extra.report) ? extra.report : extra || {};
        entry.report = report;
        entry.grade = report.grade || extra.grade || '';
        entry.label = report.label || extra.label || choiceLabel;
        entry.profileName = report.profileName || extra.profileName || '';
        entry.profileBlurb = report.profileBlurb || extra.profileBlurb || '';
        entry.display = report.display || extra.display || {};
        entry.highlights = report.highlights || extra.highlights || [];
      } else {
        if (entry.status !== 'completed') entry.status = 'in_progress';
        entry.rounds_done += 1;
        entry.last_round = round;
        var metrics = pickRoundMetrics_(extra);
        entry.rounds.push({
          timestamp: ts,
          round: round,
          choice_label: choiceLabel,
          score: scoreCell === '' || scoreCell === null || scoreCell === undefined ? null : scoreCell,
          metrics: metrics
        });
        if (metrics && Object.keys(metrics).length) entry.live = metrics;
      }
      if (idx.name >= 0 && data[i][idx.name]) entry.name = String(data[i][idx.name]);
    }
  }

  var students = Object.keys(byStudent).map(function (k) { return byStudent[k]; });
  var completed = students.filter(function (s) { return s.status === 'completed'; });
  var leaderboard = completed.slice().sort(function (a, b) {
    var ta = a.total == null ? -1 : Number(a.total);
    var tb = b.total == null ? -1 : Number(b.total);
    if (tb !== ta) return tb - ta;
    return String(a.student_id).localeCompare(String(b.student_id));
  }).map(function (s, i) {
    return {
      rank: i + 1,
      student_id: s.student_id,
      name: s.name,
      total: s.total,
      grade: s.grade,
      label: s.label,
      completed_at: s.completed_at
    };
  });

  var counts = {
    roster: students.length,
    not_started: students.filter(function (s) { return s.status === 'not_started'; }).length,
    in_progress: students.filter(function (s) { return s.status === 'in_progress'; }).length,
    completed: completed.length
  };

  var simMeta = {
    mumbai: 'The Mumbai Manufacturer',
    zara: 'Zara — The Fast-Fashion Reckoning',
    'zara-new': 'Zara — Business Model & Globalization',
    zenith: 'Zenith Appliances — The Annual Budget War Room'
  };

  return json_({
    success: 'true',
    message: 'ok',
    session: session,
    sim_title: simMeta[session.sim_id] || session.sim_id,
    counts: counts,
    leaderboard: leaderboard,
    students: students
  });
}

/* ── helpers ────────────────────────────────────────────────────────────── */

function emptyStudentEntry_(studentId, name) {
  return {
    student_id: studentId,
    name: name || studentId,
    status: 'not_started',
    rounds_done: 0,
    total: null,
    grade: '',
    label: '',
    profileName: '',
    profileBlurb: '',
    display: {},
    highlights: [],
    completed_at: '',
    last_round: '',
    report: null,
    live: null,
    rounds: []
  };
}

/** Prefer the name the student typed at login over the Roster placeholder. */
function resolveDisplayName_(d, row) {
  var fromClient = String(d.display_name || d.name || '').trim();
  if (fromClient && !/^student\s*\d+$/i.test(fromClient)) return fromClient;
  if (fromClient) return fromClient;
  var rosterName = row && row.name ? String(row.name).trim() : '';
  if (rosterName) return rosterName;
  return row ? row.student_id : '';
}

function updateRosterName_(studentId, newName) {
  var name = String(newName || '').trim();
  if (!name) return;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = findSheet_(ss, ROSTER_TAB);
  if (!sh || sh.getLastRow() < 2) return;
  var data = sh.getDataRange().getValues();
  var headers = data[0].map(function (h) { return String(h).toLowerCase().trim(); });
  var idIdx = headers.indexOf('student_id');
  if (idIdx < 0) idIdx = 0;
  var nameIdx = headers.indexOf('name');
  if (nameIdx < 0) return;
  var needle = String(studentId).toLowerCase().trim();
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][idIdx]).toLowerCase().trim() === needle) {
      sh.getRange(i + 1, nameIdx + 1).setValue(name);
      return;
    }
  }
}

/** Flatten common KPI fields from a round's extra_json for the live scoreboard. */
function pickRoundMetrics_(extra) {
  if (!extra || typeof extra !== 'object') return {};
  var keys = [
    'stores', 'profit', 'revenue', 'share', 'markdown',
    'cash_after', 'inventory_after', 'csat_after',
    'cash', 'inventory', 'customer_satisfaction',
    'type', 'strategic_type', 'title'
  ];
  var out = {};
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i];
    if (extra[k] !== undefined && extra[k] !== null && extra[k] !== '') {
      out[k] = extra[k];
    }
  }
  if (extra.decisions && typeof extra.decisions === 'object') {
    out.decisions = extra.decisions;
  }
  return out;
}

function requireInstructor_(d) {
  var studentId = String(d.student_id || d.email || '').trim();
  var password = String(d.password || '');
  if (!studentId || !password) return { error: 'instructor credentials required' };
  var row = findRoster_(studentId);
  if (!row) return { error: 'Unknown instructor ID' };
  if (String(row.password) !== password) return { error: 'Incorrect password' };
  var role = String(row.role || '').toLowerCase();
  if (role !== 'instructor' && role !== 'faculty' && role !== 'admin') {
    return { error: 'Instructor role required' };
  }
  return { row: row };
}

function findSheet_(ss, wanted) {
  var exact = ss.getSheetByName(wanted);
  if (exact) return exact;
  var sheets = ss.getSheets();
  var needle = String(wanted).toLowerCase().trim();
  for (var i = 0; i < sheets.length; i++) {
    if (String(sheets[i].getName()).toLowerCase().trim() === needle) return sheets[i];
  }
  return null;
}

function findRoster_(studentId) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) {
    throw new Error('Apps Script is not bound to the Simulok Classroom spreadsheet.');
  }
  var sh = findSheet_(ss, ROSTER_TAB);
  if (!sh) {
    throw new Error('Missing tab named "Roster".');
  }
  var data = sh.getDataRange().getValues();
  if (data.length < 2) {
    throw new Error('Roster tab is empty.');
  }
  var headers = data[0].map(function (h) { return String(h).toLowerCase().trim(); });
  if (headers.length === 1 && String(data[0][0]).indexOf(',') >= 0) {
    throw new Error('Roster looks like one column of CSV text. Import as columns A–E.');
  }
  var idIdx = headers.indexOf('student_id');
  if (idIdx < 0) idIdx = 0;
  var needle = String(studentId).toLowerCase();
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][idIdx]).toLowerCase().trim() === needle) {
      return {
        student_id: String(data[i][idIdx]).trim(),
        name: cell_(data[i], headers, 'name'),
        password: cell_(data[i], headers, 'password'),
        role: cell_(data[i], headers, 'role') || 'student',
        active: cell_(data[i], headers, 'active') || 'yes'
      };
    }
  }
  return null;
}

function listStudentRoster_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = findSheet_(ss, ROSTER_TAB);
  if (!sh || sh.getLastRow() < 2) return [];
  var data = sh.getDataRange().getValues();
  var headers = data[0].map(function (h) { return String(h).toLowerCase().trim(); });
  var idIdx = headers.indexOf('student_id');
  if (idIdx < 0) idIdx = 0;
  var out = [];
  for (var i = 1; i < data.length; i++) {
    var id = String(data[i][idIdx]).trim();
    if (!id) continue;
    var role = String(cell_(data[i], headers, 'role') || 'student').toLowerCase();
    if (role === 'instructor' || role === 'faculty' || role === 'admin') continue;
    var active = String(cell_(data[i], headers, 'active') || 'yes').toLowerCase();
    if (active === 'no') continue;
    out.push({ student_id: id, name: cell_(data[i], headers, 'name') || id });
  }
  return out;
}

function studentRunStatus_(tabName, studentId) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(tabName) || findSheet_(ss, tabName);
  if (!sh || sh.getLastRow() < 2) return 'none';
  var data = sh.getDataRange().getValues();
  var headers = data[0].map(function (h) { return String(h).toLowerCase().trim(); });
  var idIdx = headers.indexOf('student_id');
  var roundIdx = headers.indexOf('round');
  if (idIdx < 0) idIdx = 2;
  if (roundIdx < 0) roundIdx = 5;
  var needle = String(studentId).toLowerCase();
  var any = false;
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][idIdx]).toLowerCase().trim() !== needle) continue;
    any = true;
    if (String(data[i][roundIdx]) === COMPLETE_ROUND) return 'completed';
  }
  return any ? 'in_progress' : 'none';
}

function cell_(row, headers, key) {
  var idx = headers.indexOf(key);
  if (idx < 0) return '';
  return row[idx] === undefined || row[idx] === null ? '' : String(row[idx]);
}

function ensureSessionsSheet_(ss) {
  var sh = findSheet_(ss, SESSIONS_TAB);
  if (!sh) {
    sh = ss.insertSheet(SESSIONS_TAB);
    sh.appendRow(SESSION_FIELDS);
    sh.getRange(1, 1, 1, SESSION_FIELDS.length).setFontWeight('bold');
    sh.setFrozenRows(1);
    return sh;
  }
  if (sh.getLastRow() === 0) {
    sh.appendRow(SESSION_FIELDS);
    sh.getRange(1, 1, 1, SESSION_FIELDS.length).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}

function ensureRunHeader_(sh) {
  if (sh.getLastRow() === 0) {
    sh.appendRow(RUN_FIELDS);
    sh.getRange(1, 1, 1, RUN_FIELDS.length).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
}

function getOpenSession_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = findSheet_(ss, SESSIONS_TAB);
  if (!sh || sh.getLastRow() < 2) return null;
  var data = sh.getDataRange().getValues();
  var headers = data[0].map(function (h) { return String(h).toLowerCase().trim(); });
  for (var i = data.length - 1; i >= 1; i--) {
    var status = String(data[i][headers.indexOf('status') >= 0 ? headers.indexOf('status') : 3]).toLowerCase();
    if (status === 'open') {
      return {
        session_id: String(data[i][headers.indexOf('session_id') >= 0 ? headers.indexOf('session_id') : 0]),
        sim_id: String(data[i][headers.indexOf('sim_id') >= 0 ? headers.indexOf('sim_id') : 1]),
        opened_at: String(data[i][headers.indexOf('opened_at') >= 0 ? headers.indexOf('opened_at') : 2]),
        status: 'open',
        tab_name: String(data[i][headers.indexOf('tab_name') >= 0 ? headers.indexOf('tab_name') : 4])
      };
    }
  }
  return null;
}

function findSessionById_(sessionId) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = findSheet_(ss, SESSIONS_TAB);
  if (!sh || sh.getLastRow() < 2) return null;
  var data = sh.getDataRange().getValues();
  for (var i = data.length - 1; i >= 1; i--) {
    if (String(data[i][0]) === sessionId) {
      return {
        session_id: String(data[i][0]),
        sim_id: String(data[i][1]),
        opened_at: String(data[i][2]),
        status: String(data[i][3]),
        tab_name: String(data[i][4])
      };
    }
  }
  return null;
}

function nextSessionTabName_(ss) {
  var n = 1;
  var letter = 'A';
  while (ss.getSheetByName('Sess_' + letter + n) || findSheet_(ss, 'Sess_' + letter + n)) {
    n += 1;
    if (n > 99) {
      letter = String.fromCharCode(letter.charCodeAt(0) + 1);
      n = 1;
      if (letter > 'Z') throw new Error('Too many session tabs');
    }
  }
  return 'Sess_' + letter + n;
}

function stringifyExtra_(d) {
  if (typeof d.extra_json === 'string') return d.extra_json;
  try {
    return JSON.stringify(d.extra || d.extra_json || {});
  } catch (e) {
    return '{}';
  }
}

function parseExtra_(raw) {
  if (!raw) return {};
  try {
    return typeof raw === 'string' ? JSON.parse(raw) : (raw || {});
  } catch (e) {
    return {};
  }
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
