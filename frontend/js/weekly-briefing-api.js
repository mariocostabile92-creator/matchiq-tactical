(function initWeeklyBriefingApi(){
  const W=window.MatchIQWeekly;
  W.request=async function(url,options={}){
    const response=await fetch(url,{cache:"no-store",...options,headers:{...W.authHeaders(),...(options.headers||{})}});
    if(!response.ok){ const data=await response.json().catch(()=>({})); throw new Error(data?.detail?.message||data?.detail||`Errore ${response.status}`); }
    return response.json();
  };
  W.generate=()=>W.request("/api/weekly-briefing/generate",{method:"POST",body:JSON.stringify({local_sources:W.buildLocalSources(),timezone:"Europe/Rome"})});
  W.current=()=>W.request("/api/weekly-briefing/current");
  W.markRead=id=>W.request(`/api/weekly-briefing/${encodeURIComponent(id)}/read`,{method:"POST",body:"{}"});
})();
