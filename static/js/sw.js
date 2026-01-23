const CACHE_NAME = 'devtube-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css', // o'zingizning css faylingiz nomi
  '/static/js/main.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});