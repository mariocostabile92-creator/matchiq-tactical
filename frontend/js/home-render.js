(function initHomeRender(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  const $ = id => document.getElementById(id);
  const text = (tag, value, className="") => {
    const node = document.createElement(tag);
    if(className) node.className = className;
    node.textContent = value;
    return node;
  };
  const link = (label, href, className="") => {
    const node = document.createElement("a");
    node.href = href;
    node.textContent = label;
    if(className) node.className = className;
    return node;
  };

  H.metric = function(key, value){
    const available = H.state.view?.statsAvailable || {};
    return available[key] === true && value !== null && value !== undefined ? value : "—";
  };

  H.emptyState = function(title, description, actions=[]){
    const box = document.createElement("div"); box.className = "empty-state";
    box.append(text("strong", title), text("p", description));
    if(actions.length){
      const row = document.createElement("div"); row.className = "empty-actions";
      actions.forEach(action => row.append(link(action.label, action.url, `button ${action.primary ? "button-primary" : "button-muted"}`)));
      box.append(row);
    }
    return box;
  };

  H.renderAccount = function(){
    const plan = H.plan();
    const owner = H.isOwner();
    const headerPlan = $("headerPlan");
    if(headerPlan){
      headerPlan.textContent = owner ? "Owner" : (H.state.account?.label || plan || "Guest");
      headerPlan.classList.toggle("owner", owner);
    }
    const adminNav = $("adminNav");
    if(adminNav) adminNav.hidden = !owner;
    const auth = $("authAction");
    if(auth){
      if(H.isAuthenticated()){ auth.textContent = "Account"; auth.href = "/account.html"; }
      else{ auth.textContent = "Accedi"; auth.href = "/login.html"; }
    }
    const badges = $("heroBadges"); badges.replaceChildren();
    const planBadge = text("span", owner ? "Owner Pro" : `${H.state.account?.label || plan} plan`, `badge ${owner ? "gold" : ""}`);
    badges.append(planBadge);
    const mode = window.matchMedia?.("(display-mode: standalone)")?.matches ? "PWA installata" : "Web app";
    badges.append(text("span", mode, "badge"));
    if(H.state.user?.trial_active || H.state.user?.is_trial) badges.append(text("span", "Trial attivo", "badge gold"));
  };

  H.renderModules = function(){
    const stats = H.state.view?.stats || {};
    const modules = [
      {id:"coach", icon:"▣", title:"Coach", description:"Prepara la partita, gestisci il Match Day e trasforma eventi, note e pagelle in indicazioni per il post-gara.", url:"/coach.html", action:"Apri Coach", meta:`${H.metric("coach_matches",stats.coach_matches)} partite locali`},
      {id:"video", icon:"▶", title:"Video AI", description:"Carica o riapri una Sessione Video, analizza partite e allenamenti, trova frame rilevanti e organizza tutto nel Video Hub.", url:"/video.html", action:"Apri Video AI", secondaryUrl:H.isAuthenticated()?"/video.html#hubArchivePane":"/login.html?next=/video.html%23hubArchivePane", secondaryAction:"Vai all'archivio", meta:`${H.metric("video_sessions",stats.video_sessions)} sessioni · ${H.metric("video_reports",stats.video_reports)} report`},
      {id:"live", icon:"●", title:"Partite Live", description:"Consulta le partite disponibili, apri quelle in corso e accedi all'analisi live del modulo Match.", url:"#liveMatchesSection", action:"Apri Partite Live", meta:`${H.metric("live_matches",stats.live_matches)} disponibili`},
      {id:"scout", icon:"⌕", title:"Scout", description:"Analizza profili, salva giocatori e individua opportunità utili per la squadra.", url:"/scout.html", action:"Apri Scout", meta:`${H.metric("players_observed",stats.players_observed)} profili salvati`}
    ];
    const grid = $("moduleGrid"); grid.replaceChildren();
    modules.forEach(item => {
      const card = document.createElement("article"); card.className="module-card"; card.dataset.module=item.id;
      card.append(text("div", item.icon, "module-icon"), text("h3", item.title), text("p", item.description));
      const meta = document.createElement("div"); meta.className="module-meta"; meta.append(text("span", item.meta));
      const actions=document.createElement("div"); actions.className="module-actions";
      actions.append(link(item.action, item.url, `button ${item.id === "coach" ? "button-primary" : "button-muted"}`));
      if(item.secondaryUrl) actions.append(link(item.secondaryAction,item.secondaryUrl,"module-secondary"));
      card.append(meta, actions);
      grid.append(card);
    });
  };

  H.renderStats = function(){
    const stats = H.state.view?.stats || {};
    const entries = [
      ["Partite Coach", H.metric("coach_matches",stats.coach_matches), "salvate su questo dispositivo"],
      ["Sessioni Video", H.metric("video_sessions",stats.video_sessions), "nel tuo Video Hub"],
      ["Report Video", H.metric("video_reports",stats.video_reports), "nel tuo archivio"],
      ["Partite Live", H.metric("live_matches",stats.live_matches), "disponibili nel modulo Match"],
      ["Giocatori", H.metric("players_observed",stats.players_observed), "osservati o salvati"],
      ["Piano", H.isOwner()?"Owner":(H.state.account?.label || H.plan()), "accesso attuale"]
    ];
    const grid = $("statsGrid"); grid.replaceChildren();
    entries.forEach(([label,value,caption]) => {
      const card=document.createElement("article"); card.className="stat-card";
      card.append(text("small",label),text("strong",value),text("span",caption)); grid.append(card);
    });
    $("statsCaption").textContent = H.isAuthenticated() ? "Dati personali e attività locali del dispositivo." : "Accedi per vedere archivio e attività personali.";
  };

  H.itemIcon = function(kind){ return ({coach_match:"C",video_session:"V",video_report:"AI",scout_report:"S"})[kind] || "•"; };

  H.renderContinue = function(){
    const box=$("continueList"); box.replaceChildren();
    if(H.state.loading){ box.append(text("div","Cerco le tue attività più recenti...","loading-row")); return; }
    const items=H.state.view?.continueItems || [];
    if(!items.length){ box.append(H.emptyState("Non hai ancora attività recenti.","Inizia creando la prima partita o caricando la prima Sessione Video.",[{label:"Crea partita",url:"/coach.html",primary:true},{label:"Carica video",url:"/video.html"}])); return; }
    items.forEach(item => {
      const row=document.createElement("article"); row.className="activity-item";
      const content=document.createElement("div"); content.append(text("strong",item.title || item.module),text("small",`${item.module} · ${item.status || "In lavorazione"} · ${H.formatDate(item.updated_at || item.created_at)}`));
      row.append(text("span",H.itemIcon(item.kind),"activity-icon"),content,link(item.action || "Continua",item.url || "/index.html")); box.append(row);
    });
  };

  H.renderAi = function(){
    const box=$("aiPriorities"); box.replaceChildren();
    if(H.state.loading){ box.append(text("div","Preparo una sintesi basata sui tuoi dati...","loading-row")); return; }
    const items=H.state.view?.priorities || [];
    if(!items.length){ box.append(H.emptyState("Nessuna priorità disponibile.","Completa una partita o analizza un video per ricevere una sintesi operativa.",[{label:"Apri Coach",url:"/coach.html",primary:true}])); return; }
    items.forEach(item => {
      const row=document.createElement("article"); row.className="priority-item";
      const typeLabel=item.type === "confirmed" ? "Dato certo" : item.type === "system" ? "Informazione di sistema" : "Stato operativo";
      const content=document.createElement("div"); content.append(text("span",typeLabel,"priority-type"),text("strong",item.title),text("small",item.text || ""));
      row.append(content,link(item.action || "Apri",item.url || "/index.html")); box.append(row);
    });
  };

  H.renderActivity = function(){
    const box=$("recentActivity"); box.replaceChildren();
    const items=H.state.view?.activities || [];
    if(!items.length){ box.append(H.emptyState("Nessuna attività registrata.","Le attività reali compariranno qui quando utilizzi Coach, Video Hub o Scout.")); return; }
    items.slice(0,6).forEach(item => {
      const row=document.createElement("article"); row.className="timeline-item";
      const content=document.createElement("div"); content.append(text("strong",item.title || item.module),text("small",`${item.module} · ${item.status || "Aggiornato"}`));
      row.append(text("span",H.itemIcon(item.kind),"activity-icon"),content,text("time",H.formatDate(item.updated_at || item.created_at),"timeline-time"));
      if(item.url && item.action) row.append(link(item.action,item.url,"timeline-action"));
      box.append(row);
    });
  };

  H.renderNotice = function(){
    const notice=$("homeNotice");
    const errors=H.state.remote?.section_errors || [];
    const messages=[];
    if(H.state.error) messages.push(H.state.error);
    else if(errors.length) messages.push("Alcune informazioni non sono disponibili; le altre sezioni restano utilizzabili.");
    if(H.state.localOwnershipMismatch) messages.push("Le attività locali associate a un altro account non vengono mostrate.");
    const message=messages.join(" ");
    notice.hidden=!message; notice.textContent=message;
  };

  H.renderHome = function(){
    H.renderAccount(); H.renderModules(); H.renderStats(); H.renderLiveMatches?.(); H.renderContinue(); H.renderAi(); H.renderActivity(); H.renderNotice();
    const latest=(H.state.view?.activities || []).find(item => item.kind === "video_report");
    if(latest) $("latestReportAction").href=latest.url;
  };
})();
