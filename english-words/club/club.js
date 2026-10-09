const CLUB = {
  confetti: ['#ffc532', '#2f6fe4', '#ff5a4e', '#22a95f', '#ffffff'],
  fonts: [['700 40px Andika', 'Aa'], ['600 40px Fredoka', 'אבג']],

  // The card face, a picture-word card: the picture big, the English word under it, the Hebrew word
  // small. The engine calls prepare(words) once fonts are in, apply(style, cw, ch, mode) per board size,
  // build(p) per card and fit(cardEl, p, geo) per card and size.
  face(kit) {
    'use strict';

    const { el, photoFront, setVars, splits, fitLines, textEm } = kit;
    const EN_FONT = '700 100px Andika';
    const HE_FONT = '600 100px Fredoka';
    const EN_LINE = 1.02;
    const hebrew = (p) => p.he_niqqud || p.he;

    // Each word's widths at 100 px: the English on one line, or two ("ice cream"); the Hebrew on one.
    function prepare(words) {
      words.forEach((p) => {
        p.enSplits = splits(p.en, EN_FONT, 0, 2);
        p.heEm = textEm(hebrew(p), HE_FONT);
      });
    }

    // The picture's box, the padding, the two words' biggest sizes, and the room the English has.
    function faceVars(cw, ch, mode) {
      if (mode === 'side') {
        const picW = Math.min(ch * 0.95, cw * 0.52);
        const pad = Math.max(3, ch * 0.08);
        return { picW, picH: ch, pad, en: ch * 0.3, he: ch * 0.15, textW: cw - picW - pad * 1.5, enH: ch * 0.55 };
      }
      const picH = ch * (mode === 'stack' ? 0.56 : 0.6);
      const pad = Math.max(3, cw * 0.07);
      const rest = ch - picH - pad;
      return { picW: cw, picH, pad, en: rest * 0.5, he: rest * 0.27, textW: cw - pad * 2, enH: rest * 0.62 };
    }

    function apply(s, cw, ch, mode) {
      const v = faceVars(cw, ch, mode);
      setVars(s, {
        '--pic-w': `${v.picW}px`, '--pic-h': `${v.picH}px`, '--wpad': `${v.pad}px`,
        '--en-fs': `${v.en}px`, '--he-fs': `${v.he}px`,
      });
      return v;
    }

    function renderEnglish(cardEl, lines) {
      const en = cardEl.querySelector('.en');
      const key = lines.join('|');
      if (en.dataset.lines === key) return;
      en.dataset.lines = key;
      en.textContent = '';
      lines.forEach((line) => en.appendChild(el('span', null, line)));
    }

    // The English on the line count that sets it biggest within its room; the Hebrew shrinks to the
    // card's width; a short word keeps its full size.
    function fit(cardEl, p, geo) {
      if (!p.enSplits) return;
      const { v } = geo;
      const best = fitLines(p.enSplits, { cap: v.en, w: v.textW, h: v.enH, lh: EN_LINE });
      renderEnglish(cardEl, best.split.lines);
      cardEl.style.setProperty('--en-fit', (best.size / v.en).toFixed(3));
      cardEl.style.setProperty('--he-fit', Math.min(1, v.textW / (p.heEm * v.he)).toFixed(3));
    }

    function build(p) {
      const front = photoFront(p);
      const words = el('span', 'words');
      const en = Object.assign(el('span', 'en'), { lang: 'en', dir: 'ltr' });
      en.appendChild(el('span', null, p.en));
      words.append(en, el('span', 'he', hebrew(p)));
      front.appendChild(words);
      return front;
    }

    return { prepare, apply, build, fit };
  },
};
