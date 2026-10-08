// build_page.py assemble writes each game's sw.js from _memory-game/sw.template.js, filling in
// VERSION (a hash of every precached file), ASSETS and PREFIX: edit the template, not a sw.js.
const VERSION = 'maccabi-memory-4d73817a13fa';
const ASSETS = [
  './',
  'index.html',
  'manifest.webmanifest',
  'audio/match/dan-glazer.mp3',
  'audio/match/dor-peretz.mp3',
  'audio/match/elad-madmon.mp3',
  'audio/match/ester-sokler.mp3',
  'audio/match/gabi-kanichowsky.mp3',
  'audio/match/helio-varela.mp3',
  'audio/match/hisham-layous.mp3',
  'audio/match/ido-shahar.mp3',
  'audio/match/ilay-ben-simon.mp3',
  'audio/match/issouf-sissokho.mp3',
  'audio/match/itamar-noy.mp3',
  'audio/match/itay-ben-hemo.mp3',
  'audio/match/james-tavernier.mp3',
  'audio/match/kristijan-belic.mp3',
  'audio/match/mohamed-ali-camara.mp3',
  'audio/match/noam-ben-harush.mp3',
  'audio/match/ofek-melika.mp3',
  'audio/match/osher-davida.mp3',
  'audio/match/raz-shlomo.mp3',
  'audio/match/sagiv-jehezkel.mp3',
  'audio/match/shachar-rosen.mp3',
  'audio/match/tyrese-asante.mp3',
  'audio/name/dan-glazer.mp3',
  'audio/name/dor-peretz.mp3',
  'audio/name/elad-madmon.mp3',
  'audio/name/ester-sokler.mp3',
  'audio/name/gabi-kanichowsky.mp3',
  'audio/name/helio-varela.mp3',
  'audio/name/hisham-layous.mp3',
  'audio/name/ido-shahar.mp3',
  'audio/name/ilay-ben-simon.mp3',
  'audio/name/issouf-sissokho.mp3',
  'audio/name/itamar-noy.mp3',
  'audio/name/itay-ben-hemo.mp3',
  'audio/name/james-tavernier.mp3',
  'audio/name/kristijan-belic.mp3',
  'audio/name/mohamed-ali-camara.mp3',
  'audio/name/noam-ben-harush.mp3',
  'audio/name/ofek-melika.mp3',
  'audio/name/osher-davida.mp3',
  'audio/name/raz-shlomo.mp3',
  'audio/name/sagiv-jehezkel.mp3',
  'audio/name/shachar-rosen.mp3',
  'audio/name/tyrese-asante.mp3',
  'audio/ui/start.mp3',
  'audio/ui/win.mp3',
  'fonts/barlow-condensed-800-latin.woff2',
  'fonts/karantina-700-hebrew.woff2',
  'fonts/karantina-700-latin.woff2',
  'icons/apple-touch-icon.png',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-192.png',
  'icons/icon-maskable-512.png',
  'img/dan-glazer.webp',
  'img/dor-peretz.webp',
  'img/elad-madmon.webp',
  'img/ester-sokler.webp',
  'img/gabi-kanichowsky.webp',
  'img/helio-varela.webp',
  'img/hisham-layous.webp',
  'img/ido-shahar.webp',
  'img/ilay-ben-simon.webp',
  'img/issouf-sissokho.webp',
  'img/itamar-noy.webp',
  'img/itay-ben-hemo.webp',
  'img/james-tavernier.webp',
  'img/kristijan-belic.webp',
  'img/mohamed-ali-camara.webp',
  'img/noam-ben-harush.webp',
  'img/ofek-melika.webp',
  'img/osher-davida.webp',
  'img/raz-shlomo.webp',
  'img/sagiv-jehezkel.webp',
  'img/shachar-rosen.webp',
  'img/tyrese-asante.webp'
];

// The origin's Cache Storage is shared with the other games on efigorni.github.io, so this worker
// only ever deletes caches carrying its own prefix.
const PREFIX = 'maccabi-memory-';

// Without these the game can't start offline, so failing either one fails the install and the
// previous version stays in charge.
const CORE = ['./', 'index.html'];
const NAV_TIMEOUT_MS = 3000;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(VERSION)
      .then((cache) => Promise.all(ASSETS.map((url) => cache.add(new Request(url, { cache: 'reload' })).catch((err) => {
        if (CORE.includes(url)) throw err;
        // Keep offline play whole: reuse the previous version's copy of a file that failed to download.
        return caches.match(url).then((old) => (old ? cache.put(url, old) : undefined)).catch(() => {});
      }))))
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

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;

  let saved = Promise.resolve();
  const network = fetch(request).then((response) => {
    saved = store(request, response);
    return response;
  });
  event.waitUntil(network.then(() => saved, () => {}));

  if (request.mode !== 'navigate') {
    event.respondWith(caches.match(request).then((hit) => (hit ? ranged(request, hit) : network)));
    return;
  }

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
