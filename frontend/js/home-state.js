(function initHomeState(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  H.state = {
    loading: true,
    account: {plan:"guest", label:"Guest", is_owner:false, limits:{}},
    user: null,
    remote: {stats:{}, continue_items:[], activities:[], ai_priorities:[], section_errors:[]},
    local: {coachHistory:[], coachCurrent:null, scoutWatchlist:[]},
    live: {loading:true, matches:[], error:"", expanded:false, source:""},
    error: ""
  };

  H.readJson = function(key, fallback){
    try{
      const raw = localStorage.getItem(key) || sessionStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    }catch(_error){ return fallback; }
  };

  H.loadLocalContext = function(){
    const user = H.readJson("matchiq_auth_user", null) || H.readJson("matchiq_user", null);
    const coachHistory = H.readJson("matchiq_coach_history_v14", []);
    const coachCurrent = H.readJson("matchiq_coach_v13", null);
    const scoutWatchlist = H.readJson("matchiq_scout_watchlist_v803_hotfix3", []);
    H.state.user = user && typeof user === "object" ? user : null;
    H.state.local = {
      coachHistory: Array.isArray(coachHistory) ? coachHistory : [],
      coachCurrent: coachCurrent && typeof coachCurrent === "object" ? coachCurrent : null,
      scoutWatchlist: Array.isArray(scoutWatchlist) ? scoutWatchlist : []
    };
  };

  H.userName = function(){
    const user = H.state.user || {};
    return String(user.name || user.full_name || user.first_name || user.nome || "").trim();
  };

  H.plan = function(){
    return String(H.state.account?.plan || H.state.user?.plan || H.state.user?.piano || "guest").toLowerCase();
  };

  H.isAuthenticated = function(){
    return Boolean(H.state.user || window.MatchIQAuth?.isLoggedIn?.());
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

  H.coachItem = function(item, current=false){
    const match = item?.match || {};
    const meta = item?.metadata || {};
    const home = match.homeTeam || meta.homeTeam || "Casa";
    const away = match.awayTeam || meta.awayTeam || "Trasferta";
    const updated = item?.savedAt || match.date || null;
    return {
      id:item?.id || "coach-current", kind:"coach_match", module:"Coach",
      title:`${home} - ${away}`, status:current ? "Partita in lavorazione" : "Salvata nello storico",
      created_at:updated, updated_at:updated, url:"/coach.html", action:"Continua"
    };
  };

  H.mergeData = function(){
    const remote = H.state.remote || {};
    const local = H.state.local || {};
    const coachItems = local.coachHistory.slice(0, 5).map(item => H.coachItem(item));
    const current = local.coachCurrent?.match ? H.coachItem(local.coachCurrent, true) : null;
    const all = [...(remote.activities || []), ...coachItems];
    if(current) all.push(current);
    all.sort((a,b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0));
    const unique = [];
    const seen = new Set();
    all.forEach(item => {
      const key = `${item.kind}:${item.id}`;
      if(!seen.has(key)){ seen.add(key); unique.push(item); }
    });

    const stats = {...(remote.stats || {})};
    stats.coach_matches = local.coachHistory.length + (current ? 1 : 0);
    stats.players_observed = Math.max(Number(stats.players_observed || 0), local.scoutWatchlist.length);
    stats.live_matches = H.state.live.matches.length;

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

    H.state.view = {
      stats,
      activities:unique.slice(0, 8),
      continueItems:unique.slice(0, 3),
      priorities:priorities.slice(0, 3)
    };
    return H.state.view;
  };
})();
