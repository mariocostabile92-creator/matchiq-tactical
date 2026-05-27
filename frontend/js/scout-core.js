/* MatchIQ Scout - Core Module V8.0.3 Hotfix 6 Owner Override */
const APP_VERSION = "10035";

document.addEventListener("DOMContentLoaded", async () => {
  bindFilters();
  await init();
  startTimers();
  hideLoading();
});

function bindFilters(){
  ["searchInput","roleFilter","signalFilter","scoreFilter"].forEach(id => {
    const el = document.getElementById(id);
    if(el) el.addEventListener("input", renderPlayers);
  });

  document.addEventListener("keydown", e => {
    if(e.key === "Escape") closeModal();
  });

  const modalBg = document.getElementById("modalBg");
  if(modalBg){
    modalBg.addEventListener("click", e => {
      if(e.target.id === "modalBg") closeModal();
    });
  }
}

async function loadAccountLimits(){
  try{
    const token =
      localStorage.getItem("matchiq_auth_token") ||
      sessionStorage.getItem("matchiq_auth_token") ||
      "";

    const headers = token ? {"Authorization": `Bearer ${token}`} : {};

    const r = await fetch(`${API_BASE}/api/account/limits`, {
      headers,
      cache: "no-store"
    });

    if(!r.ok) throw new Error("limits not ok");

    const data = await r.json();
    applyAccountLimits(data);
  }catch(e){
    applyAccountLimits(DEFAULT_ACCOUNT_LIMITS);
  }

  forceScoutAccessUI();
}

async function init(){
  await loadAccountLimits();

  state.watchlist = canUseWatchlist() ? loadWatchlist() : [];
  state.selectedMatchId = getMatchIdFromUrl();

  await loadLiveMatches(true);

  if(!state.selectedMatchId){
    state.selectedMatchId = state.matches[0]?.id || null;
  }

  await loadScoutData(true);

  renderAll();
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
  showLoading();

  state.selectedMatchId = id;
  state.events = [];
  state.openPlayerId = null;

  closeModal(false);

  await loadScoutData(true);

  renderAll();
  forceScoutAccessUI();

  hideLoading();
  toast("Partita cambiata","Scout riallineato sul nuovo match live.");
}

async function manualRefresh(){
  showLoading();

  await loadAccountLimits();
  await loadLiveMatches(true);
  await loadScoutData(true);

  renderAll();
  forceScoutAccessUI();

  hideLoading();
  toast("Refresh completato","Dati riallineati con la Live Dashboard.");
}

function startTimers(){
  if(state.timers?.soft) clearInterval(state.timers.soft);
  if(state.timers?.events) clearInterval(state.timers.events);

  state.timers.soft = setInterval(async () => {
    state.tick++;

    await loadLiveMatches(false);

    const m = getMatch();

    if(m && num(m.minute,0) < 90){
      m.minute = num(m.minute,0) + 1;
    }

    if(state.tick % 9 === 0){
      await loadAccountLimits();
      await loadScoutData(false);
    }

    renderAll();
    forceScoutAccessUI();
  },10000);

  state.timers.events = setInterval(() => {
    if(canSimulateScout() && state.hasRealPlayers && Math.random() > .5){
      generateLocalEvent(false);
    }
  },API_SAFE.localEventMs);
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

function isLocalOwnerOverride(){
  const email = getStoredUserEmail();
  return email === "mario.costabile92@outlook.it";
}

function getScoutPlan(){
  if(isLocalOwnerOverride()){
    return "owner";
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

  const apiPill = document.getElementById("apiSafePill");
  if(apiPill){
    if(isOwner){
      apiPill.textContent = "OWNER PRO";
    }else if(isPro){
      apiPill.textContent = "PRO";
    }else{
      apiPill.textContent = "GUEST PREVIEW";
    }
  }

  const subtitle = document.getElementById("scoutSubtitle");
  if(subtitle){
    subtitle.textContent = isPro
      ? "Scout completo · Live Player Intelligence · Tactical Signals · Export Report"
      : "Scout Preview · Player Intelligence limitata · Funzioni PRO bloccate";
  }

  const loaderSubtitle = document.getElementById("loaderSubtitle");
  if(loaderSubtitle){
    loaderSubtitle.textContent = isPro
      ? "Live intelligence · Player scouting · Tactical signals"
      : "Scout Preview · funzioni avanzate disponibili nei piani PRO";
  }

  const ticker = document.getElementById("tickerText");
  if(ticker && !isPro){
    ticker.textContent = "MatchIQ Scout Preview · funzioni PRO bloccate per questo account.";
  }

  document.querySelectorAll("[data-pro-only]").forEach(el => {
    el.style.display = isPro ? "" : "none";
  });

  document.querySelectorAll("[data-owner-only]").forEach(el => {
    el.style.display = isOwner ? "" : "none";
  });
}

/* Alias per compatibilità con eventuali vecchie chiamate */
function applyScoutAccessUI(){
  forceScoutAccessUI();
}
/* =========================
   ACCOUNT LIMITS FALLBACK
   Evita crash se scout-state.js online non ha ancora applyAccountLimits()
========================= */

const DEFAULT_ACCOUNT_LIMITS_SAFE = {
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

if(typeof window.DEFAULT_ACCOUNT_LIMITS === "undefined"){
  window.DEFAULT_ACCOUNT_LIMITS = DEFAULT_ACCOUNT_LIMITS_SAFE;
}

if(typeof window.applyAccountLimits !== "function"){
  window.applyAccountLimits = function(data){
    const raw = data || {};
    const limits = raw.limits || raw.features || raw || {};

    const plan = String(
      raw.plan ||
      limits.plan ||
      raw.piano ||
      "guest"
    ).toLowerCase();

    const isOwner = plan === "owner";
    const isPro = plan === "pro" || isOwner;

    state.account = {
      plan: plan,
      label: isOwner ? "OWNER PRO" : isPro ? "PRO" : "GUEST PREVIEW",
      is_owner: isOwner,
      is_pro: isPro,
      scout_enabled: Boolean(isPro || limits.scout_enabled),
      scout_preview: !isPro,
      scout_max_players: Number(limits.scout_max_players ?? (isPro ? 999 : 4)),
      export_enabled: Boolean(isPro || limits.export_enabled),
      watchlist_enabled: Boolean(isPro || limits.watchlist_enabled),
      simulate_enabled: Boolean(isPro || limits.simulate_enabled)
    };

    state.accountReady = true;
  };
}