const CACHE_NAME = "matchiq-pwa-v106";
const APP_SHELL = [
  "/index.html?v=10506",
  "/mobile.html?v=10506",
  "/weekly-briefing.html",
  "/pattern-intelligence.html",
  "/privacy.html",
  "/terms.html",
  "/cookies.html",
  "/js/app-meta.js",
  "/css/home.css?v=10503",
  "/css/weekly-briefing.css?v=10505",
  "/css/weekly-briefing-home.css?v=10505",
  "/css/pattern-intelligence.css?v=10506",
  "/css/pattern-intelligence-home.css?v=10506",
  "/css/global-nav.css?v=10503",
  "/js/auth.js?v=10503",
  "/js/global-nav-config.js?v=10503",
  "/js/global-nav-state.js?v=10503",
  "/js/global-nav-render.js?v=10503",
  "/js/global-nav-menu.js?v=10503",
  "/js/home-state.js?v=10503",
  "/js/home-api.js?v=10503",
  "/js/home-render.js?v=10503",
  "/js/home-live.js?v=10503",
  "/js/home-actions.js?v=10503",
  "/js/home-onboarding.js?v=10503",
  "/js/home.js?v=10503",
  "/js/weekly-briefing-state.js?v=10505",
  "/js/weekly-briefing-api.js?v=10505",
  "/js/weekly-briefing-render.js?v=10506",
  "/js/weekly-briefing.js?v=10505",
  "/js/weekly-briefing-home.js?v=10505",
  "/js/pattern-intelligence-state.js?v=10506",
  "/js/pattern-intelligence-api.js?v=10506",
  "/js/pattern-intelligence-filters.js?v=10506",
  "/js/pattern-intelligence-render.js?v=10506",
  "/js/pattern-intelligence-pagination.js?v=10506",
  "/js/pattern-intelligence-detail.js?v=10506",
  "/js/pattern-intelligence.js?v=10506",
  "/js/pattern-intelligence-home.js?v=10506",
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
        .catch(() => caches.match(request).then(cached => cached || caches.match("/index.html?v=10506")))
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
