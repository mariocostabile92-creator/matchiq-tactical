(function initCoachLineupLayouts(){
  "use strict";

  const slot = (id, role, x, y) => Object.freeze({ id, role, x, y });
  const layouts = Object.freeze({
    "4-3-3": [slot("gk","Portiere",50,90),slot("d1","Difensore",16,72),slot("d2","Difensore",38,72),slot("d3","Difensore",62,72),slot("d4","Difensore",84,72),slot("m1","Centrocampista",24,50),slot("m2","Centrocampista",50,50),slot("m3","Centrocampista",76,50),slot("a1","Attaccante",18,24),slot("a2","Attaccante",50,20),slot("a3","Attaccante",82,24)],
    "4-4-2": [slot("gk","Portiere",50,90),slot("d1","Difensore",16,72),slot("d2","Difensore",38,72),slot("d3","Difensore",62,72),slot("d4","Difensore",84,72),slot("m1","Esterno",15,49),slot("m2","Centrocampista",38,52),slot("m3","Centrocampista",62,52),slot("m4","Esterno",85,49),slot("a1","Attaccante",35,23),slot("a2","Attaccante",65,23)],
    "4-2-3-1": [slot("gk","Portiere",50,90),slot("d1","Difensore",16,72),slot("d2","Difensore",38,72),slot("d3","Difensore",62,72),slot("d4","Difensore",84,72),slot("m1","Centrocampista",36,57),slot("m2","Centrocampista",64,57),slot("t1","Esterno",18,38),slot("t2","Centrocampista",50,39),slot("t3","Esterno",82,38),slot("a1","Attaccante",50,18)],
    "4-3-1-2": [slot("gk","Portiere",50,90),slot("d1","Difensore",16,72),slot("d2","Difensore",38,72),slot("d3","Difensore",62,72),slot("d4","Difensore",84,72),slot("m1","Centrocampista",24,53),slot("m2","Centrocampista",50,57),slot("m3","Centrocampista",76,53),slot("t1","Centrocampista",50,38),slot("a1","Attaccante",34,20),slot("a2","Attaccante",66,20)],
    "3-5-2": [slot("gk","Portiere",50,90),slot("d1","Difensore",24,72),slot("d2","Difensore",50,75),slot("d3","Difensore",76,72),slot("m1","Esterno",12,49),slot("m2","Centrocampista",34,54),slot("m3","Centrocampista",50,47),slot("m4","Centrocampista",66,54),slot("m5","Esterno",88,49),slot("a1","Attaccante",35,21),slot("a2","Attaccante",65,21)],
    "3-4-3": [slot("gk","Portiere",50,90),slot("d1","Difensore",24,72),slot("d2","Difensore",50,75),slot("d3","Difensore",76,72),slot("m1","Esterno",14,50),slot("m2","Centrocampista",39,53),slot("m3","Centrocampista",61,53),slot("m4","Esterno",86,50),slot("a1","Attaccante",19,23),slot("a2","Attaccante",50,18),slot("a3","Attaccante",81,23)],
    "5-3-2": [slot("gk","Portiere",50,90),slot("d1","Difensore",12,68),slot("d2","Difensore",30,73),slot("d3","Difensore",50,76),slot("d4","Difensore",70,73),slot("d5","Difensore",88,68),slot("m1","Centrocampista",27,49),slot("m2","Centrocampista",50,53),slot("m3","Centrocampista",73,49),slot("a1","Attaccante",35,21),slot("a2","Attaccante",65,21)]
  });
  const aliases = { Esterno:"Centrocampista", Jolly:"Centrocampista" };
  const SETTINGS_KEY = "matchiq_coach_lineup_formations_v1";

  function names(){ return Object.keys(layouts); }
  function normalize(name){ return layouts[name] ? name : "4-3-3"; }
  function slots(name){ return layouts[normalize(name)].map(item => ({...item})); }
  function preferredRole(role){ return aliases[role] || role || "Centrocampista"; }
  function assign(players, formation){
    const available = slots(formation);
    const used = new Set();
    const result = new Map();
    players.forEach(player => {
      if(player.slot && available.some(item => item.id === player.slot) && !used.has(player.slot)){
        used.add(player.slot); result.set(String(player.id), player.slot);
      }
    });
    players.forEach(player => {
      const key = String(player.id);
      if(result.has(key)) return;
      const role = preferredRole(player.role);
      const next = available.find(item => !used.has(item.id) && preferredRole(item.role) === role)
        || available.find(item => !used.has(item.id));
      if(next){ used.add(next.id); result.set(key, next.id); }
    });
    return result;
  }

  function storedSettings(){
    try{
      const value = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
      return value && typeof value === "object" ? value : {};
    }catch(_error){
      return {};
    }
  }

  function getFormation(side){
    const normalizedSide = side === "away" ? "away" : "home";
    const match = typeof coachState !== "undefined" ? (coachState.match || {}) : {};
    const matchValue = normalizedSide === "away" ? match.awayShape : match.homeShape;
    const savedValue = storedSettings()[normalizedSide];
    return normalize(matchValue || savedValue || "4-3-3");
  }

  function persistFormation(side, formation){
    const settings = storedSettings();
    settings[side] = normalize(formation);
    try{ localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); }catch(_error){}
  }

  function ensureSlots(side){
    if(typeof coachState === "undefined" || !Array.isArray(coachState.lineup)) return;
    const normalizedSide = side === "away" ? "away" : "home";
    const starters = coachState.lineup.filter(player =>
      (player.side === "away" ? "away" : "home") === normalizedSide && player.status !== "Panchina"
    );
    const assignments = assign(starters, getFormation(normalizedSide));
    starters.forEach(player => { player.slot = assignments.get(String(player.id)) || ""; });
  }

  function setFormation(formation){
    const side = window.activePitchSide === "away" ? "away" : "home";
    const value = normalize(formation);
    persistFormation(side, value);
    if(typeof coachState !== "undefined" && coachState.match){
      if(side === "away") coachState.match.awayShape = value;
      else coachState.match.homeShape = value;
    }
    const setupInput = document.getElementById(side === "away" ? "awayShapeInput" : "homeShapeInput");
    if(setupInput) setupInput.value = value;
    ensureSlots(side);
    if(typeof window.saveState === "function") window.saveState();
    if(typeof window.renderLineup === "function") window.renderLineup();
    if(typeof window.showNotice === "function") window.showNotice(`Modulo ${value} applicato alla squadra ${side === "away" ? "ospite" : "di casa"}.`, "ok", 2200);
  }

  function syncControl(){
    const side = window.activePitchSide === "away" ? "away" : "home";
    const select = document.getElementById("lineupFormationSelect");
    const label = document.getElementById("lineupFormationTeam");
    if(select){
      const current = getFormation(side);
      if(select.options.length !== names().length){
        select.innerHTML = names().map(name => `<option value="${name}">${name}</option>`).join("");
      }
      select.value = current;
    }
    if(label) label.textContent = side === "away" ? "Squadra ospite" : "Squadra di casa";
  }

  window.getLineupFormation = getFormation;
  window.setLineupFormation = setFormation;
  window.syncLineupFormationControl = syncControl;
  window.ensureLineupSlots = ensureSlots;
  window.MatchIQLineupLayouts = { names, normalize, slots, assign, getFormation, ensureSlots };
})();
