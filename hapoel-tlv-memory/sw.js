// build_page.py assemble writes each game's sw.js from _memory-game/sw.template.js, filling in
// VERSION (a hash of every file it ships), ASSETS, PREFIX and RUNTIME: edit the template, not a sw.js.
const VERSION = 'hapoel-tlv-memory-30c1fb8f0c8a';
const ASSETS = [
  './',
  'index.html',
  'manifest.webmanifest',
  'audio/match/amit-lemkin.mp3',
  'audio/match/andrian-kraev.mp3',
  'audio/match/assaf-tzur.mp3',
  'audio/match/chico-alves.mp3',
  'audio/match/daniel-dappa.mp3',
  'audio/match/doron-leidner.mp3',
  'audio/match/douglas-owusu.mp3',
  'audio/match/el-yam-kancepolsky.mp3',
  'audio/match/emmanuel-boateng.mp3',
  'audio/match/fernand-mayembo.mp3',
  'audio/match/itay-shavit.mp3',
  'audio/match/lucas-falcao.mp3',
  'audio/match/marcus-coco.mp3',
  'audio/match/mor-buskila.mp3',
  'audio/match/omri-altman.mp3',
  'audio/match/roei-alkukin.mp3',
  'audio/match/roy-korine.mp3',
  'audio/match/shahar-piven.mp3',
  'audio/match/stav-toriel.mp3',
  'audio/match/tal-archel.mp3',
  'audio/match/yannick-leliendal.mp3',
  'audio/match/yonatan-ferber.mp3',
  'audio/name/amit-lemkin.mp3',
  'audio/name/andrian-kraev.mp3',
  'audio/name/assaf-tzur.mp3',
  'audio/name/chico-alves.mp3',
  'audio/name/daniel-dappa.mp3',
  'audio/name/doron-leidner.mp3',
  'audio/name/douglas-owusu.mp3',
  'audio/name/el-yam-kancepolsky.mp3',
  'audio/name/emmanuel-boateng.mp3',
  'audio/name/fernand-mayembo.mp3',
  'audio/name/itay-shavit.mp3',
  'audio/name/lucas-falcao.mp3',
  'audio/name/marcus-coco.mp3',
  'audio/name/mor-buskila.mp3',
  'audio/name/omri-altman.mp3',
  'audio/name/roei-alkukin.mp3',
  'audio/name/roy-korine.mp3',
  'audio/name/shahar-piven.mp3',
  'audio/name/stav-toriel.mp3',
  'audio/name/tal-archel.mp3',
  'audio/name/yannick-leliendal.mp3',
  'audio/name/yonatan-ferber.mp3',
  'audio/ui/start.mp3',
  'audio/ui/win.mp3',
  'fonts/karantina-700-hebrew.woff2',
  'fonts/karantina-700-latin.woff2',
  'fonts/rubik-hebrew.woff2',
  'fonts/rubik-latin.woff2',
  'icons/apple-touch-icon.png',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-192.png',
  'icons/icon-maskable-512.png',
  'img/amit-lemkin.webp',
  'img/andrian-kraev.webp',
  'img/assaf-tzur.webp',
  'img/chico-alves.webp',
  'img/club/paint.webp',
  'img/daniel-dappa.webp',
  'img/doron-leidner.webp',
  'img/douglas-owusu.webp',
  'img/el-yam-kancepolsky.webp',
  'img/emmanuel-boateng.webp',
  'img/fernand-mayembo.webp',
  'img/itay-shavit.webp',
  'img/lucas-falcao.webp',
  'img/marcus-coco.webp',
  'img/mor-buskila.webp',
  'img/omri-altman.webp',
  'img/roei-alkukin.webp',
  'img/roy-korine.webp',
  'img/shahar-piven.webp',
  'img/stav-toriel.webp',
  'img/tal-archel.webp',
  'img/yannick-leliendal.webp',
  'img/yonatan-ferber.webp'
];

// The origin's Cache Storage is shared with the other games on efigorni.github.io, so this worker
// only ever deletes caches carrying its own prefix.
const PREFIX = 'hapoel-tlv-memory-';

// A game that precaches only its core (club.json play.precache "core": the page and its first words)
// keeps every other picture and clip it fetches here, across versions. Its name hashes those files,
// so it is replaced only when one of them changes. Empty when everything is precached.
const RUNTIME = '';

