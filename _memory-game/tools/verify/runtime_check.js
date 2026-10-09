// A kept file that changes evicts only its own copy (club.json play.precache "core"): serve a copy of the
// game, let the worker keep six of its later files, change one of them and assemble, reload so the new
// worker takes over, then read the runtime cache: the changed file's old copy is gone, the other five
// stayed, and the changed file is served with its new bytes.
//
//   node runtime_check.js <out-dir> <repo> <game> <port>
// Writes <out-dir>/result.json and prints one PASS/FAIL line. Exits 1 on FAIL.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawn, execFileSync } = require('child_process');
const { chromium } = require('playwright');

const [OUT_ARG, REPO, GAME, PORT] = process.argv.slice(2);
const OUT = path.resolve(OUT_ARG);
const TREE = path.join(OUT, 'tree');
const BASE = `http://localhost:${PORT}/${GAME}/`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const sha = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

function keptFiles() {
  const src = fs.readFileSync(path.join(TREE, GAME, 'sw.js'), 'utf8');
  const m = /^const RUNTIME_FILES = (\{[\s\S]*?\});$/m.exec(src);
  return { runtime: /^const RUNTIME = '([^']*)';$/m.exec(src)[1], version: /^const VERSION = '([^']+)';$/m.exec(src)[1],
    files: Object.keys(JSON.parse(m[1].replace(/'/g, '"'))) };
}

async function takeOver(page, version) {
  for (let i = 0; i < 120; i++) {
    const ok = await page.evaluate(async (v) => {
      const reg = await navigator.serviceWorker.getRegistration();
      return !!reg && !!reg.active && reg.active.state === 'activated' && !reg.installing && !reg.waiting
        && !!navigator.serviceWorker.controller && (await caches.keys()).includes(v);
    }, version).catch(() => false);
    if (ok) return true;
    await sleep(500);
  }
  return false;
}

const keys = (page, name) => page.evaluate(async (n) => (await (await caches.open(n)).keys()).map((r) => r.url), name);

(async () => {
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(TREE, { recursive: true });
  fs.cpSync(path.join(REPO, GAME), path.join(TREE, GAME), { recursive: true });
  const before = keptFiles();
  if (!before.runtime) throw new Error(`${GAME} keeps no files at runtime (play.precache is not "core")`);
  const pics = before.files.filter((f) => f.startsWith('img/')).slice(0, 7);
  const [changed, donor, ...rest] = pics;
  const server = spawn('python3', ['-I', path.join(__dirname, 'serve.py'), PORT, TREE], { stdio: 'ignore' });
  await sleep(800);
  const context = await chromium.launchPersistentContext(path.join(OUT, 'profile'), { channel: 'chromium' });
  const R = { game: GAME, changed, kept: [changed, ...rest] };
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto(BASE, { waitUntil: 'load' });
    R.installed = await takeOver(page, before.version);
    await page.evaluate((urls) => Promise.all(urls.map((u) => fetch(u).then((r) => r.blob()))), R.kept);
    R.keysBefore = await keys(page, before.runtime);
    // the changed file: another picture's bytes, a valid WebP all the same
    fs.copyFileSync(path.join(TREE, GAME, donor), path.join(TREE, GAME, changed));
    execFileSync('python3', ['-I', path.join(__dirname, '../page/build_page.py'), 'assemble', GAME, '--repo', TREE], { stdio: 'ignore' });
    const after = keptFiles();
    await page.reload({ waitUntil: 'load' });
    R.tookOver = await takeOver(page, after.version);
    R.keysAfter = await keys(page, after.runtime);
    R.servedNew = await page.evaluate(async (u) => {
      const buf = await (await fetch(u)).arrayBuffer();
      return [...new Uint8Array(await crypto.subtle.digest('SHA-256', buf))].map((b) => b.toString(16).padStart(2, '0')).join('');
    }, changed) === sha(path.join(TREE, GAME, changed));
    const has = (list, f) => list.some((u) => new URL(u).pathname.endsWith(`/${f}`));
    R.checks = {
      keptSix: R.kept.every((f) => has(R.keysBefore, f)),
      newWorker: R.installed && R.tookOver && after.version !== before.version && after.runtime === before.runtime,
      othersSurvive: rest.every((f) => R.keysBefore.filter((u) => u.includes(`/${f}?`)).every((u) => R.keysAfter.includes(u))),
      changedEvicted: !R.keysAfter.some((u) => R.keysBefore.includes(u) && u.includes(`/${changed}?`)),
      servedNew: R.servedNew,
    };
  } catch (e) {
    R.failure = String(e && e.message || e).split('\n')[0];
  }
  await context.close();
  server.kill();
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify(R, null, 1));
  const bad = R.failure ? [R.failure] : Object.entries(R.checks).filter(([, v]) => !v).map(([k]) => k);
  console.log(`runtime ${GAME}: ${bad.length ? `FAIL ${bad.join(', ')}` : 'PASS'} (changed ${changed}; ${rest.length} others kept)`);
  process.exit(bad.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
