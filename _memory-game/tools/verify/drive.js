// Seeded, instrumented playthroughs of the memory games, for P9 and for before/after comparison.
//
//   node drive.js <out-dir> <base-url> --games a,b [--vps tab-portrait,...] [--modes shots,audio,quiz]
//                 [--reduced both|on|off] [--seed N] [--jobs N]
//
// <base-url> serves a tree whose root holds the game folders (e.g. http://127.0.0.1:8767/). Service
// workers are blocked, so two runs differ only by the page code. `shots` takes start, focus, install,
// mid, confirm and win screenshots, the DOM and the computed HUD styles; `audio` plays a whole game
// and logs every clip; `quiz` plays a whole quiz (a wrong pick that turns over and says who it is,
// every player once, the end) with question, wrong, reveal and end screenshots and every clip logged.
// Output: <out-dir>/<game>/<vp>[-rm]-<mode>/{*.png,result.json}
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const argv = process.argv.slice(2);
const OUT = path.resolve(argv[0]);
const baseUrl = argv[1];
const label = path.basename(OUT);
const opt = (name, def) => { const i = argv.indexOf(`--${name}`); return i >= 0 ? argv[i + 1] : def; };
const GAMES = opt('games', '').split(',').filter(Boolean);
const VPS_SEL = opt('vps', 'tab-portrait,tab-landscape').split(',');
const MODES = opt('modes', 'shots').split(',');
const REDUCED = opt('reduced', 'off');
const SEED = Number(opt('seed', '20261008'));
const JOBS = Number(opt('jobs', '4'));
const INSTR = fs.readFileSync(path.join(__dirname, 'instr.js'), 'utf8');
if (!GAMES.length || !baseUrl) {
  console.error('usage: node drive.js <out-dir> <base-url> --games a,b [...]');
  process.exit(2);
}

const VPS = {
  'tab-portrait': { viewport: { width: 600, height: 960 }, deviceScaleFactor: 1.33, isMobile: true, hasTouch: true },
  'tab-landscape': { viewport: { width: 960, height: 600 }, deviceScaleFactor: 1.33, isMobile: true, hasTouch: true },
  phone: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  desktop: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
};

function seeded(seed) {
  let s = seed >>> 0;
  Math.random = function random() {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function until(page, fn, timeout = 15000, arg) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await page.evaluate(fn, arg).catch(() => false)) return true;
    await sleep(100);
  }
  return false;
}

async function waitImages(page) {
  await page.evaluate(async () => {
    const imgs = [...document.images];
    await Promise.all(imgs.map((img) => (img.complete ? Promise.resolve() : new Promise((r) => { img.onload = img.onerror = r; }))));
    await Promise.all(imgs.map((img) => (img.decode ? img.decode().catch(() => {}) : null)));
  });
}

async function ready(page) {
  await page.evaluate(() => document.fonts.ready);
  await waitImages(page);
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
  await sleep(700);
  await waitImages(page);
}

async function settle(page) {
  await until(page, () => !document.querySelector('.flyer'), 5000);
  await waitImages(page);
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
}

async function confettiClear(page) {
  return until(page, () => {
    const c = document.getElementById('confetti');
    if (!c.width || !c.height) return true;
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    for (let i = 3; i < d.length; i += 4) if (d[i]) return false;
    return true;
  }, 20000);
}

function snapper(page, dir) {
  return async (name) => {
    await page.screenshot({ path: path.join(dir, `${name}.png`), animations: 'disabled', caret: 'hide' });
  };
}

async function tapXY(page, vp, x, y) {
  if (vp.hasTouch) await page.touchscreen.tap(x, y);
  else await page.mouse.click(x, y);
}

async function tapSel(page, vp, sel) {
  if (vp.hasTouch) await page.tap(sel);
  else await page.click(sel);
}

async function tapCard(page, vp, index, where = '#board') {
  const [x, y] = await page.evaluate(([w, i]) => {
    const b = document.querySelector(`${w} > .card[data-index="${i}"]`).getBoundingClientRect();
    return [b.left + b.width / 2, b.top + b.height / 2];
  }, [where, index]);
  await tapXY(page, vp, x, y);
}

async function deckPairs(page) {
  const deck = await page.evaluate(() => [...document.querySelectorAll('#board > .card')].map((c) => c.dataset.id));
  const pairs = new Map();
  deck.forEach((id, i) => { if (!pairs.has(id)) pairs.set(id, []); pairs.get(id).push(i); });
  return { deck, pairs: [...pairs.entries()].map(([id, idx]) => ({ id, idx })) };
}

