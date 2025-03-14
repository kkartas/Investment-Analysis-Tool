// Service Worker for Investment Analysis Tool
const CACHE_NAME = 'smart-invest-cache-v1';

// Resources to preload and cache
const ASSETS_TO_CACHE = [
  '/',
  '/static/styles.css',
  '/static/icons/favicon.svg',
  '/static/icons/apple-touch-icon.png'
];

// Install event - cache initial assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Fetch event - serve from cache if available, otherwise fetch from network
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Cache hit - return the cached version
        if (response) {
          return response;
        }
        
        // Not in cache - fetch from network
        return fetch(event.request)
          .then((fetchResponse) => {
            // Check if we received a valid response
            if (!fetchResponse || fetchResponse.status !== 200 || fetchResponse.type !== 'basic') {
              return fetchResponse;
            }
            
            // Clone the response since we're going to consume it twice
            const responseToCache = fetchResponse.clone();
            
            // Open the cache and put the fetched response in it
            caches.open(CACHE_NAME)
              .then((cache) => {
                // Only cache assets, stylesheets, images, and fonts
                if (event.request.url.match(/\.(css|js|png|jpg|jpeg|svg|woff|woff2|ttf)$/)) {
                  cache.put(event.request, responseToCache);
                }
              });
              
            return fetchResponse;
          });
      })
  );
});
