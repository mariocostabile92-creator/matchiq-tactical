const CACHE_NAME = "matchiq-pwa-v109";
const APP_SHELL = [
  "/index.html?v=10509",
  "/mobile.html?v=10509",
  "/weekly-briefing.html",
  "/pattern-intelligence.html",
  "/training-planner.html",
  "/knowledge.html",
  "/tactical-assistant.html",
  "/privacy.html",
  "/terms.html",
  "/cookies.html",
  "/js/app-meta.js",
  "/css/home.css?v=10503",
  "/css/weekly-briefing.css?v=10505",
  "/css/weekly-briefing-home.css?v=10505",
  "/css/pattern-intelligence.css?v=10506",
  "/css/pattern-intelligence-home.css?v=10506",
  "/css/training-planner.css?v=10507",
  "/css/training-planner-order.css?v=10507",
  "/css/training-planner-home.css?v=10507",
  "/css/knowledge-intelligence.css?v=10508",
  "/css/knowledge-entry.css?v=10508",
  "/css/tactical-assistant.css?v=10509",
  "/css/tactical-assistant-entry.css?v=10509",
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
  "/js/training-planner-state.js?v=10507",
  "/js/training-planner-api.js?v=10507",
  "/js/training-planner-render.js?v=10507",
  "/js/training-planner-editor.js?v=10507",
  "/js/training-planner-order.js?v=10507",
  "/js/training-planner.js?v=10507",
  "/js/training-planner-home.js?v=10507",
  "/js/training-planner-weekly.js?v=10507",
  "/js/coach-training-planner.js?v=10507",
  "/js/knowledge-intelligence-state.js?v=10508",
  "/js/knowledge-intelligence-api.js?v=10508",
  "/js/knowledge-intelligence-render.js?v=10508",
  "/js/knowledge-intelligence-detail.js?v=10508",
  "/js/knowledge-intelligence-query.js?v=10508",
  "/js/knowledge-intelligence.js?v=10508",
  "/js/knowledge-entry.js?v=10508",
  "/js/tactical-assistant-state.js?v=10509",
  "/js/tactical-assistant-api.js?v=10509",
  "/js/tactical-assistant-sources.js?v=10509",
  "/js/tactical-assistant-render.js?v=10509",
  "/js/tactical-assistant-conversations.js?v=10509",
  "/js/tactical-assistant-feedback.js?v=10509",
  "/js/tactical-assistant.js?v=10509",
  "/js/tactical-assistant-entry.js?v=10509",
  "/js/tactical-assistant-context.js?v=10509",
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
        .catch(() => caches.match(request).then(cached => cached || caches.match("/index.html?v=10509")))
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
