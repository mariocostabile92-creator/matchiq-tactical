(function initHomeApi(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  H.authHeaders = function(){
    if(window.MatchIQAuth?.authHeaders) return window.MatchIQAuth.authHeaders();
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
    return token ? {Authorization:`Bearer ${token}`} : {};
  };

  H.fetchJson = async function(url){
    const response = await fetch(url, {headers:{Accept:"application/json", ...H.authHeaders()}, cache:"no-store"});
    if(!response.ok){
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload?.detail?.message || payload?.detail || `Errore ${response.status}`);
    }
    return response.json();
  };

  H.loadHomeData = async function(){
    H.state.loading = true;
    H.state.error = "";
    const [accountResult, summaryResult] = await Promise.allSettled([
      H.fetchJson(`/api/account/limits?ts=${Date.now()}`),
      H.fetchJson(`/api/home/summary?ts=${Date.now()}`)
    ]);

    if(accountResult.status === "fulfilled"){
      const data = accountResult.value || {};
      H.state.account = {
        plan:data.effective_plan || data.plan || "guest",
        label:data.label || data.effective_plan || data.plan || "Guest",
        is_owner:data.is_owner === true,
        limits:data.limits || data.features || {}
      };
    }
    if(summaryResult.status === "fulfilled"){
      H.state.remote = summaryResult.value || H.state.remote;
      if(summaryResult.value?.account){ H.state.account = {...H.state.account, ...summaryResult.value.account}; }
    }else{
      H.state.error = "Alcuni dati personali non sono disponibili. I collegamenti ai moduli restano attivi.";
      H.state.remote = {stats:{}, continue_items:[], activities:[], ai_priorities:[], section_errors:["home_summary"]};
    }
    H.state.loading = false;
    return H.mergeData();
  };
})();
