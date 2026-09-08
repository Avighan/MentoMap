/**
 * Simulok.ai — contact-form backend (Google Apps Script)
 * ---------------------------------------------------------------------------
 * Receives an enquiry from https://simulok.in/contact.html, logs it to a Google
 * Sheet, and emails it to NOTIFY. Free, no third-party service, and the
 * destination address never appears in the website's source.
 *
 * ── Deploy (once, ~5 minutes) ───────────────────────────────────────────────
 *  1. Create a Google Sheet to hold the log. Name the first tab "Enquiries".
 *  2. In that Sheet: Extensions → Apps Script. Delete the placeholder code and
 *     paste this whole file in.
 *  3. Set NOTIFY below to the address that should receive the emails.
 *  4. Deploy → New deployment → type "Web app", with:
 *        Execute as:      Me
 *        Who has access:  Anyone            <-- must be "Anyone", not "Anyone with Google account"
 *  5. Authorise when prompted (it will warn the app is unverified — it is your
 *     own script; continue).
 *  6. Copy the /exec URL it gives you and send it over. It goes into
 *     FORM_ENDPOINT in website/assets/js/contact.js.
 *
 * ── Giving the team access ──────────────────────────────────────────────────
 *  The Sheet is the shared record — share it, not the script. Open the Sheet →
 *  Share → add each teammate as Viewer (read-only) or Editor (so they can add
 *  an "Owner" or "Status" column and work the leads). They do NOT need access
 *  to the Apps Script project, this repo, or the website to see enquiries.
 *
 *  Only NOTIFY receives the email. To alert more people, either set NOTIFY to
 *  a Google Group address, or comma-separate addresses: 'a@x.com,b@x.com'.
 *  Everyone with the Sheet sees every enquiry regardless of the email.
 *
 * ── Re-deploying after an edit ──────────────────────────────────────────────
 *  Deploy → Manage deployments → edit the existing one → Version: New version.
 *  Keep the same deployment so the /exec URL does not change.
 *
 * ── Why the browser posts text/plain ────────────────────────────────────────
 *  A cross-origin POST with Content-Type: application/json triggers a CORS
 *  preflight, which Apps Script web apps do not answer. Posting the same JSON
 *  string as text/plain is a "simple request", so there is no preflight and the
 *  response is readable. contact.js is configured to do exactly that.
 */

var NOTIFY   = 'sumeetonline90@gmail.com';   // where enquiries land; comma-separate for several
var TAB_NAME = 'Enquiries';                  // sheet tab used as the log

/** Column order for the log. Adding a field here is all that is needed. */
var FIELDS = [
  'submitted_at', 'intent', 'name', 'email', 'organisation',
  'role', 'segment', 'cohort_size', 'message', 'consent', 'page'
];

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) return json({ success: 'false', message: 'empty request' });

    var d = JSON.parse(e.postData.contents);

    // Honeypot: a bot filled the hidden field. Accept silently so it does not retry.
    if (d.company_website) return json({ success: 'true', message: 'ok' });

    if (!d.name || !d.email || !d.message) {
      return json({ success: 'false', message: 'name, email and message are required' });
    }

    d.submitted_at = d.submitted_at || new Date().toISOString();

    logToSheet_(d);
    notify_(d);

    return json({ success: 'true', message: 'received' });
  } catch (err) {
    // Surface the failure to the visitor rather than pretending it worked.
    return json({ success: 'false', message: String(err) });
  }
}

/** A GET is only ever a human checking the deployment is alive. */
function doGet() {
  return json({ success: 'true', message: 'Simulok.ai contact endpoint is live' });
}

function logToSheet_(d) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) return;                                  // script not bound to a Sheet: email only
  var sh = ss.getSheetByName(TAB_NAME) || ss.insertSheet(TAB_NAME);

  if (sh.getLastRow() === 0) {
    sh.appendRow(FIELDS);
    sh.getRange(1, 1, 1, FIELDS.length).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  sh.appendRow(FIELDS.map(function (k) { return d[k] === undefined ? '' : String(d[k]); }));
}

function notify_(d) {
  var subject = 'Simulok.ai — ' + (d.intent || 'enquiry') + ' — ' +
                (d.organisation || d.name || 'new enquiry');

  var rows = FIELDS.map(function (k) {
    var v = d[k] === undefined || d[k] === '' ? '—' : String(d[k]);
    return '<tr>' +
      '<td style="padding:6px 14px 6px 0;color:#667;white-space:nowrap;vertical-align:top">' + esc_(k) + '</td>' +
      '<td style="padding:6px 0;vertical-align:top">' + esc_(v).replace(/\n/g, '<br>') + '</td></tr>';
  }).join('');

  var html = '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;font-size:14px;line-height:1.5">' +
             '<h2 style="margin:0 0 14px;font-size:17px">New enquiry from simulok.in</h2>' +
             '<table style="border-collapse:collapse">' + rows + '</table></div>';

  var options = { htmlBody: html, name: 'Simulok.ai website' };
  // Reply goes straight to the enquirer.
  if (d.email && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(d.email)) options.replyTo = d.email;

  MailApp.sendEmail(Object.assign({ to: NOTIFY, subject: subject }, options));
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
                       .setMimeType(ContentService.MimeType.JSON);
}

function esc_(s) {
  return String(s).replace(/[&<>"]/g, function (c) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c];
  });
}
