/*
    MatchIQ Scout - Core Module
    Init, routing, filtri, refresh, timer e navigazione dashboard.
    V7.2 Beta Form
*/

const APP_VERSION = "10016";

document.addEventListener("DOMContentLoaded", async () => {
  bindFilters();
  await init();
  startTimers();
  hideLoading();
});

function bindFilters(){
  ["searchInput","roleFilter","signalFilter","scoreFilter"].forEach(id => {
    const el = document.getElementById(id);
    if(el){
      el.addEventListener("input", renderPlayers);
    }
  });

  document.addEventListener("keydown", e => {
    if(e.key === "Escape"){
      closeModal();
    }
  });

  const modalBg = document.getElementById("modalBg");
  if(modalBg){
    modalBg.addEventListener("click", e => {
      if(e.target.id === "modalBg"){
        closeModal();
      }
    });
  }
}

async function init(){
  state.watchlist = loadWatchlist();
  state.selectedMatchId = getMatchIdFromUrl();

  await loadLiveMatches(true);

  if(!state.selectedMatchId){
    state.selectedMatchId = state.matches[0]?.id || null;
  }

  await loadScoutData(true);
  renderAll();
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
  hideLoading();
  toast("Partita cambiata","Scout riallineato sul nuovo match live.");
}

async function manualRefresh(){
  showLoading();

  await loadLiveMatches(true);
  await loadScoutData(true);

  renderAll();
  hideLoading();
  toast("Refresh completato","Dati riallineati con la Live Dashboard.");
}

function startTimers(){
  if(state.timers?.soft) clearInterval(state.timers.soft);
  if(state.timers?.events) clearInterval(state.timers.events);

  if(!state.timers){
    state.timers = {
      soft:null,
      events:null
    };
  }

  state.timers.soft = setInterval(async () => {
    state.tick++;

    await loadLiveMatches(false);

    const m = getMatch();

    if(m && num(m.minute,0) < 90){
      m.minute = num(m.minute,0) + 1;
    }

    if(state.tick % 9 === 0){
      await loadScoutData(false);
    }

    renderAll();
  },10000);

  state.timers.events = setInterval(() => {
    if(state.hasRealPlayers && Math.random() > .5){
      generateLocalEvent(false);
    }
  },API_SAFE.localEventMs);
}