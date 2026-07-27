/*
  MatchIQ Tactical - Auth Core V1.0
  Gestione centralizzata login, utente, owner/admin e headers API.
*/

const MATCHIQ_AUTH_TOKEN_KEYS = [
  "matchiq_auth_token"
];

const MATCHIQ_AUTH_USER_KEYS = [
  "matchiq_auth_user",
  "matchiq_user"
];

const MATCHIQ_OWNER_EMAILS = [
  "mario.costabile92@outlook.it"
];

const MATCHIQ_ADMIN_TOKEN_KEYS = [
  "matchiq_admin_token_v805",
  "matchiq_admin_token_v82_users"
];

const MATCHIQ_AUTH_RETURN_KEY = "matchiq_auth_return_url";

function getAuthToken(){
  for(const key of MATCHIQ_AUTH_TOKEN_KEYS){
    const value = localStorage.getItem(key) || sessionStorage.getItem(key);
    if(value) return value;
  }
  return "";
}

function getLocalUser(){
  for(const key of MATCHIQ_AUTH_USER_KEYS){
    try{
      const raw = localStorage.getItem(key) || sessionStorage.getItem(key);
      if(!raw) continue;
      const user = JSON.parse(raw);
      if(user && typeof user === "object") return user;
    }catch(e){}
  }
  return null;
}

function saveLocalUser(user){
  if(!user || typeof user !== "object") return;

  localStorage.setItem("matchiq_auth_user", JSON.stringify(user));

  if(user.email){
    localStorage.setItem("matchiq_user_email", user.email);
  }

  if(user.plan || user.piano){
    localStorage.setItem("matchiq_user_plan", user.plan || user.piano);
  }
}

function isLoggedIn(){
  return Boolean(getAuthToken());
}

function normalizePlan(plan){
  return String(plan || "").toLowerCase().trim();
}

function normalizeEmail(email){
  return String(email || "").toLowerCase().trim();
}

function isOwnerOrAdmin(user = null){
  const currentUser = user || getLocalUser();

  if(!currentUser) return false;

  const email = normalizeEmail(currentUser.email);
  const plan = normalizePlan(currentUser.plan || currentUser.piano);
  const role = normalizePlan(currentUser.role || currentUser.ruolo);

  return (
    MATCHIQ_OWNER_EMAILS.includes(email) ||
    ["owner", "admin", "owner_pro"].includes(plan) ||
    ["owner", "admin"].includes(role) ||
    currentUser.is_owner === true ||
    currentUser.is_admin === true
  );
}

function authHeaders(extra = {}){
  const token = getAuthToken();

  return {
    "Accept": "application/json",
    ...(token ? {"Authorization": "Bearer " + token} : {}),
    ...extra
  };
}

function getAdminToken(){
  for(const key of MATCHIQ_ADMIN_TOKEN_KEYS){
    const value = localStorage.getItem(key);
    if(value && value.trim()) return value.trim();
  }
  return "";
}

function clearAuthSession(){
  [
    ...MATCHIQ_AUTH_TOKEN_KEYS,
    ...MATCHIQ_AUTH_USER_KEYS,
    "matchiq_user_email",
    "matchiq_user_plan"
  ].forEach(key => {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  });
}

function normalizeReturnUrl(value, fallback = "/index.html"){
  const safeFallback = String(fallback || "/index.html");
  if(!value) return safeFallback;

  try{
    const candidate = new URL(String(value), window.location.origin);
    if(candidate.origin !== window.location.origin) return safeFallback;
    if(!candidate.pathname.startsWith("/") || candidate.pathname.startsWith("//")) return safeFallback;
    if(/[\u0000-\u001f\u007f]/.test(candidate.pathname + candidate.search + candidate.hash)) return safeFallback;
    if(["/login.html", "/register.html"].includes(candidate.pathname.toLowerCase())) return safeFallback;
    return `${candidate.pathname}${candidate.search}${candidate.hash}`;
  }catch(error){
    return safeFallback;
  }
}

function setReturnUrl(value, fallback = "/index.html"){
  const safe = normalizeReturnUrl(value, fallback);
  sessionStorage.setItem(MATCHIQ_AUTH_RETURN_KEY, safe);
  return safe;
}

function requestedReturnUrl(fallback = "/index.html"){
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("next") || params.get("return_url");
  const stored = sessionStorage.getItem(MATCHIQ_AUTH_RETURN_KEY);
  return normalizeReturnUrl(requested || stored, fallback);
}

