const CLUB = {
  confetti: ['#f8d734', '#ffffff', '#2f6fdb', '#ffe680', '#f8d734'],
  fonts: [['700 40px Karantina', 'אבג'], ['800 40px "Barlow Condensed"', '0123456789']],

  // The card face, a pocket version of the club's player page: the photo, then the number and a
  // one-tier name. The engine calls prepare(players) once fonts are in, apply(style, cw, ch, mode)
  // per board size, build(p) per card and fit(cardEl, p, geo) per card and size.
  face(kit) {
    'use strict';

    const { el, photoFront, splits, fitLines, renderName, setVars } = kit;
    const NAME_FONT = '700 100px Karantina';
    const NAME_LINE_HEIGHT = 0.84;
    const digitEm = { value: 0.46 };

    // Two lines (one for a single word), or three when that sets the name bigger.
    function prepare(players) {
      digitEm.value = kit.digitEm('800 100px "Barlow Condensed"', 0.46);
      players.forEach((p) => {
        const all = splits(p.name_he, NAME_FONT, 0, 3);
        p.split2 = all.find((s) => s.lines.length === 2) || all[0];
        p.split3 = all.find((s) => s.lines.length === 3) || null;
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
      setVars(s, {
        '--photo-w': `${v.photoW}px`, '--photo-h': `${v.photoH}px`, '--ipad': `${v.pad}px`,
        '--num-fs': `${v.num}px`, '--name-fs': `${v.name}px`, '--zoom': String(v.zoom || 1),
      });
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

    function fit(cardEl, p, geo) {
      if (!p.split2) return;
      const box = nameBox(geo, p);
      const base = geo.v.name;
      const best = fitLines([p.split2, p.split3].filter(Boolean), { cap: base, w: box.w, h: box.h, lh: NAME_LINE_HEIGHT });
      renderName(cardEl, best.split.lines);
      cardEl.style.setProperty('--fit', Math.max(0.4, best.size / base).toFixed(3));
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
