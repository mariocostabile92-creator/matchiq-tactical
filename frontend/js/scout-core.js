/* MatchIQ Scout - Core Module V8.1.2 SaaS Free/Pro Runtime */
const APP_VERSION = "10444";

document.addEventListener("DOMContentLoaded", async () => {
  try{
    bindFilters();
    injectScoutAccountButton();
    await init();
    startTimers();
  }catch(err){
    console.error("MatchIQ Scout init error:", err);
    safeToast("Errore Scout", "Lo Scout ha avuto un errore, ma la pagina resta utilizzabile.");
  }finally{
    if(typeof hideLoading === "function"){
      hideLoading();
    }else{
      const loading = document.getElementById("loading");
      if(loading) loading.classList.remove("show");
    }
  }
});

function bindFilters(){
  ["searchInput","roleFilter","signalFilter","scoreFilter"].forEach(id => {
    const el = document.getElementById(id);
    if(el && typeof renderPlayers === "function"){
      el.addEventListener("input", renderPlayers);
    }
  });

  document.addEventListener("keydown", e => {
    if(e.key === "Escape" && typeof closeModal === "function"){
      closeModal();
    }
  });

  const modalBg = document.getElementById("modalBg");
  if(modalBg){
    modalBg.addEventListener("click", e => {
      if(e.target.id === "modalBg" && typeof closeModal === "function"){
        closeModal();
      }
    });
  }
}

/* =========================
   ACCOUNT BUTTON
========================= */

function injectScoutAccountButton(){
  const actions = document.querySelector(".topbar .actions");
  if(!actions) return;

  if(document.getElementById("scoutAccountBtn")) return;

  const btn = document.createElement("button");
  btn.className = "btn";
  btn.id = "scoutAccountBtn";
  btn.textContent = "Account";
  btn.onclick = goAccount;

  const refreshBtn = [...actions.querySelectorAll("button")]
    .find(b => (b.textContent || "").toLowerCase().includes("aggiorna"));

  if(refreshBtn){
    actions.insertBefore(btn, refreshBtn);
  }else{
    actions.appendChild(btn);
  }
}

function goAccount(){
  window.location.href = versionedUrl("/account.html");
}

function goPricing(){
  window.location.href = versionedUrl("/index.html#pricing");
}

/* =========================
   ACCOUNT LIMITS SAFE
========================= */

function getDefaultAccountLimits(){
  return {
    plan: "guest",
    label: "GUEST PREVIEW",
    is_owner: false,
    is_pro: false,
    scout_enabled: false,
    scout_preview: true,
    scout_max_players: 4,
    export_enabled: false,
    watchlist_enabled: false,
    simulate_enabled: false
  };
}

function normalizeAccountLimits(data){
  const raw = data || {};
  const limits = raw.limits || raw.features || raw || {};

  let plan = String(raw.plan || limits.plan || raw.piano || "guest").toLowerCase();

  if(isLocalOwnerOverride()){
    plan = "owner";
  }

  const isOwner = plan === "owner" || plan === "admin" || plan === "owner_pro";
  const isPro = plan === "pro" || plan === "scout" || isOwner;

  return {
    plan: isOwner ? "owner" : isPro ? "pro" : plan,
    label: isOwner ? "OWNER PRO" : isPro ? "PRO" : "FREE PREVIEW",
    is_owner: isOwner,
    is_pro: isPro,
    scout_enabled: Boolean(isPro || limits.scout_enabled),
    scout_preview: !isPro,
    scout_max_players: Number(limits.scout_max_players ?? (isPro ? 999 : 4)),
    export_enabled: Boolean(isPro || limits.export_enabled),
    watchlist_enabled: Boolean(isPro || limits.watchlist_enabled),
    simulate_enabled: Boolean(isPro || limits.simulate_enabled)
  };
}

function safeApplyAccountLimits(data){
  state.account = normalizeAccountLimits(data);
  state.accountReady = true;
}

