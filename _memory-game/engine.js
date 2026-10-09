// _memory-game/engine.js, shared by the memory games: build_page.py assemble stamps it into the
// engine script of each game's page. Edit it there, not in a page. The page's DATA and CLUB come first.
(() => {
  'use strict';

  // What the game teaches, in teaching order: a squad's players (the starters, the bench and the
  // backups, the pool's other goalkeepers whom memory never deals) or a list of words. PLAY is the
  // game's own script, from club.json `play`: what each moment says, how memory deals, what the quiz
  // asks, the progress bar and what the worker keeps offline (README, "Play config").
  const ITEMS = DATA.words || DATA.players;
  const PLAY = DATA.play;
  const STARTERS = ITEMS.filter((p) => p.role === 'starter');
  const BENCH = ITEMS.filter((p) => p.role === 'bench');
  const ALL = STARTERS.concat(BENCH);
  // Whom the start screen's fan (and the link preview) shows: a starter, or one of the first words.
  const POSTER = STARTERS.length ? STARTERS : DATA.words ? ITEMS.slice(0, PLAY.deal.pairs) : ALL;
  const CHOICES = 4;
  const ADVANCE_MS = 1500;
  const TAP_ADVANCE_MS = 700;
  // A wrong pick's clip waits for the soft sound and for the card to turn over (base.css: .3 s + flip).
  const NOPE_SAY_MS = 650;
  const FLIP_MS = 460;
  const MISMATCH_MS = 2200;
  const DEAL_STAGGER_MS = 16;
  const START_LINE = 'יאללה, בואי נשחק!';
  const WIN_LINE = 'כל הכבוד! מצאת את כל השחקנים!';
  // The engine's own lines, which a game may say in its own words (club.json `lines`, with its own clip):
  // what the speech fallback says when the clip can't play.
  const UI_LINES = { start: START_LINE, win: WIN_LINE, ...DATA.lines };

  const $ = (id) => document.getElementById(id);
  const app = $('app');
  const board = $('board');
  const pipsEl = $('pips');
  const picksEl = $('picks');
  const questionEl = $('question');
  const shelfEl = $('shelf');
  const slotEl = $('flash-slot');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const landscapeQuery = matchMedia('(orientation: landscape)');
  const canFetch = location.protocol === 'http:' || location.protocol === 'https:';

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

  // DATA.audio lists, per kind, the ids whose clip ships under audio/<kind>/.
  const recorded = Object.fromEntries(Object.entries(DATA.audio || {}).map(([kind, ids]) => [kind, new Set(ids)]));
  const ships = (kind, id) => !!recorded[kind] && recorded[kind].has(id);

  // The card shows name_he; the voice says speak_he when the roster has one (a trailing nickname in
  // parentheses), else name_he.
  const spoken = (p) => p.speak_he || p.name_he;
  // Every kind of clip a game records, with what the speech fallback says instead: a player's name and
  // his "number N, <name>!", a word in English and in Hebrew.
  const LINES = {
    name: (p) => ({ text: spoken(p) }),
    match: (p) => ({ text: `מספר ${hebrewNumber(p.number)}, ${spoken(p)}!` }),
    en: (p) => ({ text: p.en, lang: 'en' }),
    he: (p) => ({ text: p.he }),
  };
  const clip = Object.fromEntries(Object.entries(LINES).map(([kind, line]) => [kind,
    (p) => ({ url: ships(kind, p.id) ? `audio/${kind}/${p.id}.mp3` : null, ...line(p) })]));
  clip.ui = (key, text) => ({ url: ships('ui', key) ? `audio/ui/${key}.mp3` : null, text });

  // The game's voice script (PLAY.voice): the clips each moment says, in order. flip and match are
  // memory's, ask, wrong and right the quiz's, card a flash card's.
  const voice = (moment, p) => PLAY.voice[moment].map((kind) => clip[kind](p));
  // The files of the clips those moments say, each once.
  const clipUrls = (p, moments) => [...new Set(moments.flatMap((m) => PLAY.voice[m]))].map((kind) => clip[kind](p).url);

  // How the engine names an item: a player by his name, a word in English and Hebrew. A squad's quiz
  // asks "who is number N, <name>?"; a word game's asks with the English word alone.
  const MODEL = DATA.words ? {
    noun: 'תמונה',
    label: (p) => `${p.en}, ${p.he}`,
    question: (p) => [Object.assign(el('span', 'qword', p.en), { lang: 'en', dir: 'ltr' })],
    chip: () => null,
  } : {
    noun: 'שחקן',
    label: (p) => p.name_he,
    question: (p) => [el('span', null, 'מי זה מספר '), el('span', 'qnum', String(p.number)), el('span', null, `, ${spoken(p)}?`)],
    chip: (p) => String(p.number),
  };

  /* ---------- audio: Web Audio buffers → HTMLAudio → speechSynthesis (he-IL, en-US) ---------- */

  const sound = (() => {
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
    // The speech fallback's voice per language: a line is Hebrew unless it says `lang: 'en'`.
    let voices = { he: null, en: null };
    let lastCancel = 0;

    function pickVoice() {
      if (!synth) return;
      const all = synth.getVoices();
      voices = {
        he: all.find((v) => /^(he|iw)([-_]|$)/i.test(v.lang)) || null,
        en: all.find((v) => /^en[-_]US/i.test(v.lang)) || all.find((v) => /^en([-_]|$)/i.test(v.lang)) || null,
      };
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
      if (!voices.he || !voices.en) pickVoice();
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

    function speak(item, my) {
      const { text } = item;
      const english = item.lang === 'en';
      const v = english ? voices.en : voices.he;
      return new Promise((done) => {
        if (!synth || !v || !text || muted || my !== token) return done();
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
        utter.voice = v;
        utter.lang = v.lang;
        utter.rate = english ? 0.8 : 0.92;
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
          else speak(item, my).then(done);
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
      if (!item.url) return speak(item, my);
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
      } else if (kind === 'hint') {
        // a locked button: two soft steps up, "over there"
        tone('sine', 523.25, 587.33, t, 0.13, 0.3);
        tone('sine', 659.25, 783.99, t + 0.14, 0.2, 0.26);
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

  /* ---------- what she has learned: a match in memory, or a flash card she looked at ---------- */

  // Kept per game on this device. The games share one origin, so the key carries the game's folder;
  // private mode or blocked storage keeps it for this visit only.
  const learned = (() => {
    const key = `${DATA.game}:learned`;
    let store = null;
    try { store = window.localStorage; } catch (e) { /* storage blocked */ }
    let saved = [];
    try { saved = JSON.parse((store && store.getItem(key)) || '[]'); } catch (e) { /* unreadable */ }
    const ids = new Set(Array.isArray(saved) ? saved.filter((id) => typeof id === 'string') : []);
    return {
      has: (id) => ids.has(id),
      // true when it is new
      add(id) {
        if (ids.has(id)) return false;
        ids.add(id);
        try { if (store) store.setItem(key, JSON.stringify([...ids])); } catch (e) { /* full or blocked */ }
        return true;
      },
      // the game's learned items, in teaching order (an id from an older list counts no more)
      items: () => ITEMS.filter((p) => ids.has(p.id)),
    };
  })();

  const progressEl = $('progress');
  const QUIZ_BUTTONS = ['play-quiz', 'yes-quiz', 'replay-quiz'];

  // A word game asks only what she has learned, so its quiz waits for PLAY.quiz.unlock words.
  function quizLocked() {
    return PLAY.quiz.pool === 'learned' && learned.items().length < PLAY.quiz.unlock;
  }

  // "learned X / N": the bar a word game shows on every screen (PLAY.progress "bar"), the shelf's count,
  // and the quiz buttons' lock.
  function syncLearned() {
    const done = learned.items().length;
    const count = `${done} / ${ITEMS.length}`;
    $('progress-count').textContent = count;
    $('shelf-count').textContent = count;
    progressEl.style.setProperty('--done', String(ITEMS.length ? done / ITEMS.length : 0));
    progressEl.setAttribute('aria-valuenow', String(done));
    progressEl.setAttribute('aria-valuemax', String(ITEMS.length));
    $('next-new').dataset.done = String(done === ITEMS.length);
    const locked = String(quizLocked());
    QUIZ_BUTTONS.forEach((id) => {
      $(id).dataset.locked = locked;
      $(id).setAttribute('aria-disabled', locked);
    });
  }

  function markLearned(p) {
    if (!learned.add(p.id)) return;
    syncLearned();
    const tile = shelf.tiles.get(p.id);
    if (tile) tile.dataset.learned = 'true';
    if (!reducedMotion.matches && PLAY.progress === 'bar') {
      progressEl.classList.remove('gained');
      void progressEl.offsetWidth; // restart the pop
      progressEl.classList.add('gained');
    }
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
    card.el.setAttribute('aria-label', state === 'down' ? 'קלף' : MODEL.label(card.p));
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
    shelf.card = null;
    slotEl.textContent = '';
    app.dataset.mode = mode;
    game.total = total;
    game.found = 0;
    app.dataset.found = '0';
    pipsEl.textContent = '';
    for (let i = 0; i < total; i++) pipsEl.appendChild(el('span', 'pip'));
  }

  // The items memory deals (PLAY.deal): a squad's starters and a random few of the bench; a word game's
  // next new words in teaching order (at most `new` of them) and a random review of learned ones, with
  // more new words while too few are learned.
  function dealPicks() {
    const { policy, pairs } = PLAY.deal;
    if (policy === 'squad') return STARTERS.concat(shuffled(BENCH).slice(0, Math.max(0, pairs - STARTERS.length)));
    const fresh = ITEMS.filter((p) => !learned.has(p.id));
    const review = shuffled(learned.items()).slice(0, pairs - Math.min(PLAY.deal.new, fresh.length));
    return fresh.slice(0, pairs - review.length).concat(review);
  }

  function newGame() {
    const picks = dealPicks();
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
    sound.prefetch(picks.flatMap((p) => clipUrls(p, ['flip', 'match'])).concat(clip.ui('win').url));
    fetchAhead(upcoming(picks));

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
      sound.say(voice('flip', card.p));
      return;
    }

    const [a, b] = game.up;
    if (a.p.id !== b.p.id) {
      setPhase('two');
      sound.say(voice('flip', card.p));
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
    markLearned(card.p);
    const lines = voice('match', card.p);
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
    const win = clip.ui('win', UI_LINES.win);
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

  // The questions (PLAY.quiz): a squad's every player once, the backups too; a word game's up to `size`
  // random learned words.
  function startQuiz() {
    quiz.order = PLAY.quiz.pool === 'learned' ? shuffled(learned.items()).slice(0, PLAY.quiz.size) : shuffled(ITEMS);
    reset('quiz', quiz.order.length);
    quiz.at = 0;
    warmImages(quiz.order);
    deal();
    // The first question's clips first: its question, the other three cards' (a wrong pick says them)
    // and its answer's; then everyone's, in question order.
    const [p, ...others] = [quiz.answer].concat(quiz.cards.filter((card) => card !== quiz.answer)).map((card) => card.p);
    sound.prefetch(clipUrls(p, ['ask']).concat(others.flatMap((q) => clipUrls(q, ['wrong'])), clipUrls(p, ['right']),
      quiz.order.flatMap((q) => clipUrls(q, ['ask', 'right'])), clip.ui('win').url));
    keepAwake();
  }

  // Three others to pick from: a squad's whole roster; a word game's learned words (while fewer than
  // four are learned, the next words in teaching order fill in). Never one PLAY.quiz.apart pairs with the
  // asked one: two pictures that look alike at a glance.
  function distractors(p) {
    const fits = (q) => q !== p && !(PLAY.quiz.apart || []).some((pair) => pair.includes(p.id) && pair.includes(q.id));
    let pool = ITEMS.filter(fits);
    if (PLAY.quiz.pool === 'learned') {
      const known = learned.items().filter(fits);
      pool = known.length >= CHOICES - 1 ? known : known.concat(pool.filter((q) => !learned.has(q.id)).slice(0, CHOICES));
    }
    return shuffled(pool).slice(0, CHOICES - 1);
  }

  // The asked item and three others, shuffled.
  function deal() {
    const p = quiz.order[quiz.at];
    const others = distractors(p);
    picksEl.textContent = '';
    picksEl.classList.remove('solved');
    quiz.cards = shuffled(others.concat(p)).map((q, i) => {
      const card = { p: q, el: buildCard(q, i, null, askFace(q)), state: 'down' };
      card.el.setAttribute('aria-label', MODEL.noun);
      picksEl.appendChild(card.el);
      return card;
    });
    quiz.answer = quiz.cards.find((card) => card.p === p);
    picksEl.dataset.answer = p.id;
    questionEl.textContent = '';
    questionEl.append(...MODEL.question(p));
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

  // The question out loud (PLAY.voice.ask): a player's "number N, <name>!", a word in English alone.
  function question() {
    return voice('ask', quiz.answer.p);
  }

  function pick(card) {
    if (game.phase !== 'ask' || card.state !== 'down' || performance.now() < game.busyUntil) return;
    sound.unlock();
    if (card !== quiz.answer) {
      // Not this one, and she learns what it is: the soft sound and a shake, then the card turns over
      // (greyed and marked, out of play) and says its line. Her next pick or #say cuts that off.
      turn(card, 'out', 'nope');
      sound.say([{ wait: NOPE_SAY_MS }].concat(voice('wrong', card.p)));
      return;
    }
    turn(card, 'up');
    picksEl.classList.add('solved');
    quiz.shownAt = performance.now();
    const lines = voice('right', card.p);
    if (scored([card])) {
      finishing(lines);
      sound.say(lines);
      return;
    }
    setPhase('reveal');
    // On after the answer's clips, or after a fallback when the voice never ends.
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

  /* ---------- flash cards: every item on a shelf, then one at a time, big ---------- */

  const shelf = { tiles: new Map(), at: 0, card: null, last: null };

  // A tile per item in teaching order, built on the first visit: learned ones in full colour with a
  // tick, the others dimmed with a dot (base.css, data-learned).
  function buildShelf() {
    if (shelf.tiles.size) return;
    ITEMS.forEach((p, i) => {
      const tile = el('button', 'tile');
      tile.type = 'button';
      tile.dataset.index = String(i);
      tile.dataset.learned = String(learned.has(p.id));
      tile.setAttribute('aria-label', MODEL.label(p));
      const pic = el('span', 'pic');
      // lazy before src: a picture loads when its tile scrolls near
      const img = Object.assign(el('img'), { loading: 'lazy', decoding: 'async', alt: '', draggable: false });
      img.src = p.img;
      // Offline, a picture that was never fetched shows the tile alone, not a broken image.
      img.addEventListener('error', () => { img.hidden = true; });
      pic.appendChild(img);
      tile.appendChild(pic);
      const chip = MODEL.chip(p);
      if (chip) tile.appendChild(el('span', 'chip', chip));
      shelfEl.appendChild(tile);
      shelf.tiles.set(p.id, tile);
    });
  }

  // The shelf opens where the new ones begin.
  function openShelf() {
    reset('cards', 0);
    buildShelf();
    setPhase('browse');
    keepAwake();
    const tile = shelf.tiles.get(ITEMS[nextNew()].id);
    if (tile.scrollIntoView) tile.scrollIntoView({ block: 'center' });
  }

  // The flash card's size: as tall as its slot allows, a card's proportions, clear of the screen's sides.
  function flashLayout() {
    if (!shelf.card) return;
    const rect = slotEl.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const ch = Math.min(rect.height, (rect.width * 0.86) / 0.78);
    const cw = ch * 0.78;
    face.fit(shelf.card.el, shelf.card.p, applyFace(slotEl, cw, ch, faceMode(cw, ch)));
  }

  // One item, big: the card turns over, says its line (PLAY.voice.card) and counts as learned. The next
  // card's picture and clips come in meanwhile, so "next" shows at once.
  function showCard(index) {
    const n = ITEMS.length;
    shelf.at = ((index % n) + n) % n;
    const p = ITEMS[shelf.at];
    const card = buildCard(p, 0, 'span');
    slotEl.textContent = '';
    slotEl.appendChild(card);
    shelf.card = { p, el: card };
    if (!isShown('flash')) show('flash');
    flashLayout();
    setPhase('card');
    const round = game.round;
    setTimeout(() => {
      if (game.round !== round || !shelf.card || shelf.card.el !== card) return;
      card.dataset.state = 'up';
      sound.sfx('flip');
    }, reducedMotion.matches ? 0 : 120);
    markLearned(p);
    sound.say(voice('card', p));
    const after = ITEMS[(shelf.at + 1) % n];
    warmImages([after]);
    sound.prefetch(clipUrls(after, ['card']));
  }

  // Back on the shelf, the last card's tile is in view and its mark pops.
  function closeCard() {
    if (game.phase !== 'card') return;
    sound.halt();
    hide('flash');
    const tile = shelf.tiles.get(shelf.card.p.id);
    shelf.card = null;
    slotEl.textContent = '';
    setPhase('browse');
    if (!tile) return;
    if (tile.scrollIntoView) tile.scrollIntoView({ block: 'nearest' });
    if (shelf.last) shelf.last.classList.remove('fresh');
    tile.classList.add('fresh');
    shelf.last = tile;
  }

  function nextNew() {
    const i = ITEMS.findIndex((p) => !learned.has(p.id));
    return i < 0 ? 0 : i;
  }

  /* ---------- a game that precaches only its first items keeps the rest as they come ---------- */

  // PLAY.precache "core" (a word game): the worker precaches the page and the first items, and keeps
  // every other picture and clip the page fetches. Online, the page fetches ahead what the next game
  // needs, so it plays offline too: every learned item (memory's review, the quiz) and the next new ones.
  const ahead = { queue: [], busy: 0, seen: new Set() };

  // The next deal's new items: those after the ones dealt now, as if she learns them all.
  function upcoming(dealt = []) {
    return ITEMS.filter((p) => !learned.has(p.id) && !dealt.includes(p)).slice(0, PLAY.deal.pairs);
  }

  function fetchAhead(items) {
    const sw = navigator.serviceWorker;
    if (PLAY.precache.policy !== 'core' || !canFetch || !window.caches || !sw || !sw.controller) return;
    if (navigator.onLine === false) return; // the 'online' event starts it again
    items.forEach((p) => [p.img].concat(clipUrls(p, Object.keys(PLAY.voice))).forEach((url) => {
      if (url && !ahead.seen.has(url)) {
        ahead.seen.add(url);
        ahead.queue.push(url);
      }
    }));
    pump();
  }

  // Three at a time, after the page's own requests; one that fails (offline) is tried again later.
  function pump() {
    while (ahead.busy < 3 && ahead.queue.length) {
      const url = ahead.queue.shift();
      ahead.busy += 1;
      caches.match(new URL(url, location.href).href)
        .then((hit) => hit || fetch(url).then((r) => {
          if (!r.ok) throw new Error(String(r.status));
          return r.blob();
        }))
        .catch(() => ahead.seen.delete(url))
        .then(() => {
          ahead.busy -= 1;
          pump();
        });
    }
  }

  function fetchAllAhead() {
    fetchAhead(learned.items().concat(upcoming()));
  }

  /* ---------- overlays ---------- */

  const OVERLAYS = ['start', 'confirm', 'win', 'flash'];

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
    const pool = POSTER;
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

  // A locked quiz button points at the other two: its padlock wiggles, theirs bounce (base.css .hint).
  let hintTimer = 0;
  function hintLocked() {
    const { body } = document;
    sound.unlock();
    sound.sfx('hint');
    body.classList.remove('hint');
    void body.offsetWidth; // restart the animation
    body.classList.add('hint');
    clearTimeout(hintTimer);
    hintTimer = setTimeout(() => body.classList.remove('hint'), 1700);
  }

  // Every new game starts from one of the three mode buttons: on the start screen, on the win screen
  // and in the ↻ confirm. A quiz opens with its first question right after the start line.
  function wireModes(ids, allowed, before) {
    ids.forEach((id) => $(id).addEventListener('click', () => {
      if (!allowed()) return;
      if (id.endsWith('-quiz') && quizLocked()) {
        hintLocked();
        return;
      }
      if (reloadIfStale()) return;
      sound.unlock();
      if (before) before();
      const start = clip.ui('start', UI_LINES.start);
      if (id.endsWith('-quiz')) {
        startQuiz();
        sound.say([start].concat(question()));
      } else if (id.endsWith('-cards')) {
        openShelf();
        sound.say([start]);
      } else {
        newGame();
        sound.say([start]);
      }
    }));
  }

  wireModes(['play', 'play-quiz', 'play-cards'], () => game.phase === 'start', goFullscreen);
  wireModes(['replay', 'replay-quiz', 'replay-cards'], () => game.phase === 'won');
  wireModes(['yes', 'yes-quiz', 'yes-cards'], () => true);

  // The shelf scrolls under a finger, so a tile opens on a click (a tap), never on the touch that starts
  // a scroll.
  shelfEl.addEventListener('click', (event) => {
    const tile = event.target.closest && event.target.closest('.tile');
    if (game.phase !== 'browse' || !tile) return;
    sound.unlock();
    showCard(Number(tile.dataset.index));
  });
  $('next-new').addEventListener('click', () => {
    if (game.phase !== 'browse') return;
    sound.unlock();
    showCard(nextNew());
  });
  $('next').addEventListener('click', () => { if (game.phase === 'card') showCard(shelf.at + 1); });
  $('prev').addEventListener('click', () => { if (game.phase === 'card') showCard(shelf.at - 1); });
  const hear = () => { if (game.phase === 'card') sound.say(voice('card', shelf.card.p)); };
  $('hear').addEventListener('click', hear);
  slotEl.addEventListener('click', hear);
  $('close').addEventListener('click', closeCard);

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

  // Only the shown grid has a box; the others' layouts return at once.
  const relayout = () => { layout(); quizLayout(); flashLayout(); };
  if (window.ResizeObserver) [board, picksEl, slotEl].forEach((grid) => new ResizeObserver(relayout).observe(grid));
  else window.addEventListener('resize', relayout);
  window.addEventListener('resize', () => { if (game.phase === 'start') buildFan(); });

  syncLearned();
  sound.prefetch([clip.ui('start').url]);
  face.prepare(ITEMS);
  buildFan();
  const fontsReady = document.fonts && document.fonts.load
    ? Promise.all(CLUB.fonts.map(([spec, sample]) => document.fonts.load(spec, sample)))
    : Promise.resolve();
  fontsReady.catch(() => {}).then(() => {
    face.prepare(ITEMS);
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
    // What the worker keeps besides its core, fetched once the page is in and the worker is in charge.
    navigator.serviceWorker.addEventListener('controllerchange', () => setTimeout(fetchAllAhead, 1500));
    window.addEventListener('load', () => setTimeout(fetchAllAhead, 3000));
    window.addEventListener('online', fetchAllAhead);
  }
})();
