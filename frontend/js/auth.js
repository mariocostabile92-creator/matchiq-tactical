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

function adminHeaders(extra = {}){
  const adminToken = getAdminToken();
  const authToken = getAuthToken();

  return {
    "Accept": "application/json",
    ...(adminToken ? {"X-Admin-Token": adminToken} : {}),
    ...(authToken ? {"Authorization": "Bearer " + authToken} : {}),
    ...extra
  };
}

function hasAdminAccess(){
  return Boolean(getAdminToken() || (getAuthToken() && isOwnerOrAdmin()));
}

function requireLogin(redirect = true){
  if(isLoggedIn()) return true;

  if(redirect){
    window.location.href = "/login.html?v=" + Date.now();
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
  [
    "matchiq_auth_user",
    "matchiq_user",
    "matchiq_auth_token",
    "matchiq_user_email",
    "matchiq_user_plan"
  ].forEach(key => localStorage.removeItem(key));

  [
    "matchiq_auth_user",
    "matchiq_user",
    "matchiq_auth_token"
  ].forEach(key => sessionStorage.removeItem(key));

  window.location.href = "/index.html?v=" + Date.now();
}

window.MatchIQAuth = {
  getAuthToken,
  getLocalUser,
  saveLocalUser,
  isLoggedIn,
  isOwnerOrAdmin,
  authHeaders,
  getAdminToken,
  adminHeaders,
  hasAdminAccess,
  requireLogin,
  requireAdminPage,
  logout
};