async function loadAccountLimits(){
  try{
    const token =
      localStorage.getItem("matchiq_auth_token") ||
      sessionStorage.getItem("matchiq_auth_token") ||
      "";

    const headers = token ? {"Authorization": `Bearer ${token}`} : {};

    const r = await fetch(`${API_BASE}/api/account/limits?ts=${Date.now()}`, {
      headers,
      cache: "no-store"
    });

    if(!r.ok) throw new Error("limits not ok");

    const data = await r.json();
    safeApplyAccountLimits(data);
  }catch(e){
    safeApplyAccountLimits(getDefaultAccountLimits());
  }

  forceScoutAccessUI();
}

/* =========================
   INIT
========================= */

async function init(){
  await loadAccountLimits();

  state.watchlist = scoutCanUseWatchlist() && typeof loadWatchlist === "function"
    ? loadWatchlist()
    : [];

  state.selectedMatchId = getMatchIdFromUrl();

  if(typeof loadLiveMatches === "function"){
    await loadLiveMatches(true);
  }

  if(!state.selectedMatchId){
    state.selectedMatchId = state.matches?.[0]?.id || null;
  }

  if(typeof loadScoutData === "function"){
    await loadScoutData(true);
  }

  if(typeof renderAll === "function"){
    renderAll();
  }

  forceScoutAccessUI();
}

function getMatchIdFromUrl(){
  const p = new URLSearchParams(window.location.search);
  return p.get("match_id") || p.get("id") || p.get("fixture_id") || p.get("matchId");
}

