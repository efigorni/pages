const CLUB = {
  confetti: ['#ffffff', '#86d094', '#007638', '#4aa45b', '#ffffff'],
  fonts: [['800 40px Heebo', 'אבג'], ['700 40px Heebo', '0123456789()']],

  // The card face, a pocket version of the club's /players card: the photo, the faded number and the
  // two-tier name (a small first name over a big surname). The engine calls prepare(players) once
  // fonts are in, apply(style, cw, ch, mode) per board size, build(p) per card and fit(cardEl, p, geo)
  // per card and size.
  face(kit) {
    'use strict';

    const { photoFront, el, splits, renderName, setVars } = kit;
    const FIRST_FONT = '400 100px Heebo';
    const LAST_FONT = '800 100px Heebo';
    const LAST_TRACK = -0.04;
    const FIRST_LH = 1.04;
    const LAST_LH = 0.94;
    const FIRST_RATIO = 0.62;
    const digitEm = { value: 0.57 };

    // Each tier: one line, plus the most balanced two-line split when there are several words.
    function prepare(players) {
      digitEm.value = kit.digitEm('700 100px Heebo', 0.57);
      players.forEach((p) => {
        p.firstSplits = splits(p.first_he, FIRST_FONT, 0);
        p.lastSplits = splits(p.last_he || p.name_he, LAST_FONT, LAST_TRACK);
      });
    }

    // The photo is a square head-and-shoulders cutout, nudged toward the end side (left in RTL)
    // so the number gets the top start corner, as on the club's cards. Type always clears the
    // found frame, whose glyph ink would otherwise overhang under it.
    function faceVars(cw, ch, mode) {
      const twoDigits = digitEm.value * 2.04;
      const frame = Math.max(3, Math.min(cw, ch) * 0.045);
      const edge = frame + 3;
      if (mode === 'side') {
        const pad = Math.max(edge, ch * 0.065);
        const s = ch * 0.94;
        const x = -s * 0.1;
        const col = cw - (x + s * 0.74) - pad;
        const num = Math.min(ch * 0.42, col / twoDigits);
        return {
          s, x, pad, frame, num, numTop: pad * 0.55,
          last: Math.min(ch * 0.21, num * 0.62), nameW: Math.max(col, cw * 0.4), nameH: ch * 0.44, nameB: pad * 0.8, fade: 0.6,
        };
      }
      if (mode === 'band') {
        const pad = Math.max(edge, cw * 0.065);
        const s = cw * 1.02;
        const x = -cw * 0.16;
        const num = Math.min(cw * 0.35, ch * 0.28);
        return {
          s, x, pad, frame, num, numTop: pad * 0.55,
          last: Math.min(cw * 0.2, ch * 0.16), nameW: cw - pad * 2, nameH: ch * 0.36, nameB: pad * 0.8, fade: 0.56,
        };
      }
      const pad = Math.max(edge, cw * 0.06);
      const s = cw * 1.1;
      const x = -cw * 0.12;
      const num = Math.min(cw * 0.36, ((cw - pad * 2) / twoDigits) * 0.8);
      return {
        s, x, pad, frame, num, numTop: pad * 0.5,
        last: cw * 0.22, nameW: cw - pad * 2, nameH: ch * 0.36, nameB: pad, fade: 0.5,
      };
    }

    function apply(s, cw, ch, mode) {
      const v = faceVars(cw, ch, mode);
      setVars(s, {
        '--frame': `${v.frame}px`, '--photo-s': `${v.s}px`, '--photo-x': `${v.x}px`, '--ipad': `${v.pad}px`,
        '--num-fs': `${v.num}px`, '--num-top': `${v.numTop}px`, '--name-w': `${v.nameW}px`, '--name-b': `${v.nameB}px`,
        '--fade-h': `${v.fade * 100}%`,
      });
      return v;
    }

    // Tries one or two lines per tier and keeps the biggest surname; an extra line has to buy
    // more than 4% of size.
    function fit(cardEl, p, geo) {
      if (!p.lastSplits || !p.lastSplits.length) return;
      const v = geo.v;
      const firsts = p.firstSplits.length ? p.firstSplits : [null];
      let best = null;
      firsts.forEach((f) => p.lastSplits.forEach((l) => {
        let last = Math.min(v.last, v.nameW / l.em);
        let first = f ? Math.min(v.last * FIRST_RATIO, last * 0.8, v.nameW / f.em) : 0;
        const height = (f ? f.lines.length * first * FIRST_LH : 0) + l.lines.length * last * LAST_LH;
        const k = Math.min(1, v.nameH / height);
        last *= k;
        first *= k;
        const lines = (f ? f.lines.length : 0) + l.lines.length;
        const score = last + first * 0.4;
        if (!best || score > best.score * 1.04 || (score >= best.score && lines <= best.lines)) {
          best = { f, l, first, last, lines, score };
        }
      }));
      renderName(cardEl, { first: best.f ? best.f.lines : [], last: best.l.lines });
      cardEl.style.setProperty('--first-px', `${best.first.toFixed(2)}px`);
      cardEl.style.setProperty('--last-px', `${best.last.toFixed(2)}px`);
    }

    function build(p) {
      const front = photoFront(p);
      front.append(el('span', 'num', String(p.number)), el('span', 'name'));
      const first = p.firstSplits && p.firstSplits[0];
      const last = p.lastSplits && p.lastSplits[0];
      renderName(front, { first: first ? first.lines : [], last: last ? last.lines : [p.name_he] });
      return front;
    }

    return { prepare, apply, build, fit };
  },
};
