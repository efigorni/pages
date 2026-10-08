// build_page.py assemble writes each game's sw.js from _memory-game/sw.template.js, filling in
// VERSION (a hash of every precached file), ASSETS and PREFIX: edit the template, not a sw.js.
const VERSION = 'maccabi-haifa-memory-25de0812e044';
const ASSETS = [
  './',
  'index.html',
  'manifest.webmanifest',
  'audio/match/adam-grimberg.mp3',
  'audio/match/ali-mohamed.mp3',
  'audio/match/andrija-novakovich.mp3',
  'audio/match/bruninho.mp3',
  'audio/match/cedric-don.mp3',
  'audio/match/ethan-azoulay.mp3',
  'audio/match/guy-melamed.mp3',
  'audio/match/iyad-khalaili.mp3',
  'audio/match/jelle-bataille.mp3',
  'audio/match/kenji-gorre.mp3',
  'audio/match/kenny-saief.mp3',
  'audio/match/navot-ratner.mp3',
  'audio/match/nigel-lonwijk.mp3',
  'audio/match/noam-shtaifman.mp3',
  'audio/match/omri-glazer.mp3',
  'audio/match/pedrao.mp3',
  'audio/match/pedro-barzao.mp3',
  'audio/match/sean-goldberg.mp3',
  'audio/match/silva-kani.mp3',
  'audio/match/tzunami.mp3',
  'audio/match/yair-mordechai.mp3',
  'audio/match/yarin-levi.mp3',
  'audio/name/adam-grimberg.mp3',
  'audio/name/ali-mohamed.mp3',
  'audio/name/andrija-novakovich.mp3',
  'audio/name/bruninho.mp3',
  'audio/name/cedric-don.mp3',
  'audio/name/ethan-azoulay.mp3',
  'audio/name/guy-melamed.mp3',
  'audio/name/iyad-khalaili.mp3',
  'audio/name/jelle-bataille.mp3',
  'audio/name/kenji-gorre.mp3',
  'audio/name/kenny-saief.mp3',
  'audio/name/navot-ratner.mp3',
  'audio/name/nigel-lonwijk.mp3',
  'audio/name/noam-shtaifman.mp3',
  'audio/name/omri-glazer.mp3',
  'audio/name/pedrao.mp3',
  'audio/name/pedro-barzao.mp3',
  'audio/name/sean-goldberg.mp3',
  'audio/name/silva-kani.mp3',
  'audio/name/tzunami.mp3',
  'audio/name/yair-mordechai.mp3',
  'audio/name/yarin-levi.mp3',
  'audio/ui/start.mp3',
  'audio/ui/win.mp3',
  'fonts/heebo-hebrew.woff2',
  'fonts/heebo-latin.woff2',
  'icons/apple-touch-icon.png',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-192.png',
  'icons/icon-maskable-512.png',
  'img/adam-grimberg.webp',
  'img/ali-mohamed.webp',
  'img/andrija-novakovich.webp',
  'img/bruninho.webp',
  'img/cedric-don.webp',
  'img/ethan-azoulay.webp',
  'img/guy-melamed.webp',
  'img/iyad-khalaili.webp',
  'img/jelle-bataille.webp',
  'img/kenji-gorre.webp',
  'img/kenny-saief.webp',
  'img/navot-ratner.webp',
  'img/nigel-lonwijk.webp',
  'img/noam-shtaifman.webp',
  'img/omri-glazer.webp',
  'img/pedrao.webp',
  'img/pedro-barzao.webp',
  'img/sean-goldberg.webp',
  'img/silva-kani.webp',
  'img/tzunami.webp',
  'img/yair-mordechai.webp',
  'img/yarin-levi.webp'
];

// The origin's Cache Storage is shared with the other games on efigorni.github.io, so this worker
// only ever deletes caches carrying its own prefix.
const PREFIX = 'maccabi-haifa-memory-';

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
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith(PREFIX) && key !== VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

function store(request, response) {
  if (!response || response.status !== 200 || response.type !== 'basic') return Promise.resolve();
  const copy = response.clone();
  return caches.open(VERSION).then((cache) => cache.put(request, copy)).catch(() => {});
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

function fetchAndStore(event, request) {
  let saved = Promise.resolve();
  const network = fetch(request).then((response) => {
    saved = store(request, response);
    return response;
  });
  event.waitUntil(network.then(() => saved, () => {}));
  return network;
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;

  if (request.mode !== 'navigate') {
    // VERSION hashes every precached file and a new version downloads them all again, so a hit in
    // this version's cache is current and needs no trip to the network.
    event.respondWith(caches.open(VERSION).then((cache) => cache.match(request))
      .then((hit) => (hit ? ranged(request, hit) : fetchAndStore(event, request))));
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