function versionedUrl(path){
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}v=${APP_VERSION}`;
}

function goDashboard(){
  window.location.href = versionedUrl("/index.html");
}

async function selectMatch(id){
  if(typeof showLoading === "function") showLoading();

  try{
    state.selectedMatchId = id;
    state.events = [];
    state.openPlayerId = null;

    if(typeof closeModal === "function") closeModal(false);

    if(typeof loadScoutData === "function"){
      await loadScoutData(true);
    }

    if(typeof renderAll === "function"){
      renderAll();
    }

    forceScoutAccessUI();
    safeToast("Partita cambiata","Scout riallineato sul nuovo match live.");
  }catch(err){
    console.error("selectMatch error:", err);
    safeToast("Errore cambio partita","Non sono riuscito a cambiare match.");
  }finally{
    if(typeof hideLoading === "function") hideLoading();
  }
}

async function manualRefresh(){
  if(typeof showLoading === "function") showLoading();

  try{
    await loadAccountLimits();

    if(typeof loadLiveMatches === "function"){
      await loadLiveMatches(true);
    }

    if(typeof loadScoutData === "function"){
      await loadScoutData(true);
    }

    if(typeof renderAll === "function"){
      renderAll();
    }

    forceScoutAccessUI();
    safeToast("Refresh completato","Dati riallineati con la Live Dashboard.");
  }catch(err){
    console.error("manualRefresh error:", err);
    safeToast("Errore refresh","Non sono riuscito ad aggiornare i dati.");
  }finally{
    if(typeof hideLoading === "function") hideLoading();
  }
}

function startTimers(){
  if(state.timers?.soft) clearInterval(state.timers.soft);
  if(state.timers?.events) clearInterval(state.timers.events);

  if(!state.timers){
    state.timers = {soft:null, events:null};
  }

  state.timers.soft = setInterval(async () => {
    try{
      state.tick++;

      if(typeof loadLiveMatches === "function"){
        await loadLiveMatches(false);
      }

      const m = typeof getMatch === "function" ? getMatch() : null;

      if(m && typeof num === "function" && num(m.minute,0) < 90){
        m.minute = num(m.minute,0) + 1;
      }

      if(state.tick % 9 === 0){
        await loadAccountLimits();

        if(typeof loadScoutData === "function"){
          await loadScoutData(false);
        }
      }

      if(typeof renderAll === "function"){
        renderAll();
      }

      forceScoutAccessUI();
    }catch(err){
      console.warn("Scout soft timer skipped:", err);
      forceScoutAccessUI();
    }
  },10000);

  state.timers.events = setInterval(() => {
    try{
      if(scoutCanSimulate() && state.hasRealPlayers && Math.random() > .5 && typeof generateLocalEvent === "function"){
        generateLocalEvent(false);
      }
    }catch(err){
      console.warn("Scout event timer skipped:", err);
    }
  },API_SAFE?.localEventMs || 7000);
}

/* =========================
   OWNER / PLAN DETECTION
========================= */

function getStoredUserEmail(){
  const keys = [
    "matchiq_user_email",
    "matchiq_email",
    "user_email",
    "email"
  ];

  for(const key of keys){
    const value =
      localStorage.getItem(key) ||
      sessionStorage.getItem(key);

    if(value && String(value).toLowerCase().trim()){
      return String(value).toLowerCase().trim();
    }
  }

  try{
    const rawUser =
      localStorage.getItem("matchiq_user") ||
      localStorage.getItem("matchiq_auth_user") ||
      sessionStorage.getItem("matchiq_user") ||
      sessionStorage.getItem("matchiq_auth_user");

    if(rawUser){
      const parsed = JSON.parse(rawUser);
      const email =
        parsed?.email ||
        parsed?.user?.email ||
        parsed?.account?.email;

      if(email){
        return String(email).toLowerCase().trim();
      }
    }
  }catch(e){}

  return "";
}

function getStoredUserPlan(){
  const keys = [
    "matchiq_user_plan",
    "matchiq_plan",
    "user_plan",
    "plan"
  ];

  for(const key of keys){
    const value =
      localStorage.getItem(key) ||
      sessionStorage.getItem(key);

    if(value && String(value).toLowerCase().trim()){
      return String(value).toLowerCase().trim();
    }
  }

  try{
    const rawUser =
      localStorage.getItem("matchiq_user") ||
      localStorage.getItem("matchiq_auth_user") ||
      sessionStorage.getItem("matchiq_user") ||
      sessionStorage.getItem("matchiq_auth_user");

    if(rawUser){
      const parsed = JSON.parse(rawUser);
      const plan =
        parsed?.plan ||
        parsed?.piano ||
        parsed?.role ||
        parsed?.user?.plan ||
        parsed?.account?.plan;

      if(plan){
        return String(plan).toLowerCase().trim();
      }
    }
  }catch(e){}

  return "";
}

function isLocalOwnerOverride(){
  const email = getStoredUserEmail();
  return email === "mario.costabile92@outlook.it";
}

function getScoutPlan(){
  if(isLocalOwnerOverride()){
    return "owner";
  }

  const localPlan = getStoredUserPlan();

  if(["owner","admin","owner_pro"].includes(localPlan)){
    return "owner";
  }

  if(["pro","scout","pro_monthly","pro_yearly"].includes(localPlan)){
    return "pro";
  }

  return String(state?.account?.plan || "guest").toLowerCase();
}

function isScoutOwner(){
  return Boolean(
    isLocalOwnerOverride() ||
    state?.account?.is_owner === true ||
    getScoutPlan() === "owner"
  );
}

function isScoutPro(){
  return Boolean(
    isScoutOwner() ||
    state?.account?.is_pro === true ||
    getScoutPlan() === "pro"
  );
}

function scoutPlayerLimit(){
  if(isScoutPro()) return 999;
  return Number(state?.account?.scout_max_players || 4);
}

function scoutCanUseWatchlist(){
  return Boolean(
    isScoutPro() ||
    state?.account?.watchlist_enabled === true
  );
}

function scoutCanExport(){
  return Boolean(
    isScoutPro() ||
    state?.account?.export_enabled === true
  );
}

function scoutCanSimulate(){
  return Boolean(
    isScoutPro() ||
    state?.account?.simulate_enabled === true
  );
}

/* Compatibilità con altri moduli */
function canUseWatchlist(){
  return scoutCanUseWatchlist();
}

function canExportScout(){
  return scoutCanExport();
}

function canSimulateScout(){
  return scoutCanSimulate();
}

/* =========================
   PRO ACTIONS
========================= */

async function startScoutCheckout(plan="pro_monthly"){
  const token =
    localStorage.getItem("matchiq_auth_token") ||
    sessionStorage.getItem("matchiq_auth_token") ||
    "";

  if(isScoutPro()){
    safeToast("Piano Pro attivo","Hai già accesso completo a MatchIQ Scout.");
    return;
  }

  if(!token){
    safeToast("Login richiesto","Per attivare Pro devi prima fare login o registrarti.");
    setTimeout(() => {
      window.location.href = versionedUrl("/login.html");
    },900);
    return;
  }

  try{
    const r = await fetch(`${API_BASE}/api/payments/create-checkout-session`, {
      method:"POST",
      headers:{
        "Content-Type":"application/json",
        "Authorization":"Bearer " + token
      },
      body:JSON.stringify({plan})
    });

    const data = await r.json();

    if(r.status === 409){
      safeToast("Piano già attivo", data?.detail?.message || "Il tuo piano Pro è già attivo.");
      await loadAccountLimits();
      if(typeof renderAll === "function") renderAll();
      return;
    }

    if(!r.ok || data.success === false || data.ok === false){
      const detail = data.detail;
      throw new Error(typeof detail === "object" ? detail.message : detail || data.message || "Errore checkout");
    }

    const url = data.checkout_url || data.url;

    if(!url) throw new Error("Checkout URL non ricevuto");

    window.location.href = url;

  }catch(e){
    console.error(e);
    safeToast("Errore Stripe", e.message || "Checkout non disponibile.");
  }
}

function openScoutProUpgrade(){
  startScoutCheckout("pro_monthly");
}

/* =========================
   UI LOCK / UNLOCK
========================= */

function setVisibleById(id, visible){
  const el = document.getElementById(id);
  if(!el) return;
  el.style.display = visible ? "" : "none";
}

function forceScoutAccessUI(){
  const plan = getScoutPlan();
  const isOwner = isScoutOwner();
  const isPro = isScoutPro();

  document.body.dataset.scoutPlan = plan;

  setVisibleById("adminActionsPill", isOwner);
  setVisibleById("exportScoutBtn", isPro);
  setVisibleById("simulateEventBtn", isPro);

  setVisibleById("exportWatchlistBtn", isPro);
  setVisibleById("clearWatchlistBtn", isPro);

  setVisibleById("modalScoutActionsCard", isPro);
  setVisibleById("modalAddWatchBtn", isPro);
  setVisibleById("modalExportPlayerBtn", isPro);
  setVisibleById("modalRemoveWatchBtn", isPro);

  const accountBtn = document.getElementById("scoutAccountBtn");
  if(accountBtn){
    accountBtn.style.display = "inline-flex";
    accountBtn.textContent = isPro ? "Account Pro" : "Account";
  }

  const apiPill = document.getElementById("apiSafePill");
  if(apiPill){
    if(isOwner){
      apiPill.textContent = "OWNER PRO";
    }else if(isPro){
      apiPill.textContent = "PRO";
    }else{
      apiPill.textContent = "FREE PREVIEW";
    }
  }

  const subtitle = document.getElementById("scoutSubtitle");
  if(subtitle){
    subtitle.textContent = isPro
      ? "Scout completo · Live Player Intelligence · Tactical Signals · Export Report"
      : "Scout Preview · player cards limitate · export, watchlist e simulazioni disponibili con Pro";
  }

  const loaderSubtitle = document.getElementById("loaderSubtitle");
  if(loaderSubtitle){
    loaderSubtitle.textContent = isPro
      ? "Live intelligence · Player scouting · Tactical signals"
      : "Scout Preview · funzioni avanzate disponibili con MatchIQ Pro";
  }

  const ticker = document.getElementById("tickerText");
  if(ticker && !isPro){
    ticker.textContent = "MatchIQ Scout Free Preview · passa a Pro per sbloccare player cards complete, watchlist, export e simulazioni.";
  }

  document.querySelectorAll("[data-pro-only]").forEach(el => {
    el.style.display = isPro ? "" : "none";
  });

  document.querySelectorAll("[data-owner-only]").forEach(el => {
    el.style.display = isOwner ? "" : "none";
  });
}

function applyScoutAccessUI(){
  forceScoutAccessUI();
}

function safeToast(title, message){
  if(typeof toast === "function"){
    toast(title, message);
  }else{
    console.log(title, message || "");
  }
}