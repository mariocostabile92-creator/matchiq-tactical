function createManualMatch(){
    const homeTeam = getInputValue("homeTeamInput");
    const awayTeam = getInputValue("awayTeamInput");
    if(!homeTeam || !awayTeam){
        showNotice("Inserisci squadra casa e squadra trasferta.", "warn");
        return;
    }
    ensureCoachStateShape();
    coachState.match = normalizeCoachMatch({
        id: coachState.match?.id || Date.now(),
        homeTeam,
        awayTeam,
        category: getInputValue("categoryInput", "Dilettanti"),
        date: getInputValue("matchDateInput", todayISO()),
        field: getInputValue("matchFieldInput", ""),
        homeShape: getInputValue("homeShapeInput", ""),
        awayShape: getInputValue("awayShapeInput", ""),
        preNotes: getInputValue("preNotesInput", "")
    });
    coachState.lineup = getLineup().map(p => ({...p, team:p.side === "home" ? homeTeam : awayTeam}));
    saveState();
    renderAll();
    showNotice("Partita Coach Mode creata/aggiornata.", "ok");
}

function clearCurrentMatch(){
    if(!confirm("Vuoi resettare partita, eventi, formazione e report Coach Mode?")) return;
    stopCoachLiveClock(false);
    coachState = {match:null, events:[], ratings:[], lineup:[], report:"", live:null};
    localStorage.removeItem(STORAGE_KEY);
    [
        "homeTeamInput","awayTeamInput","matchFieldInput","homeShapeInput","awayShapeInput","preNotesInput",
        "eventMinuteInput","eventPlayerInput","eventPlayerSelectInput","eventNoteInput","coachVoiceInput"
    ].forEach(id => setInputValue(id, ""));
    setInputValue("categoryInput", "Dilettanti");
    setInputValue("matchDateInput", todayISO());
    clearLineupForm();
    clearRatingForm();
    renderAll();
    showNotice("Partita resettata.", "ok");
}

function buildCoachEvent(type, label, icon, options={}){
    ensureCoachStateShape();
    const useLiveMinute = options.minute === "live" || (options.live && !getInputValue("eventMinuteInput", ""));
    const minuteRaw = options.minute !== undefined && options.minute !== "live" ? String(options.minute) : getInputValue("eventMinuteInput", "");
    const minute = useLiveMinute ? getLiveMinuteLabel() : (minuteRaw === "" ? "--" : Math.max(0, Math.min(130, Number(minuteRaw) || 0)));
    const side = options.side || getInputValue("eventTeamInput", "home");
    const selectedPlayerId = options.playerId || getInputValue("eventPlayerSelectInput", "");
    const selectedPlayer = selectedPlayerId ? getLineupPlayerById(selectedPlayerId) : null;
    const player = options.player || (selectedPlayer ? formatLineupPlayer(selectedPlayer) : getInputValue("eventPlayerInput", ""));
    const note = options.note !== undefined ? String(options.note || "") : getInputValue("eventNoteInput", "");
    return {
        id: Date.now() + Math.random(),
        type,
        label,
        icon,
        minute,
        period: coachState.live?.period || "",
        side,
        team: getTeamName(side),
        player,
        playerId: selectedPlayer ? selectedPlayer.id : "",
        playerRole: selectedPlayer ? selectedPlayer.role : "",
        note,
        source: options.source || (options.voice ? "voice" : "quick"),
        createdAt: new Date().toISOString()
    };
}

function addQuickEvent(type, label, icon, options={}){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }
    const event = buildCoachEvent(type, label, icon, options);
    coachState.events.unshift(event);
    setInputValue("eventNoteInput", "");
    setInputValue("eventPlayerInput", "");
    setInputValue("eventPlayerSelectInput", "");
    saveState();
    renderAll();
    showNotice(`${label} registrato per ${event.team}${event.player ? " - " + event.player : ""}.`, "ok", 2500);
}

function addLiveEvent(type, label, icon, note=""){
    addQuickEvent(type, label, icon, {minute:"live", live:true, note, source:"live"});
}