async function dom(page) {
  return page.evaluate(() => ({
    board: document.getElementById('board').outerHTML,
    fan: document.getElementById('fan').outerHTML,
    pips: document.getElementById('pips').outerHTML,
    phase: document.getElementById('app').dataset.phase,
    found: document.getElementById('app').dataset.found,
  }));
}

// The computed colours of the parts base.css draws for every club: the HUD buttons (and the muted
// icon), the pips (empty and found) and the install pill. Read after the screenshot it belongs to.
async function styles(page) {
  return page.evaluate(() => {
    const props = ['color-scheme', 'color', 'background-color', 'border-top-color', 'border-right-color',
      'border-bottom-color', 'border-left-color', 'display', 'opacity'];
    const read = (el, pseudo) => {
      if (!el) return null;
      const cs = getComputedStyle(el, pseudo || null);
      return Object.fromEntries(props.map((p) => [p, cs.getPropertyValue(p)]));
    };
    const mute = document.getElementById('mute');
    const out = {
      root: read(document.documentElement),
      body: read(document.body),
      mute: read(mute),
      again: read(document.getElementById('again')),
      install: read(document.getElementById('install')),
      pips: [...document.querySelectorAll('#pips .pip')].map((p) => ({
        full: p.classList.contains('full'), pip: read(p), ring: read(p, '::after'),
      })),
    };
    const pressed = mute.getAttribute('aria-pressed');
    mute.setAttribute('aria-pressed', 'true');
    out.muteOn = read(mute);
    mute.setAttribute('aria-pressed', pressed);
    return out;
  });
}

// The face-up card of the start screen: its name, how many lines, its size, and whether every line's
// text lies inside the card.
async function fanNames(page) {
  return page.evaluate(() => [...document.querySelectorAll('#fan .card')].filter((c) => c.dataset.state === 'up').map((card) => {
    const name = card.querySelector('.name');
    if (!name) return { name: null };
    const box = card.getBoundingClientRect();
    const walker = document.createTreeWalker(name, NodeFilter.SHOW_TEXT);
    const rects = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const range = document.createRange();
      range.selectNodeContents(n);
      rects.push(range.getBoundingClientRect());
    }
    const inside = rects.length > 0 && rects.every((r) => r.width > 0 && r.left >= box.left - 1 && r.right <= box.right + 1
      && r.top >= box.top - 1 && r.bottom <= box.bottom + 1);
    return { text: name.textContent, lines: name.children.length || 1, fontSize: getComputedStyle(name).fontSize, inside };
  }));
}

async function flightFrame(page, dir, name) {
  const ok = await until(page, () => !!document.querySelector('.flyer'), 3000);
  if (!ok) return null;
  const info = await page.evaluate(() => {
    const anims = document.getAnimations();
    const fly = anims.find((a) => a.effect && a.effect.target && a.effect.target.classList && a.effect.target.classList.contains('flyer'));
    anims.forEach((a) => { if (a !== fly) { try { a.finish(); } catch (e) { /* infinite */ } } });
    fly.pause();
    fly.currentTime = 360;
    const f = fly.effect.target;
    return { left: f.style.left, top: f.style.top, width: f.style.width };
  });
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
  await page.screenshot({ path: path.join(dir, `${name}.png`), animations: 'allow', caret: 'hide' });
  await page.evaluate(() => {
    const fly = document.getAnimations().find((a) => a.effect && a.effect.target && a.effect.target.classList && a.effect.target.classList.contains('flyer'));
    if (fly) fly.play();
  });
  return info;
}

