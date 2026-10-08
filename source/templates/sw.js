{% load static %}/* ==========================================================================
   sw.js  —  the service worker of the progressive web app
   templates/sw.js
   core/views.py serves this file at /sw.js, thus its scope is the full site.

   RULES
     - A page always comes from the network. The service worker does not
       keep pages, because they hold business data and a CSRF token. When
       the network is not available, the offline page shows.
     - A static file (CSS, JS, image) comes from the cache first. The cache
       then gets a new copy from the network in the background.
     - All other requests (POST, fetch, files) go to the network without
       change.

   Change VERSION to delete the old caches on the next visit.
   ========================================================================== */

const VERSION = "v1";
const CACHE = "pothos-" + VERSION;
const OFFLINE_URL = "{% url 'offline' %}";
const STATIC_URL = new URL("{% get_static_prefix %}", self.location).href;

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE)
            .then((cache) => cache.add(OFFLINE_URL))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (event) => {
    const request = event.request;
    if (request.method !== "GET") return;

    if (request.mode === "navigate") {
        event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
        return;
    }

    if (request.url.startsWith(STATIC_URL)) {
        const network = fetch(request).then((response) => {
            if (!response.ok) return response;
            const copy = response.clone();
            return caches.open(CACHE).then((cache) => cache.put(request, copy)).then(() => response);
        });
        event.waitUntil(network.catch(() => {}));
        event.respondWith(caches.match(request).then((cached) => cached || network));
    }
});
