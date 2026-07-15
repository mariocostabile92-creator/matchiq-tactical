(function initHomeApi(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  H.authHeaders = function(){
    if(window.MatchIQAuth?.authHeaders) return window.MatchIQAuth.authHeaders();
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
    return token ? {Authorization:`Bearer ${token}`} : {};
  };

  H.fetchJson = async function(url, timeoutMs=9000){
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try{
      const response = await fetch(url, {headers:{Accept:"application/json", ...H.authHeaders()}, cache:"no-store", signal:controller.signal});
      if(!response.ok){
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail?.message || payload?.detail || `Errore ${response.status}`);
      }
      return response.json();
    }catch(error){
      if(error?.name === "AbortError") throw new Error("Tempo di risposta scaduto");
      throw error;
    }finally{
      clearTimeout(timeout);
    }
  };

  H.loadHomeData = async function(){
    H.state.loading = true;
    H.state.error = "";
    H.loadLocalContext();
    const [accountResult, summaryResult, weeklyResult, trainingResult] = await Promise.allSettled([
      H.fetchJson(`/api/account/limits?ts=${Date.now()}`),
      H.fetchJson(`/api/home/summary?ts=${Date.now()}`),
      H.hasAuthSession() ? H.fetchJson(`/api/weekly-briefing/current?ts=${Date.now()}`) : Promise.resolve({briefing:null}),
      H.hasAuthSession() ? H.fetchJson(`/api/training-planner/current?ts=${Date.now()}`) : Promise.resolve({data:{plan:null}})
    ]);

    if(accountResult.status === "fulfilled"){
      const data = accountResult.value || {};
      H.state.account = {
        plan:data.effective_plan || data.plan || "guest",
        label:data.label || data.effective_plan || data.plan || "Guest",
        is_owner:data.is_owner === true,
        limits:data.limits || data.features || {}
      };
    }else if(H.isAuthenticated()){
      H.state.error = "Il piano account non è disponibile. Le attività personali restano accessibili.";
    }
    if(summaryResult.status === "fulfilled"){
      H.state.remote = summaryResult.value || H.state.remote;
      if(summaryResult.value?.account){
        H.state.account = {
          ...H.state.account,
          ...summaryResult.value.account,
          limits:{...(H.state.account?.limits || {}), ...(summaryResult.value.account?.limits || {})}
        };
      }
    }else{
      H.state.error = "Alcuni dati personali non sono disponibili. I collegamenti ai moduli restano attivi.";
      H.state.remote = {stats:{}, stats_available:{}, continue_items:[], activities:[], ai_priorities:[], section_errors:["home_summary"]};
    }
    H.state.weekly = weeklyResult.status === "fulfilled" ? (weeklyResult.value?.briefing || null) : null;
    H.state.training = trainingResult.status === "fulfilled" ? (trainingResult.value?.data?.plan || null) : null;
    H.state.loading = false;
    return H.mergeData();
  };
})();
