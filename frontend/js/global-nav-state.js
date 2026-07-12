(function(){
  "use strict";

  function readJson(storage, key){
    try { return JSON.parse(storage.getItem(key) || "null"); } catch (_) { return null; }
  }

  function storedUser(){
    if(window.MatchIQAuth && typeof window.MatchIQAuth.getLocalUser === "function"){
      return window.MatchIQAuth.getLocalUser() || null;
    }
    const keys = ["matchiq_auth_user", "matchiq_user", "user", "currentUser", "auth_user"];
    for(const storage of [window.localStorage, window.sessionStorage]){
      for(const key of keys){
        const user = readJson(storage, key);
        if(user && typeof user === "object") return user;
      }
    }
    return null;
  }

  function hasToken(){
    if(window.MatchIQAuth && typeof window.MatchIQAuth.isLoggedIn === "function"){
      return Boolean(window.MatchIQAuth.isLoggedIn());
    }
    const keys = ["matchiq_auth_token", "access_token", "token", "matchiq_token", "authToken"];
    return [window.localStorage, window.sessionStorage].some((storage) => keys.some((key) => Boolean(storage.getItem(key))));
  }

  function normalizedPlan(user){
    const raw = String(user?.plan || user?.piano || user?.subscription_plan || user?.role || "").toLowerCase();
    if(raw.includes("owner") || raw.includes("admin")) return "Owner";
    if(raw.includes("scout")) return "Scout";
    if(raw.includes("pro")) return "Pro";
    if(raw.includes("free")) return "Free";
    return hasToken() ? "Free" : "Piano";
  }

  function canAdmin(user){
    if(window.MatchIQAuth){
      if(typeof window.MatchIQAuth.isOwnerOrAdmin === "function" && window.MatchIQAuth.isOwnerOrAdmin()) return true;
      if(typeof window.MatchIQAuth.hasAdminAccess === "function" && window.MatchIQAuth.hasAdminAccess()) return true;
    }
    const role = String(user?.role || user?.ruolo || user?.plan || user?.piano || "").toLowerCase();
    const email = String(user?.email || "").toLowerCase();
    return email === "mario.costabile92@outlook.it" || role.includes("owner") || role.includes("admin") || user?.is_admin === true || user?.is_owner === true;
  }

  function snapshot(){
    const user = storedUser();
    return { user, loggedIn: hasToken(), plan: normalizedPlan(user), canAdmin: canAdmin(user) };
  }

  window.MatchIQGlobalNavState = { snapshot };
})();
