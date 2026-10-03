'use strict';

// Change this version whenever the deployed app shell changes.
const CACHE_PREFIX = `orbit-shell:${self.registration.scope}:`;
const CACHE_NAME = `${CACHE_PREFIX}v2-charts`;
const SCOPE = new URL(self.registration.scope);
const APP_SHELL = new URL('index.html', SCOPE).href;
const SHELL_URLS = [
  APP_SHELL,
  new URL('manifest.webmanifest', SCOPE).href,
  new URL('icon-192.png', SCOPE).href,
  new URL('icon-512.png', SCOPE).href,
  new URL('apple-touch-icon.png', SCOPE).href
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_URLS)));
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names
      .filter(name => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME)
      .map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== SCOPE.origin || !url.href.startsWith(SCOPE.href)) return;
  // Queries may vary, but only this app's document and assets are handled.
  url.search = '';
  url.hash = '';
  const resourceUrl = url.href;
  const isAppDocument = resourceUrl === APP_SHELL || resourceUrl === SCOPE.href;

  if (request.mode === 'navigate' && isAppDocument) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE_NAME);
      try {
        const response = await fetch(request);
        if (response.ok && response.type === 'basic') {
          await cache.put(APP_SHELL, response.clone());
        }
        return response;
      } catch {
        return (await cache.match(APP_SHELL)) || Response.error();
      }
    })());
    return;
  }

  if (!SHELL_URLS.includes(resourceUrl) || isAppDocument) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(resourceUrl);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok && response.type === 'basic') {
      await cache.put(resourceUrl, response.clone());
    }
    return response;
  })());
});
