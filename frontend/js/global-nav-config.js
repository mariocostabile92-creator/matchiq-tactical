(function(){
  "use strict";

  const VERSION = "10529";
  const withVersion = (path) => `${path}${path.includes("?") ? "&" : "?"}v=${VERSION}`;

  const modules = {
    home: { title: "MatchIQ Coach AI", subtitle: "L'assistente AI dello staff tecnico", href: withVersion("/index.html") },
    coach: { title: "MatchIQ Coach", subtitle: "L'assistente AI dello staff tecnico", href: withVersion("/coach.html") },
    video: { title: "MatchIQ Video AI", subtitle: "Video analysis intelligente per staff e match analyst", href: withVersion("/video.html") },
    live: { title: "MatchIQ Live", subtitle: "Partite, eventi e analisi in tempo reale", href: withVersion("/live.html") },
    scout: { title: "MatchIQ Scout", subtitle: "Player intelligence e scouting", href: withVersion("/scout.html") },
    account: { title: "MatchIQ Account", subtitle: "Profilo, piano e accesso", href: withVersion("/account.html") },
    admin: { title: "MatchIQ Admin", subtitle: "Controllo operativo e analytics", href: withVersion("/admin-beta.html") },
    auth: { title: "MatchIQ Coach AI", subtitle: "Accedi al workspace dello staff", href: withVersion("/index.html") },
    weekly: { title: "MatchIQ Weekly", subtitle: "Briefing tecnico settimanale", href: withVersion("/weekly-briefing.html") },
    pattern: { title: "MatchIQ Pattern", subtitle: "Ricorrenze tattiche verificate", href: withVersion("/pattern-intelligence.html") },
    training: { title: "MatchIQ Training", subtitle: "Pianificazione dello staff", href: withVersion("/training-planner.html") },
    knowledge: { title: "MatchIQ Knowledge", subtitle: "Memoria tecnica della squadra", href: withVersion("/knowledge.html") },
    assistant: { title: "MatchIQ Assistant", subtitle: "Supporto tattico con fonti", href: withVersion("/tactical-assistant.html") },
    identity: { title: "MatchIQ Identity", subtitle: "Identita tattica dichiarata e osservata", href: withVersion("/tactical-identity.html") },
    decision: { title: "MatchIQ Decision", subtitle: "Alternative e supporto alle decisioni", href: withVersion("/decision-engine.html") },
    club: { title: "MatchIQ Club", subtitle: "Intelligence tecnica societaria", href: withVersion("/club-intelligence.html") }
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
