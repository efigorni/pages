const VERSION = 'maccabi-haifa-memory-699a82a90c81';
const ASSETS = [
  './',
  'index.html',
  'manifest.webmanifest',
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
    event.respondWith(caches.match(request).then((hit) => hit || network));
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
