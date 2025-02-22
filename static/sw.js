// sw.js
const CACHE_NAME = 'investment-tool-cache-v1';
const urlsToCache = [
  '/',
  '/static/styles.css',
  '/static/manifest.json'
  // Add additional assets you want to cache
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
