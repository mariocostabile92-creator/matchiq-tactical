(function initLivePage(){
  "use strict";

  const list=document.getElementById("liveMatchesList");
  const summary=document.getElementById("liveSummary");
  const retry=document.getElementById("liveRetry");
  const liveCodes=new Set(["1H","2H","ET","P","LIVE","BT"]);
  const halfCodes=new Set(["HT","INT"]);
  const finishedCodes=new Set(["FT","AET","PEN"]);

  function clean(value,fallback=""){
    const text=String(value ?? "").trim();
    return text || fallback;
  }

  function createText(tag,value,className=""){
    const node=document.createElement(tag);
    if(className) node.className=className;
    node.textContent=value;
    return node;
  }

  function matchId(match){
    return match?.match_id || match?.fixture_id || match?.id || null;
  }

  function statusInfo(match){
    const code=clean(match?.status || match?.fixture_status,"LIVE").toUpperCase();
    const minute=Number(match?.minute ?? match?.elapsed ?? 0) || 0;
    if(halfCodes.has(code)) return {label:"Intervallo",className:"half",rank:1,detail:"Intervallo"};
    if(finishedCodes.has(code)) return {label:"Terminata",className:"finished",rank:3,detail:"Terminata"};
    if(liveCodes.has(code) || minute > 0) return {label:"Live",className:"live",rank:0,detail:minute > 0 ? `${minute}'` : "In corso"};
    return {label:"In programma",className:"scheduled",rank:2,detail:clean(match?.status_long,"In programma")};
  }

  function normalize(match){
    const status=statusInfo(match);
    const id=matchId(match);
    const homeGoals=match?.home_goals ?? match?.score_obj?.home ?? 0;
    const awayGoals=match?.away_goals ?? match?.score_obj?.away ?? 0;
    return {
      id,
      home:clean(match?.home || match?.home_team,"Casa"),
      away:clean(match?.away || match?.away_team,"Trasferta"),
      homeLogo:clean(match?.home_logo),
      awayLogo:clean(match?.away_logo),
      league:clean(match?.league,"Competizione"),
      country:clean(match?.country),
      score:typeof match?.score === "string" ? match.score : `${Number(homeGoals)||0}-${Number(awayGoals)||0}`,
      status,
      url:id ? `/match.html?id=${encodeURIComponent(id)}&v=${window.MATCHIQ_APP_VERSION || "10524"}` : ""
    };
  }

  function teamNode(name,logo,side){
    const team=document.createElement("div");
    team.className=`live-team ${side}`;
    if(logo){
      const image=document.createElement("img");
      image.src=logo; image.alt=""; image.width=34; image.height=34;
      image.addEventListener("error",()=>image.remove(),{once:true});
      team.append(image);
    }
    team.append(createText("strong",name));
    return team;
  }

  function matchCard(match){
    const card=document.createElement("article");
    card.className="live-match-card";
    const head=document.createElement("div");
    head.className="live-match-head";
    head.append(createText("span",match.country ? `${match.league} · ${match.country}` : match.league,"live-league"));
    head.append(createText("span",match.status.label,`live-badge ${match.status.className}`));
    const score=document.createElement("div");
    score.className="live-score-row";
    score.append(teamNode(match.home,match.homeLogo,"home"),createText("strong",match.score,"live-score"),teamNode(match.away,match.awayLogo,"away"));
    const foot=document.createElement("div");
    foot.className="live-match-foot";
    foot.append(createText("span",match.status.detail,"live-detail"));
    if(match.url){
      const action=document.createElement("a");
      action.className="button button-muted";
      action.href=match.url;
      action.textContent="Segui partita";
      action.setAttribute("aria-label",`Segui partita: ${match.home} contro ${match.away}`);
      foot.append(action);
    }
    card.append(head,score,foot);
    return card;
  }

  function showMessage(title,message){
    list.replaceChildren();
    const panel=document.createElement("div");
    panel.className="empty-state";
    panel.append(createText("strong",title),createText("p",message));
    list.append(panel);
  }

  async function loadMatches(){
    retry.disabled=true;
    list.setAttribute("aria-busy","true");
    summary.textContent="Caricamento partite...";
    try{
      const headers=window.MatchIQAuth?.authHeaders?.() || {};
      const response=await fetch(`/api/live-matches?top_only=false&ts=${Date.now()}`,{headers:{Accept:"application/json",...headers},cache:"no-store"});
      if(!response.ok) throw new Error(`Errore ${response.status}`);
      const payload=await response.json();
      const raw=Array.isArray(payload) ? payload : (payload?.matches || payload?.data || payload?.live_matches || []);
      const matches=raw.filter(item => item && typeof item === "object" && matchId(item)).map(normalize).sort((a,b)=>a.status.rank-b.status.rank);
      list.replaceChildren();
      if(!matches.length){
        summary.textContent="Nessuna partita disponibile";
        showMessage("Partite Live","Non ci sono partite disponibili in questo momento.");
        return;
      }
      summary.textContent=`${matches.length} ${matches.length === 1 ? "partita disponibile" : "partite disponibili"}`;
      matches.forEach(match=>list.append(matchCard(match)));
    }catch(error){
      summary.textContent="Partite non disponibili";
      showMessage("Connessione non disponibile","Non riesco ad aggiornare le partite. Riprova tra poco.");
      console.warn("[MatchIQ Live]",error);
    }finally{
      retry.disabled=false;
      list.setAttribute("aria-busy","false");
    }
  }

  retry.addEventListener("click",loadMatches);
  loadMatches();
})();
