(function(){
  "use strict";

  const VERSION = "10542";
  const withVersion = (path) => `${path}${path.includes("?") ? "&" : "?"}v=${VERSION}`;

  const modules = {
    home: { title: "MatchIQ Coach AI", subtitle: "Prima, durante e dopo la partita", href: withVersion("/index.html") },
    coach: { title: "MatchIQ Coach AI", subtitle: "Il lavoro operativo dello staff", href: withVersion("/coach.html") },
    video: { title: "MatchIQ Video AI", subtitle: "Rivedi, organizza e collega gli episodi", href: withVersion("/video.html") },
    live: { title: "MatchIQ Live", subtitle: "Partite, eventi e analisi in tempo reale", href: withVersion("/live.html") },
    scout: { title: "MatchIQ Scout", subtitle: "Player intelligence e scouting", href: withVersion("/scout.html") },
    account: { title: "MatchIQ Account", subtitle: "Profilo, piano e accesso", href: withVersion("/account.html") },
    admin: { title: "MatchIQ Admin", subtitle: "Controllo operativo e analytics", href: withVersion("/admin-beta.html") },
    auth: { title: "MatchIQ Coach AI", subtitle: "Accedi al workspace dello staff", href: withVersion("/index.html") },
    weekly: { title: "La tua settimana", subtitle: "La sintesi operativa dello staff", href: withVersion("/weekly-briefing.html") },
    pattern: { title: "Cosa si ripete", subtitle: "Ricorrenze tattiche verificate", href: withVersion("/pattern-intelligence.html") },
    training: { title: "Prepara l'allenamento", subtitle: "Dal lavoro raccolto alla seduta", href: withVersion("/training-planner.html") },
    knowledge: { title: "Memoria dello staff", subtitle: "Fonti e osservazioni della squadra", href: withVersion("/knowledge.html") },
    assistant: { title: "Assistente tattico", subtitle: "Supporto con fonti verificabili", href: withVersion("/tactical-assistant.html") },
    identity: { title: "Come gioca la tua squadra", subtitle: "Principi dichiarati e osservati", href: withVersion("/tactical-identity.html") },
    decision: { title: "Opzioni da valutare", subtitle: "Alternative per lo staff tecnico", href: withVersion("/decision-engine.html") },
    club: { title: "Vista società", subtitle: "Priorità tecniche condivise", href: withVersion("/club-intelligence.html") }
  };

  const navigation = [
    { key: "home", label: "Oggi", href: withVersion("/index.html") },
    { key: "coach", label: "Coach", href: withVersion("/coach.html") },
    { key: "video", label: "Video AI", href: withVersion("/video.html") },
    { key: "account", label: "Account", href: withVersion("/account.html") }
  ];

  function moduleFromPath(pathname){
    const path = String(pathname || "/").toLowerCase();
    if(path.includes("admin-")) return "admin";
    if(path.includes("account")) return "account";
    if(path.includes("login") || path.includes("register")) return "auth";
    if(path.includes("weekly-briefing")) return "weekly";
    if(path.includes("pattern-intelligence")) return "pattern";
    if(path.includes("training-planner")) return "training";
    if(path.includes("knowledge")) return "knowledge";
    if(path.includes("tactical-assistant")) return "assistant";
    if(path.includes("tactical-identity")) return "identity";
    if(path.includes("decision-engine")) return "decision";
    if(path.includes("club-intelligence")) return "club";
    if(path.includes("coach")) return "coach";
    if(path.includes("video")) return "video";
    if(path.includes("scout")) return "scout";
    if(path.includes("match") || path.includes("live.html")) return "live";
    return "home";
  }

  function activeFromLocation(locationLike){
    const active = moduleFromPath(locationLike?.pathname || "/");
    if(active === "video" && String(locationLike?.hash || "").toLowerCase() === "#hubarchivepane") return "videoHub";
    return active;
  }

  window.MatchIQGlobalNavConfig = { VERSION, modules, navigation, moduleFromPath, activeFromLocation, withVersion };
})();
