(function initHomeState(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  const LOCAL_OWNER_KEY = "matchiq_home_local_owner_v1";

  H.state = {
    loading: true,
    account: {plan:"guest", label:"Guest", is_owner:false, limits:{}},
    user: null,
    remote: {stats:{}, stats_available:{}, continue_items:[], activities:[], ai_priorities:[], section_errors:[]},
    local: {coachHistory:[], coachCurrent:null},
    weekly: null,
    training: null,
    localOwnershipMismatch: false,
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
      H.state.local = {coachHistory:[], coachCurrent:null};
      return;
    }

    const coachHistory = H.readJson("matchiq_coach_history_v14", []);
    const coachCurrent = H.readJson("matchiq_coach_v13", null);
    const hasLocalData = (Array.isArray(coachHistory) && coachHistory.length)
      || Boolean(coachCurrent?.match);
    let storedOwner = "";
    try{
      storedOwner = String(localStorage.getItem(LOCAL_OWNER_KEY) || "").toLowerCase();
      if(!storedOwner && hasLocalData) localStorage.setItem(LOCAL_OWNER_KEY, scope);
    }catch(_error){ storedOwner = scope; }
    const canReadLocal = !storedOwner || storedOwner === scope;
    H.state.localOwnershipMismatch = Boolean(hasLocalData && storedOwner && !canReadLocal);

    H.state.local = canReadLocal ? {
      coachHistory: Array.isArray(coachHistory) ? coachHistory : [],
      coachCurrent: coachCurrent && typeof coachCurrent === "object" ? coachCurrent : null
    } : {coachHistory:[], coachCurrent:null};
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

  H.isMatchDayActive = function(current=H.state.local?.coachCurrent){
    if(!current?.match) return false;
    const live=current.live||{};
    return live.running===true || (Number(live.elapsed||0)>0 && live.completed!==true && live.finished!==true);
  };

  H.isCoachWorkIncomplete = function(current=H.state.local?.coachCurrent){
    if(!current?.match || H.isMatchDayActive(current)) return false;
    const hasWork=Boolean((current.events||[]).length || (current.lineup||[]).length || String(current.preNotes||current.match?.preNotes||"").trim());
    const hasFinalReport=Boolean(String(current.report||"").trim());
    return hasWork && !hasFinalReport;
  };

  H.contextForToday = function(){
    const current=H.state.local?.coachCurrent;
    const currentItem=current?.match?H.coachItem(current,true):null;
    const remotePriorities=H.state.remote?.ai_priorities||[];
    let hero={
      key:"prepare-match",kind:"preparation",eyebrow:"OGGI · PREPARAZIONE",title:"Prepara la prossima partita.",
      lead:"Imposta avversario, obiettivi e formazione per dare allo staff un punto di partenza condiviso.",
      statusTitle:"Nessuna urgenza aperta",statusText:"Puoi iniziare dalla preparazione della prossima gara.",
      action:"Prepara partita",url:"/coach.html#matchSetup"
    };
    if(H.isMatchDayActive(current)){
      hero={key:currentItem.record_key,kind:"match-day",eyebrow:"MATCH DAY ATTIVO",title:currentItem.title,lead:"La partita è in corso. Eventi, Voice Coach e note devono restare a portata di mano.",statusTitle:"Torna alla plancia",statusText:"Riprendi timer e raccolta eventi senza perdere il contesto.",action:"Apri Match Day",url:"/coach.html#matchDayWorkspace"};
    }else if(H.isCoachWorkIncomplete(current)){
      hero={key:currentItem.record_key,kind:"coach-work",eyebrow:"LAVORO DA RIPRENDERE",title:currentItem.title,lead:"La preparazione è iniziata ma non è ancora completa.",statusTitle:"Continua da dove eri rimasto",statusText:"Completa formazione, obiettivi o note prima della gara.",action:"Continua in Coach",url:"/coach.html"};
    }else if(remotePriorities.length){
      const item=remotePriorities[0];
      hero={key:`priority:${item.url||item.title}`,kind:"video",eyebrow:"VIDEO AI · ATTENZIONE",title:item.title,lead:item.text||"Una sessione Video AI richiede un controllo.",statusTitle:item.action||"Apri Video AI",statusText:"Controlla il progetto prima di passare al prossimo lavoro.",action:item.action||"Apri",url:item.url||"/video.html"};
    }
    return {hero,currentItem};
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

    const coachActivities = (remote.activities || []).filter(item => item?.kind !== "scout_report" && String(item?.module || "").toLowerCase() !== "scout");
    const activities = H.dedupeItems([...coachActivities, ...(current ? [current] : []), ...coachHistory])
      .sort((a,b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0));
    const today=H.contextForToday();
    const continueItems = H.dedupeItems([...(current ? [current] : []), ...(remote.continue_items || [])])
      .filter(item=>String(item.record_key||"")!==String(today.hero.key||""))
      .slice(0,3);

    const stats = {...(remote.stats || {})};
    const available = {...(remote.stats_available || {})};
    if(H.isAuthenticated()){
      stats.coach_matches = local.coachHistory.length + (current ? 1 : 0);
      available.coach_matches = true;
    }
    const priorities = [...(remote.ai_priorities || [])];
    if(current && String(today.hero.key)!==String(current.record_key)){
      const ratings = Array.isArray(local.coachCurrent?.ratings) ? local.coachCurrent.ratings.length : 0;
      const report = String(local.coachCurrent?.report || "").trim();
      priorities.unshift({
        type:"operational", title:report ? "Partita Coach pronta da riaprire" : "Partita Coach da completare",
        text:report ? current.title : `${current.title}${ratings ? ` · ${ratings} pagelle inserite` : ""}`,
        url:"/coach.html", action:report ? "Riapri partita" : "Continua in Coach"
      });
    }
    const uniquePriorities = H.dedupeItems(priorities.map((item,index) => ({...item, kind:"priority", id:item.url || `${item.title}:${index}`, record_key:`priority:${item.url || item.title}`})))
      .filter(item=>String(item.record_key)!==String(today.hero.key||""))
      .slice(0,4);

    H.state.view = {
      stats,
      statsAvailable:available,
      activities:activities.slice(0,8),
      continueItems,
      priorities:uniquePriorities,
      hero:today.hero
    };
    return H.state.view;
  };
})();
