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
    addSmartCoachNote(value, "voice");
    setInputValue("coachVoiceInput", "");
}

function normalizeCoachSpeechText(text){
    return String(text || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[.,;:!?]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function extractCoachMinuteFromText(text){
    const clean = normalizeCoachSpeechText(text);
    const direct = clean.match(/\b(?:minuto|min|al|all)\s*(\d{1,3})\b/);
    if(direct) return Math.max(0, Math.min(130, Number(direct[1]) || 0));
    const lone = clean.match(/\b(\d{1,3})\s*(?:'| minuto|min)\b/);
    if(lone) return Math.max(0, Math.min(130, Number(lone[1]) || 0));
    return "live";
}

function inferCoachSideFromText(text){
    const clean = normalizeCoachSpeechText(text);
    if(/\b(loro|avversari|avversario|trasferta|ospiti|subiamo|ci attaccano|ci pressano)\b/.test(clean)) return "away";
    if(/\b(noi|nostra|nostro|casa|noi siamo|attacchiamo|pressiamo|recuperiamo)\b/.test(clean)) return "home";
    return getInputValue("eventTeamInput", "home");
}

function inferCoachPlayerFromText(text){
    const clean = normalizeCoachSpeechText(text);
    const number = clean.match(/\b(?:numero|n)\s*(\d{1,2})\b/);
    if(number) return `#${number[1]}`;
    const player = clean.match(/\b(?:giocatore|il|la)\s+([a-z]{3,}(?:\s+[a-z]{3,})?)\b/);
    if(player && !["nostra","nostro","loro","casa","trasferta"].includes(player[1])) return player[1];
    return "";
}

function inferCoachEventFromText(text){
    const clean = normalizeCoachSpeechText(text);
    const rules = [
        {type:"gol", label:"Gol", icon:"GOL", pattern:/\b(gol|rete|segnato|pareggio|vantaggio)\b/},
        {type:"occasione", label:"Occasione", icon:"OCC", pattern:/\b(occasione|chance|tiro pericoloso|traversa|palo|parata|quasi gol)\b/},
        {type:"palla_persa", label:"Palla persa", icon:"PERSA", pattern:/\b(palla persa|perdiamo palla|perso palla|uscita sporca|errore in uscita|transizione negativa)\b/},
        {type:"recupero", label:"Recupero palla", icon:"REC", pattern:/\b(recupero|riconquista|rubiamo|palla recuperata|pressing riuscito)\b/},
        {type:"errore_difensivo", label:"Errore difensivo", icon:"ERR", pattern:/\b(errore difensivo|marcatura|copertura|linea bassa|linea troppo bassa|difesa scoperta|buco|imbucata)\b/},
        {type:"pressing", label:"Pressing", icon:"PRESS", pattern:/\b(pressing|pressione|pressiamo|pressano|aggressione|riaggressione)\b/},
        {type:"transizione", label:"Transizione", icon:"TRANS", pattern:/\b(transizione|ripartenza|contropiede|rest defense|preventiva)\b/},
        {type:"ampiezza", label:"Ampiezza", icon:"WIDTH", pattern:/\b(ampiezza|larghi|stretto|larga|esterno libero|cambio lato)\b/},
        {type:"seconda_palla", label:"Seconda palla", icon:"2BALL", pattern:/\b(seconda palla|duello|rimbalzo|spizzata)\b/},
        {type:"cambio", label:"Cambio", icon:"CAMBIO", pattern:/\b(cambio|sostituzione|entra|esce|modulo)\b/}
    ];
    return rules.find(rule => rule.pattern.test(clean)) || {type:"nota", label:"Nota staff", icon:"NOTE"};
}

function buildCoachPromptFromEvent(event){
    if(!event) return "";
    const sideName = event.team || getTeamName(event.side);
    const suggestions = {
        palla_persa: `Domanda MatchIQ: la palla persa di ${sideName} nasce da uscita bassa, scelta forzata o mancanza di sostegno?`,
        errore_difensivo: `Domanda MatchIQ: l'errore difensivo di ${sideName} riguarda linea, marcatura o copertura preventiva?`,
        pressing: `Domanda MatchIQ: il pressing di ${sideName} e organizzato o solo reazione individuale?`,
        transizione: `Domanda MatchIQ: questa transizione nasce da perdita centrale, lato scoperto o squadra lunga?`,
        ampiezza: `Domanda MatchIQ: l'ampiezza crea vantaggio a destra, sinistra o cambio lato?`,
        seconda_palla: `Domanda MatchIQ: sulla seconda palla manca aggressione, distanza o comunicazione?`,
        occasione: `Domanda MatchIQ: occasione costruita da combinazione, palla lunga, errore o palla inattiva?`
    };
    return suggestions[event.type] || "";
}

function addSmartCoachNote(text, source="smart"){
    const value = String(text || "").trim();
    if(!value){
        showNotice("Scrivi o detta una nota per aggiungerla alla timeline.", "warn");
        return null;
    }
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return null;
    }

    const inferred = inferCoachEventFromText(value);
    const minute = extractCoachMinuteFromText(value);
    const side = inferCoachSideFromText(value);
    const player = inferCoachPlayerFromText(value);
    const event = buildCoachEvent(inferred.type, inferred.label, inferred.icon, {
        minute,
        live: minute === "live",
        side,
        player,
        note:value,
        source
    });
    event.aiPrompt = buildCoachPromptFromEvent(event);
    coachState.events.unshift(event);
    saveState();
    renderAll();
    showNotice(`MatchIQ ha capito: ${event.label} per ${event.team}.`, "ok", 2800);
    return event;
}

function applyCoachAssistantQuestion(button){
    const question = button?.dataset?.question || button?.textContent || "";
    setInputValue("coachVoiceInput", question);
    const input = document.getElementById("coachVoiceInput");
    if(input) input.focus();
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
        addSmartCoachNote(text, "voice");
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
