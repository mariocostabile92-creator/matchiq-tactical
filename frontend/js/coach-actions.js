function createManualMatch(){}

/* Coach Lineup V1.7 */
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
