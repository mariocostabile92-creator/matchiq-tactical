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
    const name = H.userName();
    $("headerPlan").textContent = owner ? "Owner" : (H.state.account?.label || plan || "Guest");
    $("headerPlan").classList.toggle("owner", owner);
    $("heroGreeting").textContent = name ? `Bentornato, ${name}` : "Bentornato in MatchIQ";
    $("adminNav").hidden = !owner;
    const auth = $("authAction");
    if(H.isAuthenticated()){ auth.textContent = "Account"; auth.href = "/account.html"; }
    else{ auth.textContent = "Accedi"; auth.href = "/login.html"; }
    const badges = $("heroBadges"); badges.replaceChildren();
    const planBadge = text("span", owner ? "Owner Pro" : `${H.state.account?.label || plan} plan`, `badge ${owner ? "gold" : ""}`);
    badges.append(planBadge);
    const mode = window.matchMedia?.("(display-mode: standalone)")?.matches ? "PWA installata" : "Web app";
    badges.append(text("span", mode, "badge"));
    if(H.state.user?.trial_active || H.state.user?.is_trial) badges.append(text("span", "Trial attivo", "badge gold"));
  };

  H.renderModules = function(){
    const stats = H.state.view?.stats || {};
    const authenticated = H.isAuthenticated();
    const modules = [
      {id:"coach", icon:"▣", title:"Coach", description:"Prepara la partita, gestisci il Match Day e trasforma eventi, note e pagelle in indicazioni per il post-gara.", url:"/coach.html", action:"Apri Coach", meta:`${stats.coach_matches || 0} partite locali`},
      {id:"video", icon:"▶", title:"Video AI", description:"Analizza partite, allenamenti e clip. Trova frame rilevanti e prepara materiale tecnico per lo staff.", url:"/video.html", action:"Apri Video AI", meta:`${stats.video_reports || 0} report`},
      {id:"hub", icon:"▤", title:"Video Hub", description:"Organizza tutte le Sessioni Video della stagione e continua il lavoro senza ripartire da zero.", url:authenticated?"/video.html#videoHubSection":"/login.html?next=/video.html%23videoHubSection", action:authenticated?"Apri Video Hub":"Accedi per usare Hub", meta:`${stats.video_sessions || 0} sessioni`},
      {id:"scout", icon:"⌕", title:"Scout", description:"Analizza profili, salva giocatori e individua opportunità utili per la squadra.", url:"/scout.html", action:"Apri Scout", meta:`${stats.players_observed || 0} profili salvati`}
    ];
    const grid = $("moduleGrid"); grid.replaceChildren();
    modules.forEach(item => {
      const card = document.createElement("article"); card.className="module-card"; card.dataset.module=item.id;
      card.append(text("div", item.icon, "module-icon"), text("h3", item.title), text("p", item.description));
      const meta = document.createElement("div"); meta.className="module-meta"; meta.append(text("span", item.meta));
      card.append(meta, link(item.action, item.url, `button ${item.id === "coach" ? "button-primary" : "button-muted"}`));
      grid.append(card);
    });
  };

  H.renderStats = function(){
    const stats = H.state.view?.stats || {};
    const entries = [
      ["Partite Coach", stats.coach_matches, "salvate su questo dispositivo"],
      ["Sessioni Video", stats.video_sessions, "nel tuo Video Hub"],
      ["Report Video", stats.video_reports, "nel tuo archivio"],
      ["Frame analizzati", stats.frames_saved, "nei report salvati"],
      ["Giocatori", stats.players_observed, "osservati o salvati"],
      ["Piano", H.isOwner()?"Owner":(H.state.account?.label || H.plan()), "accesso attuale"]
    ];
    const grid = $("statsGrid"); grid.replaceChildren();
    entries.forEach(([label,value,caption]) => {
      const card=document.createElement("article"); card.className="stat-card";
      card.append(text("small",label),text("strong",value ?? 0),text("span",caption)); grid.append(card);
    });
    $("statsCaption").textContent = H.isAuthenticated() ? "Dati personali e attività locali del dispositivo." : "Accedi per vedere archivio e attività personali.";
  };

  H.itemIcon = function(kind){ return ({coach_match:"C",video_session:"V",video_report:"AI",scout_report:"S"})[kind] || "•"; };

  H.renderContinue = function(){
    const box=$("continueList"); box.replaceChildren();
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
    const items=H.state.view?.priorities || [];
    if(!items.length){ box.append(H.emptyState("Nessuna priorità disponibile.","Completa una partita o analizza un video per ricevere una sintesi operativa.",[{label:"Apri Coach",url:"/coach.html",primary:true}])); return; }
    items.forEach(item => {
      const row=document.createElement("article"); row.className="priority-item";
      const content=document.createElement("div"); content.append(text("span",item.type === "confirmed" ? "Dato certo" : "Stato operativo","priority-type"),text("strong",item.title),text("small",item.text || ""));
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
      row.append(text("span",H.itemIcon(item.kind),"activity-icon"),content,text("time",H.formatDate(item.updated_at || item.created_at),"timeline-time")); box.append(row);
    });
  };

  H.renderNotice = function(){
    const notice=$("homeNotice");
    const errors=H.state.remote?.section_errors || [];
    const message=H.state.error || (errors.length ? "Alcune informazioni non sono disponibili; le altre sezioni restano utilizzabili." : "");
    notice.hidden=!message; notice.textContent=message;
  };

  H.renderHome = function(){
    H.renderAccount(); H.renderModules(); H.renderStats(); H.renderContinue(); H.renderAi(); H.renderActivity(); H.renderNotice();
    const latest=(H.state.view?.activities || []).find(item => item.kind === "video_report");
    if(latest) $("latestReportAction").href=latest.url;
  };
})();