async function shotsFlow(page, vp, dir, reduced, res) {
  const snap = snapper(page, dir);
  await ready(page);
  await snap('start');
  res.domStart = await dom(page);
  res.fanNames = await fanNames(page);
  await page.keyboard.press('Tab');
  await sleep(150);
  res.focus = await page.evaluate(() => document.activeElement && document.activeElement.id);
  await snap('start-focus');
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  await page.evaluate(() => {
    const e = new Event('beforeinstallprompt', { cancelable: true });
    e.prompt = () => Promise.resolve();
    window.dispatchEvent(e);
  });
  await sleep(150);
  await snap('start-install');
  res.stylesStart = await styles(page);
  res.installedCss = await page.evaluate(() => {
    const out = { rules: 0 };
    const btn = document.getElementById('install');
    out.shownDisplay = getComputedStyle(btn).display;
    const rules = [];
    for (const sheet of document.styleSheets) {
      for (const rule of sheet.cssRules) {
        if (rule.media && /display-mode/.test(rule.media.mediaText)) rules.push([rule, rule.media.mediaText]);
      }
    }
    out.rules = rules.length;
    rules.forEach(([r]) => { r.media.mediaText = 'all'; });
    out.installedDisplay = getComputedStyle(btn).display;
    rules.forEach(([r, text]) => { r.media.mediaText = text; });
    out.restoredDisplay = getComputedStyle(btn).display;
    return out;
  });
  await page.evaluate(() => window.dispatchEvent(new Event('appinstalled')));
  await sleep(150);

  await tapSel(page, vp, '#play');
  await sleep(1700);
  await waitImages(page);
  const { deck, pairs } = await deckPairs(page);
  res.deck = deck;
  for (let k = 0; k < 5; k++) {
    await tapCard(page, vp, pairs[k].idx[0]);
    await sleep(150);
    await tapCard(page, vp, pairs[k].idx[1]);
    if (k === 0 && !reduced && vp.hasTouch) res.flight = await flightFrame(page, dir, 'flight-360ms');
    await sleep(750);
  }
  await tapCard(page, vp, pairs[5].idx[0]);
  await sleep(1900);
  await settle(page);
  await snap('mid');
  res.domMid = await dom(page);
  res.stylesMid = await styles(page);
  await tapSel(page, vp, '#again');
  await sleep(700);
  await snap('confirm');
  await tapSel(page, vp, '#no');
  await sleep(700);
  await tapCard(page, vp, pairs[5].idx[1]);
  await sleep(750);
  for (let k = 6; k < pairs.length; k++) {
    await tapCard(page, vp, pairs[k].idx[0]);
    await sleep(150);
    await tapCard(page, vp, pairs[k].idx[1]);
    await sleep(750);
  }
  res.won = await until(page, () => document.getElementById('app').dataset.phase === 'won', 15000);
  await sleep(1600); // past the second confetti burst
  res.confettiClear = await confettiClear(page);
  await settle(page);
  await snap('win');
  res.domWin = await dom(page);
}

async function audioFlow(page, vp, dir, res) {
  const snap = snapper(page, dir);
  const mark = (l) => page.evaluate((x) => window.__push('mark', { label: x }), l);
  await ready(page);
  await mark('play');
  await tapSel(page, vp, '#play');
  await sleep(2600);
  await waitImages(page);
  const { deck, pairs } = await deckPairs(page);
  res.deck = deck;
  const P = pairs;
  const tap = async (k, side, what, wait) => { await mark(`${what} ${P[k].id}`); await tapCard(page, vp, P[k].idx[side]); await sleep(wait); };
  await tap(0, 0, 'flip', 300);
  await tap(0, 0, 'double', 200);
  await tap(1, 0, 'flip', 250);
  await tap(0, 0, 'faceup', 250);
  await tap(2, 0, 'hurry', 1500);
  await tap(2, 1, 'match', 5000);
  await tap(2, 0, 'matched', 300);
  await tap(0, 0, 'flip', 1300);
  await tap(1, 0, 'flip', 2700);
  const rest = [0, 1].concat([...Array(P.length).keys()].slice(3));
  for (let n = 0; n < rest.length; n++) {
    const k = rest[n];
    const last = n === rest.length - 1;
    await tap(k, 0, 'flip', last ? 1600 : 150);
    await tap(k, 1, 'match', last ? 0 : (n % 2 ? 5000 : 650));
  }
  const t0 = Date.now();
  res.won = await until(page, () => document.getElementById('app').dataset.phase === 'won', 15000);
  res.winAfterMs = Date.now() - t0;
  await sleep(4000);
  await mark('end');
  await confettiClear(page);
  await settle(page);
  await snap('audio-win');
}

const CLIP_EVENTS = ['buf-start', 'html-play'];

