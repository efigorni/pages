// The GitHub Pages upgrade, simulated under the same sub-path: /pages/<game>/ is served from
// <out-dir>/root/pages, a symlink repointed from the old tree to the new one. One persistent profile:
//   1. the old tree installs and plays, every game;
//   2. the new tree, online: the new worker takes over with a full cache, the old cache is deleted
//      and the other games' caches are untouched; a whole audio game; byte ranges from the cache;
//      the HTMLAudio fallback with Web Audio suspended; installability;
//   3. a second online load reaches the server only for the navigation and sw.js;
//   4. offline (the server stopped): reload and play a whole game.
// --quick (the sanity check) plays two pairs where the steps above play a whole game, one pair on the
// old tree, and skips the HTMLAudio fallback.
//
//   node sim.js <out-dir> <old-tree> <new-tree> <port> [--quick] <game>...
// Writes <out-dir>/result.json and prints one PASS/FAIL line per game. Exits 1 on any FAIL.
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const QUICK = process.argv.includes('--quick');
const [OUT_ARG, OLD, NEW, PORT_ARG, ...GAMES] = process.argv.slice(2).filter((a) => a !== '--quick');
const OUT = path.resolve(OUT_ARG);
const ROOT = path.join(OUT, 'root');
const LINK = path.join(ROOT, 'pages');
const TREES = { old: path.resolve(OLD), new: path.resolve(NEW) };
const PORT = Number(PORT_ARG);
const BASE = `http://localhost:${PORT}/pages/`;
const PROFILE = path.join(OUT, 'profile');
const LOG = path.join(OUT, 'server.log');
const INSTR = fs.readFileSync(path.join(__dirname, 'instr.js'), 'utf8');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const say = (...a) => console.log('[sim]', ...a);
if (!GAMES.length || !PORT) {
  console.error('usage: node sim.js <out-dir> <old-tree> <new-tree> <port> <game>...');
  process.exit(2);
}

function point(tree) {
  fs.rmSync(LINK, { force: true });
  fs.symlinkSync(TREES[tree], LINK);
  say(`pages -> ${tree}`);
}

function swInfo(tree, game) {
  const src = fs.readFileSync(path.join(TREES[tree], game, 'sw.js'), 'utf8');
  return { version: src.match(/^const VERSION = '([^']+)';$/m)[1], assets: (src.match(/^ {2}'/gm) || []).length };
}

let server = null;
function startServer() {
  const log = fs.openSync(LOG, 'a');
  server = spawn('python3', ['-I', path.join(__dirname, 'serve.py'), String(PORT), ROOT], { stdio: ['ignore', log, log] });
  return sleep(800);
}
function stopServer() {
  if (server) server.kill();
  server = null;
  return sleep(500);
}
function serverLines() {
  return fs.readFileSync(LOG, 'utf8').split('\n').map((l) => l.match(/"(GET|HEAD) (\S+) HTTP\/[\d.]+" (\d{3})/)).filter(Boolean)
    .map((m) => ({ path: m[2], status: Number(m[3]) }));
}

async function until(page, fn, timeout = 30000, arg) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await page.evaluate(fn, arg).catch(() => false)) return true;
    await sleep(200);
  }
  return false;
}

async function state(page) {
  return page.evaluate(async () => {
    const reg = await navigator.serviceWorker.getRegistration();
    const caches_ = {};
    for (const k of await caches.keys()) caches_[k] = (await (await caches.open(k)).keys()).length;
    return {
      scope: reg && reg.scope, active: reg && reg.active && reg.active.state, controlled: !!navigator.serviceWorker.controller,
      caches: caches_, phase: document.getElementById('app').dataset.phase,
    };
  });
}

async function waitVersion(page, game, tree, timeout = 60000) {
  const { version, assets } = swInfo(tree, game);
  // The new cache is complete before its worker finishes installing, while the old worker is still the
  // active one: wait until no worker is installing or waiting too.
  const ok = await until(page, async ([v, n]) => {
    const reg = await navigator.serviceWorker.getRegistration();
    if (!reg || !reg.active || reg.active.state !== 'activated' || !navigator.serviceWorker.controller) return false;
    if (reg.installing || reg.waiting) return false;
    const keys = await caches.keys();
    return keys.includes(v) && (await (await caches.open(v)).keys()).length === n;
  }, timeout, [version, assets]);
  return { ok, version, assets };
}

