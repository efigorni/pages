/* deck.js — אתחול המצגת (reveal.js 5).
   ?print-pdf — תצוגת הדפסה ל-PDF (עמוד לכל שקף, כל החשיפות גלויות).
   ?thumb=1&slide=N — תמונה ממוזערת סטטית של שקף N (בלי חיצים, מקלדת או מספור).
   T — מפעיל / עוצר את הטיימר של השקף הנוכחי. */
(function () {
  'use strict';
  var q = new URLSearchParams(location.search);
  var thumb = q.get('thumb') === '1';
  var print = /print-pdf/i.test(location.search);
  var phone = window.matchMedia('(max-width: 435px)');
  var RevealDeck = window.Reveal;
  var sections = Array.from(document.querySelectorAll('.reveal .slides > section'));
  var deck = null, reading = false, initializing = false, scrollFrame = 0;

  function toggleTimer() {
    var cur = deck && deck.getCurrentSlide();
    var t = cur && cur.querySelector('.timer[data-sec]');
    if (t && window.LessonTheme) window.LessonTheme.toggle(t);
  }

  var cfg = {
    width: 1440, height: 810, margin: 0.04, center: false, rtl: true,
    hash: true, controls: true, progress: true,
    slideNumber: 'c', showSlideNumber: 'all',
    transition: 'slide', transitionSpeed: 'fast',
    scrollActivationWidth: null,
    pdfSeparateFragments: false, pdfMaxPagesPerSlide: 1,
    keyboard: { 84: toggleTimer }
  };
  if (print) cfg.margin = 0;  // PDF page = exactly 1440×810
  if (thumb) {
    cfg.controls = false; cfg.progress = false; cfg.slideNumber = false;
    cfg.keyboard = false; cfg.touch = false; cfg.transition = 'none'; cfg.margin = 0; cfg.hash = false;
  }

  function hashIndex() {
    var match = location.hash.match(/^#\/(\d+)/);
    return Math.min(match ? +match[1] : 0, sections.length - 1);
  }

  function remember(index) {
    // Keep fragment deep links while reading the same slide; scrolling replaces only the current entry.
    if (index !== hashIndex()) history.replaceState(null, '', '#/' + index);
  }

  function visibleIndex() {
    var index = 0;
    sections.forEach(function (section, i) {
      if (section.getBoundingClientRect().top <= innerHeight / 4) index = i;
    });
    return index;
  }

  function followHash() {
    if (reading && sections[hashIndex()]) sections[hashIndex()].scrollIntoView({ block: 'start' });
  }

  function onScroll() {
    if (!reading || scrollFrame) return;
    scrollFrame = requestAnimationFrame(function () {
      scrollFrame = 0;
      if (reading) remember(visibleIndex());
    });
  }

  function wantsReading() { return phone.matches && !thumb && !print; }

  function setMode() {
    // Let Reveal finish before destroying it: its async startup also mutates the DOM.
    if (initializing) return;
    if (wantsReading()) {
      if (reading) return;
      if (deck) {
        remember(deck.getIndices().h);
        deck.destroy();
        deck = null;
      }
      reading = true;
      document.documentElement.classList.add('lesson-reading');
      if (window.LessonTheme) window.LessonTheme.decorate(document);
      followHash();
    } else if (!deck) {
      if (reading) remember(visibleIndex());
      reading = false;
      document.documentElement.classList.remove('lesson-reading');
      window.scrollTo(0, 0);
      deck = new RevealDeck(document.querySelector('.reveal'));
      window.Reveal = deck;
      initializing = true;
      deck.initialize(cfg).then(function () {
        initializing = false;
        if (thumb && q.get('slide')) deck.slide(+q.get('slide'));
        if (window.LessonTheme) window.LessonTheme.decorate(document);
        setMode();
      });
    }
  }

  if (!thumb && !print) {
    phone.addEventListener('change', setMode);
    window.addEventListener('hashchange', followHash);
    window.addEventListener('scroll', onScroll, { passive: true });
  }
  setMode();
  // Font loading can move the target after an initial phone deep link.
  if (document.fonts) document.fonts.ready.then(followHash);
})();
