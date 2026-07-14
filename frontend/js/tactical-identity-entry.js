(function(){
  const path=location.pathname.toLowerCase(),token=localStorage.getItem("matchiq_auth_token")||sessionStorage.getItem("matchiq_auth_token");
  if(!token||document.getElementById("tacticalIdentityEntry"))return;
  const allowed=new Set(["/index.html","/","/coach.html","/weekly-briefing.html","/training-planner.html","/pattern-intelligence.html","/video.html"]);if(!allowed.has(path))return;
  const copyByPath={
    "/weekly-briefing.html":["CONTESTO IDENTITA","Il briefing puo leggere tratti consolidati e scostamenti nelle prossime generazioni."],
    "/training-planner.html":["CONTESTO IDENTITA","Scostamenti ed evoluzioni sono disponibili come contesto per i prossimi piani."],
    "/pattern-intelligence.html":["IDENTITA E PATTERN","Solo i pattern validi e affidabili contribuiscono alla Tactical Identity."],
    "/video.html":["IDENTITA E VIDEO AI","Contribuiscono soltanto analisi persistenti, collegate a una partita e sufficientemente affidabili."],
    "/coach.html":["IMPATTO SULL'IDENTITA TATTICA","La partita salvata sara valutata al prossimo aggiornamento dell'identita, senza bloccare il report Coach."],
  };
  const create=(data)=>{
    const section=document.createElement("section");section.id="tacticalIdentityEntry";section.className="identity-entry";section.setAttribute("aria-label","AI Tactical Identity");
    const empty=!data||data.status==="empty",dims=data?.dimensions||[],consolidated=dims.filter(item=>item.observed_value&&item.confidence_level==="alta").length,evolving=dims.filter(item=>["in_aumento","in_diminuzione","in_trasformazione"].includes(item.trend_direction)).length;
    const custom=copyByPath[path];section.dataset.state=empty?"empty":"ready";
    const copy=document.createElement("div");copy.className="identity-entry-copy";const label=document.createElement("small"),title=document.createElement("strong"),lead=document.createElement("span");label.textContent=custom?.[0]||"AI TACTICAL IDENTITY";title.textContent=empty?"Servono piu partite per costruire un'identita affidabile.":(custom?.[1]||`${consolidated} tratti consolidati - ${evolving} in evoluzione`);lead.textContent=empty?"MatchIQ non inventa: aggiorna l'identita quando esistono fonti reali.":(data.summary?.text||"Apri il profilo per verificare fonti, limiti e allineamento.");copy.append(label,title,lead);
    const action=document.createElement("a");action.href="/tactical-identity.html";action.textContent=empty?"Costruisci identita":"Apri identita";section.append(copy,action);return section;
  };
  const mount=(section)=>{
    if(path==="/coach.html"){
      const post=document.getElementById("coachPhasePost");if(!post)return false;post.prepend(section);return true;
    }
    if(path==="/index.html"||path==="/"){
      const grid=document.getElementById("homeIntelligenceGrid");if(!grid)return false;grid.appendChild(section);return true;
    }
    const host=path==="/weekly-briefing.html"?document.querySelector(".weekly-shell"):path==="/training-planner.html"?document.getElementById("trainingMain"):path==="/pattern-intelligence.html"?document.getElementById("patternMain"):document.querySelector("main,.wrap,.video-container");if(!host)return false;
    const anchor=host.children[2];host.insertBefore(section,anchor||null);return true;
  };
  fetch("/api/tactical-identity",{cache:"no-store",headers:{Authorization:`Bearer ${token}`,Accept:"application/json"}}).then(response=>response.ok?response.json():Promise.reject()).then(payload=>{const section=create(payload.data);if(!mount(section)&&path==="/coach.html"){const observer=new MutationObserver(()=>{if(mount(section))observer.disconnect()});observer.observe(document.body,{childList:true,subtree:true})}}).catch(()=>{});
})();
