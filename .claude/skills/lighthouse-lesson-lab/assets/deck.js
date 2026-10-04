/* deck.js — אתחול המצגת (reveal.js 5).
   ?print-pdf — תצוגת הדפסה ל-PDF (עמוד לכל שקף, כל החשיפות גלויות).
   ?thumb=1&slide=N — תמונה ממוזערת סטטית של שקף N (בלי חיצים, מקלדת או מספור).
   T — מפעיל / עוצר את הטיימר של השקף הנוכחי. */
(function () {
  'use strict';
  var q = new URLSearchParams(location.search);
  var thumb = q.get('thumb') === '1';

  function toggleTimer() {
    var cur = Reveal.getCurrentSlide();
    var t = cur && cur.querySelector('.timer[data-sec]');
    if (t && window.LessonTheme) window.LessonTheme.toggle(t);
  }

  var cfg = {
    width: 1440, height: 810, margin: 0.04, center: false, rtl: true,
    hash: true, controls: true, progress: true,
    slideNumber: 'c', showSlideNumber: 'all',
    transition: 'slide', transitionSpeed: 'fast',
    pdfSeparateFragments: false, pdfMaxPagesPerSlide: 1,
    keyboard: { 84: toggleTimer }
  };
  if (/print-pdf/i.test(location.search)) cfg.margin = 0;  // PDF page = exactly 1440×810
  if (thumb) {
    cfg.controls = false; cfg.progress = false; cfg.slideNumber = false;
    cfg.keyboard = false; cfg.touch = false; cfg.transition = 'none'; cfg.margin = 0; cfg.hash = false;
  }
  Reveal.initialize(cfg).then(function () {
    if (thumb && q.get('slide')) Reveal.slide(+q.get('slide'));
    if (window.LessonTheme) window.LessonTheme.decorate(document);
  });
})();
