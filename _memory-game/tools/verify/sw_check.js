// One game with its service worker on, in a fresh persistent profile at 600x960 touch: wait for the
// worker to control the page, play a few flips online, read installability over CDP, then go
// offline, reload and play again.
//
//   node sw_check.js <base-url> <game> <out-dir> [<want-version>]
//   e.g. node sw_check.js http://127.0.0.1:8781/ hapoel-tlv-memory /tmp/v/local
//        node sw_check.js https://efigorni.github.io/pages/ hapoel-tlv-memory /tmp/v/live hapoel-tlv-memory-abc123
// Writes <out-dir>/sw-<game>.json and <out-dir>/sw-<game>-offline.png.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [BASE, GAME, OUT_ARG, WANT] = process.argv.slice(2);
const OUT = path.resolve(OUT_ARG);
const INSTR = fs.readFileSync(path.join(__dirname, 'instr.js'), 'utf8');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const say = (...a) => console.log(`[sw ${GAME}]`, ...a);

async function until(page, fn, timeout, arg) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await page.evaluate(fn, arg).catch(() => false)) return true;
    await sleep(500);
  }
  return false;
}

async function state(page) {
  return page.evaluate(async () => {
    const reg = await navigator.serviceWorker.getRegistration();
    const c = {};
    for (const k of await caches.keys()) c[k] = (await (await caches.open(k)).keys()).length;
    return { scope: reg && reg.scope, active: reg && reg.active && reg.active.state, controlled: !!navigator.serviceWorker.controller,
      caches: c, phase: document.getElementById('app').dataset.phase };
  });
}

async function tapCard(page, i) {
  const [x, y] = await page.evaluate((k) => { const r = document.querySelector(`#board > .card[data-index="${k}"]`).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }, i);
  await page.touchscreen.tap(x, y);
}

async function pairs(page) {
  const deck = await page.evaluate(() => [...document.querySelectorAll('#board > .card')].map((c) => c.dataset.id));
  const m = new Map();
  deck.forEach((id, i) => { if (!m.has(id)) m.set(id, []); m.get(id).push(i); });
  return [...m.entries()].map(([id, idx]) => ({ id, idx }));
}

async function play(page) {
  await page.evaluate(() => { window.__same = 1; });
  await page.tap('#play');
  await sleep(1500);
  const reloaded = await page.evaluate(() => window.__same !== 1);
  if (reloaded) { await page.waitForLoadState('load'); await sleep(2000); await page.tap('#play'); }
  await sleep(2600);
  return reloaded;
}

async function flips(page, count) {
  const P = (await pairs(page)).slice(0, count);
  const mark = (l) => page.evaluate((x) => window.__push('mark', { label: x }), l);
  for (let k = 0; k < P.length; k++) {
    await mark(`flip ${P[k].id}`); await tapCard(page, P[k].idx[0]); await sleep(1500);
    await mark(`match ${P[k].id}`); await tapCard(page, P[k].idx[1]); await sleep(k % 2 ? 4500 : 3000);
  }
  return { found: await page.evaluate(() => document.getElementById('app').dataset.found), ids: P.map((p) => p.id) };
}

