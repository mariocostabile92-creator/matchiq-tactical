(function initHomeActions(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  H.refreshHome = async function(){
    await H.loadHomeData();
    H.renderHome();
  };

  H.bindActions = function(){
    document.querySelectorAll("[data-home-retry]").forEach(button => button.addEventListener("click", async () => {
      button.disabled=true; button.textContent="…";
      try{ await H.refreshHome(); }
      finally{ button.disabled=false; button.textContent="↻"; }
    }));
    let lastResumeRefresh=0;
    const refreshAfterResume=async () => {
      if(document.visibilityState === "hidden" || Date.now() - lastResumeRefresh < 15000) return;
      lastResumeRefresh=Date.now();
      try{ await H.refreshHome(); }catch(_error){ /* Stato parziale già gestito dalla Home. */ }
    };
    window.addEventListener("pageshow",event => { if(event.persisted) refreshAfterResume(); });
    document.addEventListener("visibilitychange",refreshAfterResume);
  };
})();
