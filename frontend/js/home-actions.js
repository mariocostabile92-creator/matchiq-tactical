(function initHomeActions(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  H.bindActions = function(){
    document.querySelectorAll("[data-home-retry]").forEach(button => button.addEventListener("click", async () => {
      button.disabled=true; button.textContent="…";
      try{ await H.loadHomeData(); H.renderHome(); }
      finally{ button.disabled=false; button.textContent="↻"; }
    }));
    document.querySelectorAll("[data-live-retry]").forEach(button => button.addEventListener("click", async () => {
      button.disabled=true; button.textContent="Caricamento...";
      try{ await H.loadLiveMatches(); H.mergeData(); H.renderHome(); }
      finally{ button.disabled=false; button.textContent="Riprova"; }
    }));
    document.querySelectorAll("[data-live-more]").forEach(button => button.addEventListener("click", () => {
      H.state.live.expanded=!H.state.live.expanded;
      H.renderLiveMatches();
      document.getElementById("liveMatchesSection")?.scrollIntoView({behavior:"smooth",block:"start"});
    }));
  };
})();