// The wrong card after its turn: face up (the card turned), its number and name on the face.
function wrongCard(i) {
  const card = document.querySelector(`#picks > .card[data-index="${i}"]`);
  const m = new DOMMatrixReadOnly(getComputedStyle(card.querySelector('.card-inner')).transform);
  const front = card.querySelector('.front');
  return {
    state: card.dataset.state,
    turned: m.m11 < -0.99,
    face: front.textContent.replace(/\s+/g, ' ').trim(),
    phase: document.getElementById('app').dataset.phase,
    answer: document.getElementById('picks').dataset.answer,
  };
}

// The quiz, played to the end at this viewport: on the first question a wrong pick (it turns over
// and says that player's match clip, which the right pick then cuts off), then the right one; every
// question waits for its match clip to start before the pick; the first three reveals move on by
// themselves, the others on a tap.
async function quizFlow(page, vp, dir, res) {
  const snap = snapper(page, dir);
  const mark = (l) => page.evaluate((x) => window.__push('mark', { label: x }), l);
  const logLen = () => page.evaluate(() => window.__log.length);
  const played = (from, url) => until(page, ([k, u]) => window.__log.slice(k)
    .some((e) => (e.type === 'buf-start' || e.type === 'html-play') && e.url === u), 10000, [from, url]);
  await ready(page);
  res.pool = await page.evaluate(() => DATA.starters.concat(DATA.bench, DATA.backup || []).map((p) => p.id));
  const faces = await page.evaluate(() => Object.fromEntries(DATA.starters.concat(DATA.bench, DATA.backup || [])
    .map((p) => [p.id, { number: String(p.number), name: p.name_he }])));
  res.questions = [];
  let from = await logLen();
  await mark('start');
  await tapSel(page, vp, '#play-quiz');
  for (let n = 0; n < res.pool.length; n++) {
    const q = { n, asked: await until(page, () => document.getElementById('app').dataset.phase === 'ask', 10000) };
    Object.assign(q, await page.evaluate(() => ({
      id: document.getElementById('picks').dataset.answer,
      cards: [...document.querySelectorAll('#picks > .card')].map((c) => c.dataset.id),
      text: document.getElementById('question').textContent,
    })));
    res.questions.push(q);
    q.heard = await played(from, `audio/match/${q.id}.mp3`);
    // The question's clip starts with the deal, and a pick in its first 450 ms is ignored (a tap that
    // moved on must not also pick).
    await sleep(500);
    if (n === 0) {
      await sleep(900);
      await waitImages(page);
      await snap('quiz-question');
      const wrong = q.cards.findIndex((id) => id !== q.id);
      const wrongId = q.cards[wrong];
      from = await logLen();
      await mark(`wrong ${wrongId}`);
      const wrongAt = Date.now();
      await tapCard(page, vp, wrong, '#picks');
      const said = await played(from, `audio/match/${wrongId}.mp3`);
      const saidMs = Date.now() - wrongAt;
      await sleep(Math.max(0, 1150 - (Date.now() - wrongAt))); // the turn and the ✗ settle
      q.wrong = { id: wrongId, said, saidMs, ...await page.evaluate(wrongCard, wrong) };
      const shown = faces[wrongId];
      q.wrong.shows = q.wrong.face.includes(shown.number) && q.wrong.face.replace(/\s/g, '').includes(shown.name.replace(/\s/g, ''));
      await snap('quiz-wrong');
    }
    from = await logLen();
    await mark(`right ${q.id}`);
    const pickedAt = Date.now();
    await tapCard(page, vp, q.cards.indexOf(q.id), '#picks');
    q.named = await played(from, `audio/name/${q.id}.mp3`);
    q.revealed = await page.evaluate(() => document.getElementById('app').dataset.phase);
    if (n === 0) {
      await sleep(1100);
      await settle(page);
      await snap('quiz-reveal');
    }
    if (n === res.pool.length - 1) break;
    from = await logLen();
    if (n < 3) {
      q.auto = await until(page, (id) => document.getElementById('picks').dataset.answer !== id, 12000, q.id);
      q.advanceMs = Date.now() - pickedAt;
    } else {
      await sleep(Math.max(0, 750 - (Date.now() - pickedAt)));
      await mark('advance');
      await tapCard(page, vp, 0, '#picks');
    }
  }
  res.found = await page.evaluate(() => document.getElementById('app').dataset.found);
  res.won = await until(page, () => document.getElementById('app').dataset.phase === 'won', 15000);
  await sleep(1600); // past the second confetti burst
  res.confettiClear = await confettiClear(page);
  await settle(page);
  await snap('quiz-end');
}

