// A game's link-preview image, <game>/og.jpg: 1200x630, JPEG, at most 300 KB, what WhatsApp and the like
// show when the game's link is shared. It is the game's own start screen at that size, its background and
// title in the club's fonts and colours, with three card faces under the title in place of the fan and the
// mode buttons: three starters, or three of a word game's first words (the engine's POSTER, which the start
// screen's fan shows too). So the game's look is drawn by its own page, never again here. The page runs
// from the repo through a route (no server, no service worker), and its engine is opened up the way the
// state-machine harness does it, so the cards are built by the engine's buildCard and sized by the face.
//
//   _memory-game/tools/og/render_og.sh [<game>...]      (sets up the verify harness's pinned Playwright)
//   node og.js <repo> <game> [--players <id>,<id>,<id>]
// Without --players, the three come from a shuffle seeded by the game's id: the same three until the
// starters (or the first words) change.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const argv = process.argv.slice(2);
const REPO = path.resolve(argv[0] || '.');
const GAME = argv[1];
const opt = (name) => { const i = argv.indexOf(`--${name}`); return i >= 0 ? argv[i + 1] : null; };
const WIDTH = 1200;
const HEIGHT = 630;
const MAX_BYTES = 300 * 1024;
const ORIGIN = 'http://og.invalid/';
// The poster: the title over three cards fanned out a little, side by side so no face, number or name is
// covered, the middle one a little bigger.
const POSTER_CSS = `
  .start .modes, .install, .fan, [data-progress] .progress { display: none; }
  .start-stage { grid-template-areas: "title" "cards"; row-gap: var(--og-gap); }
  .og-cards { grid-area: cards; display: flex; align-items: center; gap: calc(var(--cw) * .07); }
  .og-cards .card { flex: none; width: var(--cw); height: var(--ch); }
  .og-cards .card:nth-child(1) { transform: rotate(5deg) translateY(4%); }
  .og-cards .card:nth-child(2) { z-index: 1; transform: scale(1.06); }
  .og-cards .card:nth-child(3) { transform: rotate(-5deg) translateY(4%); }
`;
if (!GAME) {
  console.error('usage: node og.js <repo> <game> [--players <id>,<id>,<id>]');
  process.exit(2);
}

// The engine keeps its parts inside one closure; this hands the ones the poster needs to the window.
function opened(html) {
  const start = html.indexOf('<script id="engine">');
  const cut = html.lastIndexOf('})();', html.indexOf('</script>', start));
  if (start < 0 || cut < start) throw new Error(`${GAME}/index.html has no engine script to open`);
  return `${html.slice(0, cut)}window.__og = { buildCard, applyFace, face, POSTER };\n${html.slice(cut)}`;
}

function seeded(text) {
  let s = [...text].reduce((h, c) => Math.imul(h ^ c.charCodeAt(0), 16777619) >>> 0, 2166136261);
  return () => {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick(ids) {
  if (opt('players')) return opt('players').split(',');
  const rnd = seeded(GAME);
  const a = ids.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, 3);
}

// In the page: the title's height decides how big the three cards can be.
function poster(ids) {
  const { buildCard, applyFace, face, POSTER } = window.__og;
  const stage = document.querySelector('.start-stage');
  const gap = 22;
  const pad = 30;
  stage.style.setProperty('--og-gap', `${gap}px`);
  const title = stage.querySelector('.title').getBoundingClientRect().height;
  // Three cards, two gaps and the side cards' tilt across; the middle card's scale and the tilt down.
  const cw = Math.min((innerWidth - 2 * pad) / 3.45, (innerHeight - 2 * pad - gap - title) / 1.28 / 1.12);
  const cards = document.createElement('div');
  cards.className = 'og-cards';
  const geo = applyFace(cards, cw, cw * 1.28, 'band');
  ids.forEach((id, i) => {
    const p = POSTER.find((q) => q.id === id);
    const card = buildCard(p, i, 'span');
    card.dataset.state = 'up';
    cards.appendChild(card);
    face.fit(card, p, geo);
  });
  stage.appendChild(cards);
  return Math.round(cw);
}

(async () => {
  const html = fs.readFileSync(path.join(REPO, GAME, 'index.html'), 'utf8');
  const browser = await chromium.launch({ channel: 'chromium' });
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1, serviceWorkers: 'block',
    reducedMotion: 'reduce', locale: 'he-IL',
  });
  await context.route(`${ORIGIN}**`, (route) => {
    const rel = decodeURIComponent(new URL(route.request().url()).pathname).replace(/^\/+/, '');
    if (rel === `${GAME}/` || rel === `${GAME}/index.html`) {
      return route.fulfill({ contentType: 'text/html; charset=utf-8', body: opened(html) });
    }
    const file = path.join(REPO, rel);
    const ok = file.startsWith(`${REPO}${path.sep}`) && fs.existsSync(file) && fs.statSync(file).isFile();
    return ok ? route.fulfill({ path: file }) : route.fulfill({ status: 404, body: '' });
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`${ORIGIN}${GAME}/`, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const pool = await page.evaluate(() => window.__og.POSTER.map((p) => [p.id, p.name_he || p.en]));
  const names = new Map(pool);
  const ids = pick(pool.map(([id]) => id));
  if (ids.length !== 3 || !ids.every((id) => names.has(id))) {
    throw new Error(`${GAME}: --players wants three ids of the start screen's pool (the starters, or the first words), not ${ids.join(',')}`);
  }
  await page.addStyleTag({ content: POSTER_CSS });
  const cw = await page.evaluate(poster, ids);
  await page.evaluate(async () => {
    const imgs = [...document.images];
    await Promise.all(imgs.map((img) => (img.complete ? null : new Promise((r) => { img.onload = img.onerror = r; }))));
    await Promise.all(imgs.map((img) => img.decode().catch(() => {})));
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  });
  const broken = await page.evaluate(() => [...document.querySelectorAll('.og-cards img')].filter((i) => !i.naturalWidth).length);
  if (broken || errors.length) throw new Error(`${GAME}: ${broken} photo(s) missing; page errors: ${errors.join(' | ') || 'none'}`);
  let quality = 88;
  let jpg = await page.screenshot({ type: 'jpeg', quality, animations: 'disabled', caret: 'hide' });
  while (jpg.length > MAX_BYTES && quality > 60) {
    quality -= 4;
    jpg = await page.screenshot({ type: 'jpeg', quality, animations: 'disabled', caret: 'hide' });
  }
  await browser.close();
  if (jpg.length > MAX_BYTES) throw new Error(`${GAME}: og.jpg is ${Math.round(jpg.length / 1024)} KB even at quality ${quality}`);
  fs.writeFileSync(path.join(REPO, GAME, 'og.jpg'), jpg);
  console.log(`${GAME}: og.jpg ${WIDTH}x${HEIGHT}, ${Math.round(jpg.length / 1024)} KB (JPEG quality ${quality}), cards ${cw} px wide: `
    + `${ids.map((id) => names.get(id)).join(', ')}`);
})().catch((e) => { console.error(`og: ${e.message || e}`); process.exit(1); });