function consumeReturnUrl(fallback = "/index.html"){
  const safe = requestedReturnUrl(fallback);
  sessionStorage.removeItem(MATCHIQ_AUTH_RETURN_KEY);
  return safe;
}

function authPageUrl(path, returnUrl = window.location.pathname + window.location.search + window.location.hash){
  const target = new URL(path, window.location.origin);
  target.searchParams.set("next", setReturnUrl(returnUrl));
  return `${target.pathname}${target.search}${target.hash}`;
}

async function validateSession(){
  const token = getAuthToken();
  if(!token) return {authenticated:false, reason:"missing"};

  try{
    const response = await fetch("/api/auth/me", {
      headers:authHeaders(),
      credentials:"same-origin",
      cache:"no-store"
    });
    if(response.status === 401 || response.status === 403){
      clearAuthSession();
      return {authenticated:false, reason:"expired"};
    }
    if(!response.ok) return {authenticated:true, reason:"unverified"};
    const payload = await response.json().catch(() => ({}));
    if(payload.user) saveLocalUser(payload.user);
    return {authenticated:true, reason:"valid", user:payload.user || getLocalUser()};
  }catch(error){
    return {authenticated:true, reason:"offline", error};
  }
}

function clearAdminTokens(){
  MATCHIQ_ADMIN_TOKEN_KEYS.forEach(key => {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  });
}

function clearSensitiveLocalState(){
  const clearStorage = storage => {
    const keys = [];
    for(let index = 0; index < storage.length; index += 1){
      const key = storage.key(index);
      if(key) keys.push(key);
    }

    keys.forEach(key => {
      if(
        key.startsWith("matchiq_") ||
        ["token", "access_token", "user"].includes(key)
      ){
        storage.removeItem(key);
      }
    });
  };

  clearStorage(localStorage);
  clearStorage(sessionStorage);
}

function adminHeaders(extra = {}){
  const authToken = getAuthToken();
  const ownerAuth = authToken && isOwnerOrAdmin();
  const adminToken = ownerAuth ? "" : getAdminToken();

  return {
    "Accept": "application/json",
    ...(authToken ? {"Authorization": "Bearer " + authToken} : {}),
    ...(adminToken ? {"X-Admin-Token": adminToken} : {}),
    ...extra
  };
}

function hasAdminAccess(){
  return Boolean(getAdminToken() || (getAuthToken() && isOwnerOrAdmin()));
}

function requireLogin(redirect = true){
  if(isLoggedIn()) return true;

  if(redirect){
    window.location.href = authPageUrl("/login.html?v=" + Date.now());
  }

  return false;
}

function requireAdminPage(){
  const user = getLocalUser();

  if(!isLoggedIn() || !isOwnerOrAdmin(user)){
    document.body.innerHTML = `
      <div style="
        min-height:100vh;
        display:flex;
        align-items:center;
        justify-content:center;
        background:#03050b;
        color:white;
        font-family:Inter,Arial,sans-serif;
        padding:24px;
      ">
        <div style="
          max-width:520px;
          background:rgba(255,255,255,.07);
          border:1px solid rgba(255,255,255,.12);
          border-radius:26px;
          padding:28px;
          text-align:center;
        ">
          <h1 style="margin-bottom:12px;">Accesso admin riservato</h1>
          <p style="color:#aebee7;line-height:1.6;margin-bottom:20px;">
            Questa sezione è disponibile solo per account Owner/Admin.
          </p>
          <button onclick="window.location.href='/index.html'" style="
            border:0;
            border-radius:14px;
            padding:13px 18px;
            color:white;
            font-weight:900;
            cursor:pointer;
            background:linear-gradient(135deg,#2f6bff,#7c4dff);
          ">
            Torna alla Dashboard
          </button>
        </div>
      </div>
    `;

    return false;
  }

  return true;
}

function logout(){
  clearSensitiveLocalState();

  window.location.href = "/index.html?v=" + Date.now();
}

window.MatchIQAuth = {
  getAuthToken,
  getLocalUser,
  saveLocalUser,
  isLoggedIn,
  isOwnerOrAdmin,
  authHeaders,
  clearAuthSession,
  normalizeReturnUrl,
  setReturnUrl,
  requestedReturnUrl,
  consumeReturnUrl,
  authPageUrl,
  validateSession,
  getAdminToken,
  clearAdminTokens,
  clearSensitiveLocalState,
  adminHeaders,
  hasAdminAccess,
  requireLogin,
  requireAdminPage,
  logout
};
