(function initCoachMatchFeedback(){
  "use strict";

  const recent = new Map();
  const LOCK_MS = 900;

  function announce(message, tone="ok"){
    const box = document.getElementById("coachEventFeedback");
    if(!box) return;
    box.textContent = message;
    box.className = `coach-event-feedback ${tone}`;
  }

  function allow(fingerprint){
    const key = String(fingerprint || "event");
    const now = Date.now();
    if(now - Number(recent.get(key) || 0) < LOCK_MS){
      announce("Tocco doppio ignorato: l'evento era gia stato registrato.", "warn");
      return false;
    }
    recent.set(key, now);
    const button = document.activeElement?.closest?.("button");
    if(button){
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      setTimeout(() => { button.disabled = false; button.removeAttribute("aria-busy"); }, LOCK_MS);
    }
    return true;
  }

  function isDuplicate(event, existing){
    if(!event || !existing) return false;
    const age = Date.now() - new Date(existing.createdAt || 0).getTime();
    if(!Number.isFinite(age) || age < 0 || age > 1500) return false;
    return event.type === existing.type
      && event.side === existing.side
      && event.source === existing.source
      && String(event.playerId || event.player || "") === String(existing.playerId || existing.player || "");
  }

  function confirmEvent(event){
    const time = typeof formatCoachEventTime === "function" ? formatCoachEventTime(event) : `${event.minute || 0}'`;
    announce(`${time} ${event.label} registrato per ${event.team}.`, "ok");
    if(navigator.vibrate) navigator.vibrate(20);
  }

  function renderNetwork(){
    const box = document.getElementById("coachNetworkState");
    if(!box) return;
    const online = navigator.onLine !== false;
    box.className = `coach-network-state ${online ? "online" : "offline"}`;
    box.textContent = online
      ? "Online · eventi salvati sul dispositivo"
      : "Offline · eventi salvati sul dispositivo; il cloud riprendera quando torna la rete";
  }

  function bindNetwork(){
    if(document.documentElement.dataset.coachNetworkBound === "1") return;
    document.documentElement.dataset.coachNetworkBound = "1";
    window.addEventListener("online", renderNetwork);
    window.addEventListener("offline", renderNetwork);
    renderNetwork();
  }

  window.MatchIQMatchDayGuard = {allow, isDuplicate, confirmEvent, renderNetwork};
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", bindNetwork, {once:true});
  else bindNetwork();
})();
