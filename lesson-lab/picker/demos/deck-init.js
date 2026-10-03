/* אתחול משותף לדמואים של העזר החזותי.
   ?thumb=1&slide=N — תמונה ממוזערת סטטית של שקף N (בלי חיצים, מקלדת או מספור), לתצוגה מקדימה בפיקר. */
(function () {
  var q = new URLSearchParams(location.search);
  var thumb = q.get('thumb') === '1';
  var cfg = { width: 1440, height: 810, margin: 0.04, center: false, rtl: true, hash: false, controls: true, progress: true, slideNumber: 'c/t', transition: 'slide', transitionSpeed: 'fast' };
  if (thumb) { cfg.controls = false; cfg.progress = false; cfg.slideNumber = false; cfg.keyboard = false; cfg.touch = false; cfg.transition = 'none'; cfg.margin = 0; }
  Reveal.initialize(cfg).then(function () {
    if (q.get('slide')) Reveal.slide(+q.get('slide'));
    if (window.LessonTheme) window.LessonTheme.decorate(document);
  });
})();
