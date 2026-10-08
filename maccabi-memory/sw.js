const VERSION = 'maccabi-memory-59b159fad37e';
const ASSETS = [
  './',
  'index.html',
  'manifest.webmanifest',
  'fonts/barlow-condensed-800-latin.woff2',
  'fonts/karantina-700-hebrew.woff2',
  'fonts/karantina-700-latin.woff2',
  'icons/apple-touch-icon.png',
  'icons/icon-192.png',
  'icons/icon-512.png',
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

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(VERSION)
      .then((cache) => Promise.all(ASSETS.map((url) => cache.add(new Request(url, { cache: 'reload' })).catch(() => {}))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith('maccabi-memory-') && key !== VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

function store(request, response) {
  if (response && response.status === 200 && response.type === 'basic') {
    const copy = response.clone();
    caches.open(VERSION).then((cache) => cache.put(request, copy)).catch(() => {});
  }
  return response;
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => store(request, response))
        .catch(() => caches.match(request, { ignoreSearch: true }).then((hit) => hit || caches.match('./'))),
    );
    return;
  }

  const network = fetch(request).then((response) => store(request, response));
  event.respondWith(caches.match(request).then((hit) => hit || network));
  event.waitUntil(network.then(() => {}, () => {}));
});