// The quiz's clips, in order: start, then per question the asked player's match clip alone, the
// wrong player's match clip after a wrong pick, the name on the right pick; then win. The right pick
// cuts off the wrong player's clip.
function analyseQuiz(res) {
  const log = res.log || [];
  const at = log.map((e, i) => ({ ...e, i }));
  const clips = at.filter((e) => CLIP_EVENTS.includes(e.type));
  const marks = at.filter((e) => e.type === 'mark');
  const qs = res.questions || [];
  const asked = qs.map((q) => q.id);
  const expected = ['audio/ui/start.mp3'].concat(...qs.map((q) => [`audio/match/${q.id}.mp3`]
    .concat(q.wrong ? [`audio/match/${q.wrong.id}.mp3`] : [], [`audio/name/${q.id}.mp3`])), 'audio/ui/win.mp3');
  const sequence = clips.map((c) => c.url);
  const pool = res.pool || [];
  const after = (m) => {
    const next = marks.find((x) => x.i > m.i);
    return (list) => list.filter((e) => e.i > m.i && (!next || e.i < next.i));
  };
  const wrongs = marks.filter((m) => m.label.startsWith('wrong'));
  return {
    sequence,
    sequenceOk: JSON.stringify(sequence) === JSON.stringify(expected),
    firstMismatch: expected.findIndex((u, i) => sequence[i] !== u),
    everyPlayerOnce: asked.length === pool.length && new Set(asked).size === pool.length && pool.every((id) => asked.includes(id)),
    fourDistinct: qs.every((q) => q.cards.length === 4 && new Set(q.cards).size === 4 && q.cards.includes(q.id)),
    // Between a wrong pick and the next mark: exactly that player's match clip.
    wrongTeaches: wrongs.length > 0 && wrongs.every((m) => JSON.stringify(after(m)(clips).map((c) => c.url))
      === JSON.stringify([`audio/match/${m.label.split(' ')[1]}.mp3`])),
    // The right pick after a wrong one stops the wrong player's clip before the name starts.
    wrongCut: wrongs.length > 0 && wrongs.every((m) => {
      const url = `audio/match/${m.label.split(' ')[1]}.mp3`;
      const right = marks.find((x) => x.i > m.i);
      const name = right && clips.find((c) => c.i > right.i);
      return !!right && at.some((e) => (e.type === 'buf-stop' || e.type === 'html-pause') && e.url === url
        && e.i > right.i && (!name || e.i < name.i));
    }),
    nopeTones: at.filter((e) => e.type === 'osc').length,
  };
}

function analyse(log, game) {
  const marks = [];
  const starts = [];
  const stops = [];
  log.forEach((e, i) => {
    if (e.type === 'mark') marks.push({ ...e, i });
    if (e.type === 'buf-start') starts.push({ ...e, i });
    if (e.type === 'buf-stop') stops.push({ ...e, i });
  });
  const flipsOk = [];
  const bad = [];
  marks.forEach((m, j) => {
    const [what, id] = m.label.split(' ');
    if (!['flip', 'hurry', 'match'].includes(what)) return;
    const next = marks[j + 1] ? marks[j + 1].i : Infinity;
    const clips = starts.filter((s) => s.i > m.i && s.i < next).map((s) => s.url);
    const want = `audio/name/${id}.mp3`;
    if (clips[0] === want) flipsOk.push(m.label); else bad.push({ mark: m.label, clips });
    if (what === 'match' && clips.length > 1 && clips[1] !== `audio/match/${id}.mp3` && clips[1] !== 'audio/ui/win.mp3') bad.push({ mark: m.label, clips, why: 'second clip' });
  });
  const matchFollow = marks.filter((m) => m.label.startsWith('match')).map((m, j, arr) => {
    const id = m.label.split(' ')[1];
    const nextMark = marks.find((x) => x.i > m.i);
    const clips = starts.filter((s) => s.i > m.i && (!nextMark || s.i < nextMark.i)).map((s) => s.url);
    return { id, clips };
  });
  return {
    effectiveFlips: flipsOk.length,
    badFlips: bad,
    starts: starts.map((s) => s.url),
    stops: stops.map((s) => s.url),
    matchesWithFollow: matchFollow.filter((m) => m.clips[1] === `audio/match/${m.id}.mp3`).length,
    matches: matchFollow.length,
    startClip: starts.filter((s) => s.url === 'audio/ui/start.mp3').length,
    winClip: starts.filter((s) => s.url === 'audio/ui/win.mp3').length,
    speech: log.filter((e) => e.type === 'speech').map((e) => e.text),
    html: log.filter((e) => e.type === 'html-play').map((e) => e.url),
    fetchBad: log.filter((e) => (e.type === 'fetch' && e.status !== 200) || e.type === 'fetch-fail'),
    errors: log.filter((e) => e.type === 'error' || e.type === 'rejection'),
    osc: log.filter((e) => e.type === 'osc').length,
    wake: log.filter((e) => e.type.startsWith('wake')).map((e) => e.type),
    fullscreen: log.filter((e) => e.type === 'fullscreen-request').length,
    flyers: log.filter((e) => e.type === 'flyer'),
  };
}

