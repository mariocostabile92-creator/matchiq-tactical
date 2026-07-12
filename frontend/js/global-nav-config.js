(function(){
  "use strict";

  const VERSION = "10503";
  const withVersion = (path) => `${path}${path.includes("?") ? "&" : "?"}v=${VERSION}`;

  const modules = {
    home: { title: "MatchIQ", subtitle: "AI Football Technology", href: withVersion("/index.html") },
    coach: { title: "MatchIQ Coach", subtitle: "L'assistente AI dello staff tecnico", href: withVersion("/coach.html") },
    video: { title: "MatchIQ Video AI", subtitle: "Video analysis intelligente per staff e match analyst", href: withVersion("/video.html") },
    live: { title: "MatchIQ Live", subtitle: "Partite, eventi e analisi in tempo reale", href: withVersion("/index.html") + "#liveMatchesSection" },
    scout: { title: "MatchIQ Scout", subtitle: "Player intelligence e scouting", href: withVersion("/scout.html") },
    account: { title: "MatchIQ Account", subtitle: "Profilo, piano e accesso", href: withVersion("/account.html") },
    admin: { title: "MatchIQ Admin", subtitle: "Controllo operativo e analytics", href: withVersion("/admin-beta.html") },
    auth: { title: "MatchIQ", subtitle: "Accedi al tuo ecosistema", href: withVersion("/index.html") }
  };

  const navigation = [
    { key: "home", label: "Home", href: withVersion("/index.html") },
    { key: "coach", label: "Coach", href: withVersion("/coach.html") },
    { key: "video", label: "Video AI", href: withVersion("/video.html") },
    { key: "live", label: "Partite Live", href: withVersion("/index.html") + "#liveMatchesSection" },
    { key: "scout", label: "Scout", href: withVersion("/scout.html") }
  ];

  function moduleFromPath(pathname){
    const path = String(pathname || "/").toLowerCase();
    if(path.includes("admin-")) return "admin";
    if(path.includes("account")) return "account";
    if(path.includes("login") || path.includes("register")) return "auth";
    if(path.includes("coach")) return "coach";
    if(path.includes("video")) return "video";
    if(path.includes("scout")) return "scout";
    if(path.includes("match")) return "live";
    return "home";
  }

  function activeFromLocation(locationLike){
    const active = moduleFromPath(locationLike?.pathname || "/");
    if(active === "home" && String(locationLike?.hash || "").toLowerCase() === "#livematchessection") return "live";
    return active;
  }

  window.MatchIQGlobalNavConfig = { VERSION, modules, navigation, moduleFromPath, activeFromLocation, withVersion };
})();
