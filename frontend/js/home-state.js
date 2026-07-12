(function initHomeState(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  const LOCAL_OWNER_KEY = "matchiq_home_local_owner_v1";

  H.state = {
    loading: true,
    account: {plan:"guest", label:"Guest", is_owner:false, limits:{}},
    user: null,
    remote: {stats:{}, stats_available:{}, continue_items:[], activities:[], ai_priorities:[], section_errors:[]},
    local: {coachHistory:[], coachCurrent:null, scoutWatchlist:[]},
    localOwnershipMismatch: false,
    live: {loading:true, matches:[], error:"", expanded:false, source:""},
    error: ""
  };

  H.readJson = function(key, fallback){
    try{
      const raw = localStorage.getItem(key) || sessionStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    }catch(_error){ return fallback; }
  };

  H.userScope = function(user=H.state.user){
    return String(user?.id || user?.user_id || user?.email || "").trim().toLowerCase();
  };

  H.hasAuthSession = function(){
    try{
      return Boolean(
        localStorage.getItem("matchiq_auth_token")
        || sessionStorage.getItem("matchiq_auth_token")
        || window.MatchIQAuth?.isLoggedIn?.()
      );
    }catch(_error){ return Boolean(window.MatchIQAuth?.isLoggedIn?.()); }
  };

  H.loadLocalContext = function(){
    const user = H.readJson("matchiq_auth_user", null) || H.readJson("matchiq_user", null);
    H.state.user = user && typeof user === "object" ? user : null;
    H.state.localOwnershipMismatch = false;
    const scope = H.userScope();
    if(!scope || !H.hasAuthSession()){
      H.state.local = {coachHistory:[], coachCurrent:null, scoutWatchlist:[]};
      return;
    }

    const coachHistory = H.readJson("matchiq_coach_history_v14", []);
    const coachCurrent = H.readJson("matchiq_coach_v13", null);
    const scoutWatchlist = H.readJson("matchiq_scout_watchlist_v803_hotfix3", []);
    const hasLocalData = (Array.isArray(coachHistory) && coachHistory.length)
      || Boolean(coachCurrent?.match)
      || (Array.isArray(scoutWatchlist) && scoutWatchlist.length);
    let storedOwner = "";
    try{
      storedOwner = String(localStorage.getItem(LOCAL_OWNER_KEY) || "").toLowerCase();
      if(!storedOwner && hasLocalData) localStorage.setItem(LOCAL_OWNER_KEY, scope);
    }catch(_error){ storedOwner = scope; }
    const canReadLocal = !storedOwner || storedOwner === scope;
    H.state.localOwnershipMismatch = Boolean(hasLocalData && storedOwner && !canReadLocal);

    H.state.local = canReadLocal ? {
      coachHistory: Array.isArray(coachHistory) ? coachHistory : [],
      coachCurrent: coachCurrent && typeof coachCurrent === "object" ? coachCurrent : null,
      scoutWatchlist: Array.isArray(scoutWatchlist) ? scoutWatchlist : []
    } : {coachHistory:[], coachCurrent:null, scoutWatchlist:[]};
  };

  H.userName = function(){
    const user = H.state.user || {};
    return String(user.name || user.full_name || user.first_name || user.nome || "").trim();
  };

  H.plan = function(){
    return String(H.state.account?.plan || H.state.user?.plan || H.state.user?.piano || "guest").toLowerCase();
  };

  H.isAuthenticated = function(){
    return Boolean(H.state.user && H.hasAuthSession());
  };

  H.isOwner = function(){
    const user = H.state.user || {};
    const email = String(user.email || "").toLowerCase();
    return H.state.account?.is_owner === true || H.plan() === "owner" || ["owner","admin"].includes(String(user.role || "").toLowerCase()) || email === "mario.costabile92@outlook.it";
  };

  H.formatDate = function(value){
    if(!value) return "Data non disponibile";
    const date = new Date(value);
    if(Number.isNaN(date.getTime())) return "Data non disponibile";
    return new Intl.DateTimeFormat("it-IT", {day:"2-digit", month:"short", hour:"2-digit", minute:"2-digit"}).format(date);
  };

  H.coachFingerprint = function(item){
    const match = item?.match || {};
    const meta = item?.metadata || {};
    const home = String(match.homeTeam || meta.homeTeam || "casa").trim().toLowerCase();
    const away = String(match.awayTeam || meta.awayTeam || "trasferta").trim().toLowerCase();
    const date = String(match.date || meta.date || "").slice(0,10);
    return `${home}|${away}|${date}`;
  };

  H.coachItem = function(item, current=false){
    const match = item?.match || {};
    const meta = item?.metadata || {};
    const home = match.homeTeam || meta.homeTeam || "Casa";
    const away = match.awayTeam || meta.awayTeam || "Trasferta";
    const updated = item?.savedAt || item?.updatedAt || match.date || null;
    const fingerprint = H.coachFingerprint(item);
    return {
      id:current ? `current:${fingerprint}` : (item?.id || `history:${fingerprint}`),
      record_key:`coach_match:${fingerprint}`,
      kind:"coach_match", module:"Coach", title:`${home} - ${away}`,
      status:current ? "Partita in lavorazione" : "Salvata nello storico",
      created_at:updated, updated_at:updated, url:current ? "/coach.html" : "", action:current ? "Continua" : "",
      current
    };
  };

  H.dedupeItems = function(items){
    const seen = new Set();
    return items.filter(item => {
      if(!item || !item.kind) return false;
      const key = String(item.record_key || `${item.kind}:${item.id}`);
      if(seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };

  H.deriveHomeBrief = function(current, priorities){
    if(H.state.loading) return {eyebrow:"Aggiornamento", title:"Sto sincronizzando il tuo lavoro.", lead:"Recupero attività, Sessioni Video e partite disponibili senza bloccare i moduli."};
    if(current){
      const live = H.state.local.coachCurrent?.live || {};
      const report = String(H.state.local.coachCurrent?.report || "").trim();
      if(live.running) return {eyebrow:"Match Day live", title:"La partita è in corso.", lead:`Continua ${current.title} dal Coach e registra soltanto ciò che serve allo staff.`};
      if(H.state.local.coachCurrent?.phase === "post" && !report) return {eyebrow:"Post-partita", title:"Completa il lavoro dopo la gara.", lead:`${current.title} è pronta per pagelle, report e indicazioni per il prossimo allenamento.`};
      return {eyebrow:"Prossima priorità", title:"Riprendi la partita in preparazione.", lead:`Continua ${current.title} senza perdere eventi, formazione e note già inserite.`};
    }
    const first = priorities[0];
    if(first) return {eyebrow:"Prossima priorità", title:first.title, lead:first.text || "Apri l'attività e continua da dove eri rimasto."};
    return H.isAuthenticated()
      ? {eyebrow:"Tutto pronto", title:"Scegli da dove iniziare.", lead:"Crea una partita, carica un video oppure consulta le partite disponibili."}
      : {eyebrow:"Benvenuto", title:"Il tuo lavoro tecnico, in un solo posto.", lead:"Accedi per ritrovare attività, report e Sessioni Video del tuo account."};
  };

  H.mergeData = function(){
    const remote = H.state.remote || {};
    const local = H.state.local || {};
    const current = local.coachCurrent?.match ? H.coachItem(local.coachCurrent, true) : null;
    const currentFingerprint = current ? H.coachFingerprint(local.coachCurrent) : "";
    const coachHistory = local.coachHistory
      .filter(item => !currentFingerprint || H.coachFingerprint(item) !== currentFingerprint)
      .slice(0,5)
      .map(item => H.coachItem(item));

    const activities = H.dedupeItems([...(remote.activities || []), ...(current ? [current] : []), ...coachHistory])
      .sort((a,b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0));
    const continueItems = H.dedupeItems([...(current ? [current] : []), ...(remote.continue_items || [])]).slice(0,3);

    const stats = {...(remote.stats || {})};
    const available = {...(remote.stats_available || {})};
    if(H.isAuthenticated()){
      stats.coach_matches = local.coachHistory.length + (current ? 1 : 0);
      available.coach_matches = true;
      if(local.scoutWatchlist.length){
        stats.players_observed = available.players_observed
          ? Math.max(Number(stats.players_observed || 0), local.scoutWatchlist.length)
          : local.scoutWatchlist.length;
        available.players_observed = true;
      }
    }
    if(!H.state.live.loading && !H.state.live.error){
      stats.live_matches = H.state.live.matches.length;
      available.live_matches = true;
    }else{
      stats.live_matches = null;
      available.live_matches = false;
    }

    const priorities = [...(remote.ai_priorities || [])];
    if(H.state.live.matches.length){
      priorities.push({
        type:"system", title:"Partite live disponibili",
        text:`${H.state.live.matches.length} ${H.state.live.matches.length === 1 ? "partita è disponibile" : "partite sono disponibili"} nel modulo Match.`,
        url:"#liveMatchesSection", action:"Vedi Partite Live"
      });
    }
    if(current){
      const ratings = Array.isArray(local.coachCurrent?.ratings) ? local.coachCurrent.ratings.length : 0;
      const report = String(local.coachCurrent?.report || "").trim();
      priorities.unshift({
        type:"operational", title:report ? "Partita Coach pronta da riaprire" : "Partita Coach da completare",
        text:report ? current.title : `${current.title}${ratings ? ` · ${ratings} pagelle inserite` : ""}`,
        url:"/coach.html", action:report ? "Riapri partita" : "Continua in Coach"
      });
    }
    const uniquePriorities = H.dedupeItems(priorities.map((item,index) => ({...item, kind:"priority", id:item.url || `${item.title}:${index}`, record_key:`priority:${item.url || item.title}`}))).slice(0,3);

    H.state.view = {
      stats,
      statsAvailable:available,
      activities:activities.slice(0,8),
      continueItems,
      priorities:uniquePriorities,
      brief:H.deriveHomeBrief(current, uniquePriorities)
    };
    return H.state.view;
  };
})();
