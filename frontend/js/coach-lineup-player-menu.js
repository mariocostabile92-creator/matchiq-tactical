(function initCoachLineupPlayerMenu(){
  "use strict";

  function getPlayer(playerId){
    if(typeof coachState === "undefined" || !Array.isArray(coachState.lineup)) return null;
    return coachState.lineup.find(player => String(player.id) === String(playerId)) || null;
  }

  function fillSlotOptions(player){
    const select = document.getElementById("lineupEditSlot");
    if(!select) return;
    const formation = typeof getLineupFormation === "function" ? getLineupFormation(player.side) : "4-3-3";
    const slots = window.MatchIQLineupLayouts?.slots(formation) || [];
    select.innerHTML = `<option value="">Posizione automatica</option>` + slots.map(slot =>
      `<option value="${slot.id}">${slot.role} · ${slot.id.toUpperCase()}</option>`
    ).join("");
    select.value = player.slot || "";
    select.disabled = player.status === "Panchina";
  }

  function open(playerId){
    const player = getPlayer(playerId);
    const dialog = document.getElementById("lineupPlayerDialog");
    if(!player || !dialog) return;
    if(typeof setPitchSide === "function") setPitchSide(player.side);
    document.getElementById("lineupEditId").value = player.id;
    document.getElementById("lineupEditNumber").value = player.number || "";
    document.getElementById("lineupEditName").value = player.name || "";
    document.getElementById("lineupEditRole").value = player.role || "Jolly";
    document.getElementById("lineupEditStatus").value = player.status || "Titolare";
    document.getElementById("lineupDialogTeam").textContent = player.side === "away" ? "Squadra ospite" : "Squadra di casa";
    fillSlotOptions(player);
    if(typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }

  function close(){
    const dialog = document.getElementById("lineupPlayerDialog");
    if(!dialog) return;
    if(typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  }

  function save(){
    const player = getPlayer(document.getElementById("lineupEditId")?.value);
    if(!player) return;
    const name = String(document.getElementById("lineupEditName")?.value || "").trim();
    if(!name){
      if(typeof showNotice === "function") showNotice("Inserisci il nome del giocatore.", "warn");
      return;
    }

    const nextStatus = document.getElementById("lineupEditStatus")?.value === "Panchina" ? "Panchina" : "Titolare";
    const otherStarters = coachState.lineup.filter(item =>
      String(item.id) !== String(player.id) && item.side === player.side && item.status !== "Panchina"
    );
    if(nextStatus === "Titolare" && otherStarters.length >= 11){
      if(typeof showNotice === "function") showNotice("Ci sono gia 11 titolari: spostane prima uno in panchina.", "warn", 3200);
      return;
    }

    player.number = String(document.getElementById("lineupEditNumber")?.value || "").trim();
    player.name = name;
    player.role = document.getElementById("lineupEditRole")?.value || "Jolly";
    player.status = nextStatus;
    if(nextStatus === "Panchina"){
      player.slot = "";
    }else{
      const requestedSlot = document.getElementById("lineupEditSlot")?.value || "";
      const occupant = requestedSlot ? otherStarters.find(item => item.slot === requestedSlot) : null;
      if(occupant){ occupant.status = "Panchina"; occupant.slot = ""; }
      player.slot = requestedSlot;
      if(typeof ensureLineupSlots === "function") ensureLineupSlots(player.side);
    }

    if(typeof saveState === "function") saveState();
    close();
    if(typeof renderLineup === "function") renderLineup();
    if(typeof renderEventPlayerSelect === "function") renderEventPlayerSelect();
    if(typeof showNotice === "function") showNotice(`${player.name} aggiornato.`, "ok", 2200);
  }

  function setStatus(status){
    const select = document.getElementById("lineupEditStatus");
    if(!select) return;
    select.value = status === "Panchina" ? "Panchina" : "Titolare";
    const player = getPlayer(document.getElementById("lineupEditId")?.value);
    if(player) fillSlotOptions({...player, status:select.value});
  }

  function remove(){
    const id = document.getElementById("lineupEditId")?.value;
    const player = getPlayer(id);
    if(!player || !confirm(`Rimuovere ${player.name} dalla formazione?`)) return;
    close();
    if(typeof deleteLineupPlayer === "function") deleteLineupPlayer(id);
  }

  window.openLineupPlayerMenu = open;
  window.closeLineupPlayerMenu = close;
  window.saveLineupPlayerChanges = save;
  window.setLineupPlayerDialogStatus = setStatus;
  window.removeLineupPlayerFromDialog = remove;
})();