async function tapCard(page, index) {
  const [x, y] = await page.evaluate((i) => {
    const b = document.querySelector(`#board > .card[data-index="${i}"]`).getBoundingClientRect();
    return [b.left + b.width / 2, b.top + b.height / 2];
  }, index);
  await page.touchscreen.tap(x, y);
}

async function pairs(page) {
  const deck = await page.evaluate(() => [...document.querySelectorAll('#board > .card')].map((c) => c.dataset.id));
  const m = new Map();
  deck.forEach((id, i) => { if (!m.has(id)) m.set(id, []); m.get(id).push(i); });
  return [...m.entries()].map(([id, idx]) => ({ id, idx }));
}

async function mark(page, l) { await page.evaluate((x) => window.__push('mark', { label: x }), l); }

// Starts a game, plus a reload if the page reloads itself first (a worker took over: CR1).
async function play(page) {
  await page.evaluate(() => { window.__same = 1; });
  await page.tap('#play', { timeout: 15000 });
  await sleep(1200);
  const reloaded = await page.evaluate(() => window.__same !== 1);
  if (reloaded) {
    await page.waitForLoadState('load');
    await sleep(1500);
    await page.tap('#play');
  }
  await sleep(2600);
  return reloaded;
}

// drive.js's audio game: a mismatch with cut-offs, a double tap, a tap on a face-up and on a matched
// card, a hurry-up, then every pair, half of them letting the match clip finish.
async function fullGame(page) {
  const P = await pairs(page);
  const tap = async (k, side, what, wait) => { await mark(page, `${what} ${P[k].id}`); await tapCard(page, P[k].idx[side]); await sleep(wait); };
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
    const last = n === rest.length - 1;
    await tap(rest[n], 0, 'flip', last ? 1600 : 150);
    await tap(rest[n], 1, 'match', last ? 0 : (n % 2 ? 5000 : 650));
  }
  const won = await until(page, () => document.getElementById('app').dataset.phase === 'won', 15000);
  await sleep(4000);
  return { won, deck: P.map((p) => p.id) };
}

// --quick's game: two pairs, each match let finish so its match clip follows the name.
async function twoPairs(page) {
  const P = (await pairs(page)).slice(0, 2);
  for (const p of P) {
    await mark(page, `flip ${p.id}`); await tapCard(page, p.idx[0]); await sleep(1500);
    await mark(page, `match ${p.id}`); await tapCard(page, p.idx[1]); await sleep(3500);
  }
  return { deck: P.map((p) => p.id) };
}

function audit(log) {
  const marks = log.map((e, i) => ({ ...e, i })).filter((e) => e.type === 'mark');
  const starts = log.map((e, i) => ({ ...e, i })).filter((e) => e.type === 'buf-start' || e.type === 'html-play');
  let flips = 0;
  let follows = 0;
  const bad = [];
  marks.forEach((m, j) => {
    const [what, id] = m.label.split(' ');
    if (!['flip', 'hurry', 'match'].includes(what)) return;
    const next = marks[j + 1] ? marks[j + 1].i : Infinity;
    const clips = starts.filter((s) => s.i > m.i && s.i < next).map((s) => s.url);
    if (clips[0] === `audio/name/${id}.mp3`) flips++; else bad.push({ mark: m.label, clips });
    if (what === 'match' && clips[1] === `audio/match/${id}.mp3`) follows++;
    if (what === 'match' && clips[1] && clips[1] !== `audio/match/${id}.mp3` && clips[1] !== 'audio/ui/win.mp3') {
      bad.push({ mark: m.label, clips, why: 'second clip' });
    }
  });
  return {
    flips, follows, bad,
    win: starts.filter((s) => s.url === 'audio/ui/win.mp3').length,
    speech: log.filter((e) => e.type === 'speech').length,
    htmlErrors: log.filter((e) => e.type === 'html-error').length,
    fetchBad: log.filter((e) => (e.type === 'fetch' && e.status !== 200) || e.type === 'fetch-fail'),
    errors: log.filter((e) => e.type === 'error' || e.type === 'rejection'),
  };
}

