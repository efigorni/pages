// Runs a game page's data, club and engine scripts in a vm with a minimal fake DOM, fake timers,
// fake speechSynthesis, fake Web Audio and fake Wake Lock, so state-machine and audio paths can be
// exercised deterministically. Usage: HARNESS_HTML=<game>/index.html, then require('./harness').boot({...}).
// boot({ clips: true }) pretends every clip ships; boot({ noClips: true }) that none does (speech only);
// boot({ storage: [[key, value]] }) starts with that localStorage (what she has learned, a reload later);
// boot({ html: <path> }) runs another page than HARNESS_HTML (a game built in a scratch folder).
const fs = require('fs');
const vm = require('vm');

const HTML = process.env.HARNESS_HTML ? fs.readFileSync(process.env.HARNESS_HTML, 'utf8') : '';

function extractScripts(html) {
  const dataSrc = html.match(/<script id="data">([\s\S]*?)<\/script>/)[1];
  const engine = html.match(/<script id="engine">([\s\S]*?)<\/script>/);
  if (engine) {
    // Split pages: data, then club, then engine, in that order.
    const club = html.match(/<script id="club">([\s\S]*?)<\/script>/)[1];
    return { dataSrc: `${dataSrc}\n${club}`, main: engine[1] };
  }
  const all = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  const main = all[all.length - 1];
  return { dataSrc, main };
}

class ClassList {
  constructor() { this.set = new Set(); }
  add(...c) { c.forEach((x) => this.set.add(x)); }
  remove(...c) { c.forEach((x) => this.set.delete(x)); }
  contains(c) { return this.set.has(c); }
}

class El {
  constructor(tag, id) {
    this.tagName = String(tag).toUpperCase();
    this.id = id || '';
    this.children = [];
    this.parentElement = null;
    this.dataset = {};
    const props = {};
    this.style = { props, setProperty(k, v) { props[k] = v; } };
    this.attrs = {};
    this.listeners = {};
    this.classList = new ClassList();
    this._text = '';
    this.inert = false;
  }
  set className(v) { this.classList.set = new Set(String(v).split(/\s+/).filter(Boolean)); }
  get className() { return [...this.classList.set].join(' '); }
  set textContent(v) { this.children.forEach((c) => { c.parentElement = null; }); this.children = []; this._text = String(v); }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(''); }
  appendChild(c) { if (c.parentElement) c.remove(); c.parentElement = this; this.children.push(c); return c; }
  append(...cs) { cs.forEach((c) => this.appendChild(c)); }
  remove() { const p = this.parentElement; if (p) { p.children = p.children.filter((x) => x !== this); this.parentElement = null; } }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  removeEventListener(t, fn) { if (this.listeners[t]) this.listeners[t] = this.listeners[t].filter((f) => f !== fn); }
  dispatch(t, ev) { const e = Object.assign({ target: this, preventDefault() {} }, ev); (this.listeners[t] || []).slice().forEach((fn) => fn(e)); }
  contains(n) { while (n) { if (n === this) return true; n = n.parentElement; } return false; }
  matchesSel(sel) { return sel.startsWith('.') ? this.classList.contains(sel.slice(1)) : this.tagName === sel.toUpperCase(); }
  closest(sel) { let n = this; while (n) { if (n.matchesSel(sel)) return n; n = n.parentElement; } return null; }
  querySelector(sel) { for (const c of this.children) { if (c.matchesSel(sel)) return c; const r = c.querySelector(sel); if (r) return r; } return null; }
  getBoundingClientRect() { return { left: 0, top: 0, width: this.rectW || 580, height: this.rectH || 860 }; }
  blur() {}
  getContext() { return ctx2d; }
}

const ctx2d = {
  font: '', fillStyle: '',
  measureText(t) { return { width: String(t).length * 40 }; },
  clearRect() {}, save() {}, restore() {}, translate() {}, rotate() {}, scale() {}, fillRect() {},
};

