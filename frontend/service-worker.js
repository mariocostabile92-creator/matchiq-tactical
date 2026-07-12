const CACHE_NAME = "matchiq-pwa-v99";
const APP_SHELL = [
  "/index.html?v=10499",
  "/mobile.html?v=10499",
  "/privacy.html",
  "/terms.html",
  "/cookies.html",
  "/js/app-meta.js",
  "/css/home.css?v=10499",
  "/js/auth.js?v=10499",
  "/js/home-state.js?v=10499",
  "/js/home-api.js?v=10499",
  "/js/home-render.js?v=10499",
  "/js/home-actions.js?v=10499",
  "/js/home.js?v=10499",
  "/manifest.json",
  "/assets/matchiq-logo.png"
];

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL).catch(() => null))
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);

  if(request.method !== "GET" || url.pathname.startsWith("/api/")){
    return;
  }

  if(request.mode === "navigate"){
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request).then(cached => cached || caches.match("/index.html?v=10499")))
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then(response => {
        if(response.ok && url.origin === self.location.origin){
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
