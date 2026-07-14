const CACHE_NAME = "matchiq-pwa-v121";
const APP_SHELL = [
  "/index.html?v=10521",
  "/mobile.html?v=10521",
  "/weekly-briefing.html",
  "/pattern-intelligence.html",
  "/training-planner.html",
  "/knowledge.html",
  "/tactical-assistant.html",
  "/tactical-identity.html",
  "/decision-engine.html",
  "/club-intelligence.html",
  "/privacy.html",
  "/terms.html",
  "/cookies.html",
  "/js/app-meta.js",
  "/css/components.css?v=10521",
  "/js/ux-hardening.js?v=10521",
  "/css/home.css?v=10521",
  "/css/home-intelligence.css?v=10521",
  "/css/weekly-briefing.css?v=10521",
  "/css/weekly-briefing-home.css?v=10521",
  "/css/pattern-intelligence.css?v=10521",
  "/css/pattern-intelligence-home.css?v=10521",
  "/css/training-planner.css?v=10521",
  "/css/training-planner-order.css?v=10521",
  "/css/training-planner-home.css?v=10521",
  "/css/knowledge-intelligence.css?v=10521",
  "/css/knowledge-entry.css?v=10521",
  "/css/tactical-assistant.css?v=10521",
  "/css/tactical-assistant-layout.css?v=10521",
  "/css/tactical-assistant-entry.css?v=10521",
  "/css/tactical-identity.css?v=10521",
  "/css/tactical-identity-entry.css?v=10521",
  "/css/decision-engine.css?v=10521",
  "/css/decision-engine-entry.css?v=10521",
  "/css/club-intelligence.css?v=10521",
  "/css/club-intelligence-entry.css?v=10521",
  "/css/global-nav.css?v=10521",
  "/js/auth.js?v=10521",
  "/js/safe-render.js?v=10521",
  "/js/global-nav-config.js?v=10521",
  "/js/global-nav-state.js?v=10521",
  "/js/global-nav-render.js?v=10521",
  "/js/global-nav-menu.js?v=10521",
  "/js/home-state.js?v=10521",
  "/js/home-api.js?v=10521",
  "/js/home-render.js?v=10521",
  "/js/home-live.js?v=10521",
  "/js/home-actions.js?v=10521",
  "/js/home-onboarding.js?v=10521",
  "/js/home.js?v=10521",
  "/js/home-intelligence.js?v=10521",
  "/js/weekly-briefing-state.js?v=10521",
  "/js/weekly-briefing-api.js?v=10521",
  "/js/weekly-briefing-render.js?v=10521",
  "/js/weekly-briefing.js?v=10521",
  "/js/weekly-briefing-home.js?v=10521",
  "/js/pattern-intelligence-state.js?v=10521",
  "/js/pattern-intelligence-api.js?v=10521",
  "/js/pattern-intelligence-filters.js?v=10521",
  "/js/pattern-intelligence-render.js?v=10521",
  "/js/pattern-intelligence-pagination.js?v=10521",
  "/js/pattern-intelligence-detail.js?v=10521",
  "/js/pattern-intelligence.js?v=10521",
  "/js/pattern-intelligence-home.js?v=10521",
  "/js/training-planner-state.js?v=10521",
  "/js/training-planner-api.js?v=10521",
  "/js/training-planner-render.js?v=10521",
  "/js/training-planner-editor.js?v=10521",
  "/js/training-planner-order.js?v=10521",
  "/js/training-planner.js?v=10521",
  "/js/training-planner-home.js?v=10521",
  "/js/training-planner-weekly.js?v=10521",
  "/js/coach-training-planner.js?v=10521",
  "/js/knowledge-intelligence-state.js?v=10521",
  "/js/knowledge-intelligence-api.js?v=10521",
  "/js/knowledge-intelligence-render.js?v=10521",
  "/js/knowledge-intelligence-detail.js?v=10521",
  "/js/knowledge-intelligence-query.js?v=10521",
  "/js/knowledge-intelligence.js?v=10521",
  "/js/knowledge-entry.js?v=10521",
  "/js/tactical-assistant-state.js?v=10521",
  "/js/tactical-assistant-api.js?v=10521",
  "/js/tactical-assistant-sources.js?v=10521",
  "/js/tactical-assistant-render.js?v=10521",
  "/js/tactical-assistant-conversations.js?v=10521",
  "/js/tactical-assistant-feedback.js?v=10521",
  "/js/tactical-assistant.js?v=10521",
  "/js/tactical-assistant-entry.js?v=10521",
  "/js/tactical-assistant-context.js?v=10521",
  "/js/tactical-identity-state.js?v=10521",
  "/js/tactical-identity-api.js?v=10521",
  "/js/tactical-identity-render.js?v=10521",
  "/js/tactical-identity-detail.js?v=10521",
  "/js/tactical-identity-validation.js?v=10521",
  "/js/tactical-identity.js?v=10521",
  "/js/tactical-identity-entry.js?v=10521",
  "/js/decision-engine-state.js?v=10521",
  "/js/decision-engine-api.js?v=10521",
  "/js/decision-engine-situation.js?v=10521",
  "/js/decision-engine-options.js?v=10521",
  "/js/decision-engine-sources.js?v=10521",
  "/js/decision-engine-history.js?v=10521",
  "/js/decision-engine.js?v=10521",
  "/js/decision-engine-entry.js?v=10521",
  "/js/club-intelligence-state.js?v=10521",
  "/js/club-intelligence-api.js?v=10521",
  "/js/club-intelligence-render.js?v=10521",
  "/js/club-intelligence.js?v=10521",
  "/js/club-intelligence-entry.js?v=10521",
  "/manifest.json",
  "/assets/matchiq-logo.png"
];

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => Promise.allSettled(APP_SHELL.map(path => cache.add(path))))
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
  const sensitiveExtension = /\.(?:pdf|mp4|webm|mov|avi|mp3|wav|m4a|ogg|csv)$/i.test(url.pathname);
  const staticExtension = /\.(?:css|js|png|jpg|jpeg|webp|gif|svg|ico|woff2?)$/i.test(url.pathname);

  if(request.method !== "GET" || url.pathname.startsWith("/api/") || sensitiveExtension){
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
        .catch(() => caches.match(request).then(cached => cached || caches.match("/index.html?v=10521")))
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then(response => {
        if(response.ok && url.origin === self.location.origin && staticExtension){
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