async function run(browser, game, vpName, mode, reduced) {
  const vp = VPS[vpName];
  const name = `${vpName}${reduced ? '-rm' : ''}-${mode}`;
  const dir = path.join(OUT, game, name);
  fs.mkdirSync(dir, { recursive: true });
  const context = await browser.newContext({
    ...vp, serviceWorkers: 'block', reducedMotion: reduced ? 'reduce' : 'no-preference', locale: 'he-IL',
  });
  await context.addInitScript(seeded, SEED);
  await context.addInitScript(INSTR);
  const page = await context.newPage();
  const res = { game, vp: vpName, mode, reduced, console: [], http: [] };
  page.on('console', (m) => res.console.push(`${m.type()}: ${m.text()}`));
  page.on('pageerror', (e) => res.console.push(`pageerror: ${e.message}`));
  page.on('response', (r) => { if (r.status() >= 400) res.http.push(`${r.status()} ${r.url()}`); });
  page.on('requestfailed', (r) => res.http.push(`failed ${r.url()} ${r.failure() && r.failure().errorText}`));
  const t0 = Date.now();
  try {
    await page.goto(`${baseUrl}${game}/`, { waitUntil: 'load' });
    if (mode === 'shots') await shotsFlow(page, vp, dir, reduced, res);
    else if (mode === 'quiz') await quizFlow(page, vp, dir, res);
    else await audioFlow(page, vp, dir, res);
  } catch (e) {
    res.failure = String(e && e.stack || e);
  }
  res.log = await page.evaluate(() => window.__log).catch(() => []);
  res.analysis = analyse(res.log, game);
  if (mode === 'quiz') res.quiz = analyseQuiz(res);
  res.ms = Date.now() - t0;
  fs.writeFileSync(path.join(dir, 'result.json'), JSON.stringify(res, null, 1));
  await context.close();
  const detail = res.quiz
    ? `asked=${res.questions.length}/${res.pool.length} once=${res.quiz.everyPlayerOnce} clips=${res.quiz.sequenceOk} wrongTeaches=${res.quiz.wrongTeaches} wrongCut=${res.quiz.wrongCut}`
    : `flips=${res.analysis.effectiveFlips} bad=${res.analysis.badFlips.length} follow=${res.analysis.matchesWithFollow}/${res.analysis.matches}`;
  console.log(`[${label}] ${game} ${name}: ${res.failure ? 'FAIL ' + res.failure.split('\n')[0] : 'ok'} won=${res.won} `
    + `${detail} errors=${res.analysis.errors.length} http=${res.http.length} ${res.ms} ms`);
}

(async () => {
  const browser = await chromium.launch({ channel: 'chromium', args: ['--autoplay-policy=no-user-gesture-required'] });
  const jobs = [];
  for (const game of GAMES) {
    for (const vp of VPS_SEL) {
      for (const mode of MODES) {
        const rm = mode !== 'shots' ? [false] : REDUCED === 'both' ? [false, true] : [REDUCED === 'on'];
        rm.forEach((r) => jobs.push([game, vp, mode, r]));
      }
    }
  }
  console.log(`[${label}] ${jobs.length} runs, ${JOBS} at a time, seed ${SEED}`);
  let next = 0;
  await Promise.all([...Array(Math.min(JOBS, jobs.length))].map(async () => {
    while (next < jobs.length) {
      const j = jobs[next++];
      await run(browser, ...j);
    }
  }));
  await browser.close();
  console.log(`[${label}] done`);
})().catch((e) => { console.error(e); process.exit(1); });
