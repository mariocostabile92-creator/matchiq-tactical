function createManualMatch(){
    const homeTeam = getInputValue("homeTeamInput");
    const awayTeam = getInputValue("awayTeamInput");

    if(!homeTeam || !awayTeam){
        showNotice("Inserisci squadra casa e squadra trasferta.", "warn");
        return;
    }

    coachState.match = {
        id: coachState.match?.id || Date.now(),
        homeTeam,
        awayTeam,
        category: getInputValue("categoryInput","Dilettanti"),
        date: getInputValue("matchDateInput", todayISO()),
        homeShape: getInputValue("homeShapeInput",""),
        awayShape: getInputValue("awayShapeInput",""),
        preNotes: getInputValue("preNotesInput","")
    };

    if(!Array.isArray(coachState.events)) coachState.events = [];
    if(!Array.isArray(coachState.ratings)) coachState.ratings = [];
    if(!Array.isArray(coachState.lineup)) coachState.lineup = [];

    saveState();
    renderAll();

    showNotice("Partita Coach Mode creata/aggiornata.", "ok");
}

function clearCurrentMatch(){
    if(!confirm("Vuoi resettare partita, eventi, formazione e report Coach Mode?")) return;

    coachState = {
        match: null,
        events: [],
        ratings: [],
        lineup: [],
        report: ""
    };

    localStorage.removeItem(STORAGE_KEY);

    setInputValue("homeTeamInput","");
    setInputValue("awayTeamInput","");
    setInputValue("categoryInput","Dilettanti");
    setInputValue("matchDateInput",todayISO());
    setInputValue("homeShapeInput","");
    setInputValue("awayShapeInput","");
    setInputValue("preNotesInput","");
    setInputValue("eventMinuteInput","");
    setInputValue("eventPlayerInput","");
    setInputValue("eventPlayerSelectInput","");
    setInputValue("eventNoteInput","");
    clearLineupForm();
    clearRatingForm();

    renderAll();
    showNotice("Partita resettata.", "ok");
}

function addQuickEvent(type,label,icon){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }

    const minuteRaw = getInputValue("eventMinuteInput","");
    const minute = minuteRaw === "" ? "--" : Math.max(0, Math.min(130, Number(minuteRaw) || 0));
    const side = getInputValue("eventTeamInput","home");
    const selectedPlayerId = getInputValue("eventPlayerSelectInput","");
    const selectedPlayer = selectedPlayerId ? getLineupPlayerById(selectedPlayerId) : null;
    const player = selectedPlayer ? formatLineupPlayer(selectedPlayer) : getInputValue("eventPlayerInput","");
    const note = getInputValue("eventNoteInput","");

    const event = {
        id: Date.now() + Math.random(),
        type,
        label,
        icon,
        minute,
        side,
        team: getTeamName(side),
        player,
        playerId: selectedPlayer ? selectedPlayer.id : "",
        playerRole: selectedPlayer ? selectedPlayer.role : "",
        note,
        createdAt: new Date().toISOString()
    };

    coachState.events.unshift(event);

    setInputValue("eventNoteInput","");
    setInputValue("eventPlayerInput","");
    setInputValue("eventPlayerSelectInput","");

    saveState();
    renderAll();

    showNotice(`${label} registrato per ${event.team}${player ? " · " + player : ""}.`, "ok", 2500);
}

function deleteEvent(eventId){
    coachState.events = coachState.events.filter(e => String(e.id) !== String(eventId));
    saveState();
    renderAll();
}

function fillFormFromState(){
    if(!coachState.match) return;

    setInputValue("homeTeamInput", coachState.match.homeTeam);
    setInputValue("awayTeamInput", coachState.match.awayTeam);
    setInputValue("categoryInput", coachState.match.category || "Dilettanti");
    setInputValue("matchDateInput", coachState.match.date || todayISO());
    setInputValue("homeShapeInput", coachState.match.homeShape);
    setInputValue("awayShapeInput", coachState.match.awayShape);
    setInputValue("preNotesInput", coachState.match.preNotes);
}

function clearRatingForm(){
    setInputValue("ratingPlayerInput","");
    setInputValue("ratingNoteInput","");
    setInputValue("ratingVoteInput","6");
    setInputValue("ratingRoleInput","Portiere");
    setInputValue("ratingTeamInput","home");
}

