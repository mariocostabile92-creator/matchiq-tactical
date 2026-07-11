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
    coachState = {match:null, events:[], ratings:[], lineup:[], report:"", live:null, memory:null};
    localStorage.removeItem(STORAGE_KEY);
    [
        "homeTeamInput","awayTeamInput","matchFieldInput","homeShapeInput","awayShapeInput","preNotesInput",
        "eventMinuteInput","eventPlayerInput","eventPlayerSelectInput","eventNoteInput","coachVoiceInput",
        "precheckObjectiveInput","precheckRiskInput","precheckObserveInput","precheckOpponentInput","precheckTrainingFocusInput"
    ].forEach(id => setInputValue(id, ""));
    setInputValue("categoryInput", "Dilettanti");
    setInputValue("matchDateInput", todayISO());
    clearLineupForm();
    clearRatingForm();
    renderAll();
    showNotice("Partita resettata.", "ok");
}

function getCoachEventTags(event){
    const type = String(event?.type || "").toLowerCase();
    const note = normalizeCoachSpeechText(event?.note || event?.label || "");
    const tags = [];
    const add = tag => { if(tag && !tags.includes(tag)) tags.push(tag); };

    const map = {
        gol:["finalizzazione","momento chiave"],
        tiro:["produzione offensiva"],
        occasione:["rifinitura","area"],
        palla_persa:["transizione negativa","uscita palla"],
        recupero:["riaggressione","pressing"],
        errore_difensivo:["fase difensiva","coperture"],
        pressing:["pressing","intensita"],
        transizione:["rest defense","transizioni"],
        ampiezza:["ampiezza","lato debole"],
        seconda_palla:["duelli","seconde palle"],
        squadra_lunga:["distanze reparti","compattezza"],
        uscita_lato:["costruzione laterale","sostegno"],
        profondita:["profondita","attacco spazio"],
        comunicazione:["comunicazione","guida reparto"],
        cambio:["gestione gara"],
        cartellino:["gestione emotiva"]
    };
    (map[type] || ["nota staff"]).forEach(add);
    if(/\b(linea|difesa|copertura|marcatura)\b/.test(note)) add("fase difensiva");
    if(/\b(pressing|pressione|riaggressione)\b/.test(note)) add("pressing");
    if(/\b(ampiezza|lato|esterno|cambio gioco)\b/.test(note)) add("ampiezza");
    if(/\b(profondita|spalle|imbucata)\b/.test(note)) add("profondita");
    if(/\b(comunicazione|parlare|guida|chiamata)\b/.test(note)) add("comunicazione");
    return tags.slice(0,4);
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
    const event = {
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
    event.tags = Array.isArray(options.tags) ? options.tags : getCoachEventTags(event);
    return event;
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

function addTacticalLiveEvent(type, label, icon, note, side="home"){
    addQuickEvent(type, label, icon, {
        minute:"live",
        live:true,
        side,
        note,
        source:"smart-tap"
    });
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
    const player = clean.match(/\b(?:giocatore|calciatore|nome)\s+([a-z]{3,}(?:\s+[a-z]{3,})?)\b/);
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

function answerCoachFollowUp(button){
    const answer = button?.dataset?.answer || button?.textContent || "";
    if(!answer) return;
    addSmartCoachNote(answer, "follow-up");
}

function fillCoachPrecheckFromState(){
    ensureCoachStateShape();
    const pre = coachState.memory?.precheck || {};
    setInputValue("precheckObjectiveInput", pre.objective);
    setInputValue("precheckRiskInput", pre.risk);
    setInputValue("precheckObserveInput", pre.observe);
    setInputValue("precheckOpponentInput", pre.opponent);
    setInputValue("precheckTrainingFocusInput", pre.trainingFocus);
}

function saveCoachPrecheck(){
    ensureCoachStateShape();
    coachState.memory.precheck = {
        objective: getInputValue("precheckObjectiveInput", ""),
        risk: getInputValue("precheckRiskInput", ""),
        observe: getInputValue("precheckObserveInput", ""),
        opponent: getInputValue("precheckOpponentInput", ""),
        trainingFocus: getInputValue("precheckTrainingFocusInput", "")
    };
    saveState();
    renderAll();
    showNotice("Checklist pre-partita salvata nella memoria Coach.", "ok");
}

function fillCoachPrecheckFromMatch(){
    ensureCoachStateShape();
    const match = coachState.match || {};
    const home = match.homeTeam || "Squadra casa";
    const away = match.awayTeam || "avversario";
    const shapeText = [match.homeShape, match.awayShape].filter(Boolean).join(" vs ") || "moduli non indicati";
    setInputValue("precheckObjectiveInput", getInputValue("precheckObjectiveInput", `Tenere ordine tra i reparti, ridurre errori gratuiti e trasformare gli episodi chiave in report utile per lo staff.`));
    setInputValue("precheckRiskInput", getInputValue("precheckRiskInput", `Attenzione a transizioni, seconde palle e distanze squadra con ${shapeText}.`));
    setInputValue("precheckObserveInput", getInputValue("precheckObserveInput", `Osservare uscita palla, pressing dopo perdita, coperture preventive e comportamento della linea difensiva.`));
    setInputValue("precheckOpponentInput", getInputValue("precheckOpponentInput", `${home} contro ${away}: segnare subito lato forte, giocatori pericolosi e momenti in cui l'avversario alza pressione.`));
    setInputValue("precheckTrainingFocusInput", getInputValue("precheckTrainingFocusInput", `Dopo gara preparare esercizi su tema ricorrente piu evidente: possesso sotto pressione, compattezza o finalizzazione.`));
    saveCoachPrecheck();
}

function setCoachVoiceHint(message){
    const hint = document.getElementById("coachVoiceAutopilotHint");
    if(hint) hint.textContent = message || "";
}

function setCoachVoiceStatus(message, mode="idle"){
    const status = document.getElementById("coachVoiceStatus");
    if(status){
        status.className = `coach-voice-status ${mode === "listening" ? "listening" : mode === "blocked" ? "blocked" : ""}`;
        status.innerHTML = `<span class="coach-voice-dot"></span><span>${esc(message || "")}</span>`;
    }
    const voiceBtn = document.getElementById("coachVoiceBtn");
    if(voiceBtn){
        const label = mode === "listening" ? "Ascolto..." : "Voce";
        const sub = mode === "listening" ? "Parla adesso" : "Detta nota tattica";
        voiceBtn.innerHTML = `<strong>${label}</strong><span>${sub}</span>`;
    }
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

function startCoachMatchDay(){
    if(!coachState.match){
        showNotice("Prima crea o aggiorna la partita nel Pre-partita.", "warn");
        setCoachPhase("pre");
        return;
    }
    const starters = getLineup().filter(p => p.status === "Titolare").length;
    const bench = getLineup().filter(p => p.status === "Panchina").length;
    if(starters < 1 && !confirm("Non hai ancora completato la formazione. Vuoi comunque avviare il Match Day?")) return;
    ensureCoachStateShape();
    coachState.phase = "match";
    saveState();
    startCoachLiveClock();
    renderAll();
    showNotice(`Match Day avviato. Titolari inseriti: ${starters}. Panchina: ${bench}.`, "ok", 3500);
}

function finishCoachMatchDay(){
    if(!coachState.match){
        showNotice("Nessuna partita attiva da terminare.", "warn");
        return;
    }
    if(!confirm("Vuoi passare al Post-partita? Timer, eventi, note e pagelle restano salvati.")) return;
    stopCoachLiveClock(true);
    ensureCoachStateShape();
    coachState.phase = "post";
    if(!coachState.report && coachState.events.length){
        generateCoachReport();
    }
    saveState();
    renderAll();
    showNotice("Partita spostata nel Post-partita. Completa pagelle, report e storico.", "ok", 4000);
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

function prepareCoachHalftimeSummary(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }
    ensureCoachStateShape();
    if(coachState.live?.running){
        stopCoachLiveClock(true);
    }
    coachState.live.period = "INT";
    coachState.phase = "match";
    saveState();
    renderAll();
    const panel = document.getElementById("coachHalftimeTalk");
    if(panel) panel.scrollIntoView({behavior:"smooth", block:"center"});
    showNotice("Sintesi intervallo pronta con i dati registrati finora.", "ok", 3500);
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
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }

    const input = document.getElementById("coachVoiceInput");
    if(input){
        input.placeholder = "Parla o scrivi: es. palla persa nostra al 18...";
        input.focus();
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!SpeechRecognition){
        setCoachVoiceStatus("Questo browser non permette la dettatura qui. Scrivi la frase nel campo sopra e premi Aggiungi nota.", "blocked");
        setCoachVoiceHint("Dettatura non disponibile qui: scrivi la frase nel campo e premi Aggiungi nota.");
        showNotice("Dettatura non disponibile qui. Ho aperto il campo nota rapida.", "warn", 4500);
        return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "it-IT";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    let gotResult = false;
    setCoachVoiceStatus("Sto provando ad aprire il microfono. Se compare una richiesta del browser, premi Consenti.", "listening");
    setCoachVoiceHint("Microfono pronto: detta una frase breve, poi MatchIQ la trasforma in evento.");
    showNotice("Sto ascoltando: detta una nota tattica breve.", "ok", 2500);
    recognition.onaudiostart = () => {
        setCoachVoiceStatus("Ti sto ascoltando. Parla adesso vicino al microfono.", "listening");
        setCoachVoiceHint("Ti sto ascoltando...");
    };
    recognition.onresult = event => {
        gotResult = true;
        const text = event.results?.[0]?.[0]?.transcript || "";
        setInputValue("coachVoiceInput", text);
        if(text.trim()){
            addSmartCoachNote(text, "voice");
            setCoachVoiceStatus(`Nota letta: "${esc(text)}". MatchIQ l'ha trasformata in evento.`, "idle");
            setCoachVoiceHint(`Nota letta: "${text}"`);
        }else{
            setCoachVoiceStatus("Non ho ricevuto testo. Riprova o scrivi la nota nel campo.", "blocked");
            setCoachVoiceHint("Non ho ricevuto testo. Riprova o scrivi la nota.");
        }
    };
    recognition.onerror = event => {
        const reason = event?.error === "not-allowed" || event?.error === "service-not-allowed"
            ? "Microfono bloccato: clicca sul lucchetto vicino all'indirizzo, abilita Microfono e ricarica la pagina. Intanto puoi scrivere la nota."
            : "Non sono riuscito a leggere la voce. Scrivi la nota nel campo rapido o riprova.";
        setCoachVoiceStatus(reason, "blocked");
        setCoachVoiceHint(reason);
        showNotice("Microfono non attivo. Usa il campo nota o abilita il permesso.", "warn");
    };
    recognition.onend = () => {
        if(!gotResult){
            setCoachVoiceStatus("Dettatura chiusa senza testo. Riprova con Voce oppure scrivi la nota e premi Aggiungi nota.", "blocked");
            setCoachVoiceHint("Dettatura chiusa senza testo. Puoi riprovare o scrivere la nota.");
        }
    };
    try{
        recognition.start();
    }catch{
        setCoachVoiceStatus("Il browser non ha avviato il microfono. Scrivi la nota e premi Aggiungi nota.", "blocked");
        setCoachVoiceHint("Il browser non ha avviato il microfono. Scrivi la nota e premi Aggiungi nota.");
        showNotice("Il microfono non si e avviato. Usa il campo nota rapida.", "warn");
    }
}

function bindCoachVoiceInput(){
    const input = document.getElementById("coachVoiceInput");
    if(!input || input.dataset.boundVoice === "1") return;
    input.dataset.boundVoice = "1";
    input.addEventListener("keydown", event => {
        if(event.key === "Enter"){
            event.preventDefault();
            addLiveNote();
        }
    });
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

function getPlayerEventImpact(player){
    const name = String(player?.name || player?.player || "").toLowerCase();
    const number = String(player?.number || "").trim();
    const side = normalizeLineupSide(player?.side || "home", player);
    const events = coachState.events.filter(e => {
        if(e.side !== side) return false;
        const text = `${e.player || ""} ${e.note || ""}`.toLowerCase();
        return (name && text.includes(name)) || (number && text.includes(`#${number}`)) || (number && text.includes(` ${number} `));
    });
    const positive = events.filter(e => ["gol","occasione","tiro","recupero","pressing","ampiezza"].includes(e.type)).length;
    const negative = events.filter(e => ["palla_persa","errore_difensivo","cartellino"].includes(e.type)).length;
    const goals = events.filter(e => e.type === "gol").length;
    const chances = events.filter(e => e.type === "occasione" || e.type === "tiro").length;
    const recoveries = events.filter(e => e.type === "recupero" || e.type === "pressing").length;
    const errors = events.filter(e => e.type === "palla_persa" || e.type === "errore_difensivo").length;
    return {events, positive, negative, goals, chances, recoveries, errors};
}

function buildAiRatingForPlayer(player){
    const p = normalizeLineupPlayer(player);
    const impact = getPlayerEventImpact(p);
    let vote = 6;
    vote += impact.goals * 1.2;
    vote += impact.chances * 0.35;
    vote += impact.recoveries * 0.25;
    vote -= impact.errors * 0.45;
    vote = Math.max(4.5, Math.min(9, Math.round(vote * 2) / 2));

    const strengths = [];
    const improve = [];
    if(impact.goals) strengths.push("incide negli episodi decisivi");
    if(impact.chances) strengths.push("partecipa alla produzione offensiva");
    if(impact.recoveries) strengths.push("porta intensita e recupero palla");
    if(!strengths.length) strengths.push("prestazione ordinata da confermare con osservazione staff");
    if(impact.errors) improve.push("gestire meglio scelta e coperture nei momenti critici");
    if(Number(vote) <= 6) improve.push("aumentare continuita, comunicazione e presenza nel gioco");
    if(!improve.length) improve.push("consolidare quanto fatto bene nel prossimo allenamento");

    return {
        id:Date.now()+Math.random(),
        player:formatLineupPlayer(p),
        side:p.side,
        team:getTeamName(p.side),
        role:p.role || "Jolly",
        vote,
        note:`Bozza AI: punti forti: ${strengths.slice(0,2).join(", ")}. Da migliorare: ${improve[0]}. Consiglio: lavoro specifico su ruolo e principi della partita.`,
        ai:true,
        createdAt:new Date().toISOString()
    };
}

function generateAiRatings(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }
    ensureCoachStateShape();
    const players = getLineup().filter(p => p.status !== "Panchina").slice(0,18);
    if(!players.length){
        showNotice("Inserisci la formazione: MatchIQ usa i giocatori per proporre le pagelle.", "warn");
        return;
    }

    let added = 0;
    players.forEach(player => {
        if(!canAddCoachRating()) return;
        const exists = coachState.ratings.some(r => String(r.player || "").toLowerCase() === formatLineupPlayer(player).toLowerCase());
        if(exists) return;
        coachState.ratings.push(buildAiRatingForPlayer(player));
        added += 1;
    });

    if(!added){
        showNotice("Le pagelle sono gia presenti oppure hai raggiunto il limite del piano.", "warn");
        renderAll();
        return;
    }

    saveState();
    renderAll();
    showNotice(`Pagelle AI create: ${added}. Controllale e correggile prima del report.`, "ok", 3500);
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
