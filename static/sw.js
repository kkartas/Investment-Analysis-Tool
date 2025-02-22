// sw.js
const CACHE_NAME = 'investment-tool-cache-v1';
const urlsToCache = [
  '/',
  '/static/styles.css',
  '/static/manifest.json'
  // Add more files or routes that you want to cache
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return the response from the cached version
        if (response) {
          return response;
        }
        // Otherwise fetch from the network
        return fetch(event.request);
      })
  );
});
