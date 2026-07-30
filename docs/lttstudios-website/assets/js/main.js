/* ============================================================
 * LTTStudios — Shared JS
 * v1.0 · Mobile nav toggle + minor interactions.
 * No tracking. No third-party. Vanilla only.
 * ============================================================ */

(function () {
  'use strict';

  /* Mobile nav toggle */
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.querySelector('.nav-toggle');
    var nav = document.querySelector('.nav-main');
    if (btn && nav) {
      btn.addEventListener('click', function () {
        nav.classList.toggle('open');
        var expanded = nav.classList.contains('open');
        btn.setAttribute('aria-expanded', expanded);
        btn.textContent = expanded ? '✕' : '☰';
      });
    }

    /* Highlight active nav link by path */
    var path = location.pathname.replace(/\/index\.html$/, '/').toLowerCase();
    document.querySelectorAll('.nav-main a').forEach(function (a) {
      var href = a.getAttribute('href').toLowerCase();
      var hrefPath = href.split('#')[0].replace(/\/index\.html$/, '/');
      if (hrefPath === path || (hrefPath !== '/' && path.indexOf(hrefPath) === 0)) {
        a.classList.add('active');
      }
    });

    /* Smooth-scroll for in-page anchors */
    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener('click', function (e) {
        var id = this.getAttribute('href').slice(1);
        if (!id) return;
        var target = document.getElementById(id);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          history.pushState(null, '', '#' + id);
        }
      });
    });

    /* Copy buttons inside <pre><code> blocks */
    document.querySelectorAll('pre').forEach(function (pre) {
      if (pre.querySelector('.copy-btn')) return;
      var btn = document.createElement('button');
      btn.className = 'copy-btn btn btn-sm btn-ghost';
      btn.type = 'button';
      btn.textContent = 'Copy';
      btn.style.cssText = 'position:absolute;top:8px;right:8px;font-size:11px;';
      pre.style.position = 'relative';
      pre.appendChild(btn);
      btn.addEventListener('click', function () {
        var code = pre.querySelector('code') || pre;
        navigator.clipboard.writeText(code.innerText).then(function () {
          btn.textContent = 'Copied!';
          setTimeout(function () { btn.textContent = 'Copy'; }, 1500);
        });
      });
    });
  });

  /* Year stamp helper (used in footers) */
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-year]').forEach(function (el) {
      el.textContent = new Date().getFullYear();
    });
  });
})();