function addLiveNote(note){
    const value = String(note || getInputValue("coachVoiceInput", "") || "").trim();
    if(!value){
        showNotice("Scrivi o detta una nota per aggiungerla alla timeline.", "warn");
        return;
    }
    addQuickEvent("nota", "Nota staff", "NOTE", {minute:"live", live:true, note:value, source:"voice"});
    setInputValue("coachVoiceInput", "");
}

function deleteEvent(eventId){
    ensureCoachStateShape();
    coachState.events = coachState.events.filter(e => String(e.id) !== String(eventId));
    saveState();
    renderAll();
}

function fillFormFromState(){
    if(!coachState.match) return;
    coachState.match = normalizeCoachMatch(coachState.match);
    setInputValue("homeTeamInput", coachState.match.homeTeam);
    setInputValue("awayTeamInput", coachState.match.awayTeam);
    setInputValue("categoryInput", coachState.match.category || "Dilettanti");
    setInputValue("matchDateInput", coachState.match.date || todayISO());
    setInputValue("matchFieldInput", coachState.match.field);
    setInputValue("homeShapeInput", coachState.match.homeShape);
    setInputValue("awayShapeInput", coachState.match.awayShape);
    setInputValue("preNotesInput", coachState.match.preNotes);
}

function startCoachLiveClock(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }
    ensureCoachStateShape();
    if(!coachState.live.running){
        coachState.live.running = true;
        coachState.live.startedAt = new Date().toISOString();
        saveState();
    }
    ensureCoachLiveTicker();
    renderLiveAssistant();
}

function stopCoachLiveClock(persist=true){
    ensureCoachStateShape();
    if(coachState.live.running){
        coachState.live.elapsed = getCoachLiveElapsedSeconds();
        coachState.live.running = false;
        coachState.live.startedAt = null;
    }
    if(coachLiveTimer){
        clearInterval(coachLiveTimer);
        coachLiveTimer = null;
    }
    if(persist) saveState();
    renderLiveAssistant();
}

function toggleCoachLiveClock(){
    ensureCoachStateShape();
    if(coachState.live.running) stopCoachLiveClock();
    else startCoachLiveClock();
}

function resetCoachLiveClock(){
    if(!confirm("Vuoi azzerare solo il timer live? Eventi e report restano salvati.")) return;
    ensureCoachStateShape();
    coachState.live = normalizeCoachLive({period:coachState.live?.period || "1T"});
    saveState();
    stopCoachLiveClock(false);
    renderLiveAssistant();
}

function setCoachLivePeriod(period){
    ensureCoachStateShape();
    if(coachState.live.running){
        coachState.live.elapsed = getCoachLiveElapsedSeconds();
        coachState.live.startedAt = new Date().toISOString();
    }
    coachState.live.period = period || "1T";
    saveState();
    renderLiveAssistant();
}

function ensureCoachLiveTicker(){
    if(coachLiveTimer) return;
    coachLiveTimer = setInterval(() => {
        if(!coachState.live?.running){
            clearInterval(coachLiveTimer);
            coachLiveTimer = null;
            return;
        }
        renderLiveAssistant();
    }, 1000);
}

function startCoachVoiceNote(){
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!SpeechRecognition){
        showNotice("Dettatura non disponibile su questo browser. Usa il campo nota rapida.", "warn", 4500);
        return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "it-IT";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    showNotice("Sto ascoltando: detta una nota tattica breve.", "ok", 2500);
    recognition.onresult = event => {
        const text = event.results?.[0]?.[0]?.transcript || "";
        setInputValue("coachVoiceInput", text);
        addLiveNote(text);
    };
    recognition.onerror = () => showNotice("Non sono riuscito a leggere la voce. Riprova o scrivi la nota.", "warn");
    recognition.start();
}

function clearRatingForm(){
    setInputValue("ratingPlayerInput", "");
    setInputValue("ratingNoteInput", "");
    setInputValue("ratingVoteInput", "6");
    setInputValue("ratingRoleInput", "Portiere");
    setInputValue("ratingTeamInput", "home");
}

