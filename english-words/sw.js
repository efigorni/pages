// build_page.py assemble writes each game's sw.js from _memory-game/sw.template.js, filling in
// VERSION (a hash of every file it ships), ASSETS, PREFIX and RUNTIME: edit the template, not a sw.js.
const VERSION = 'english-words-7f779fb8bd73';
const ASSETS = [
  './',
  'index.html',
  'manifest.webmanifest',
  'audio/en/apple.mp3',
  'audio/en/baby.mp3',
  'audio/en/ball.mp3',
  'audio/en/banana.mp3',
  'audio/en/bird.mp3',
  'audio/en/blue.mp3',
  'audio/en/bus.mp3',
  'audio/en/cake.mp3',
  'audio/en/car.mp3',
  'audio/en/cat.mp3',
  'audio/en/dad.mp3',
  'audio/en/dog.mp3',
  'audio/en/egg.mp3',
  'audio/en/eye.mp3',
  'audio/en/fish.mp3',
  'audio/en/hand.mp3',
  'audio/en/hat.mp3',
  'audio/en/horse.mp3',
  'audio/en/house.mp3',
  'audio/en/ice-cream.mp3',
  'audio/en/mom.mp3',
  'audio/en/moon.mp3',
  'audio/en/nose.mp3',
  'audio/en/one.mp3',
  'audio/en/red.mp3',
  'audio/en/shoe.mp3',
  'audio/en/sun.mp3',
  'audio/en/train.mp3',
  'audio/en/tree.mp3',
  'audio/en/two.mp3',
  'audio/he/apple.mp3',
  'audio/he/baby.mp3',
  'audio/he/ball.mp3',
  'audio/he/banana.mp3',
  'audio/he/bird.mp3',
  'audio/he/blue.mp3',
  'audio/he/bus.mp3',
  'audio/he/cake.mp3',
  'audio/he/car.mp3',
  'audio/he/cat.mp3',
  'audio/he/dad.mp3',
  'audio/he/dog.mp3',
  'audio/he/egg.mp3',
  'audio/he/eye.mp3',
  'audio/he/fish.mp3',
  'audio/he/hand.mp3',
  'audio/he/hat.mp3',
  'audio/he/horse.mp3',
  'audio/he/house.mp3',
  'audio/he/ice-cream.mp3',
  'audio/he/mom.mp3',
  'audio/he/moon.mp3',
  'audio/he/nose.mp3',
  'audio/he/one.mp3',
  'audio/he/red.mp3',
  'audio/he/shoe.mp3',
  'audio/he/sun.mp3',
  'audio/he/train.mp3',
  'audio/he/tree.mp3',
  'audio/he/two.mp3',
  'audio/ui/start.mp3',
  'audio/ui/win.mp3',
  'fonts/andika-700-latin.woff2',
  'fonts/fredoka-400-700-hebrew.woff2',
  'fonts/fredoka-400-700-latin.woff2',
  'icons/apple-touch-icon.png',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-192.png',
  'icons/icon-maskable-512.png',
  'img/apple.webp',
  'img/baby.webp',
  'img/ball.webp',
  'img/banana.webp',
  'img/bird.webp',
  'img/blue.webp',
  'img/bus.webp',
  'img/cake.webp',
  'img/car.webp',
  'img/cat.webp',
  'img/dad.webp',
  'img/dog.webp',
  'img/egg.webp',
  'img/eye.webp',
  'img/fish.webp',
  'img/hand.webp',
  'img/hat.webp',
  'img/horse.webp',
  'img/house.webp',
  'img/ice-cream.webp',
  'img/mom.webp',
  'img/moon.webp',
  'img/nose.webp',
  'img/one.webp',
  'img/red.webp',
  'img/shoe.webp',
  'img/sun.webp',
  'img/train.webp',
  'img/tree.webp',
  'img/two.webp'
];

// The origin's Cache Storage is shared with the other games on efigorni.github.io, so this worker
// only ever deletes caches carrying its own prefix.
const PREFIX = 'english-words-';

// A game that precaches only its core (club.json play.precache "core": the page and its first words)
// keeps every other picture and clip it fetches here, across versions. Its name hashes those files,
// so it is replaced only when one of them changes. Empty when everything is precached.
const RUNTIME = 'english-words-runtime-c0ae802dee89';

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
