/*
    MatchIQ Scout - Utils Module
    Utility globali, helper UI, cache, escape, numeri e toast.
    V6.7 Utils
*/

function updateCache(){
  if(!state.selectedMatchId) return;

  state.playerCache[state.selectedMatchId] = {
    players:clone(state.players),
    events:clone(state.events),
    match:clone(state.currentMatch),
    summary:clone(state.summary)
  };
}

function flashCard(id){
  requestAnimationFrame(() => {
    const el = document.getElementById(`card-${CSS.escape(String(id))}`);
    if(!el) return;

    el.classList.remove("flash");
    void el.offsetWidth;
    el.classList.add("flash");

    setTimeout(() => el.classList.remove("flash"),1000);
  });
}

function getMatch(){
  return state.currentMatch ||
    state.matches.find(m => String(m.id) === String(state.selectedMatchId)) ||
    state.matches[0];
}

function valuePct(v){
  return Number.isFinite(Number(v)) ? Math.round(Number(v)) + "%" : "--";
}

function avgField(list,field){
  if(!list.length) return 0;

  return list.reduce((a,b) => a + Number(b[field] || 0),0) / list.length;
}

function cleanRole(v){
  const r = String(v || "MID").toUpperCase();

  if(["ATT","MID","DEF","GK"].includes(r)) return r;
  if(r.includes("ATT") || r.includes("FORWARD") || r.includes("STRIKER")) return "ATT";
  if(r.includes("MID")) return "MID";
  if(r.includes("DEF") || r.includes("BACK")) return "DEF";
  if(r.includes("KEEP") || r === "G") return "GK";

  return "MID";
}

function intNum(v){
  return Math.round(num(v,0));
}

function num(v,f=0){
  const n = Number(v);
  return Number.isFinite(n) ? n : f;
}

function clamp(v,min,max){
  return Math.max(min,Math.min(max,Number(v) || 0));
}

function cleanText(v,f="Unknown"){
  if(v === null || v === undefined || v === "") return f;
  return String(v);
}

function clone(obj){
  return JSON.parse(JSON.stringify(obj || {}));
}

function uid(){
  return `id_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function esc(v){
  return String(v ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

function escAttr(v){
  return esc(v).replaceAll("\\","\\\\");
}

function updateLastRefresh(){
  const now = new Date();
  const el = document.getElementById("lastUpdate");

  if(el){
    el.textContent = "refresh " + now.toLocaleTimeString("it-IT",{
      hour:"2-digit",
      minute:"2-digit",
      second:"2-digit"
    });
  }
}

function updateApiPill(){
  const el = document.getElementById("apiSafePill");

  if(el){
    el.textContent = `API SAFE ${Math.round(API_SAFE.scoutRefreshMs/1000)}s`;
  }
}

function showNotice(message){
  const box = document.getElementById("noticeBox");
  if(!box) return;

  box.innerHTML = `<strong>Nota:</strong> ${esc(message)}`;
  box.classList.add("show");
}

function clearNotice(){
  const box = document.getElementById("noticeBox");
  if(!box) return;

  box.classList.remove("show");
  box.innerHTML = "";
}

function showLoading(){
  const loading = document.getElementById("loading");
  if(loading) loading.classList.add("show");
}

function hideLoading(){
  const loading = document.getElementById("loading");
  if(loading) loading.classList.remove("show");
}

function toast(title,desc){
  const area = document.getElementById("toastArea");
  if(!area) return;

  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<strong>${esc(title)}</strong><span>${esc(desc)}</span>`;

  area.appendChild(el);

  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(8px)";
    el.style.transition = ".2s";
  },3500);

  setTimeout(() => el.remove(),3900);
}