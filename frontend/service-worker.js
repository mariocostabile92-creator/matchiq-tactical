const CACHE_NAME = "matchiq-tactical-pwa-v1";

const CORE_ASSETS = [
  "/",
  "/mobile.html",
  "/index.html",
  "/scout.html",
  "/account.html",
  "/login.html",
  "/register.html",
  "/manifest.json",
  "/assets/matchiq-logo.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(CORE_ASSETS))
      .catch(() => null)
  );

  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
  );

  self.clients.claim();
});

self.addEventListener("fetch", event => {
  const request = event.request;

  if(request.method !== "GET"){
    return;
  }

  const url = new URL(request.url);

  if(url.pathname.startsWith("/api/")){
    event.respondWith(
      fetch(request).catch(() =>
        new Response(
          JSON.stringify({
            ok: false,
            offline: true,
            message: "Connessione assente. Riprova quando sei online."
          }),
          {
            headers: {
              "Content-Type": "application/json"
            }
          }
        )
      )
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then(response => {
        const copy = response.clone();

        caches.open(CACHE_NAME).then(cache => {
          cache.put(request, copy);
        });

        return response;
      })
      .catch(() => caches.match(request).then(cached => cached || caches.match("/mobile.html")))
  );
});