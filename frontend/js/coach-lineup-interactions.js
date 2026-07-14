(function initCoachLineupInteractions(){
  "use strict";

  let gesture = null;
  let suppressClickUntil = 0;
  const DRAG_THRESHOLD = 7;

  function playerById(playerId){
    if(typeof coachState === "undefined" || !Array.isArray(coachState.lineup)) return null;
    return coachState.lineup.find(player => String(player.id) === String(playerId)) || null;
  }

  function commitLineup(message){
    if(typeof saveState === "function") saveState();
    if(typeof renderLineup === "function") renderLineup();
    if(typeof showNotice === "function") showNotice(message, "ok", 2100);
  }

  function moveLineupPlayerToSlot(playerId, slotId, side){
    const player = playerById(playerId);
    const normalizedSide = side === "away" ? "away" : "home";
    if(!player || normalizedSide !== (window.activePitchSide === "away" ? "away" : "home")) return false;

    const validSlots = window.MatchIQLineupLayouts?.slots(
      typeof getLineupFormation === "function" ? getLineupFormation(normalizedSide) : "4-3-3"
    ) || [];
    if(!validSlots.some(slot => slot.id === slotId)) return false;

    const previousSlot = player.slot || "";
    const wasBench = player.status === "Panchina";
    const occupant = coachState.lineup.find(item =>
      String(item.id) !== String(player.id)
      && item.side === normalizedSide
      && item.status !== "Panchina"
      && item.slot === slotId
    );

    player.side = normalizedSide;
    player.team = typeof getTeamName === "function" ? getTeamName(normalizedSide) : player.team;
    player.status = "Titolare";
    player.slot = slotId;

    if(occupant){
      if(wasBench || !previousSlot){
        occupant.status = "Panchina";
        occupant.slot = "";
      }else{
        occupant.slot = previousSlot;
      }
    }

    commitLineup(occupant ? `Posizioni scambiate: ${player.name} e ${occupant.name}.` : `${player.name} spostato sul campo.`);
    return true;
  }

  function moveLineupPlayerToBench(playerId){
    const player = playerById(playerId);
    if(!player || player.status === "Panchina") return false;
    player.status = "Panchina";
    player.slot = "";
    commitLineup(`${player.name} spostato in panchina.`);
    return true;
  }

  function clearDragState(){
    document.querySelectorAll(".is-drag-target,.is-dragging").forEach(node => node.classList.remove("is-drag-target","is-dragging"));
    document.body.classList.remove("is-lineup-dragging");
    gesture = null;
  }

  function dragTargetAt(x, y){
    const node = document.elementFromPoint(x, y);
    return node?.closest?.("[data-lineup-slot], [data-lineup-bench]") || null;
  }

  function onPointerDown(event){
    const player = event.target.closest?.("[data-lineup-player]");
    if(!player || event.button > 0) return;
    gesture = {
      pointerId:event.pointerId,
      playerId:player.dataset.lineupPlayer,
      startX:event.clientX,
      startY:event.clientY,
      node:player,
      dragging:false,
      target:null
    };
    player.setPointerCapture?.(event.pointerId);
  }

  function onPointerMove(event){
    if(!gesture || gesture.pointerId !== event.pointerId) return;
    const distance = Math.hypot(event.clientX - gesture.startX, event.clientY - gesture.startY);
    if(!gesture.dragging && distance < DRAG_THRESHOLD) return;
    if(!gesture.dragging){
      gesture.dragging = true;
      gesture.node.classList.add("is-dragging");
      document.body.classList.add("is-lineup-dragging");
    }
    event.preventDefault();
    gesture.target?.classList.remove("is-drag-target");
    gesture.target = dragTargetAt(event.clientX, event.clientY);
    gesture.target?.classList.add("is-drag-target");
  }

  function onPointerUp(event){
    if(!gesture || gesture.pointerId !== event.pointerId) return;
    const current = gesture;
    const target = current.dragging ? (current.target || dragTargetAt(event.clientX, event.clientY)) : null;
    if(target?.hasAttribute("data-lineup-slot")){
      moveLineupPlayerToSlot(current.playerId, target.dataset.lineupSlot, target.dataset.lineupSide);
    }else if(target?.hasAttribute("data-lineup-bench")){
      moveLineupPlayerToBench(current.playerId);
    }
    if(current.dragging) suppressClickUntil = Date.now() + 350;
    clearDragState();
  }

  function bind(){
    const workspace = document.getElementById("lineupWorkspace");
    if(!workspace || workspace.dataset.pointerLineupBound === "1") return;
    workspace.dataset.pointerLineupBound = "1";
    workspace.addEventListener("pointerdown", onPointerDown);
    workspace.addEventListener("pointermove", onPointerMove, {passive:false});
    workspace.addEventListener("pointerup", onPointerUp);
    workspace.addEventListener("pointercancel", clearDragState);
    workspace.addEventListener("click", event => {
      if(Date.now() < suppressClickUntil){ event.preventDefault(); event.stopPropagation(); }
    }, true);
  }

  window.moveLineupPlayerToSlot = moveLineupPlayerToSlot;
  window.moveLineupPlayerToBench = moveLineupPlayerToBench;
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind, {once:true});
  else bind();
})();