const own = (caches_, game) => Object.keys(caches_).filter((k) => k.startsWith(`${game}-`)).sort();
const others = (caches_, game) => Object.fromEntries(Object.entries(caches_).filter(([k]) => !k.startsWith(`${game}-`)));
// A whole game must be won; --quick's two pairs must say every name and at least one match clip.
const gameOk = (g) => (QUICK ? g.flips > 0 && g.follows > 0 : g.won) && !g.bad.length && !g.speech && !g.htmlErrors
  && !g.fetchBad.length && !g.errors.length;

(async () => {
  fs.mkdirSync(ROOT, { recursive: true });
  fs.rmSync(PROFILE, { recursive: true, force: true });
  fs.writeFileSync(LOG, '');
  const R = { versions: {} };
  for (const t of Object.keys(TREES)) R.versions[t] = Object.fromEntries(GAMES.map((g) => [g, swInfo(t, g)]));
  say('versions', JSON.stringify(R.versions));

  point('old');
  await startServer();
  const context = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chromium', viewport: { width: 600, height: 960 }, deviceScaleFactor: 1.33, isMobile: true, hasTouch: true,
    locale: 'he-IL', args: ['--autoplay-policy=no-user-gesture-required'],
  });
  await context.addInitScript(INSTR);
  const http = [];
  context.on('response', (r) => { if (r.status() >= 400) http.push(`${r.status()} ${r.url()}`); });
  const pages = {};
  const consoleMsgs = [];

  for (const game of GAMES) {
    const page = await context.newPage();
    page.on('console', (m) => { if (m.type() === 'error') consoleMsgs.push(`${game} ${m.type()}: ${m.text()}`); });
    page.on('pageerror', (e) => consoleMsgs.push(`${game} pageerror: ${e.message}`));
    pages[game] = page;
    await page.goto(`${BASE}${game}/`, { waitUntil: 'load' });
    const v = await waitVersion(page, game, 'old');
    await play(page);
    const P = await pairs(page);
    for (const k of QUICK ? [0] : [0, 1]) { await tapCard(page, P[k].idx[0]); await sleep(300); await tapCard(page, P[k].idx[1]); await sleep(1500); }
    R[`${game}:old`] = { installed: v, state: await state(page) };
    say(game, 'old installed', JSON.stringify(v));
  }

  point('new');
  for (const game of GAMES) {
    const page = pages[game];
    const before = await state(page);
    await page.reload({ waitUntil: 'load' });
    const v = await waitVersion(page, game, 'new');
    const st = await state(page);
    const reloadedOnPlay = await play(page);
    const markAt = await page.evaluate(() => window.__log.length);
    const g1 = QUICK ? await twoPairs(page) : await fullGame(page);
    const log = (await page.evaluate(() => window.__log)).slice(markAt);
    const ranges = await page.evaluate(async (id) => {
      const out = {};
      for (const r of ['bytes=0-', 'bytes=100-199']) {
        const res = await fetch(`audio/name/${id}.mp3`, { headers: { Range: r } });
        const body = await res.arrayBuffer();
        out[r] = { status: res.status, contentRange: res.headers.get('content-range'), length: body.byteLength };
      }
      const whole = await fetch(`audio/name/${id}.mp3`);
      out.whole = { status: whole.status, length: (await whole.arrayBuffer()).byteLength };
      return out;
    }, g1.deck[0]);
    let fb = [];
    if (!QUICK) {
      const fallbackMark = await page.evaluate(async () => {
        await window.__ctx.suspend();
        window.__ctx.resume = () => Promise.reject(new Error('refused'));
        return window.__log.length;
      });
      await page.tap('#replay');
      await sleep(3500);
      const P2 = await pairs(page);
      await mark(page, `flip ${P2[0].id}`); await tapCard(page, P2[0].idx[0]); await sleep(2500);
      await mark(page, `match ${P2[0].id}`); await tapCard(page, P2[0].idx[1]); await sleep(5000);
      fb = (await page.evaluate(() => window.__log)).slice(fallbackMark);
    }
    const cdp = await context.newCDPSession(page);
    const installability = (await cdp.send('Page.getInstallabilityErrors')).installabilityErrors;
    await cdp.detach();
    const n = ranges.whole.length;
    const r = {
      installed: v, cachesBefore: before.caches, cachesAfter: st.caches, reloadedOnPlay,
      game: { won: g1.won, ...audit(log) }, ranges,
      fallback: { html: fb.filter((e) => e.type === 'html-play').length, htmlErrors: fb.filter((e) => e.type === 'html-error').length,
        speech: fb.filter((e) => e.type === 'speech').length },
      installability,
    };
    r.checks = {
      newWorker: v.ok,
      oldCacheGone: JSON.stringify(own(st.caches, game)) === JSON.stringify([v.version]),
      otherGamesUntouched: JSON.stringify(others(before.caches, game)) === JSON.stringify(others(st.caches, game)),
      game: gameOk(r.game),
      ranges: ranges['bytes=0-'].status === 206 && ranges['bytes=0-'].contentRange === `bytes 0-${n - 1}/${n}`
        && ranges['bytes=100-199'].status === 206 && ranges['bytes=100-199'].length === 100,
      ...(QUICK ? {} : { htmlAudioFallback: r.fallback.html > 0 && !r.fallback.htmlErrors && !r.fallback.speech }),
      installable: Array.isArray(installability) && installability.length === 0,
    };
    R[`${game}:new`] = r;
    say(game, 'new online', JSON.stringify(r.checks));
  }

  for (const game of GAMES) {
    const page = pages[game];
    const before = serverLines().length;
    await page.reload({ waitUntil: 'load' });
    await sleep(4000);
    const hits = serverLines().slice(before).map((l) => l.path.split('?')[0]);
    R[`${game}:secondLoad`] = { hits, ok: hits.every((h) => h === `/pages/${game}/` || h === `/pages/${game}/sw.js`) };
    say(game, 'second load reached the server for', JSON.stringify(hits));
  }

  await stopServer();
  for (const game of GAMES) {
    const page = pages[game];
    await page.reload({ waitUntil: 'load' });
    await sleep(1500);
    await play(page);
    const markAt = await page.evaluate(() => window.__log.length);
    const g1 = QUICK ? await twoPairs(page) : await fullGame(page);
    await page.screenshot({ path: path.join(OUT, `${game}-offline-${QUICK ? 'play' : 'win'}.png`) });
    const log = (await page.evaluate(() => window.__log)).slice(markAt);
    const imgs = await page.evaluate(() => { const i = [...document.querySelectorAll('#board img')]; return [i.length, i.filter((x) => x.complete && x.naturalWidth > 0).length]; });
    const st = await state(page);
    const r = { won: g1.won, imgs, ...audit(log), state: st };
    r.checks = { controlled: st.controlled, game: gameOk(r), imgs: imgs[0] > 0 && imgs[0] === imgs[1] };
    R[`${game}:offline`] = r;
    say(game, 'offline', JSON.stringify(r.checks));
  }

  R.http4xx = http;
  R.console = consoleMsgs;
  let failed = 0;
  for (const game of GAMES) {
    const checks = {
      oldInstalled: R[`${game}:old`].installed.ok, ...R[`${game}:new`].checks,
      secondLoad: R[`${game}:secondLoad`].ok, ...Object.fromEntries(Object.entries(R[`${game}:offline`].checks).map(([k, v]) => [`offline.${k}`, v])),
    };
    const bad = Object.entries(checks).filter(([, v]) => !v).map(([k]) => k);
    R[`${game}:verdict`] = bad.length ? `FAIL ${bad.join(', ')}` : 'PASS';
    failed += !!bad.length;
    console.log(`upgrade ${game}: ${R[`${game}:verdict`]} (${R.versions.old[game].version} -> ${R.versions.new[game].version})`);
  }
  if (http.length || consoleMsgs.length) console.log(`upgrade: http ${JSON.stringify(http)} console ${JSON.stringify(consoleMsgs)}`);
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify(R, null, 1));
  await context.close();
  fs.rmSync(LINK, { force: true });
  process.exit(failed ? 1 : 0);
})().catch(async (e) => { console.error(e); if (server) server.kill(); process.exit(1); });