function audit(log) {
  const marks = log.map((e, i) => ({ ...e, i })).filter((e) => e.type === 'mark');
  const starts = log.map((e, i) => ({ ...e, i })).filter((e) => e.type === 'buf-start' || e.type === 'html-play');
  let ok = 0;
  let follow = 0;
  const bad = [];
  marks.forEach((m, j) => {
    const [what, id] = m.label.split(' ');
    const next = marks[j + 1] ? marks[j + 1].i : Infinity;
    const clips = starts.filter((s) => s.i > m.i && s.i < next).map((s) => s.url);
    if (clips[0] === `audio/name/${id}.mp3`) ok++; else bad.push({ mark: m.label, clips });
    if (what === 'match' && clips[1] === `audio/match/${id}.mp3`) follow++;
  });
  return { rightNameClip: ok, of: marks.length, bad, matchFollows: follow, matches: marks.filter((m) => m.label.startsWith('match')).length,
    start: starts.filter((s) => s.url === 'audio/ui/start.mp3').length, speech: log.filter((e) => e.type === 'speech').length,
    errors: log.filter((e) => e.type === 'error' || e.type === 'rejection').length,
    fetchBad: log.filter((e) => (e.type === 'fetch' && e.status !== 200) || e.type === 'fetch-fail').length };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  // A persistent profile: an incognito context always reports the "in-incognito" installability error.
  const profile = fs.mkdtempSync(path.join(OUT, `.profile-${GAME}-`));
  const context = await chromium.launchPersistentContext(profile, {
    channel: 'chromium', args: ['--autoplay-policy=no-user-gesture-required'],
    viewport: { width: 600, height: 960 }, deviceScaleFactor: 1.33, isMobile: true, hasTouch: true, locale: 'he-IL',
  });
  await context.addInitScript(INSTR);
  const R = { base: BASE, game: GAME, at: new Date().toISOString(), console: [], http: [] };
  const page = context.pages()[0] || await context.newPage();
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') R.console.push(`${m.type()}: ${m.text()}`); });
  page.on('pageerror', (e) => R.console.push(`pageerror: ${e.message}`));
  page.on('response', (r) => { if (r.status() >= 400) R.http.push(`${r.status()} ${r.url()}`); });
  page.on('requestfailed', (r) => R.http.push(`failed ${r.url()} ${r.failure() && r.failure().errorText}`));
  await page.goto(`${BASE}${GAME}/`, { waitUntil: 'load' });
  R.controlled = await until(page, async (v) => {
    const reg = await navigator.serviceWorker.getRegistration();
    if (!reg || !reg.active || reg.active.state !== 'activated' || !navigator.serviceWorker.controller) return false;
    return !v || (await caches.keys()).includes(v);
  }, 120000, WANT || '');
  R.online = { state: await state(page) };
  await play(page);
  let at = await page.evaluate(() => window.__log.length);
  const g1 = await flips(page, 3);
  R.online.audio = { ...g1, ...audit((await page.evaluate(() => window.__log)).slice(at)) };
  const cdp = await context.newCDPSession(page);
  R.installability = (await cdp.send('Page.getInstallabilityErrors')).installabilityErrors;
  const manifest = await cdp.send('Page.getAppManifest');
  R.manifestErrors = manifest.errors;
  R.manifestUrl = manifest.url;
  R.appId = await cdp.send('Page.getAppId').catch((e) => String(e));
  await cdp.detach();
  await context.setOffline(true);
  // An uncached URL while offline must fail; its expected error is not a finding.
  const consoleAt = R.console.length;
  R.offlineProbe = await page.evaluate(() => fetch(`./probe-${Date.now()}.txt`).then((r) => `resolved ${r.status}`, (e) => `rejected ${e.message}`));
  await sleep(300);
  R.console = R.console.filter((m, i) => i < consoleAt || !m.includes('net::ERR_FAILED'));
  R.http = R.http.filter((h) => !h.includes('/probe-'));
  await page.reload({ waitUntil: 'load' });
  await sleep(2000);
  R.offline = { state: await state(page) };
  await play(page);
  at = await page.evaluate(() => window.__log.length);
  const g2 = await flips(page, 3);
  R.offline.audio = { ...g2, ...audit((await page.evaluate(() => window.__log)).slice(at)) };
  R.offline.imgs = await page.evaluate(() => { const i = [...document.querySelectorAll('#board img')]; return [i.length, i.filter((x) => x.complete && x.naturalWidth > 0).length]; });
  await page.screenshot({ path: path.join(OUT, `sw-${GAME}-offline.png`) });
  await context.setOffline(false);
  R.console = R.console.filter((m) => !m.includes('Banner not shown'));
  fs.writeFileSync(path.join(OUT, `sw-${GAME}.json`), JSON.stringify(R, null, 1));
  say(JSON.stringify({ controlled: R.controlled, installability: R.installability, manifestErrors: R.manifestErrors, appId: R.appId,
    online: R.online.audio, offlineProbe: R.offlineProbe, offline: { controlled: R.offline.state.controlled, imgs: R.offline.imgs, audio: R.offline.audio },
    console: R.console, http: R.http }));
  await context.close();
  fs.rmSync(profile, { recursive: true, force: true });
})().catch((e) => { console.error(e); process.exit(1); });
