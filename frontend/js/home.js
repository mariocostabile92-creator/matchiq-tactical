(async function bootMatchIqHome(){
  const H = window.MatchIQHome;
  if(!H) return;
  H.loadLocalContext();
  H.mergeData();
  H.renderHome();
  H.bindActions();
  H.bindOnboarding?.();
  try{
    await H.loadHomeData();
  }catch(error){
    H.state.error="Non riesco ad aggiornare tutti i dati della Home. Puoi comunque aprire i moduli.";
    console.warn("[MatchIQ Home] Aggiornamento parziale", error);
  }
  H.renderHome();
  window.setTimeout(()=>H.openOnboarding?.(),250);
  if("serviceWorker" in navigator){
    navigator.serviceWorker.register("/service-worker.js").catch(error => console.warn("Service worker non disponibile", error));
  }
})();