function boot(opts = {}) {
  const log = [];
  const clock = { now: 0 };
  let timerSeq = 0;
  const timers = new Map();
  const setTimeoutF = (fn, ms) => { const id = ++timerSeq; timers.set(id, { at: clock.now + Math.max(0, ms || 0), fn, seq: id }); return id; };
  const clearTimeoutF = (id) => { timers.delete(id); };

  const flush = async () => { for (let i = 0; i < 6; i++) await new Promise((r) => setImmediate(r)); };
  async function advance(ms) {
    const target = clock.now + ms;
    for (;;) {
      let next = null;
      for (const [id, t] of timers) if (t.at <= target && (!next || t.at < next.t.at || (t.at === next.t.at && t.seq < next.t.seq))) next = { id, t };
      if (!next) break;
      timers.delete(next.id);
      clock.now = Math.max(clock.now, next.t.at);
      next.t.fn();
      await flush();
    }
    clock.now = target;
    await flush();
  }

  // speechSynthesis
  const synth = {
    speaking: false, pending: false, spoken: [], cancels: 0, current: null,
    getVoices: () => (opts.noHebrewVoice ? [{ lang: 'en-US', name: 'X' }] : [{ lang: 'he-IL', name: 'Carmit' }, { lang: 'en-US', name: 'Samantha' }]),
    addEventListener() {},
    speak(u) {
      this.spoken.push({ text: u.text, at: clock.now });
      log.push(`speak@${clock.now}: ${u.text}`);
      this.speaking = true;
      this.current = u;
      const dur = 60 * u.text.length;
      u._t = setTimeoutF(() => { if (this.current === u) { this.current = null; this.speaking = false; if (u.onend) u.onend(); } }, dur);
    },
    cancel() {
      this.cancels++;
      const u = this.current;
      this.current = null;
      this.speaking = false;
      if (u) { clearTimeoutF(u._t); if (u.onerror) u.onerror({ error: 'interrupted' }); }
    },
  };
  class Utterance { constructor(text) { this.text = text; } }

  // Web Audio
  const audioCtxs = [];
  class FakeAudioContext {
    constructor() {
      this.state = 'running'; this.currentTime = 0; this.destination = {};
      this.decodes = []; this.sources = []; this.oscillators = 0; this.resumes = 0;
      audioCtxs.push(this);
    }
    createGain() { return { gain: { value: 1, setValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect() {} }; }
    createBuffer() { return { duration: 0 }; }
    createBufferSource() {
      const ac = this;
      const src = {
        buffer: null, onended: null, ended: false, timer: 0,
        connect() {},
        start() { ac.sources.push(src); if (src.buffer && src.buffer.url) log.push(`buffer-start@${clock.now}: ${src.buffer.url} (ctx ${ac.state})`); if (ac.state === 'running') src.arm(); },
        arm() { if (src.buffer && src.buffer.duration && !src.timer && !src.ended) src.timer = setTimeoutF(() => src.end(), src.buffer.duration * 1000); },
        end() { if (src.ended) return; src.ended = true; clearTimeoutF(src.timer); if (src.onended) src.onended(); },
        stop() { src.end(); },
      };
      return src;
    }
    createOscillator() { this.oscillators++; return { type: '', frequency: { setValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect() {}, start() {}, stop() {} }; }
    decodeAudioData(buf, ok, fail) {
      this.decodes.push(buf);
      if (buf.detached) {
        log.push(`decode-detached@${clock.now}: ${buf.url}`);
        Promise.resolve().then(() => fail(new Error('DataCloneError')));
        return Promise.reject(new Error('DataCloneError')).catch(() => {});
      }
      buf.detached = true;
      Promise.resolve().then(() => ok({ duration: buf.duration, url: buf.url }));
      return Promise.resolve();
    }
    resume() { this.resumes++; this.state = 'running'; this.sources.forEach((s) => s.arm()); return Promise.resolve(); }
  }

  const served = opts.served || new Set();
  const fetches = [];
  const fetchF = (url) => {
    fetches.push(url);
    if (!served.has(url)) return Promise.resolve({ ok: false, arrayBuffer: () => Promise.resolve(null) });
    const duration = url.includes('/match/') ? 2.5 : url.includes('/ui/') ? 2.0 : 1.2;
    return Promise.resolve({ ok: true, arrayBuffer: () => Promise.resolve({ url, duration }) });
  };

  // Wake Lock
  const sentinels = [];
  class Sentinel {
    constructor() { this.released = false; this.ls = []; }
    addEventListener(t, fn) { if (t === 'release') this.ls.push(fn); }
    release() { if (this.released) return Promise.resolve(); this.released = true; this.ls.forEach((fn) => fn()); return Promise.resolve(); }
  }

  // Every element of the page that has an id, with its tag, so a new one the engine looks up needs no edit here.
  const html = opts.html ? fs.readFileSync(opts.html, 'utf8') : HTML;
  const byId = Object.fromEntries([...html.matchAll(/<([a-z]+)\b[^>]*\sid="([\w-]+)"/g)].map(([, tag, id]) => [id, new El(tag, id)]));
  byId.start.classList.add('show');
  byId.confirm.inert = true;
  byId.win.inert = true;
  const body = new El('body');
  const docListeners = {};
  const fullscreenRequests = [];
  const document = {
    getElementById: (id) => byId[id] || null,
    createElement: (tag) => new El(tag),
    body,
    activeElement: body,
    head: new El('head'),
    documentElement: { requestFullscreen(o) { fullscreenRequests.push(o); return Promise.resolve(); } },
    fullscreenElement: null,
    visibilityState: 'visible',
    fonts: { load: () => Promise.resolve([]) },
    addEventListener(t, fn) { (docListeners[t] = docListeners[t] || []).push(fn); },
  };
  const store = new Map(opts.storage || []);
  const winListeners = {};
  const g = {
    console,
    document,
    navigator: opts.noWakeLock ? {} : { wakeLock: { request: async () => { const s = new Sentinel(); sentinels.push(s); log.push(`wakelock-acquire@${clock.now}`); return s; } } },
    location: { protocol: opts.protocol || 'https:', hostname: 'efigorni.github.io' },
    localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)) },
    matchMedia: (q) => ({ matches: q.includes('pointer: coarse') ? true : q.includes('landscape') ? !!opts.landscape : false, addEventListener() {} }),
    getComputedStyle: () => ({ columnGap: '8px', rowGap: '8px' }),
    performance: { now: () => clock.now },
    setTimeout: setTimeoutF,
    clearTimeout: clearTimeoutF,
    requestAnimationFrame: () => 1,
    cancelAnimationFrame: () => {},
    ResizeObserver: class { observe() {} },
    Image: class { decode() { return Promise.resolve(); } },
    Audio: class { constructor(src) { this.src = src; this.ls = {}; } addEventListener(t, f) { (this.ls[t] = this.ls[t] || []).push(f); } removeEventListener(t, f) { if (this.ls[t]) this.ls[t] = this.ls[t].filter((x) => x !== f); } play() { return Promise.resolve(); } pause() {} },
    fetch: fetchF,
    SpeechSynthesisUtterance: Utterance,
    innerWidth: opts.landscape ? 960 : 600,
    innerHeight: opts.landscape ? 600 : 960,
    addEventListener(t, fn) { (winListeners[t] = winListeners[t] || []).push(fn); },
    Promise,
    Math,
    Map,
    Set,
  };
  if (!opts.noSpeech) g.speechSynthesis = synth;
  if (opts.webAudio) g.AudioContext = FakeAudioContext;
  g.window = g;

  const { dataSrc, main } = extractScripts(html);
  let data = dataSrc;
  if (opts.clips || opts.noClips) {
    const d = JSON.parse(data.match(/const DATA = (\{.*\});/)[1]);
    const all = opts.noClips ? [] : (d.words || d.players).map((p) => p.id);
    // every clip kind the game records (a squad's name and match, a word game's en and he)
    d.audio = Object.fromEntries(Object.keys(d.audio).map((kind) => [kind, kind === 'ui' ? (opts.noClips ? [] : ['start', 'win']) : all]));
    data = data.replace(/const DATA = \{.*\};/, `const DATA = ${JSON.stringify(d)};`);
  }
  const exportLine = 'globalThis.__t = { DATA, ITEMS, PLAY, game, quiz, shelf, stats, level, LEARN, pickQuiz, updateStats, tap, newGame, '
    + 'dealPicks, startQuiz, sound, clip, voice, hebrewNumber, get wakeLock() { return wakeLock; } };\n';
  const cut = main.lastIndexOf('})();');
  const patched = main.slice(0, cut) + exportLine + main.slice(cut);
  vm.createContext(g);
  vm.runInContext(`${data}\n${patched}`, g, { filename: 'index.html' });

  const T = g.__t;
  const api = {
    g, T, clock, log, synth, audioCtxs, fetches, sentinels, byId, document, fullscreenRequests, docListeners, store,
    advance, flush,
    click: async (id) => { byId[id].dispatch('click', { detail: 1 }); await flush(); },
    down: async (card) => { byId.board.dispatch('pointerdown', { target: card.el, button: 0 }); await flush(); },
    pick: async (card) => { byId.picks.dispatch('pointerdown', { target: card.el, button: 0 }); await flush(); },
    tile: async (index) => { byId.shelf.dispatch('click', { target: byId.shelf.children[index], detail: 1 }); await flush(); },
    cards: () => T.game.cards,
    phase: () => T.game.phase,
    pairOf: (card) => T.game.cards.find((c) => c !== card && c.p.id === card.p.id),
    firstDown: (pred = () => true) => T.game.cards.find((c) => c.state === 'down' && pred(c)),
    setVisibility: async (state) => {
      document.visibilityState = state;
      if (state === 'hidden') sentinels.forEach((s) => s.release());
      (docListeners.visibilitychange || []).forEach((fn) => fn({}));
      await flush();
    },
  };
  return api;
}

module.exports = { boot };
