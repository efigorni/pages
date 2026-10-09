// _memory-game/engine.js, shared by the memory games: build_page.py assemble stamps it into the
// engine script of each game's page. Edit it there, not in a page. The page's DATA and CLUB come first.
(() => {
  'use strict';

  // The quiz asks every player once, in roster order: the starters, the bench and the backups (the
  // pool's other goalkeepers, whom the memory game never deals).
  const QUIZ = DATA.players;
  const STARTERS = QUIZ.filter((p) => p.role === 'starter');
  const BENCH = QUIZ.filter((p) => p.role === 'bench');
  const ALL = STARTERS.concat(BENCH);
  const CHOICES = 4;
  const ADVANCE_MS = 1500;
  const TAP_ADVANCE_MS = 700;
  // A wrong pick's clip waits for the soft sound and for the card to turn over (base.css: .3 s + flip).
  const NOPE_SAY_MS = 650;
  const PAIRS = 15;
  const FLIP_MS = 460;
  const MISMATCH_MS = 2200;
  const DEAL_STAGGER_MS = 16;
  const START_LINE = 'יאללה, בואי נשחק!';
  const WIN_LINE = 'כל הכבוד! מצאת את כל השחקנים!';

  const $ = (id) => document.getElementById(id);
  const app = $('app');
  const board = $('board');
  const pipsEl = $('pips');
  const picksEl = $('picks');
  const questionEl = $('question');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const landscapeQuery = matchMedia('(orientation: landscape)');

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function shuffled(list) {
    const a = list.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  /* ---------- Hebrew numbers, feminine counting form ("מספר ארבעים ושתיים") ---------- */

  const UNITS = ['', 'אחת', 'שתיים', 'שלוש', 'ארבע', 'חמש', 'שש', 'שבע', 'שמונה', 'תשע'];
  const TEENS = ['עשר', 'אחת עשרה', 'שתים עשרה', 'שלוש עשרה', 'ארבע עשרה', 'חמש עשרה', 'שש עשרה', 'שבע עשרה', 'שמונה עשרה', 'תשע עשרה'];
  const TENS = ['', '', 'עשרים', 'שלושים', 'ארבעים', 'חמישים', 'שישים', 'שבעים', 'שמונים', 'תשעים'];

  function hebrewNumber(n) {
    if (n === 0) return 'אפס';
    if (n < 10) return UNITS[n];
    if (n < 20) return TEENS[n - 10];
    if (n < 100) {
      const unit = n % 10;
      return TENS[(n - unit) / 10] + (unit ? ' ו' + UNITS[unit] : '');
    }
    return String(n);
  }

  /* ---------- clips ---------- */

  const AUDIO = DATA.audio || {};
  const recorded = {
    ui: new Set(AUDIO.ui || []),
    name: new Set(AUDIO.name || []),
    match: new Set(AUDIO.match || []),
  };

  // The card shows name_he; the voice says speak_he when the roster has one (a trailing nickname in
  // parentheses), else name_he.
  const spoken = (p) => p.speak_he || p.name_he;
  const clip = {
    name: (p) => ({ url: recorded.name.has(p.id) ? `audio/name/${p.id}.mp3` : null, text: spoken(p) }),
    match: (p) => ({
      url: recorded.match.has(p.id) ? `audio/match/${p.id}.mp3` : null,
      text: `מספר ${hebrewNumber(p.number)}, ${spoken(p)}!`,
    }),
    ui: (key, text) => ({ url: recorded.ui.has(key) ? `audio/ui/${key}.mp3` : null, text }),
  };

  /* ---------- audio: Web Audio buffers → HTMLAudio → speechSynthesis (he-IL) ---------- */

  const sound = (() => {
    const canFetch = location.protocol === 'http:' || location.protocol === 'https:';
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const synth = 'speechSynthesis' in window ? window.speechSynthesis : null;
    const raw = new Map();
    const decoded = new Map();
    const elements = new Map();
    let ctx = null;
    let voiceBus = null;
    let sfxBus = null;
    // Never persisted: one stray tap must not silence every later launch.
    let muted = false;
    let token = 0;
    let stopCurrent = null;
    let hebrewVoice = null;
    let lastCancel = 0;

    function pickVoice() {
      if (!synth) return;
      const voices = synth.getVoices();
      hebrewVoice = voices.find((v) => /^(he|iw)([-_]|$)/i.test(v.lang)) || null;
    }
    if (synth) {
      pickVoice();
      if (synth.addEventListener) synth.addEventListener('voiceschanged', pickVoice);
    }

    function prefetch(urls) {
      urls.forEach((url) => {
        if (!url) return;
        if (!canFetch) {
          if (!elements.has(url)) {
            const audio = new Audio();
            audio.preload = 'auto';
            audio.src = url;
            elements.set(url, audio);
          }
          return;
        }
        fetchRaw(url);
        if (ctx) decode(url);
      });
    }

    // A clip whose fetch or decode failed is forgotten, so the next request for it tries again.
    function forget(url) {
      raw.delete(url);
      decoded.delete(url);
    }

    function fetchRaw(url) {
      if (!raw.has(url)) {
        raw.set(url, fetch(url)
          .then((r) => (r.ok ? r.arrayBuffer() : null))
          .catch(() => null)
          .then((buf) => {
            if (!buf) forget(url);
            return buf;
          }));
      }
      return raw.get(url);
    }

    function decode(url) {
      if (!decoded.has(url)) {
        decoded.set(url, fetchRaw(url).then((buf) => buf && new Promise((resolve) => {
          const done = (buffer) => {
            if (!buffer) forget(url);
            resolve(buffer || null);
          };
          const pending = ctx.decodeAudioData(buf, done, () => done(null));
          if (pending && pending.catch) pending.catch(() => {});
        })));
      }
      return decoded.get(url);
    }

    function running() {
      return !!ctx && ctx.state === 'running';
    }

    // Resumes a context the system suspended (screen lock, audio focus loss). Never creates one:
    // that needs the ▶ tap.
    function wake() {
      if (ctx && ctx.state !== 'running' && ctx.state !== 'closed') ctx.resume().catch(() => {});
    }

    function unlock() {
      if (!ctx && AudioCtx) {
        try {
          ctx = new AudioCtx();
          voiceBus = ctx.createGain();
          voiceBus.connect(ctx.destination);
          sfxBus = ctx.createGain();
          sfxBus.gain.value = 0.28;
          sfxBus.connect(ctx.destination);
          const blip = ctx.createBufferSource();
          blip.buffer = ctx.createBuffer(1, 1, 22050);
          blip.connect(ctx.destination);
          blip.start(0);
          raw.forEach((_, url) => decode(url));
        } catch (e) {
          ctx = null;
        }
      }
      wake();
      if (!hebrewVoice) pickVoice();
    }

    function halt() {
      token++;
      const stop = stopCurrent;
      stopCurrent = null;
      if (stop) stop();
      if (synth && (synth.speaking || synth.pending)) {
        synth.cancel();
        lastCancel = performance.now();
      }
    }

    function speak(text, my) {
      return new Promise((done) => {
        if (!synth || !hebrewVoice || !text || muted || my !== token) return done();
        let over = false;
        let guard = 0;
        const finish = () => {
          if (over) return;
          over = true;
          clearTimeout(guard);
          if (stopCurrent === finish) stopCurrent = null;
          done();
        };
        const utter = new SpeechSynthesisUtterance(text);
        utter.voice = hebrewVoice;
        utter.lang = hebrewVoice.lang;
        utter.rate = 0.92;
        utter.onend = finish;
        utter.onerror = finish;
        stopCurrent = finish;
        guard = setTimeout(finish, 2500 + text.length * 180);
        // Chrome drops an utterance queued in the same tick as cancel().
        const wait = Math.max(0, 80 - (performance.now() - lastCancel));
        setTimeout(() => { if (!over && my === token) synth.speak(utter); }, wait);
      });
    }

    function viaElement(item, my) {
      return new Promise((done) => {
        if (!elements.has(item.url)) {
          const fresh = new Audio(item.url);
          fresh.preload = 'auto';
          elements.set(item.url, fresh);
        }
        const audio = elements.get(item.url);
        let over = false;
        const finish = (ok) => {
          if (over) return;
          over = true;
          audio.removeEventListener('ended', onEnded);
          audio.removeEventListener('error', onError);
          if (stopCurrent === stop) stopCurrent = null;
          if (ok || my !== token) done();
          else speak(item.text, my).then(done);
        };
        const onEnded = () => finish(true);
        const onError = () => finish(false);
        const stop = () => { audio.pause(); finish(true); };
        audio.addEventListener('ended', onEnded);
        audio.addEventListener('error', onError);
        stopCurrent = stop;
        try { audio.currentTime = 0; } catch (e) { /* not seekable yet */ }
        const playing = audio.play();
        if (playing && playing.catch) playing.catch(() => finish(false));
      });
    }

    function viaBuffer(item, my) {
      return decode(item.url).then((buffer) => {
        if (my !== token) return undefined;
        if (!buffer || !running()) return viaElement(item, my);
        return new Promise((done) => {
          const src = ctx.createBufferSource();
          let over = false;
          const finish = () => {
            if (over) return;
            over = true;
            if (stopCurrent === stop) stopCurrent = null;
            done();
          };
          const stop = () => { try { src.stop(); } catch (e) { /* already stopped */ } finish(); };
          src.buffer = buffer;
          src.connect(voiceBus);
          src.onended = finish;
          stopCurrent = stop;
          src.start();
        });
      });
    }

    function playItem(item, my) {
      if (muted || my !== token) return Promise.resolve();
      // { wait: ms } is a beat of silence; a newer say() or halt() during it drops the rest.
      if (item.wait) return new Promise((done) => setTimeout(done, item.wait));
      if (!item.url) return speak(item.text, my);
      // A suspended or interrupted context would swallow the clip and never fire 'ended'.
      if (canFetch && running()) return viaBuffer(item, my);
      return viaElement(item, my);
    }

    async function say(items) {
      halt();
      const my = token;
      for (const item of items) {
        if (my !== token) return;
        if (item.onstart) item.onstart();
        await playItem(item, my);
      }
    }

    function tone(type, f0, f1, at, dur, peak) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(f0, at);
      if (f1 !== f0) osc.frequency.exponentialRampToValueAtTime(f1, at + dur);
      gain.gain.setValueAtTime(0.0001, at);
      gain.gain.exponentialRampToValueAtTime(peak, at + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, at + dur);
      osc.connect(gain);
      gain.connect(sfxBus);
      osc.start(at);
      osc.stop(at + dur + 0.05);
    }

    function sfx(kind) {
      if (muted || !ctx || ctx.state !== 'running') return;
      const t = ctx.currentTime + 0.01;
      if (kind === 'flip') {
        tone('sine', 420, 880, t, 0.1, 0.55);
      } else if (kind === 'match') {
        [1046.5, 1318.5, 1568].forEach((f, i) => tone('triangle', f, f, t + i * 0.08, 0.45, 0.5));
      } else if (kind === 'nope') {
        tone('sine', 330, 262, t, 0.16, 0.4);
        tone('sine', 262, 220, t + 0.15, 0.24, 0.34);
      } else if (kind === 'win') {
        const notes = [523.25, 659.25, 783.99, 1046.5];
        notes.forEach((f, i) => tone('triangle', f, f, t + i * 0.12, 0.28, 0.55));
        notes.forEach((f) => tone('triangle', f, f, t + 0.5, 1.3, 0.3));
      }
    }

    function setMuted(value) {
      muted = value;
      if (value) halt();
    }

    return { unlock, wake, prefetch, say, halt, sfx, setMuted, get muted() { return muted; } };
  })();

  /* ---------- names: the kit a club's card face measures and splits them with ---------- */

  const KEEP_WITH_NEXT = new Set(['בן', 'בר', 'אבו', 'אל', 'דה', 'די', 'דוס', 'ואן', 'פון']);
  let measurer = null;

  // `track` is CSS letter-spacing in em, which canvas measurement leaves out.
  function textEm(text, font, track) {
    measurer = measurer || document.createElement('canvas').getContext('2d');
    measurer.font = font;
    return measurer.measureText(text).width / 100 + (track || 0) * [...text].length;
  }

  // A parenthetical is one unbreakable word, so "(אבו פאני)" never splits across lines.
  function words(text) {
    return String(text || '').match(/\([^)]*\)|\S+/g) || [];
  }

  function partitions(list, count) {
    if (count === 1) return [[list.join(' ')]];
    const out = [];
    for (let i = 1; i <= list.length - count + 1; i++) {
      if (KEEP_WITH_NEXT.has(list[i - 1])) continue;
      const head = list.slice(0, i).join(' ');
      partitions(list.slice(i), count - 1).forEach((rest) => out.push([head].concat(rest)));
    }
    return out;
  }

  // The split into `count` lines whose widest line is the narrowest; null when no split is allowed.
  function bestSplit(list, count, font, track) {
    let best = null;
    partitions(list, count).forEach((lines) => {
      const em = Math.max(...lines.map((line) => textEm(line, font, track)));
      if (!best || em < best.em) best = { lines, em };
    });
    return best;
  }

  // The one-line split, then the best split into 2..max lines; a count no split allows is left out.
  function splits(text, font, track, max = 2) {
    const list = words(text);
    const out = [];
    for (let n = 1; n <= Math.min(max, list.length); n++) {
      const split = bestSplit(list, n, font, track);
      if (split) out.push(split);
    }
    return out;
  }

  // The candidate split that sets the name biggest in a w x h box, at most cap; a later candidate
  // has to buy more than 4% of size.
  function fitLines(candidates, { cap, w, h, lh }) {
    let best = null;
    candidates.forEach((split) => {
      const size = Math.min(cap, w / split.em, h / (split.lines.length * lh));
      if (!best || size > best.size * 1.04) best = { split, size };
    });
    return best;
  }

  // The name element's lines: one tier (an array of lines), or {first, last} tiers, each a span of
  // line spans. data-lines keeps a resize from rebuilding an unchanged name.
  function renderName(scope, lines) {
    const name = scope.querySelector('.name');
    const tiers = Array.isArray(lines) ? null : lines;
    const key = tiers ? `${tiers.first.join('|')}/${tiers.last.join('|')}` : lines.join('|');
    if (name.dataset.lines === key) return;
    name.dataset.lines = key;
    name.textContent = '';
    const fill = (parent, list) => list.forEach((line) => parent.appendChild(el('span', null, line)));
    if (!tiers) {
      fill(name, lines);
      return;
    }
    if (tiers.first.length) {
      const top = el('span', 'first');
      fill(top, tiers.first);
      name.appendChild(top);
    }
    const big = el('span', 'last');
    fill(big, tiers.last);
    name.appendChild(big);
  }

  function setVars(style, vars) {
    Object.entries(vars).forEach(([key, value]) => style.setProperty(key, value));
  }

  // The width of one digit of `font`, in em.
  function digitEm(font, fallback) {
    return textEm('0123456789', font) / 10 || fallback;
  }

  /* ---------- card face: CLUB.face draws it, the engine sizes it ---------- */

  function photoImg(p) {
    return Object.assign(el('img'), { src: p.img, alt: '', decoding: 'async', draggable: false });
  }

  // Every face starts with the photo; a match flight starts from its `.photo img`.
  function photoFront(p) {
    const front = el('span', 'face front');
    const photo = el('span', 'photo');
    photo.appendChild(photoImg(p));
    front.appendChild(photo);
    return front;
  }

  const face = CLUB.face({
    el, textEm, words, bestSplit, photoFront, splits, fitLines, renderName, setVars, digitEm,
  });

  function faceMode(cw, ch) {
    const ratio = cw / ch;
    if (ratio >= 1.1) return 'side';
    return ratio < 0.7 ? 'stack' : 'band';
  }

  function applyFace(target, cw, ch, mode) {
    const s = target.style;
    target.dataset.face = mode;
    s.setProperty('--cw', `${cw}px`);
    s.setProperty('--ch', `${ch}px`);
    return { cw, ch, mode, v: face.apply(s, cw, ch, mode) };
  }

  /* ---------- DOM ---------- */

  // `back` is the side that shows first: the card back, or a quiz card's photo-only side.
  function buildCard(p, index, tag, back) {
    const card = el(tag || 'button', 'card');
    if (!tag) {
      card.type = 'button';
      card.setAttribute('aria-label', 'קלף');
    }
    card.dataset.id = p.id;
    card.dataset.index = String(index);
    card.dataset.state = 'down';
    card.style.setProperty('--i', String(index));
    const inner = el('span', 'card-inner');
    inner.append(back || el('span', 'face back'), face.build(p));
    card.appendChild(inner);
    return card;
  }

  // A quiz card asks with the photo alone: no name, no number.
  function askFace(p) {
    const side = el('span', 'face ask');
    side.appendChild(photoImg(p));
    return side;
  }

  /* ---------- game state ---------- */

  const game = {
    phase: 'start',
    round: 0,
    cards: [],
    total: 0, // finds that win: the memory game's pairs, or the quiz's players
    up: [],
    found: 0,
    flipBack: 0,
    winFallback: 0,
    winEarliest: 0,
    busyUntil: 0,
    flights: new Set(),
  };

  function setPhase(phase) {
    game.phase = phase;
    app.dataset.phase = phase;
  }

  function setCard(card, state) {
    card.state = state;
    card.el.dataset.state = state;
    card.el.setAttribute('aria-label', state === 'down' ? 'קלף' : card.p.name_he);
  }

  // A grid's cell for the [cols, rows] shape that shows the faces biggest, from the grid's own box
  // and gaps; null while the grid isn't shown.
  function cell(grid, shapes) {
    const rect = grid.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    const cs = getComputedStyle(grid);
    const gx = parseFloat(cs.columnGap) || 0;
    const gy = parseFloat(cs.rowGap) || 0;
    return shapes.map(([cols, rows]) => ({
      cols, cw: (rect.width - gx * (cols - 1)) / cols, ch: (rect.height - gy * (rows - 1)) / rows,
    })).reduce((a, b) => (Math.min(b.cw, b.ch) > Math.min(a.cw, a.ch) ? b : a));
  }

  function fitCards(grid, cards, { cw, ch }) {
    const geo = applyFace(grid, cw, ch, faceMode(cw, ch));
    cards.forEach((card) => face.fit(card.el, card.p, geo));
  }

  function layout() {
    const c = cell(board, [landscapeQuery.matches ? [6, 5] : [5, 6]]);
    if (c) fitCards(board, game.cards, c);
  }

  function warmImages(players) {
    players.forEach((p) => {
      const img = new Image();
      img.decoding = 'async';
      img.src = p.img;
      if (img.decode) img.decode().catch(() => {});
    });
  }

  // What every new game, of either mode, starts from: `total` finds to win, one pip each.
  function reset(mode, total) {
    clearTimeout(game.flipBack);
    clearTimeout(game.winFallback);
    clearTimeout(quiz.next);
    game.round += 1;
    game.flights.forEach((flight) => flight.cancel());
    game.flights.clear();
    confetti.stop();
    OVERLAYS.forEach(hide);
    app.dataset.mode = mode;
    game.total = total;
    game.found = 0;
    app.dataset.found = '0';
    pipsEl.textContent = '';
    for (let i = 0; i < total; i++) pipsEl.appendChild(el('span', 'pip'));
  }

  function newGame() {
    const benchPicks = shuffled(BENCH).slice(0, Math.max(0, PAIRS - STARTERS.length));
    const picks = STARTERS.concat(benchPicks);
    const deck = shuffled(picks.concat(picks));

    reset('memory', picks.length);
    game.up = [];
    board.textContent = '';
    game.cards = deck.map((p, i) => {
      const card = { p, el: buildCard(p, i), state: 'down' };
      board.appendChild(card.el);
      return card;
    });
    layout();
    warmImages(picks);
    sound.prefetch(picks.flatMap((p) => [clip.name(p).url, clip.match(p).url]).concat(clip.ui('win').url));

    if (!reducedMotion.matches) {
      const round = game.round;
      const dealMs = 520 + deck.length * DEAL_STAGGER_MS;
      board.classList.add('dealing');
      game.busyUntil = performance.now() + dealMs * 0.6;
      setTimeout(() => { if (game.round === round) board.classList.remove('dealing'); }, dealMs);
    }
    setPhase('idle');
    keepAwake();
  }

  function lift(card) {
    if (reducedMotion.matches || !card.el.animate) return;
    card.lift = card.el.animate([
      { transform: 'scale(1)', zIndex: 3 },
      { transform: 'scale(1.09)', zIndex: 3, offset: 0.45 },
      { transform: 'scale(1)', zIndex: 3 },
    ], { duration: FLIP_MS, easing: 'ease-out' });
  }

  // A card shows its face: memory's flip and the quiz's picks. A face that turns up lifts; a wrong pick
  // ('out') shakes instead (base.css), so it never moves like a right one.
  function turn(card, state, sfx = 'flip') {
    setCard(card, state);
    if (state !== 'out') lift(card);
    sound.sfx(sfx);
  }

  // A find of either mode: the count, then its pip and celebration once the flip lands; true for the
  // last one.
  function scored(cards) {
    game.found += 1;
    app.dataset.found = String(game.found);
    const pipIndex = game.found - 1;
    const round = game.round;
    setTimeout(() => { if (game.round === round) celebrate(cards, pipIndex); }, FLIP_MS * 0.85);
    return game.found === game.total;
  }

  function tap(card) {
    if (game.phase !== 'idle' && game.phase !== 'one' && game.phase !== 'two') return;
    if (card.state !== 'down' || performance.now() < game.busyUntil) return;
    sound.unlock();

    if (game.up.length === 2) {
      clearTimeout(game.flipBack);
      game.up.forEach((c) => setCard(c, 'down'));
      game.up = [];
    }

    turn(card, 'up');
    game.up.push(card);

    if (game.up.length === 1) {
      setPhase('one');
      sound.say([clip.name(card.p)]);
      return;
    }

    const [a, b] = game.up;
    if (a.p.id !== b.p.id) {
      setPhase('two');
      sound.say([clip.name(card.p)]);
      game.flipBack = setTimeout(() => {
        game.up.forEach((c) => setCard(c, 'down'));
        game.up = [];
        setPhase('idle');
      }, MISMATCH_MS);
      return;
    }

    game.up = [];
    setCard(a, 'matched');
    setCard(b, 'matched');
    const lines = [clip.name(card.p), clip.match(card.p)];
    if (scored([a, b])) finishing(lines);
    else setPhase('idle');
    sound.say(lines);
  }

  // The last find of either mode: the win clip follows `lines`, and the win screen comes when it
  // starts (at least 1.5 s on), or after a fallback when the voice never gets there.
  function finishing(lines) {
    setPhase('finishing');
    const round = game.round;
    game.winEarliest = performance.now() + 1500;
    const finish = () => { if (game.round === round) showWin(); };
    const win = clip.ui('win', WIN_LINE);
    win.onstart = () => setTimeout(finish, Math.max(0, game.winEarliest - performance.now()));
    lines.push(win);
    game.winFallback = setTimeout(finish, sound.muted ? 1500 : 9000);
  }

  // When the voice queue is cut while finishing (mute, page hidden), the win clip never starts,
  // so bring the win screen forward instead of waiting for the long fallback.
  function hurryWin() {
    if (game.phase !== 'finishing') return;
    clearTimeout(game.winFallback);
    const round = game.round;
    game.winFallback = setTimeout(() => { if (game.round === round) showWin(); },
      Math.max(0, game.winEarliest - performance.now()));
  }

  function celebrate(cards, pipIndex) {
    cards.forEach((card) => {
      if (card.lift) card.lift.cancel();
      card.el.classList.add('found');
      if (!reducedMotion.matches) {
        const burst = el('span', 'burst');
        card.el.appendChild(burst);
        setTimeout(() => burst.remove(), 800);
      }
    });
    sound.sfx('match');
    flyToPip(cards[0], pipIndex);
  }

  function flyToPip(card, index) {
    const pip = pipsEl.children[index];
    if (!pip) return;
    const fill = () => {
      pip.textContent = '';
      const img = el('img');
      img.src = card.p.img;
      img.alt = '';
      pip.appendChild(img);
      pip.classList.add('full');
    };
    const photo = card.el.querySelector('.photo');
    const pic = photo && photo.querySelector('img');
    if (reducedMotion.matches || !pic || !document.body.animate) return fill();

    // Centred on the photo itself, which a face may place off the middle of its .photo box.
    const from = photo.getBoundingClientRect();
    const shot = pic.getBoundingClientRect();
    const to = pip.getBoundingClientRect();
    const size = Math.min(from.width, from.height);
    const x0 = shot.left + (shot.width - size) / 2;
    const y0 = from.top;
    const flyer = el('span', 'flyer');
    const img = el('img');
    img.src = card.p.img;
    img.alt = '';
    flyer.appendChild(img);
    flyer.style.width = `${size}px`;
    flyer.style.height = `${size}px`;
    flyer.style.left = `${x0}px`;
    flyer.style.top = `${y0}px`;
    document.body.appendChild(flyer);

    const dx = to.left + to.width / 2 - (x0 + size / 2);
    const dy = to.top + to.height / 2 - (y0 + size / 2);
    const end = to.width / size;
    const anim = flyer.animate([
      { transform: 'translate(0, 0) scale(1)' },
      { transform: `translate(${dx * 0.4}px, ${dy * 0.4 - size * 0.35}px) scale(${Math.max(end, 0.75)})`, offset: 0.45 },
      { transform: `translate(${dx}px, ${dy}px) scale(${end})` },
    ], { duration: 720, easing: 'cubic-bezier(.45, 0, .3, 1)' });
    const flight = {
      cancel() {
        anim.onfinish = null;
        anim.cancel();
        flyer.remove();
      },
    };
    game.flights.add(flight);
    anim.onfinish = () => {
      game.flights.delete(flight);
      flyer.remove();
      fill();
    };
  }

  /* ---------- quiz: who is this? ---------- */

  const quiz = { order: [], at: 0, cards: [], answer: null, next: 0, shownAt: 0 };

  // 2 x 2, or one row of 4 when that shows the faces bigger (a wide landscape screen).
  function quizLayout() {
    const c = cell(picksEl, [[2, 2], [4, 1]]);
    if (!c) return;
    picksEl.style.setProperty('--cols', String(c.cols));
    fitCards(picksEl, quiz.cards, c);
  }

  function startQuiz() {
    reset('quiz', QUIZ.length);
    quiz.order = shuffled(QUIZ);
    quiz.at = 0;
    warmImages(QUIZ);
    deal();
    // The first question's clips first: its match line, the other three cards' (a wrong pick says one)
    // and its name; then everyone's, in question order.
    const first = [quiz.answer].concat(quiz.cards.filter((card) => card !== quiz.answer)).map((card) => card.p);
    sound.prefetch(first.map((p) => clip.match(p).url).concat(clip.name(first[0]).url,
      quiz.order.flatMap((p) => [clip.match(p).url, clip.name(p).url]), clip.ui('win').url));
    keepAwake();
  }

  // The asked player and three others from the quiz roster, shuffled.
  function deal() {
    const p = quiz.order[quiz.at];
    const others = shuffled(QUIZ.filter((q) => q !== p)).slice(0, CHOICES - 1);
    picksEl.textContent = '';
    picksEl.classList.remove('solved');
    quiz.cards = shuffled(others.concat(p)).map((q, i) => {
      const card = { p: q, el: buildCard(q, i, null, askFace(q)), state: 'down' };
      card.el.setAttribute('aria-label', 'שחקן');
      picksEl.appendChild(card.el);
      return card;
    });
    quiz.answer = quiz.cards.find((card) => card.p === p);
    picksEl.dataset.answer = p.id;
    questionEl.textContent = '';
    questionEl.append(el('span', null, 'מי זה מספר '), el('span', 'qnum', String(p.number)), el('span', null, `, ${spoken(p)}?`));
    quizLayout();
    // A tap that moved on to this question must not also pick on it.
    game.busyUntil = performance.now() + 450;
    if (!reducedMotion.matches) {
      const round = game.round;
      const at = quiz.at;
      picksEl.classList.add('dealing');
      setTimeout(() => { if (game.round === round && quiz.at === at) picksEl.classList.remove('dealing'); }, 900);
    }
    setPhase('ask');
  }

  // The question out loud is the asked player's match clip: "number N, <name>!".
  function question() {
    return [clip.match(quiz.answer.p)];
  }

  function pick(card) {
    if (game.phase !== 'ask' || card.state !== 'down' || performance.now() < game.busyUntil) return;
    sound.unlock();
    if (card !== quiz.answer) {
      // Not him, and she learns who it is: the soft sound and a shake, then the card turns over (greyed
      // and marked, out of play) and says his number and name. Her next pick or #say cuts that off.
      turn(card, 'out', 'nope');
      sound.say([{ wait: NOPE_SAY_MS }, clip.match(card.p)]);
      return;
    }
    turn(card, 'up');
    picksEl.classList.add('solved');
    quiz.shownAt = performance.now();
    const lines = [clip.name(card.p)];
    if (scored([card])) {
      finishing(lines);
      sound.say(lines);
      return;
    }
    setPhase('reveal');
    // On after the name clip, or after a fallback when the voice never ends.
    const round = game.round;
    const at = quiz.at;
    advance(8000);
    sound.say(lines).then(() => { if (game.round === round && quiz.at === at) advance(ADVANCE_MS); });
  }

  // The reveal moves on by itself `ms` from now, but not under the ↻ confirm or on a hidden page: closing
  // the one or coming back to the other arms it again.
  function advance(ms) {
    clearTimeout(quiz.next);
    if (game.phase !== 'reveal' || isShown('confirm') || document.visibilityState !== 'visible') return;
    quiz.next = setTimeout(nextQuestion, ms);
  }

  function nextQuestion() {
    clearTimeout(quiz.next);
    if (game.phase !== 'reveal') return;
    quiz.at += 1;
    deal();
    sound.say(question());
  }

  function showWin() {
    if (game.phase === 'won') return;
    clearTimeout(game.winFallback);
    setPhase('won');
    letSleep();
    show('win');
    sound.sfx('win');
    if (!reducedMotion.matches) {
      confetti.burst(150);
      setTimeout(() => { if (game.phase === 'won') confetti.burst(90); }, 1300);
    }
  }

  /* ---------- overlays ---------- */

  const OVERLAYS = ['start', 'confirm', 'win'];

  function isShown(id) {
    return $(id).classList.contains('show');
  }

  function syncInert() {
    app.inert = OVERLAYS.some(isShown);
  }

  function show(id) {
    const node = $(id);
    node.inert = false;
    node.classList.add('show');
    syncInert();
  }

  function hide(id) {
    const node = $(id);
    if (node.contains(document.activeElement)) document.activeElement.blur();
    node.classList.remove('show');
    node.inert = true;
    syncInert();
  }

  /* ---------- confetti (canvas at CSS-pixel resolution keeps it cheap) ---------- */

  const confetti = (() => {
    const canvas = $('confetti');
    const g = canvas.getContext('2d');
    const colors = CLUB.confetti;
    let parts = [];
    let frame = 0;
    let last = 0;

    function resize() {
      canvas.width = Math.round(window.innerWidth);
      canvas.height = Math.round(window.innerHeight);
    }

    function burst(count) {
      if (!frame) resize();
      const w = canvas.width;
      const h = canvas.height;
      for (let i = 0; i < count; i++) {
        parts.push({
          x: Math.random() * w,
          y: -20 - Math.random() * h * 0.6,
          vx: (Math.random() - 0.5) * 60,
          vy: 120 + Math.random() * 160,
          spin: Math.random() * Math.PI * 2,
          vspin: (Math.random() - 0.5) * 9,
          tilt: Math.random() * Math.PI * 2,
          vtilt: 4 + Math.random() * 6,
          size: 7 + Math.random() * 7,
          color: colors[i % colors.length],
        });
      }
      if (!frame) {
        last = performance.now();
        frame = requestAnimationFrame(tick);
      }
    }

    function tick(now) {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (canvas.width !== Math.round(window.innerWidth) || canvas.height !== Math.round(window.innerHeight)) resize();
      const h = canvas.height;
      g.clearRect(0, 0, canvas.width, h);
      parts = parts.filter((p) => p.y < h + 30);
      for (const p of parts) {
        p.vy = Math.min(p.vy + 140 * dt, 320);
        p.x += (p.vx + Math.sin(p.tilt) * 40) * dt;
        p.y += p.vy * dt;
        p.spin += p.vspin * dt;
        p.tilt += p.vtilt * dt;
        g.save();
        g.translate(p.x, p.y);
        g.rotate(p.spin);
        g.scale(1, Math.cos(p.tilt));
        g.fillStyle = p.color;
        g.fillRect(-p.size / 2, -p.size / 3, p.size, p.size * 0.66);
        g.restore();
      }
      frame = parts.length ? requestAnimationFrame(tick) : 0;
      if (!frame) g.clearRect(0, 0, canvas.width, h);
    }

    function stop() {
      parts = [];
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      g.clearRect(0, 0, canvas.width, canvas.height);
    }

    return { burst, stop };
  })();

  /* ---------- start screen ---------- */

  let fanStar = null;

  function buildFan() {
    const fan = $('fan');
    const short = Math.min(window.innerWidth, window.innerHeight);
    const landscape = landscapeQuery.matches;
    const cw = Math.max(84, Math.min(230, short * (landscape ? 0.36 : 0.34), window.innerHeight * (landscape ? 0.42 : 0.24)));
    const ch = cw * 1.28;
    const geo = applyFace(fan, cw, ch, 'band');
    const pool = STARTERS.length ? STARTERS : ALL;
    if (!pool.length) return;
    fanStar = fanStar || pool[Math.floor(Math.random() * pool.length)];
    const star = fanStar;
    fan.textContent = '';
    [star, star, star].forEach((p, i) => {
      const card = buildCard(p, i, 'span');
      if (i === 1) card.dataset.state = 'up';
      face.fit(card, p, geo);
      fan.appendChild(card);
    });
  }

  let wakeLock = null;
  let wakePending = false;

  function inGame() {
    return game.phase !== 'start' && game.phase !== 'won';
  }

  function letSleep() {
    const lock = wakeLock;
    wakeLock = null;
    if (lock) lock.release().catch(() => {});
  }

  async function keepAwake() {
    if (!('wakeLock' in navigator) || wakeLock || wakePending || document.visibilityState !== 'visible') return;
    wakePending = true;
    try {
      const lock = await navigator.wakeLock.request('screen');
      lock.addEventListener('release', () => { if (wakeLock === lock) wakeLock = null; });
      wakeLock = lock;
      if (!inGame()) letSleep();
    } catch (e) {
      wakeLock = null;
    } finally {
      wakePending = false;
    }
  }

  const installedQuery = matchMedia('(display-mode: fullscreen), (display-mode: standalone)');

  function goFullscreen() {
    if (!matchMedia('(pointer: coarse)').matches || document.fullscreenElement || installedQuery.matches) return;
    const root = document.documentElement;
    const request = root.requestFullscreen || root.webkitRequestFullscreen;
    if (!request) return;
    try {
      const pending = request.call(root, { navigationUI: 'hide' });
      if (pending && pending.catch) pending.catch(() => {});
    } catch (e) { /* fullscreen refused */ }
  }

  /* ---------- wiring ---------- */

  // A grid's cards answer the first touch (pointerdown) and a keyboard press (a click with no pointer).
  function onCard(grid, cards, fn) {
    const handle = (event) => {
      const node = event.target.closest && event.target.closest('.card');
      fn(node && node.parentElement === grid ? cards()[Number(node.dataset.index)] : null);
    };
    grid.addEventListener('pointerdown', (event) => { if (event.button <= 0) handle(event); });
    grid.addEventListener('click', (event) => { if (event.detail === 0) handle(event); });
  }

  onCard(board, () => game.cards, (card) => { if (card) tap(card); });
  // A tap on a quiz card picks it; once the face shows, a tap anywhere on the cards moves on.
  onCard(picksEl, () => quiz.cards, (card) => {
    if (game.phase === 'reveal') {
      if (performance.now() - quiz.shownAt >= TAP_ADVANCE_MS) nextQuestion();
    } else if (card) pick(card);
  });

  $('say').addEventListener('click', () => {
    if (game.phase !== 'ask') return;
    sound.unlock();
    sound.say(question());
  });

  // A newer service worker took over this open page, and its cache only holds the files of its own
  // roster, so a new game starts from a reloaded page rather than from this page's DATA.
  let stale = false;

  function reloadIfStale() {
    if (stale) location.reload();
    return stale;
  }

  // Every new game starts from one of the two mode buttons: on the start screen, on the win screen
  // and in the ↻ confirm. A quiz opens with its first question right after the start line.
  function wireModes(ids, allowed, before) {
    ids.forEach((id) => $(id).addEventListener('click', () => {
      if (!allowed() || reloadIfStale()) return;
      sound.unlock();
      if (before) before();
      const start = clip.ui('start', START_LINE);
      if (id.endsWith('-quiz')) {
        startQuiz();
        sound.say([start].concat(question()));
      } else {
        newGame();
        sound.say([start]);
      }
    }));
  }

  wireModes(['play', 'play-quiz'], () => game.phase === 'start', goFullscreen);
  wireModes(['replay', 'replay-quiz'], () => game.phase === 'won');
  wireModes(['yes', 'yes-quiz'], () => true);

  // A quiz reveal waits under the confirm: "no" picks it up again, a mode button starts afresh.
  $('again').addEventListener('click', () => {
    if (!inGame() || game.phase === 'finishing') return;
    clearTimeout(quiz.next);
    show('confirm');
  });

  $('no').addEventListener('click', () => {
    hide('confirm');
    advance(ADVANCE_MS);
  });

  const muteBtn = $('mute');
  function syncMute() { muteBtn.setAttribute('aria-pressed', sound.muted ? 'true' : 'false'); }
  muteBtn.addEventListener('click', () => {
    sound.unlock();
    sound.setMuted(!sound.muted);
    syncMute();
    if (sound.muted) hurryWin();
  });
  syncMute();
  syncInert();

  document.addEventListener('contextmenu', (event) => event.preventDefault());
  document.addEventListener('gesturestart', (event) => event.preventDefault());
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') {
      letSleep();
      clearTimeout(quiz.next); // a reveal waits for her: the halted name clip must not move it on
      sound.halt();
      hurryWin();
    } else {
      sound.wake();
      if (inGame()) keepAwake();
      advance(ADVANCE_MS);
    }
  });
  window.addEventListener('pageshow', () => sound.wake());
  // Some browsers (iOS Safari) resume audio only inside a real gesture event, not on pointerdown.
  ['touchend', 'click'].forEach((type) => {
    document.addEventListener(type, () => sound.wake(), { capture: true, passive: true });
  });

  // Only the shown grid has a box; the other's layout returns at once.
  const relayout = () => { layout(); quizLayout(); };
  if (window.ResizeObserver) [board, picksEl].forEach((grid) => new ResizeObserver(relayout).observe(grid));
  else window.addEventListener('resize', relayout);
  window.addEventListener('resize', () => { if (game.phase === 'start') buildFan(); });

  sound.prefetch([clip.ui('start').url]);
  face.prepare(QUIZ);
  buildFan();
  const fontsReady = document.fonts && document.fonts.load
    ? Promise.all(CLUB.fonts.map(([spec, sample]) => document.fonts.load(spec, sample)))
    : Promise.resolve();
  fontsReady.catch(() => {}).then(() => {
    face.prepare(QUIZ);
    buildFan();
    relayout();
  });

  /* ---------- home-screen install (parent-facing, start screen only) ---------- */

  const installBtn = $('install');
  let installPrompt = null;

  function syncInstall() {
    installBtn.hidden = !installPrompt || installedQuery.matches;
  }

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    installPrompt = event;
    syncInstall();
  });
  window.addEventListener('appinstalled', () => {
    installPrompt = null;
    syncInstall();
  });
  installBtn.addEventListener('click', () => {
    const pending = installPrompt;
    installPrompt = null;
    syncInstall();
    if (pending) pending.prompt().catch(() => {});
  });

  const secure = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  if ('serviceWorker' in navigator && secure) {
    // A first install also takes over the page, but that page came from the network and is current.
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.addEventListener('controllerchange', () => { stale = true; });
    }
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => {});
    });
  }
})();
