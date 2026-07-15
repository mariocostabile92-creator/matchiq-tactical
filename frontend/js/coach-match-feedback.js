(function initCoachMatchFeedback(){
  "use strict";

  const recent = new Map();
  const buttonStates = new WeakMap();
  const LOCK_MS = 900;
  const SUCCESS_MS = 1250;
  const ERROR_MS = 1500;

  function announce(message, tone="ok"){
    const box = document.getElementById("coachEventFeedback");
    if(!box) return;
    box.textContent = message;
    box.className = `coach-event-feedback ${tone}`;
  }

  function resolveButton(button){
    if(button instanceof HTMLElement) return button.closest("button");
    return document.activeElement?.closest?.("button") || null;
  }

  function snapshotButton(button){
    if(!button || buttonStates.has(button)) return;
    buttonStates.set(button, {
      html:button.innerHTML,
      disabled:Boolean(button.disabled),
      timer:null
    });
  }

  function setButtonMessage(button, title, detail){
    if(!button) return;
    button.innerHTML = `<strong>${title}</strong><span>${detail}</span>`;
  }

  function restoreButton(button){
    const state = button && buttonStates.get(button);
    if(!state) return;
    clearTimeout(state.timer);
    button.innerHTML = state.html;
    button.disabled = state.disabled;
    button.removeAttribute("aria-busy");
    button.removeAttribute("data-feedback-state");
    buttonStates.delete(button);
  }

  function beginAction(button){
    const target = resolveButton(button);
    if(!target) return null;
    snapshotButton(target);
    target.disabled = true;
    target.setAttribute("aria-busy", "true");
    target.dataset.feedbackState = "saving";
    setButtonMessage(target, "Salvataggio...", "Attendi");
    return target;
  }

  function completeAction(button){
    const target = resolveButton(button);
    const state = target && buttonStates.get(target);
    if(!target || !state) return;
    target.removeAttribute("aria-busy");
    target.dataset.feedbackState = "success";
    setButtonMessage(target, "\u2713 Registrato", "Evento salvato");
    state.timer = setTimeout(() => restoreButton(target), SUCCESS_MS);
  }

  function failAction(button, message="Riprova"){
    const target = resolveButton(button);
    if(!target) return;
    snapshotButton(target);
    const state = buttonStates.get(target);
    target.disabled = false;
    target.removeAttribute("aria-busy");
    target.dataset.feedbackState = "error";
    setButtonMessage(target, "Non salvato", message);
    state.timer = setTimeout(() => restoreButton(target), ERROR_MS);
  }

  function allow(fingerprint, button=null){
    const key = String(fingerprint || "event");
    const now = Date.now();
    if(now - Number(recent.get(key) || 0) < LOCK_MS){
      announce("Tocco doppio ignorato: l'evento era gia stato registrato.", "warn");
      failAction(button, "Gia registrato");
      return false;
    }
    recent.set(key, now);
    beginAction(button);
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

  function confirmEvent(event, button=null){
    const time = typeof formatCoachEventTime === "function" ? formatCoachEventTime(event) : `${event.minute || 0}'`;
    announce(`${time} ${event.label} registrato per ${event.team}.`, "ok");
    const finish = () => completeAction(button);
    if(typeof requestAnimationFrame === "function") requestAnimationFrame(finish);
    else setTimeout(finish, 0);
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

  window.MatchIQMatchDayGuard = {allow, isDuplicate, confirmEvent, failAction, renderNetwork};
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", bindNetwork, {once:true});
  else bindNetwork();
})();
