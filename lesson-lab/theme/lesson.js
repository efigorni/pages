/* lesson.js — עיגולי המסילה, אמנות ה-hero וטיימרים. ללא תלויות. */
(function () {
  'use strict';
  var C = { open: '#f7ae4d', body: '#63b1af', talk: '#8c82c1', close: '#619f88' };
  var uid = 0;

  function node(k) {
    var c = C[k] || C.body, id = 'h' + (++uid);
    if (k === 'open') return '<svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="58" cy="44" r="34" fill="#f7ae4d"/><circle cx="40" cy="60" r="28" fill="#63b1af" fill-opacity=".8"/></svg>';
    if (k === 'talk') return '<svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="46" fill="#fff"/><g fill="none" stroke="' + c + '" stroke-width="7"><circle cx="50" cy="50" r="12"/><circle cx="50" cy="50" r="27"/><circle cx="50" cy="50" r="42"/></g></svg>';
    if (k === 'close') return '<svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="44" fill="' + c + '"/><path d="M50 28a20 18 0 1 0 -11 33 l-6 11 l13 -7 a20 18 0 0 0 4 -37 z" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round"/></svg>';
    return '<svg viewBox="0 0 100 100" aria-hidden="true"><defs><pattern id="' + id + '" width="12" height="12" patternTransform="rotate(45)" patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="12" stroke="#f7ae4d" stroke-width="6"/></pattern></defs><circle cx="50" cy="50" r="46" fill="#fff"/><circle cx="44" cy="56" r="40" fill="url(#' + id + ')"/><circle cx="64" cy="38" r="26" fill="' + c + '"/></svg>';
  }

  function motif(k) {
    var c = C[k] || C.body;
    if (k === 'talk') return '<svg viewBox="0 0 100 100" aria-hidden="true"><g fill="none" stroke="' + c + '" stroke-width="2.6"><circle cx="50" cy="50" r="8"/><circle cx="50" cy="50" r="16"/><circle cx="50" cy="50" r="24"/><circle cx="50" cy="50" r="32"/><circle cx="50" cy="50" r="40"/></g></svg>';
    if (k === 'close') return '<svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="52" cy="48" r="31" fill="' + c + '"/><path d="M52 26a22 20 0 1 0 -12 36 l-6 12 l14 -8 a22 20 0 0 0 4 -40 z" fill="none" stroke="#fff" stroke-width="2.6" stroke-linejoin="round"/></svg>';
    if (k === 'open') return '<svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="60" cy="42" r="30" fill="' + c + '" fill-opacity=".9"/><circle cx="36" cy="60" r="25" fill="#63b1af" fill-opacity=".78"/></svg>';
    var id = 'm' + (++uid);
    return '<svg viewBox="0 0 100 100" aria-hidden="true"><defs><pattern id="' + id + '" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="8" stroke="#f7ae4d" stroke-width="3.6"/></pattern></defs><circle cx="42" cy="55" r="30" fill="url(#' + id + ')"/><circle cx="66" cy="36" r="20" fill="' + c + '" fill-opacity=".88"/></svg>';
  }

  var HERO = '<svg class="a" viewBox="0 0 100 100" aria-hidden="true"><g fill="none" stroke="#8c82c1" stroke-width="1.7"><circle cx="50" cy="50" r="6"/><circle cx="50" cy="50" r="12"/><circle cx="50" cy="50" r="18"/><circle cx="50" cy="50" r="24"/><circle cx="50" cy="50" r="30"/><circle cx="50" cy="50" r="36"/><circle cx="50" cy="50" r="42"/><circle cx="50" cy="50" r="48"/></g></svg>' +
    '<svg class="b" viewBox="0 0 100 100" aria-hidden="true"><defs><pattern id="hs-hero" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="7" stroke="#f7ae4d" stroke-width="3.4"/></pattern></defs><circle cx="50" cy="50" r="46" fill="url(#hs-hero)"/></svg>';

  function fmt(s) { var m = Math.floor(s / 60), r = s % 60; return m + ':' + (r < 10 ? '0' : '') + r; }

  function timers(root) {
    root.querySelectorAll('.timer[data-sec]').forEach(function (t) {
      if (t._wired) return; t._wired = true;
      var total = +t.getAttribute('data-sec') || 60, left = total, h = null;
      var tm = t.querySelector('.tm'), b = t.querySelector('button');
      if (!tm) { tm = document.createElement('span'); tm.className = 'tm'; t.appendChild(tm); }
      if (!b) { b = document.createElement('button'); b.type = 'button'; t.appendChild(b); }
      function draw() { tm.textContent = fmt(left); b.textContent = h ? 'עצירה' : (left === total ? 'הפעלה' : (left === 0 ? 'שוב' : 'המשך')); }
      b.addEventListener('click', function () {
        if (h) { clearInterval(h); h = null; draw(); return; }
        if (left === 0) left = total;
        h = setInterval(function () { left = Math.max(0, left - 1); if (!left) { clearInterval(h); h = null; } draw(); }, 1000);
        draw();
      });
      draw();
    });
  }

  function decorate(root) {
    root = root || document;
    root.querySelectorAll('.step-node[data-k]').forEach(function (n) { if (!n.firstChild) n.innerHTML = node(n.getAttribute('data-k')); });
    root.querySelectorAll('.motif[data-k]').forEach(function (n) { if (!n.firstChild) n.innerHTML = motif(n.getAttribute('data-k')); });
    root.querySelectorAll('.hero-art:empty').forEach(function (n) { n.innerHTML = HERO; });
    timers(root);
  }

  window.LessonTheme = { decorate: decorate };
  if (document.readyState !== 'loading') decorate(); else document.addEventListener('DOMContentLoaded', function () { decorate(); });
})();
