(function initHomeActions(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  H.bindActions = function(){
    document.querySelectorAll("[data-home-retry]").forEach(button => button.addEventListener("click", async () => {
      button.disabled=true; button.textContent="…";
      try{ await H.loadHomeData(); H.renderHome(); }
      finally{ button.disabled=false; button.textContent="↻"; }
    }));
  };
})();
