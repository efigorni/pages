const CLUB = {
  confetti: ['#ff1521', '#ffffff', '#ffb5ba', '#ff5a64', '#ffffff'],
  fonts: [['600 40px Rubik', 'אבג'], ['700 40px Karantina', 'אבג'], ['700 40px Karantina', '0123456789']],

  // The card face, the site's player card in a pocket: a cutout on the wall paint, the big white
  // number beside it and the name under the picture. The engine calls prepare(players) once fonts
  // are in, apply(style, cw, ch, mode) per board size, build(p) per card and fit(cardEl, p, geo) per
  // card and size.
  face(kit) {
    'use strict';

    const { el, photoFront, splits, fitLines, renderName, setVars } = kit;
    const NAME_FONT = '600 100px Rubik';
    const NAME_LH = 1.04;
    const digitEm = { value: 0.3 };

    // One line, plus a two-line split when the name allows one ("בר כהן" doesn't).
    function prepare(players) {
      digitEm.value = kit.digitEm('700 100px Karantina', 0.3);
      players.forEach((p) => {
        p.nameSplits = splits(p.name_he, NAME_FONT);
      });
    }

    // The name band is the card's bottom strip; the photo stands on it, shifted to the end side
    // (left in RTL), and the number fills the strip the photo leaves at the top start corner.
    function faceVars(cw, ch, mode) {
      const short = Math.min(cw, ch);
      const frame = Math.max(3, short * 0.045);
      const pad = Math.max(frame + 2, short * 0.06);
      const band = ch * (mode === 'side' ? 0.24 : 0.2);
      const pic = ch - band;
      const s = mode === 'side' ? pic * 1.1 : Math.min(cw * 1.02, pic * 1.06);
      const x = mode === 'side' ? -s * 0.04 : -cw * 0.22;
      const panelW = mode === 'side' ? cw - (x + s * 0.72) : cw * 0.47;
      const num = Math.min(pic * 0.66, (panelW - frame * 2) / (digitEm.value * 2.06));
      return {
        frame, pad, band, s, x, y: pic - s * 0.98, panelW, num, numTop: frame + pic * 0.04,
        nameW: cw - pad * 2, nameH: band * 0.86,
      };
    }

    function apply(st, cw, ch, mode) {
      const v = faceVars(cw, ch, mode);
      setVars(st, {
        '--frame': `${v.frame}px`, '--band-h': `${v.band}px`, '--photo-s': `${v.s}px`, '--photo-x': `${v.x}px`,
        '--photo-y': `${v.y}px`, '--panel-w': `${v.panelW}px`, '--num-fs': `${v.num}px`, '--num-top': `${v.numTop}px`,
      });
      return v;
    }

    // One line or two, whichever sets the name bigger; the second line has to buy more than 4%.
    function fit(cardEl, p, geo) {
      if (!p.nameSplits) return;
      const v = geo.v;
      const best = fitLines(p.nameSplits, { cap: v.band * 0.5, w: v.nameW, h: v.nameH, lh: NAME_LH });
      renderName(cardEl, best.split.lines);
      cardEl.style.setProperty('--name-px', `${best.size.toFixed(2)}px`);
    }

    function build(p) {
      const front = photoFront(p);
      front.append(el('span', 'num', String(p.number)), el('span', 'name'));
      renderName(front, p.nameSplits ? p.nameSplits[0].lines : [p.name_he]);
      return front;
    }

    return { prepare, apply, build, fit };
  },
};