function addPlayerRating(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }

    if(!canAddCoachRating()){
        showCoachProNotice("Pagelle illimitate");
        return;
    }

    const player = getInputValue("ratingPlayerInput","");
    const side = getInputValue("ratingTeamInput","home");
    const role = getInputValue("ratingRoleInput","Jolly");
    const vote = Number(getInputValue("ratingVoteInput","6"));
    const note = getInputValue("ratingNoteInput","");

    if(!player){
        showNotice("Inserisci il nome del giocatore.", "warn");
        return;
    }

    const rating = {
        id: Date.now() + Math.random(),
        player,
        side,
        team: getTeamName(side),
        role,
        vote: Number.isFinite(vote) ? vote : 6,
        note,
        createdAt: new Date().toISOString()
    };

    coachState.ratings.unshift(rating);

    saveState();

    if(typeof trackCoachFeature === "function"){
        trackCoachFeature("coach_pagelle", {
            player: rating.player,
            role: rating.role,
            team: rating.team,
            vote: rating.vote,
            total_ratings: coachState.ratings.length
        });
    }

    clearRatingForm();
    renderAll();

    const limits = getCoachLimits();

    if(!isCoachPro()){
        showNotice(`Pagella aggiunta: ${player} (${rating.vote}). Free: ${coachState.ratings.length}/${limits.maxRatings}.`, "ok", 3500);
    }else{
        showNotice(`Pagella aggiunta: ${player} (${rating.vote}).`, "ok", 2500);
    }
}

function deleteRating(ratingId){
    coachState.ratings = coachState.ratings.filter(r => String(r.id) !== String(ratingId));
    saveState();
    renderAll();
}

function getBestRating(){
    if(!coachState.ratings.length) return null;
    return [...coachState.ratings].sort((a,b) => Number(b.vote || 0) - Number(a.vote || 0))[0];
}

/* Coach Lineup V1.7.1 */
function clearLineupForm(){
    setInputValue("lineupNumberInput","");
    setInputValue("lineupNameInput","");
    setInputValue("lineupTeamInput","home");
    setInputValue("lineupRoleInput","Portiere");
    setInputValue("lineupStatusInput","Titolare");
}

function addLineupPlayer(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }

    const name = getInputValue("lineupNameInput","");
    if(!name){
        showNotice("Inserisci il nome del giocatore.", "warn");
        return;
    }

    const side = getInputValue("lineupTeamInput","home");
    const player = {
        id: Date.now() + Math.random(),
        number: getInputValue("lineupNumberInput",""),
        name,
        side,
        team: getTeamName(side),
        role: getInputValue("lineupRoleInput","Jolly"),
        status: getInputValue("lineupStatusInput","Titolare"),
        createdAt: new Date().toISOString()
    };

    if(!Array.isArray(coachState.lineup)){
        coachState.lineup = [];
    }

    coachState.lineup.push(player);
    saveState();
    clearLineupForm();
    renderAll();

    showNotice(`Giocatore aggiunto: ${formatLineupPlayer(player)}.`, "ok", 2500);
}

function deleteLineupPlayer(playerId){
    coachState.lineup = getLineup().filter(p => String(p.id) !== String(playerId));
    saveState();
    renderAll();
}

function clearLineup(){
    if(!getLineup().length){
        showNotice("Formazione già vuota.", "warn");
        return;
    }

    if(!confirm("Vuoi svuotare tutta la formazione? Gli eventi già inseriti resteranno salvati.")) return;

    coachState.lineup = [];
    saveState();
    renderAll();
    showNotice("Formazione svuotata.", "ok");
}

function syncEventPlayerFromSelect(){
    const playerId = getInputValue("eventPlayerSelectInput","");
    const player = playerId ? getLineupPlayerById(playerId) : null;
    if(player){
        setInputValue("eventPlayerInput", formatLineupPlayer(player));
    }
}

function syncRatingPlayerFromLineup(playerId){
    const player = playerId ? getLineupPlayerById(playerId) : null;
    if(!player) return;
    setInputValue("ratingPlayerInput", formatLineupPlayer(player));
    setInputValue("ratingTeamInput", player.side);
    setInputValue("ratingRoleInput", player.role || "Jolly");
}


/* Coach Lineup Pitch Hotfix V1.7.4 */
function clearLineup(){
    if(!getLineup().length){
        showNotice("Formazione già vuota.", "warn");
        return;
    }

    if(!confirm("Vuoi svuotare tutta la formazione? Gli eventi già inseriti resteranno salvati.")) return;

    coachState.lineup = [];
    saveState();

    setInputValue("eventPlayerSelectInput","");
    setInputValue("eventPlayerInput","");

    if(typeof renderAll === "function"){
        renderAll();
    }

    if(typeof renderLineup === "function"){
        renderLineup();
    }

    if(typeof renderLineupPitch === "function"){
        renderLineupPitch();
    }

    console.log("[Coach Lineup] cleared", coachState.lineup);

    showNotice("Formazione svuotata.", "ok");
}