function addPlayerRating(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }
    ensureCoachStateShape();
    if(!canAddCoachRating()){
        showCoachProNotice("Pagelle illimitate");
        return;
    }
    const player = getInputValue("ratingPlayerInput", "");
    const side = getInputValue("ratingTeamInput", "home");
    const role = getInputValue("ratingRoleInput", "Jolly");
    const vote = Number(getInputValue("ratingVoteInput", "6"));
    const note = getInputValue("ratingNoteInput", "");
    if(!player){
        showNotice("Inserisci il nome del giocatore.", "warn");
        return;
    }
    coachState.ratings.unshift({
        id:Date.now()+Math.random(),
        player,
        side,
        team:getTeamName(side),
        role,
        vote:Number.isFinite(vote) ? vote : 6,
        note,
        createdAt:new Date().toISOString()
    });
    saveState();
    clearRatingForm();
    renderAll();
    showNotice(`Pagella aggiunta: ${player} (${Number.isFinite(vote) ? vote : 6}).`, "ok", 2500);
}

function deleteRating(ratingId){
    ensureCoachStateShape();
    coachState.ratings = coachState.ratings.filter(r => String(r.id) !== String(ratingId));
    saveState();
    renderAll();
}

function getBestRating(){
    ensureCoachStateShape();
    if(!coachState.ratings.length) return null;
    return [...coachState.ratings].sort((a,b) => Number(b.vote || 0) - Number(a.vote || 0))[0];
}

function clearLineupForm(){
    setInputValue("lineupNumberInput", "");
    setInputValue("lineupNameInput", "");
    setInputValue("lineupTeamInput", "home");
    setInputValue("lineupRoleInput", "Portiere");
    setInputValue("lineupStatusInput", "Titolare");
}

function addLineupPlayer(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }
    ensureCoachStateShape();
    const name = getInputValue("lineupNameInput", "");
    if(!name){
        showNotice("Inserisci il nome del giocatore.", "warn");
        return;
    }
    const side = getInputValue("lineupTeamInput", "home") === "away" ? "away" : "home";
    const player = normalizeLineupPlayer({
        id:Date.now()+Math.random(),
        number:getInputValue("lineupNumberInput", ""),
        name,
        side,
        team:getTeamName(side),
        role:getInputValue("lineupRoleInput", "Jolly"),
        status:getInputValue("lineupStatusInput", "Titolare"),
        createdAt:new Date().toISOString()
    });
    coachState.lineup.push(player);
    window.activePitchSide = side;
    saveState();
    clearLineupForm();
    renderAll();
    showNotice(`Giocatore aggiunto: ${formatLineupPlayer(player)}.`, "ok", 2500);
}

function deleteLineupPlayer(playerId){
    ensureCoachStateShape();
    coachState.lineup = getLineup().filter(p => String(p.id) !== String(playerId));
    saveState();
    renderAll();
}

function clearLineup(){
    ensureCoachStateShape();
    if(!getLineup().length){
        showNotice("Formazione gia vuota.", "warn");
        return;
    }
    if(!confirm("Vuoi svuotare tutta la formazione? Gli eventi gia inseriti resteranno salvati.")) return;
    coachState.lineup = [];
    saveState();
    setInputValue("eventPlayerSelectInput", "");
    setInputValue("eventPlayerInput", "");
    renderAll();
    showNotice("Formazione svuotata.", "ok");
}

function syncEventPlayerFromSelect(){
    const playerId = getInputValue("eventPlayerSelectInput", "");
    const player = playerId ? getLineupPlayerById(playerId) : null;
    if(player) setInputValue("eventPlayerInput", formatLineupPlayer(player));
}

function syncRatingPlayerFromLineup(playerId){
    const player = playerId ? getLineupPlayerById(playerId) : null;
    if(!player) return;
    setInputValue("ratingPlayerInput", formatLineupPlayer(player));
    setInputValue("ratingTeamInput", player.side);
    setInputValue("ratingRoleInput", player.role || "Jolly");
}
