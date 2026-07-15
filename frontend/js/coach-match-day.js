(function initCoachMatchDayControls(){
  "use strict";

  const PERIOD_LABELS = {
    "1T":"Primo tempo",
    "INT":"Intervallo",
    "2T":"Secondo tempo",
    "REC":"Recupero",
    "ET1":"Supplementare 1",
    "ET2":"Supplementare 2"
  };

  function command(action){
    if(typeof ensureCoachStateShape === "function") ensureCoachStateShape();
    if(!coachState.match && action !== "finish"){
      if(typeof showNotice === "function") showNotice("Prima crea la partita nel Pre-partita.", "warn");
      return;
    }
    switch(action){
      case "start":
      case "resume":
        startCoachLiveClock();
        break;
      case "pause":
        stopCoachLiveClock(true);
        break;
      case "1T":
      case "2T":
      case "REC":
        setCoachLivePeriod(action);
        break;
      case "INT":
        prepareCoachHalftimeSummary();
        break;
      case "finish":
        finishCoachMatchDay();
        break;
      default:
        return;
    }
    renderStatus();
  }

  function renderStatus(){
    const box = document.getElementById("coachMatchStateCard");
    if(!box || typeof coachState === "undefined") return;
    const home = typeof getTeamName === "function" ? getTeamName("home") : "Casa";
    const away = typeof getTeamName === "function" ? getTeamName("away") : "Ospite";
    const homeGoals = typeof getGoals === "function" ? getGoals("home") : 0;
    const awayGoals = typeof getGoals === "function" ? getGoals("away") : 0;
    const period = coachState.live?.period || "1T";
    const running = Boolean(coachState.live?.running);
    box.innerHTML = `
      <div><span>Partita</span><strong>${esc(home)} <b>${homeGoals} - ${awayGoals}</b> ${esc(away)}</strong></div>
      <div><span>Fase</span><strong>${esc(PERIOD_LABELS[period] || period)}</strong></div>
      <div><span>Timer</span><strong class="${running ? "is-running" : ""}">${running ? "In corso" : "In pausa"}</strong></div>
    `;
    document.querySelectorAll("[data-match-period]").forEach(button => {
      button.classList.toggle("active", button.dataset.matchPeriod === period);
    });
    const startButton = document.getElementById("coachLiveToggle");
    if(startButton){
      startButton.textContent = running
        ? "Pausa timer"
        : (getCoachLiveElapsedSeconds() > 0 ? "Riprendi timer" : "Avvia timer");
      startButton.setAttribute("aria-pressed", running ? "true" : "false");
    }
  }

  function focusManualNote(){
    const input = document.getElementById("coachVoiceInput");
    if(!input) return;
    try{ input.focus({preventScroll:true}); }
    catch{ input.focus(); }
    input.scrollIntoView({behavior:"smooth", block:"center"});
  }

  function addReviewBookmark(feedbackButton=null){
    if(!coachState.match){
      if(typeof showNotice === "function") showNotice("Prima crea la partita nel Pre-partita.", "warn");
      window.MatchIQMatchDayGuard?.failAction(feedbackButton, "Crea prima la partita");
      return;
    }
    const noteInput = document.getElementById("coachReviewNoteInput");
    const note = String(noteInput?.value || "").trim();
    const side = document.getElementById("eventTeamInput")?.value === "away" ? "away" : "home";
    const event = addQuickEvent("da_rivedere", "Da rivedere", "REVIEW", {
      minute:"live",
      live:true,
      side,
      note,
      source:"match-day-bookmark",
      tags:["Da rivedere", "Match Day", coachState.live?.period || "1T"],
      feedbackButton
    });
    if(!event) return;
    if(noteInput) noteInput.value = "";
    if(typeof showNotice === "function"){
      showNotice(`Momento segnato al minuto ${event.minute}.`, "ok", 2800);
    }
  }

  window.setCoachMatchCommand = command;
  window.renderCoachMatchDayStatus = renderStatus;
  window.focusCoachManualNote = focusManualNote;
  window.addCoachReviewBookmark = addReviewBookmark;
})();
