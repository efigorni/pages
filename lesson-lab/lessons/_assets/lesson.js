/* lesson.js — אמנות ה-hero וטיימרים, למערך ולמצגת. ללא תלויות.
   .timer[data-sec] → תצוגת דקות:שניות + כפתור הפעלה / עצירה / המשך / שוב. */
(function () {
  'use strict';

  var HERO = '<svg class="a" viewBox="0 0 100 100" aria-hidden="true"><g fill="none" stroke="#8c82c1" stroke-width="1.7"><circle cx="50" cy="50" r="6"/><circle cx="50" cy="50" r="12"/><circle cx="50" cy="50" r="18"/><circle cx="50" cy="50" r="24"/><circle cx="50" cy="50" r="30"/><circle cx="50" cy="50" r="36"/><circle cx="50" cy="50" r="42"/><circle cx="50" cy="50" r="48"/></g></svg>' +
    '<svg class="b" viewBox="0 0 100 100" aria-hidden="true"><defs><pattern id="hs-hero" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="7" stroke="#f7ae4d" stroke-width="3.4"/></pattern></defs><circle cx="50" cy="50" r="46" fill="url(#hs-hero)"/></svg>';

  function fmt(s) { var m = Math.floor(s / 60), r = s % 60; return m + ':' + (r < 10 ? '0' : '') + r; }

  function wire(t) {
    if (t._wired) return;
    t._wired = true;
    var total = +t.getAttribute('data-sec') || 60, left = total, h = null;
    var tm = t.querySelector('.tm'), b = t.querySelector('button');
    if (!tm) { tm = document.createElement('span'); tm.className = 'tm'; t.appendChild(tm); }
    if (!b) { b = document.createElement('button'); b.type = 'button'; t.appendChild(b); }
    function draw() {
      tm.textContent = fmt(left);
      b.textContent = h ? 'עצירה' : (left === total ? 'הפעלה' : (left === 0 ? 'שוב' : 'המשך'));
      t.classList.toggle('done', left === 0);
    }
    function toggle() {
      if (h) { clearInterval(h); h = null; draw(); return; }
      if (left === 0) left = total;
      h = setInterval(function () { left = Math.max(0, left - 1); if (!left) { clearInterval(h); h = null; } draw(); }, 1000);
      draw();
    }
    b.addEventListener('click', function (e) { e.stopPropagation(); toggle(); });
    t._toggle = toggle;
    draw();
  }

  function decorate(root) {
    root = root || document;
    root.querySelectorAll('.hero-art:empty').forEach(function (n) { n.innerHTML = HERO; });
    root.querySelectorAll('.timer[data-sec]').forEach(wire);
  }

  window.LessonTheme = {
    decorate: decorate,
    toggle: function (t) { if (t) { wire(t); t._toggle(); } }
  };
  if (document.readyState !== 'loading') decorate(); else document.addEventListener('DOMContentLoaded', function () { decorate(); });
})();