const NAV_TIMEOUT_MS = 3000;

// Offline play needs every file, so one failed download fails the whole install (addAll stores
// nothing then): the previous version stays in charge and the browser tries again on a later visit.
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(VERSION)
      .then((cache) => cache.addAll(ASSETS.map((url) => new Request(url, { cache: 'reload' }))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith(PREFIX) && key !== VERSION && key !== RUNTIME)
        .map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

function store(name, request, response) {
  if (!response || response.status !== 200 || response.type !== 'basic') return Promise.resolve();
  const copy = response.clone();
  return caches.open(name).then((cache) => cache.put(request, copy)).catch(() => {});
}

function cached(request) {
  return caches.match(request, { ignoreSearch: true });
}

function cachedPage(request) {
  return cached(request).then((hit) => hit || caches.match('./'));
}

// <audio> asks for byte ranges, and some players (iOS Safari) refuse a whole 200 in reply. A cached
// file answers a single range itself; any other request gets the whole file.
function ranged(request, response) {
  const m = /^bytes=(\d*)-(\d*)$/.exec(request.headers.get('range') || '');
  if (!m || (m[1] === '' && m[2] === '')) return Promise.resolve(response);
  return response.arrayBuffer().then((body) => {
    const size = body.byteLength;
    const start = m[1] === '' ? Math.max(0, size - Number(m[2])) : Number(m[1]);
    const end = m[1] === '' || m[2] === '' ? size - 1 : Math.min(Number(m[2]), size - 1);
    if (start > end) return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${size}` } });
    return new Response(body.slice(start, end + 1), {
      status: 206,
      statusText: 'Partial Content',
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/octet-stream',
        'Content-Range': `bytes ${start}-${end}/${size}`,
        'Content-Length': String(end - start + 1),
        'Accept-Ranges': 'bytes',
      },
    });
  });
}

function fetchAndStore(event, request, name = VERSION) {
  let saved = Promise.resolve();
  // A clip the runtime cache keeps is fetched whole even when <audio> asks for a range, so the copy
  // kept is the whole file; the range is cut from it.
  const whole = name === RUNTIME && request.headers.has('range') ? new Request(request.url) : request;
  const network = fetch(whole).then((response) => {
    saved = store(name, whole, response);
    return whole === request ? response : ranged(request, response.clone());
  });
  event.waitUntil(network.then(() => saved, () => {}));
  return network;
}

// The pictures and clips a core-precached game keeps as they come (RUNTIME).
function kept(url) {
  return !!RUNTIME && /\/(img|audio)\//.test(new URL(url).pathname);
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;

  if (request.mode !== 'navigate') {
    // VERSION hashes every file the game ships and a new version downloads its core again, so a hit in
    // this version's cache, or in the runtime cache its name vouches for, is current and needs no trip
    // to the network.
    const runtime = kept(request.url);
    event.respondWith(caches.open(VERSION).then((cache) => cache.match(request))
      .then((hit) => hit || (runtime ? caches.open(RUNTIME).then((cache) => cache.match(request)) : undefined))
      .then((hit) => (hit ? ranged(request, hit) : fetchAndStore(event, request, runtime ? RUNTIME : VERSION))));
    return;
  }

  const network = fetchAndStore(event, request);

  // Network-first. An error page falls back to the cached copy, and a connection that is up but
  // barely working gets the cached game after NAV_TIMEOUT_MS while the fetch refreshes the cache.
  event.respondWith(new Promise((resolve, reject) => {
    let settled = false;
    let timer = 0;
    const settle = (response) => {
      if (settled || !response) return;
      settled = true;
      clearTimeout(timer);
      resolve(response);
    };
    timer = setTimeout(() => { cachedPage(request).then(settle, () => {}); }, NAV_TIMEOUT_MS);
    network.then(
      (response) => (response.status < 400
        ? settle(response)
        : cached(request).catch(() => undefined).then((hit) => settle(hit || response))),
      (err) => cachedPage(request).catch(() => undefined).then((hit) => {
        if (hit) return settle(hit);
        if (settled) return undefined;
        settled = true;
        clearTimeout(timer);
        return reject(err);
      }),
    );
  }));
});
