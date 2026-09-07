/* ==========================================================================
   Simulok.ai — site behaviour
   No dependencies. Everything degrades gracefully without JS.
   ========================================================================== */
(function () {
  'use strict';

  var $  = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Year ---------- */
  var yr = $('#yr');
  if (yr) yr.textContent = new Date().getFullYear();

  /* ---------- Sticky nav + scroll progress ---------- */
  var nav = $('#nav');
  var progress = $('#progress');
  function onScroll() {
    var y = window.pageYOffset || document.documentElement.scrollTop;
    if (nav) nav.classList.toggle('is-stuck', y > 12);
    if (progress) {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      progress.style.width = (h > 0 ? Math.min(100, (y / h) * 100) : 0) + '%';
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- Mobile drawer ---------- */
  var burger = $('#burger');
  var drawer = $('#drawer');
  if (burger && nav) {
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  if (drawer) {
    drawer.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        nav.classList.remove('is-open');
        burger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ---------- Reveal on scroll ---------- */
  var revealables = $$('[data-reveal], [data-reveal-stagger]');
  if (!('IntersectionObserver' in window) || reduced) {
    revealables.forEach(function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.08 });
    revealables.forEach(function (el) { io.observe(el); });
  }

  /* ---------- Cursor glow on cards ---------- */
  if (window.matchMedia('(hover: hover)').matches) {
    document.addEventListener('mousemove', function (e) {
      var card = e.target.closest && e.target.closest('.card, .sim, .path');
      if (!card) return;
      var r = card.getBoundingClientRect();
      card.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100) + '%');
      card.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100) + '%');
    }, { passive: true });
  }

  /* ---------- Count-up numbers ---------- */
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    var dec = parseInt(el.getAttribute('data-decimals') || '0', 10);
    var suffix = el.getAttribute('data-suffix') || '';
    if (isNaN(target)) return;
    if (reduced) { el.textContent = target.toFixed(dec) + suffix; return; }
    var dur = 1400, t0 = null;
    function step(t) {
      if (t0 === null) t0 = t;
      var p = Math.min(1, (t - t0) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * eased).toFixed(dec) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  var counters = $$('[data-count]');
  if ('IntersectionObserver' in window) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { countUp(en.target); cio.unobserve(en.target); }
      });
    }, { threshold: 0.6 });
    counters.forEach(function (el) { cio.observe(el); });
  } else {
    counters.forEach(countUp);
  }

  /* ---------- Benefits tabs ---------- */
  var tabs = $$('.tab');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) {
        t.classList.remove('is-on');
        t.setAttribute('aria-selected', 'false');
        var p = document.getElementById(t.getAttribute('aria-controls'));
        if (p) { p.classList.remove('is-on'); p.hidden = true; }
      });
      tab.classList.add('is-on');
      tab.setAttribute('aria-selected', 'true');
      var pane = document.getElementById(tab.getAttribute('aria-controls'));
      if (pane) { pane.hidden = false; pane.classList.add('is-on'); }
    });
  });

  /* ==========================================================================
     Skill-map radar
     ========================================================================== */
  var AXES = ['Strategy', 'Analysis', 'Risk', 'Collab.', 'Speed'];
  var LEARNER = [0.86, 0.72, 0.55, 0.80, 0.63];
  var COHORT  = [0.60, 0.64, 0.58, 0.55, 0.70];

  function polar(cx, cy, r, i, n) {
    var a = (Math.PI * 2 * i / n) - Math.PI / 2;
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  }

  (function radar() {
    var grid = $('#radarGrid');
    if (!grid) return;
    var cx = 150, cy = 112, R = 74, n = AXES.length;
    var ns = 'http://www.w3.org/2000/svg';

    [0.25, 0.5, 0.75, 1].forEach(function (f) {
      var pts = [];
      for (var i = 0; i < n; i++) pts.push(polar(cx, cy, R * f, i, n).join(','));
      var p = document.createElementNS(ns, 'polygon');
      p.setAttribute('points', pts.join(' '));
      p.setAttribute('class', 'grid-line');
      grid.appendChild(p);
    });
    for (var i = 0; i < n; i++) {
      var e = polar(cx, cy, R, i, n);
      var l = document.createElementNS(ns, 'line');
      l.setAttribute('x1', cx); l.setAttribute('y1', cy);
      l.setAttribute('x2', e[0]); l.setAttribute('y2', e[1]);
      l.setAttribute('class', 'axis');
      grid.appendChild(l);
    }

    var labels = $('#radarLabels');
    AXES.forEach(function (name, i) {
      var p = polar(cx, cy, R + 17, i, n);
      var t = document.createElementNS(ns, 'text');
      t.setAttribute('x', p[0]); t.setAttribute('y', p[1] + 2.5);
      t.setAttribute('text-anchor', i === 0 ? 'middle' : (p[0] > cx + 2 ? 'start' : (p[0] < cx - 2 ? 'end' : 'middle')));
      t.textContent = name.toUpperCase();
      labels.appendChild(t);
    });

    function pointsFor(vals) {
      return vals.map(function (v, i) { return polar(cx, cy, R * v, i, n).join(','); }).join(' ');
    }
    var shape = $('#radarShape');
    var cohort = $('#radarCohort');
    cohort.setAttribute('points', pointsFor(COHORT));

    var zero = AXES.map(function () { return 0.001; });
    shape.setAttribute('points', pointsFor(reduced ? LEARNER : zero));

    var dots = $('#radarDots');
    LEARNER.forEach(function (v, i) {
      var p = polar(cx, cy, R * v, i, n);
      var c = document.createElementNS(ns, 'circle');
      c.setAttribute('cx', p[0]); c.setAttribute('cy', p[1]); c.setAttribute('r', 2.6);
      c.setAttribute('class', 'dot');
      c.setAttribute('opacity', reduced ? '1' : '0');
      dots.appendChild(c);
    });

    if (reduced) return;
    function animate() {
      var dur = 1100, t0 = null;
      function step(t) {
        if (t0 === null) t0 = t;
        var p = Math.min(1, (t - t0) / dur);
        var e = 1 - Math.pow(1 - p, 3);
        shape.setAttribute('points', pointsFor(LEARNER.map(function (v) { return Math.max(0.001, v * e); })));
        $$('circle', dots).forEach(function (c, i) {
          var pt = polar(cx, cy, R * LEARNER[i] * e, i, n);
          c.setAttribute('cx', pt[0]); c.setAttribute('cy', pt[1]);
          c.setAttribute('opacity', e);
        });
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }
    if ('IntersectionObserver' in window) {
      var rio = new IntersectionObserver(function (en) {
        if (en[0].isIntersecting) { animate(); rio.disconnect(); }
      }, { threshold: 0.4 });
      rio.observe(shape.closest('svg'));
    } else { animate(); }
  })();

  /* ==========================================================================
     Cohort heat map
     ========================================================================== */
  (function heat() {
    var box = $('#heat');
    if (!box) return;
    var rows = ['Segmentation', 'Pricing', 'Capacity', 'Cash flow', 'Ethics'];
    /* 0 = cohort broke, 1 = cohort held. Hand-tuned to read like a real class. */
    var data = [
      [0.85, 0.70, 0.42, 0.25, 0.30, 0.48, 0.62],
      [0.78, 0.55, 0.30, 0.18, 0.22, 0.35, 0.50],
      [0.90, 0.82, 0.75, 0.60, 0.55, 0.68, 0.80],
      [0.72, 0.64, 0.58, 0.45, 0.38, 0.52, 0.66],
      [0.95, 0.88, 0.80, 0.72, 0.40, 0.58, 0.85]
    ];

    var frag = document.createDocumentFragment();
    var corner = document.createElement('span');
    corner.className = 'heat__lbl';
    corner.textContent = '';
    frag.appendChild(corner);
    for (var r = 1; r <= 7; r++) {
      var hd = document.createElement('span');
      hd.className = 'heat__hd';
      hd.textContent = 'R' + r;
      frag.appendChild(hd);
    }
    rows.forEach(function (name, i) {
      var lbl = document.createElement('span');
      lbl.className = 'heat__lbl';
      lbl.textContent = name;
      frag.appendChild(lbl);
      data[i].forEach(function (v, j) {
        var c = document.createElement('span');
        c.className = 'heat__c';
        c.title = name + ' · Round ' + (j + 1) + ' · ' + Math.round(v * 100) + '% held';
        var col = v < 0.45
          ? 'rgba(255,122,92,' + (0.42 + (0.45 - v) * 1.1).toFixed(2) + ')'
          : (v < 0.68 ? 'rgba(240,180,41,' + (0.40 + (v - 0.45) * 1.1).toFixed(2) + ')'
                      : 'rgba(63,211,190,' + (0.34 + (v - 0.6) * 1.1).toFixed(2) + ')');
        c.style.background = col;
        c.style.transitionDelay = ((i * 7 + j) * 12) + 'ms';
        frag.appendChild(c);
      });
    });
    box.appendChild(frag);
  })();

  /* ==========================================================================
     Simulation library
     ========================================================================== */
  var SEG_LABEL = {
    graduates: 'Graduate & MBA',
    schools: 'Schools',
    corporates: 'Corporate L&D',
    specialisation: 'Specialisation · CA'
  };
  var SEG_COLOR = {
    graduates: '#3FD3BE',
    schools: '#F0B429',
    corporates: '#6FC3FF',
    specialisation: '#A78BFA'
  };

  var sims = window.SIMULOK_SIMS || [];
  var grid = $('#simGrid');
  var countEl = $('#simCount');
  var byId = {};
  sims.forEach(function (s) { byId[s.id] = s; });

  /* A slice only — never the full roster, never a count. */
  var SAMPLE = {
    all: ['heliogrid', 'k2-ascent', 'macroecon', 'invogrid', 'zara', 'lemonade', 'mumbai', 'pharma-batch'],
    graduates: ['heliogrid', 'mumbai', 'k2-ascent', 'zara', 'soleforce'],
    schools: ['lemonade', 'finance', 'bazaar', 'macroecon'],
    corporates: ['heliogrid', 'k2-ascent', 'zara', 'pharma-batch', 'auto-launch'],
    specialisation: ['invogrid', 'indas-peak', 'kavericirp', 'tplex']
  };

  function segLabel(segs) {
    return segs.map(function (s) { return SEG_LABEL[s] || s; }).join(' · ');
  }

  function moreCard(delay) {
    return '<article class="sim sim--more" style="animation-delay:' + delay + 'ms">' +
      '<div class="sim__seg">And many more</div>' +
      '<h3>This is a slice, not the catalogue</h3>' +
      '<p>New titles ship every month. Tell us the concept you need to teach — we will show you the simulation that fits, or build one around your syllabus.</p>' +
      '<a class="textlink" href="contact.html?intent=custom">Ask about the library' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a>' +
      '</article>';
  }

  function render(filter) {
    if (!grid) return;
    var ids = SAMPLE[filter] || SAMPLE.all;
    var list = ids.map(function (id) { return byId[id]; }).filter(Boolean);
    grid.innerHTML = list.map(function (s, i) {
      var primary = s.seg[0];
      return '<article class="sim" style="--seg:' + (SEG_COLOR[primary] || '#3FD3BE') +
        ';animation-delay:' + Math.min(i * 22, 380) + 'ms">' +
        '<div class="sim__seg">' + segLabel(s.seg) + '</div>' +
        '<h3>' + s.title + '</h3>' +
        '<p>' + s.desc + '</p>' +
        '<div class="sim__meta">' + s.meta.map(function (m) { return '<span>' + m + '</span>'; }).join('') + '</div>' +
        '</article>';
    }).join('') + moreCard(Math.min(list.length * 22, 400));
    if (countEl) countEl.textContent = 'A growing sample';
  }

  $$('.filters .chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      $$('.filters .chip').forEach(function (c) { c.classList.remove('is-on'); });
      chip.classList.add('is-on');
      render(chip.getAttribute('data-filter'));
    });
  });
  render('all');

})();
