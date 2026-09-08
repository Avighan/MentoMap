/* ==========================================================================
   Simulok.ai — contact form
   --------------------------------------------------------------------------
   Static hosting has no backend, so enquiries go to a relay. Two are
   supported; switch by changing PROVIDER below and nothing else.

   'formsubmit'  — https://formsubmit.co, no account needed. FORM_ENDPOINT
                   contains the destination address in clear text, so it is
                   visible in this file and scrapeable. Requires a one-time
                   activation click on an email it sends to that address.

   'appsscript'  — a Google Apps Script web app you own (see
                   tools/contact-form.gs). Logs every enquiry to a Google Sheet
                   and emails it on. No third party in the path, and the
                   destination address never appears here. Preferred.

   Apps Script cannot answer a CORS preflight, so that provider posts the JSON
   as text/plain — a "simple request" — which avoids the preflight entirely
   while still letting us read the response. That is why the content type is
   per-provider rather than fixed.

   Delivery is judged on the response BODY, not the status code: both relays
   can answer 200 while refusing the submission, and showing a visitor a false
   confirmation loses the enquiry silently.
   ========================================================================== */
(function () {
  'use strict';

  var PROVIDER = 'appsscript';          /* 'formsubmit' | 'appsscript' */

  var PROVIDERS = {
    formsubmit: {
      endpoint: 'https://formsubmit.co/ajax/sumeetonline90@gmail.com',
      contentType: 'application/json',
      /* FormSubmit control fields — not part of the enquiry itself. */
      meta: {
        _template: 'table',   /* readable table in the email rather than a raw dump */
        _captcha: 'false'     /* a captcha redirect would break the AJAX round-trip */
      },
      /* FormSubmit builds the subject from a _subject field. */
      subjectKey: '_subject'
    },
    appsscript: {
      endpoint: 'https://script.google.com/macros/s/AKfycbw5ALz47QrWUaQKbucwUGaigeD6fA37cBnpUto1NjOLwnxoXwqeNcov3xcNlHx5CizW/exec',
      contentType: 'text/plain;charset=utf-8',   /* avoids the CORS preflight */
      meta: {},
      subjectKey: null        /* the script composes its own subject */
    }
  };

  var CFG = PROVIDERS[PROVIDER] || PROVIDERS.formsubmit;
  var FORM_ENDPOINT = CFG.endpoint;

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var form = $('#contactForm');
  if (!form) return;

  if (!FORM_ENDPOINT) {
    console.warn('[Simulok] provider "' + PROVIDER + '" has no endpoint configured — ' +
                 'enquiries cannot be delivered. Set it in website/assets/js/contact.js.');
  }

  var sent = $('#sent');
  var sentBody = $('#sentBody');
  var btn = $('#submitBtn');
  var label = $('#submitLabel');
  var note = $('#formNote');

  /* ---------- Intent chips (pre-selected from ?intent=) ---------- */
  var INTENT_COPY = {
    demo:    'We will come back within two working days to schedule a guided run through HelioGrid, MacroEcon or InvoGrid.',
    pilot:   'We will come back within two working days with a pilot outline — one course, one semester, measured against your current assessment.',
    custom:  'We will come back within two working days with a first read on what your custom simulation would look like.',
    pricing: 'We will come back within two working days with plans and pricing for your cohort size.',
    other:   'We will come back to you within two working days.'
  };
  var chips = $$('#intentChips .chip');
  var intentValue = $('#intentValue');

  function setIntent(v) {
    var found = false;
    chips.forEach(function (c) {
      var on = c.getAttribute('data-intent') === v;
      c.classList.toggle('is-on', on);
      if (on) found = true;
    });
    if (!found) { chips[0].classList.add('is-on'); v = chips[0].getAttribute('data-intent'); }
    intentValue.value = v;
  }
  chips.forEach(function (c) {
    c.addEventListener('click', function () { setIntent(c.getAttribute('data-intent')); });
  });

  var params = new URLSearchParams(window.location.search);
  if (params.get('intent')) setIntent(params.get('intent'));

  /* ---------- Validation ---------- */
  function fieldOf(el) { return el.closest('.field') || el.closest('.consent'); }

  function validate(el) {
    var ok = true;
    var v = (el.value || '').trim();
    if (el.type === 'checkbox') ok = el.checked;
    else if (el.hasAttribute('required') && !v) ok = false;
    else if (el.type === 'email' && v) ok = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);
    var f = fieldOf(el);
    if (f && f.classList.contains('field')) f.classList.toggle('has-error', !ok);
    if (el.type === 'checkbox') el.style.outline = ok ? '' : '2px solid var(--coral)';
    return ok;
  }

  $$('input, select, textarea', form).forEach(function (el) {
    el.addEventListener('blur', function () { if (el.value || el.hasAttribute('required')) validate(el); });
    el.addEventListener('input', function () {
      var f = fieldOf(el);
      if (f && f.classList.contains('has-error')) validate(el);
      if (el.type === 'checkbox') validate(el);
    });
  });

  /* ---------- Submit ---------- */
  function collect() {
    var d = {};
    new FormData(form).forEach(function (v, k) { d[k] = typeof v === 'string' ? v.trim() : v; });
    d.intent = intentValue.value;
    d.page = window.location.href;
    d.submitted_at = new Date().toISOString();
    return d;
  }

  function succeed(intent) {
    form.style.display = 'none';
    if (sentBody) sentBody.textContent = INTENT_COPY[intent] || INTENT_COPY.other;
    sent.classList.add('is-on');
    sent.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    /* honeypot — a bot filled the hidden field */
    if (form.company_website && form.company_website.value) { succeed(intentValue.value); return; }

    var fields = $$('[required]', form);
    var firstBad = null;
    fields.forEach(function (el) { if (!validate(el) && !firstBad) firstBad = el; });
    if (firstBad) {
      firstBad.focus();
      firstBad.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (note) { note.textContent = 'Please complete the highlighted fields.'; note.style.color = 'var(--coral)'; }
      return;
    }
    if (note) { note.textContent = 'We reply within two working days.'; note.style.color = ''; }

    var data = collect();
    delete data.company_website;

    var payload = {};
    Object.keys(CFG.meta).forEach(function (k) { payload[k] = CFG.meta[k]; });
    /* Give each email a subject that is scannable in an inbox. */
    if (CFG.subjectKey) {
      payload[CFG.subjectKey] = 'Simulok.ai — ' + (data.intent || 'enquiry') + ' — ' +
                                (data.organisation || data.name || 'new enquiry');
    }
    Object.keys(data).forEach(function (k) { payload[k] = data[k]; });

    if (!FORM_ENDPOINT) {
      /* Misconfigured provider. Never show a confirmation for an enquiry that
         was not sent — a false "thank you" loses the lead silently. */
      console.error('[Simulok] provider "' + PROVIDER + '" has no endpoint: enquiry NOT delivered.', data);
      if (note) {
        note.textContent = 'The form is not accepting enquiries right now. Please try again shortly.';
        note.style.color = 'var(--coral)';
      }
      return;
    }

    btn.disabled = true;
    if (label) label.textContent = 'Sending…';

    fetch(FORM_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': CFG.contentType, 'Accept': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      /* A 2xx is not proof of delivery: both relays can answer 200 while
         refusing the submission (FormSubmit before activation, Apps Script on
         a validation or send error). Trust the body when it says so, otherwise
         fall back to the status code — relays that return no body still
         resolve as success. */
      return res.json().catch(function () { return null; });
    }).then(function (body) {
      if (body && String(body.success) === 'false') {
        throw new Error(body.message || 'relay rejected the submission');
      }
      succeed(data.intent);
    }).catch(function (err) {
      console.error('[Simulok] enquiry NOT delivered:', err && err.message, data);
      btn.disabled = false;
      if (label) label.textContent = 'Send enquiry';
      if (note) {
        note.textContent = 'That did not go through. Please try again in a moment.';
        note.style.color = 'var(--coral)';
      }
    });
  });

})();
