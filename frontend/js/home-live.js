(function initHomeLive(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  const $ = id => document.getElementById(id);
  const LIVE_CODES = new Set(["1H","2H","ET","P","LIVE","BT"]);
  const HALF_CODES = new Set(["HT","INT"]);
  const SCHEDULED_CODES = new Set(["NS","TBD"]);
  const FINISHED_CODES = new Set(["FT","AET","PEN"]);

  function clean(value, fallback=""){
    const text = String(value ?? "").trim();
    return text || fallback;
  }

  function matchId(match){
    return match?.match_id || match?.fixture_id || match?.id || null;
  }

  function statusInfo(match){
    const code = clean(match?.status || match?.fixture_status, "LIVE").toUpperCase();
    const minute = Number(match?.minute ?? match?.elapsed ?? 0) || 0;
    if(HALF_CODES.has(code)) return {code, label:"Intervallo", className:"half", rank:1, detail:"Intervallo"};
    if(FINISHED_CODES.has(code)) return {code, label:"Terminata", className:"finished", rank:3, detail:"Terminata"};
    if(LIVE_CODES.has(code) || minute > 0) return {code, label:"Live", className:"live", rank:0, detail:minute > 0 ? `${minute}'` : clean(match?.status_long,"In corso")};
    if(SCHEDULED_CODES.has(code)) return {code, label:"In programma", className:"scheduled", rank:2, detail:clean(match?.status_long,"In programma")};
    return {code, label:clean(match?.status_long, code), className:"scheduled", rank:2, detail:clean(match?.status_long, code)};
  }

  H.normalizeLiveMatch = function(match){
    const status = statusInfo(match);
    const id = matchId(match);
    const homeGoals = match?.home_goals ?? match?.score_obj?.home ?? 0;
    const awayGoals = match?.away_goals ?? match?.score_obj?.away ?? 0;
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
      date:match?.fixture_date || match?.date || match?.kickoff || "",
      url:id ? (() => {
        const candidate=clean(match?.url_match);
        return candidate.startsWith("/") ? candidate : `/match.html?id=${encodeURIComponent(id)}&v=${window.MATCHIQ_APP_VERSION || "10502"}`;
      })() : ""
    };
  };

  H.applyLivePayload = function(payload){
    const raw = Array.isArray(payload) ? payload : (payload?.matches || payload?.data || payload?.live_matches || []);
    const matches = (Array.isArray(raw) ? raw : [])
      .filter(item => item && typeof item === "object" && matchId(item))
      .map(H.normalizeLiveMatch)
      .sort((a,b) => a.status.rank - b.status.rank || (b.status.detail.localeCompare(a.status.detail)));
    H.state.live = {
      ...H.state.live,
      loading:false,
      matches,
      error:matches.length ? "" : clean(payload?.error),
      source:clean(payload?.source,"api-football")
    };
  };

  function createText(tag, value, className=""){
    const node=document.createElement(tag);
    if(className) node.className=className;
    node.textContent=value;
    return node;
  }

  function teamNode(name, logo, side){
    const team=document.createElement("div"); team.className=`live-team ${side}`;
    if(logo){
      const image=document.createElement("img"); image.src=logo; image.alt=""; image.width=34; image.height=34;
      image.addEventListener("error",()=>image.remove(),{once:true}); team.append(image);
    }
    team.append(createText("strong",name));
    return team;
  }

  function matchCard(match){
    const card=document.createElement("article"); card.className="live-match-card";
    const head=document.createElement("div"); head.className="live-match-head";
    head.append(createText("span",match.country ? `${match.league} · ${match.country}` : match.league,"live-league"));
    head.append(createText("span",match.status.label,`live-badge ${match.status.className}`));
    const score=document.createElement("div"); score.className="live-score-row";
    score.append(teamNode(match.home,match.homeLogo,"home"),createText("strong",match.score,"live-score"),teamNode(match.away,match.awayLogo,"away"));
    const foot=document.createElement("div"); foot.className="live-match-foot";
    const details=[match.status.detail];
    if(match.date){ const date=new Date(match.date); if(!Number.isNaN(date.getTime())) details.push(H.formatDate(date)); }
    foot.append(createText("span",details.join(" · "),"live-detail"));
    if(match.url){
      const action=document.createElement("a"); action.className="button button-muted"; action.href=match.url;
      action.textContent=match.status.className === "live" || match.status.className === "half" ? "Segui partita" : "Apri analisi";
      action.setAttribute("aria-label",`${action.textContent}: ${match.home} contro ${match.away}`); foot.append(action);
    }
    card.append(head,score,foot); return card;
  }

  H.renderLiveMatches = function(){
    const live=H.state.live;
    const list=$("liveMatchesList");
    const summary=$("liveSummary");
    const moreRow=$("liveMoreRow");
    if(!list || !summary || !moreRow) return;
    list.replaceChildren(); list.setAttribute("aria-busy",String(Boolean(live.loading)));
    if(live.loading){
      summary.textContent="Caricamento partite...";
      for(let i=0;i<3;i++) list.append(createText("div","","skeleton-card"));
      moreRow.hidden=true; return;
    }
    if(!live.matches.length){
      summary.textContent="Nessuna partita disponibile";
      const message=live.error ? "Le partite live non sono disponibili in questo momento." : "Non ci sono partite live disponibili ora.";
      list.append(H.emptyState("Partite Live",message));
      moreRow.hidden=true; return;
    }
    const accountLimit=Number(H.state.account?.limits?.max_live_matches || live.matches.length) || live.matches.length;
    const previewLimit=Math.max(1,Math.min(5,accountLimit));
    const visible=live.expanded ? live.matches.slice(0,accountLimit) : live.matches.slice(0,previewLimit);
    summary.textContent=`${live.matches.length} ${live.matches.length === 1 ? "partita disponibile" : "partite disponibili"}`;
    visible.forEach(match => list.append(matchCard(match)));
    moreRow.hidden=live.matches.length <= previewLimit;
    const button=moreRow.querySelector("[data-live-more]");
    if(button) button.textContent=live.expanded ? "Mostra anteprima" : "Vedi tutte le partite";
  };
})();
