const CLUB = {
  confetti: ['#f8d734', '#ffffff', '#2f6fdb', '#ffe680', '#f8d734'],
  fonts: [['700 40px Karantina', 'אבג'], ['800 40px "Barlow Condensed"', '0123456789']],

  // The card face, a pocket version of the club's player page: the photo, then the number and a
  // one-tier name. The engine calls prepare(players) once fonts are in, apply(style, cw, ch, mode)
  // per board size, build(p) per card and fit(cardEl, p, geo) per card and size.
  face(kit) {
    'use strict';

    const { el, textEm, words, bestSplit, photoFront } = kit;
    const NAME_FONT = '700 100px Karantina';
    const NAME_LINE_HEIGHT = 0.84;
    const digitEm = { value: 0.46 };

    function prepare(players) {
      digitEm.value = textEm('0123456789', '800 100px "Barlow Condensed"') / 10 || 0.46;
      players.forEach((p) => {
        const list = words(p.name_he);
        const whole = bestSplit(list, 1, NAME_FONT);
        p.split2 = (list.length > 1 && bestSplit(list, 2, NAME_FONT)) || whole;
        p.split3 = list.length >= 3 ? bestSplit(list, 3, NAME_FONT) : null;
      });
    }

    function faceVars(cw, ch, mode) {
      if (mode === 'side') {
        const photoW = Math.min(ch * 0.84, cw * 0.6);
        const pad = Math.max(3, ch * 0.07);
        const infoW = cw - photoW - pad * 1.4;
        const num = Math.min(ch * 0.46, infoW / (digitEm.value * 2.1));
        return { photoW, photoH: ch, pad, num, name: Math.min(ch * 0.2, num * 0.55), nameW: infoW };
      }
      if (mode === 'band') {
        const photoH = ch * 0.63;
        const band = ch - photoH;
        const pad = Math.max(3, cw * 0.06);
        const num = Math.min(band * 0.9, cw * 0.42);
        return { photoW: cw, photoH, pad, num, name: Math.min(band * 0.38, num * 0.5), nameW: 0, zoom: 1.04 };
      }
      const photoH = ch * 0.56;
      const rest = ch - photoH;
      const pad = Math.max(2, cw * 0.06);
      const num = Math.min(rest * 0.46, (cw - pad * 2) / (digitEm.value * 2.1));
      return { photoW: cw, photoH, pad, num, name: rest * 0.21, nameW: cw - pad * 2 };
    }

    function apply(s, cw, ch, mode) {
      const v = faceVars(cw, ch, mode);
      s.setProperty('--photo-w', `${v.photoW}px`);
      s.setProperty('--photo-h', `${v.photoH}px`);
      s.setProperty('--ipad', `${v.pad}px`);
      s.setProperty('--num-fs', `${v.num}px`);
      s.setProperty('--name-fs', `${v.name}px`);
      s.setProperty('--zoom', String(v.zoom || 1));
      return v;
    }

    function nameBox(geo, p) {
      const { v, mode, cw, ch } = geo;
      if (mode === 'side') return { w: v.nameW, h: ch - v.pad * 2.7 - v.num * 0.78 };
      if (mode === 'band') {
        const numW = String(p.number).length * digitEm.value * v.num;
        return { w: cw - numW - v.pad * 3, h: (ch - v.photoH) * 0.92 };
      }
      return { w: v.nameW, h: ch - v.photoH - v.num * 0.78 - v.pad * 1.2 };
    }

    function nameSize(split, box, base) {
      return Math.min(base, box.w / split.em, box.h / (split.lines.length * NAME_LINE_HEIGHT));
    }

    function renderName(cardEl, lines) {
      const name = cardEl.querySelector('.name');
      const key = lines.join('|');
      if (name.dataset.lines === key) return;
      name.dataset.lines = key;
      name.textContent = '';
      lines.forEach((line) => name.appendChild(el('span', null, line)));
    }

    function fit(cardEl, p, geo) {
      if (!p.split2) return;
      const box = nameBox(geo, p);
      const base = geo.v.name;
      let split = p.split2;
      let size = nameSize(split, box, base);
      if (p.split3) {
        const size3 = nameSize(p.split3, box, base);
        if (size3 > size * 1.04) {
          split = p.split3;
          size = size3;
        }
      }
      renderName(cardEl, split.lines);
      cardEl.style.setProperty('--fit', Math.max(0.4, size / base).toFixed(3));
    }

    function build(p) {
      const front = photoFront(p);
      const info = el('span', 'info');
      info.append(el('span', 'num', String(p.number)), el('span', 'name'));
      front.appendChild(info);
      renderName(front, p.split2 ? p.split2.lines : [p.name_he]);
      return front;
    }

    return { prepare, apply, build, fit };
  },
};
