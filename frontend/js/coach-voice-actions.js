let coachVoiceRecognition = null;
let coachVoiceStopTimer = null;

const COACH_VOICE_SESSION_STATES = Object.freeze({
    IDLE:"IDLE",
    RECORDING:"RECORDING",
    PROCESSING:"PROCESSING",
    REVIEW:"REVIEW",
    SUCCESS:"SUCCESS",
    ERROR:"ERROR"
});

const coachVoiceSession = {
    state:COACH_VOICE_SESSION_STATES.IDLE,
    segments:[],
    startedAt:0,
    durationTimer:null,
    restartTimer:null,
    manualStop:false,
    finalizing:false,
    generation:0
};

function formatCoachVoiceDuration(ms){
    const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
}

function renderCoachVoiceSession(){
    const state = coachVoiceSession.state;
    const labels = {
        IDLE:"Pronto",
        RECORDING:"Registrazione in corso",
        PROCESSING:"Analisi in corso",
        REVIEW:"Controlla prima di salvare",
        SUCCESS:"Salvato nella timeline",
        ERROR:"Registrazione non disponibile"
    };
    const panel = document.getElementById("coachVoiceSession");
    const label = document.getElementById("coachVoiceSessionState");
    const duration = document.getElementById("coachVoiceDuration");
    const start = document.getElementById("coachVoiceSessionStart");
    const headStart = document.getElementById("coachVoiceStartButton");
    const stop = document.getElementById("coachVoiceSessionStop");
    const cancel = document.getElementById("coachVoiceSessionCancel");
    if(panel) panel.dataset.voiceState = state;
    if(label) label.textContent = labels[state] || state;
    if(duration){
        const elapsed = coachVoiceSession.startedAt ? Date.now() - coachVoiceSession.startedAt : 0;
        duration.textContent = formatCoachVoiceDuration(elapsed);
    }
    const recording = state === COACH_VOICE_SESSION_STATES.RECORDING;
    const busy = state === COACH_VOICE_SESSION_STATES.PROCESSING;
    if(start){ start.hidden = recording || busy; start.disabled = busy; }
    if(headStart){ headStart.hidden = recording || busy; headStart.disabled = busy; }
    if(stop){ stop.hidden = !recording; stop.disabled = !recording; }
    if(cancel){ cancel.hidden = !(recording || busy); cancel.disabled = false; }
}

function setCoachVoiceSessionState(state){
    coachVoiceSession.state = COACH_VOICE_SESSION_STATES[state] || state;
    if(coachVoiceSession.durationTimer){
        clearInterval(coachVoiceSession.durationTimer);
        coachVoiceSession.durationTimer = null;
    }
    if(coachVoiceSession.state === COACH_VOICE_SESSION_STATES.RECORDING){
        coachVoiceSession.durationTimer = setInterval(renderCoachVoiceSession, 500);
    }
    renderCoachVoiceSession();
}

function clearCoachVoiceRuntime(){
    clearTimeout(coachVoiceStopTimer);
    clearTimeout(coachVoiceSession.restartTimer);
    coachVoiceStopTimer = null;
    coachVoiceSession.restartTimer = null;
    if(coachVoiceSession.durationTimer){
        clearInterval(coachVoiceSession.durationTimer);
        coachVoiceSession.durationTimer = null;
    }
}

function addCoachVoiceSegment(text){
    const clean = String(text || "").replace(/\s+/g, " ").trim();
    if(!clean) return;
    const key = clean.toLocaleLowerCase("it-IT");
    if(coachVoiceSession.segments.some(item => item.key === key)) return;
    coachVoiceSession.segments.push({key, text:clean});
    setInputValue("coachVoiceInput", coachVoiceSession.segments.map(item => item.text).join(" "));
}

function setCoachVoiceUiStatus(message, mode="idle"){
    const vc = ensureCoachVoiceMemory();
    vc.lastStatus = String(message || "");
    const status = document.getElementById("coachVoiceStatus");
    if(status){
        status.className = `coach-voice-status ${mode === "listening" ? "listening" : mode === "blocked" ? "blocked" : ""}`;
        status.innerHTML = `<span class="coach-voice-dot"></span><span>${esc(message || "")}</span>`;
    }
    const button = document.getElementById("coachVoiceBtn");
    if(button){
        const label = mode === "listening" ? "Sto ascoltando..." : "AI Voice Coach";
        const sub = mode === "listening" ? "Interrompi" : "Parla con Coach";
        button.innerHTML = `<strong>${esc(label)}</strong><span>${esc(sub)}</span>`;
    }
}

function failCoachVoiceSession(message){
    coachVoiceSession.manualStop = true;
    coachVoiceSession.finalizing = false;
    clearCoachVoiceRuntime();
    if(coachVoiceRecognition){
        try{ coachVoiceRecognition.abort(); }catch{}
        coachVoiceRecognition = null;
    }
    setCoachVoiceSessionState("ERROR");
    setCoachVoiceUiStatus(message, "blocked");
}

function createCoachVoiceRecognition(generation){
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!SpeechRecognition){
        failCoachVoiceSession("Microfono non disponibile in questo browser. Scrivi il comando e premi Interpreta.");
        const input = document.getElementById("coachVoiceInput");
        if(input) input.focus();
        return null;
    }
    const recognition = new SpeechRecognition();
    coachVoiceRecognition = recognition;
    recognition.lang = "it-IT";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
        if(generation !== coachVoiceSession.generation) return;
        setCoachVoiceUiStatus("Sto ascoltando. Quando hai finito premi Termina e analizza.", "listening");
    };
    recognition.onresult = event => {
        if(generation !== coachVoiceSession.generation) return;
        for(let index=event.resultIndex || 0; index<event.results.length; index += 1){
            const result = event.results[index];
            if(result?.isFinal) addCoachVoiceSegment(result?.[0]?.transcript || "");
        }
    };
    recognition.onerror = event => {
        if(generation !== coachVoiceSession.generation) return;
        const code = String(event?.error || "");
        if(code === "aborted" && coachVoiceSession.manualStop) return;
        if(code === "no-speech") return;
        const denied = event?.error === "not-allowed" || event?.error === "service-not-allowed";
        failCoachVoiceSession(denied
            ? "Microfono bloccato. Abilitalo dal browser oppure usa Scrivi il comando."
            : "Registrazione interrotta dal browser. Riprova o usa il testo.");
    };
    recognition.onend = () => {
        if(coachVoiceRecognition === recognition) coachVoiceRecognition = null;
        if(generation !== coachVoiceSession.generation) return;
        if(coachVoiceSession.state !== COACH_VOICE_SESSION_STATES.RECORDING || coachVoiceSession.manualStop) return;
        clearTimeout(coachVoiceSession.restartTimer);
        coachVoiceSession.restartTimer = setTimeout(() => {
            if(coachVoiceSession.state === COACH_VOICE_SESSION_STATES.RECORDING && !coachVoiceSession.manualStop){
                startCoachVoiceRecognitionCycle(generation);
            }
        }, 300);
    };
    return recognition;
}

function startCoachVoiceRecognitionCycle(generation){
    const recognition = createCoachVoiceRecognition(generation);
    if(!recognition) return;
    try{
        recognition.start();
    }catch{
        failCoachVoiceSession("Il browser non ha avviato il microfono. Usa Scrivi il comando.");
    }
}

function beginCoachVoiceListening(){
    if(coachVoiceSession.state === COACH_VOICE_SESSION_STATES.RECORDING) return;
    coachVoiceSession.generation += 1;
    coachVoiceSession.segments = [];
    coachVoiceSession.startedAt = Date.now();
    coachVoiceSession.manualStop = false;
    coachVoiceSession.finalizing = false;
    setInputValue("coachVoiceInput", "");
    setCoachVoiceSessionState("RECORDING");
    startCoachVoiceRecognitionCycle(coachVoiceSession.generation);
    coachVoiceStopTimer = setTimeout(() => {
        if(coachVoiceSession.state === COACH_VOICE_SESSION_STATES.RECORDING){
            setCoachVoiceUiStatus("Durata massima raggiunta. Analizzo quanto registrato.", "idle");
            stopCoachVoiceRecording();
        }
    }, 120000);
}

async function finishCoachVoiceRecording(){
    if(coachVoiceSession.finalizing) return;
    coachVoiceSession.finalizing = true;
    clearCoachVoiceRuntime();
    const text = coachVoiceSession.segments.map(item => item.text).join(" ").trim() || getInputValue("coachVoiceInput", "").trim();
    if(!text){
        coachVoiceSession.finalizing = false;
        failCoachVoiceSession("Non ho rilevato parole complete. Riprova o scrivi il comando.");
        return;
    }
    setCoachVoiceSessionState("PROCESSING");
    await processCoachVoiceCommand(text, "speech");
    coachVoiceSession.finalizing = false;
}

function stopCoachVoiceRecording(){
    if(coachVoiceSession.state !== COACH_VOICE_SESSION_STATES.RECORDING) return;
    coachVoiceSession.manualStop = true;
    setCoachVoiceSessionState("PROCESSING");
    if(coachVoiceRecognition){
        try{ coachVoiceRecognition.stop(); }catch{}
    }
    setTimeout(finishCoachVoiceRecording, 220);
}

function cancelCoachVoiceRecording(){
    coachVoiceSession.generation += 1;
    coachVoiceSession.manualStop = true;
    coachVoiceSession.finalizing = false;
    clearCoachVoiceRuntime();
    if(coachVoiceRecognition){
        try{ coachVoiceRecognition.abort(); }catch{}
        coachVoiceRecognition = null;
    }
    coachVoiceSession.segments = [];
    coachVoiceSession.startedAt = 0;
    setInputValue("coachVoiceInput", "");
    setCoachVoiceSessionState("IDLE");
    setCoachVoiceUiStatus("Registrazione annullata. Nessun evento e stato salvato.", "idle");
}

function startCoachVoiceNote(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        setCoachPhase("pre");
        return;
    }
    const input = document.getElementById("coachVoiceInput");
    if(input){
        input.placeholder = "Scrivi il comando: es. Cambio Rossi per Bianchi";
    }
    beginCoachVoiceListening();
}

function addLiveNote(){
    const value = getInputValue("coachVoiceInput", "");
    if(!value){
        showNotice("Scrivi il comando o usa AI Voice Coach.", "warn");
        return;
    }
    setCoachVoiceSessionState("PROCESSING");
    processCoachVoiceCommand(value, "text");
}

async function processCoachVoiceCommand(text, source="text"){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return null;
    }
    ensureCoachStateShape();
    let proposal = null;
    if(typeof interpretCoachVoiceCommandFromServer === "function" && navigator.onLine !== false){
        try{
            setCoachVoiceUiStatus("Sto interpretando il comando con MatchIQ...", "idle");
            proposal = await interpretCoachVoiceCommandFromServer(text, source);
        }catch{
            proposal = buildCoachVoiceProposal(text, source);
            proposal.warnings = [...(proposal.warnings || []), "Connessione o servizio non disponibile: interpretazione locale usata."];
        }
    }else{
        proposal = buildCoachVoiceProposal(text, source);
        proposal.warnings = [...(proposal.warnings || []), "Offline: interpretazione locale usata."];
    }
    const vc = ensureCoachVoiceMemory();
    vc.lastProposal = proposal;
    saveState();
    renderCoachVoiceCoach();

    if(proposal.intent === "cancel"){
        vc.lastProposal = null;
        saveState();
        renderCoachVoiceCoach();
        setCoachVoiceUiStatus("Comando annullato.", "idle");
        setCoachVoiceSessionState("IDLE");
        return proposal;
    }

    setCoachVoiceSessionState("REVIEW");
    setCoachVoiceUiStatus("Ho preparato una proposta. Controllala e conferma prima del salvataggio.", "idle");
    showNotice("Controlla la trascrizione: nulla viene salvato senza conferma.", "warn", 3500);
    return proposal;
}

function getCoachVoiceProposalById(id){
    const proposal = ensureCoachVoiceMemory().lastProposal;
    return proposal && String(proposal.id) === String(id) ? proposal : null;
}

function clampCoachVoiceNumber(value, min, max){
    const parsed = Number(value);
    if(!Number.isFinite(parsed)) return min;
    return Math.max(min, Math.min(max, Math.round(parsed)));
}

function refreshCoachVoiceProposalSummary(proposal){
    const e = proposal.entities || {};
    if(proposal.intent === "score_update"){
        proposal.normalized_summary = `Aggiornamento punteggio: ${getTeamName("home")} ${e.home_goals || 0} - ${e.away_goals || 0} ${getTeamName("away")}.`;
    }else if(proposal.intent === "substitution"){
        proposal.normalized_summary = e.player_out_name && e.player_in_name
            ? `Cambio: ${e.player_out_name} esce, ${e.player_in_name} entra al ${proposal.minute}'.`
            : "Cambio da completare: non ho riconosciuto tutti i giocatori.";
    }else if(proposal.intent === "player_event"){
        proposal.normalized_summary = `${e.event_label || "Evento"}${e.player_name ? " di " + e.player_name : ""} al ${proposal.minute}'.`;
    }else if(proposal.intent === "tactical_note" || proposal.intent === "player_note"){
        proposal.normalized_summary = `${e.topic_label || "Nota staff"}: ${proposal.transcript || e.note_original || ""}`;
    }
}

function updateCoachVoiceProposalField(id, field, value){
    const proposal = getCoachVoiceProposalById(id);
    if(!proposal) return;
    proposal.entities = proposal.entities || {};
    if(field === "transcript"){
        proposal.transcript = String(value || "").trim();
        proposal.entities.note_original = proposal.transcript;
    }else if(field === "minute"){
        proposal.minute = clampCoachVoiceNumber(value, 0, 130);
    }else if(field === "team"){
        proposal.team = value === "away" ? "away" : "home";
    }else if(field === "player_id"){
        const player = value ? getLineupPlayerById(value) : null;
        proposal.entities.player_id = player?.id || "";
        proposal.entities.player_name = player ? formatLineupPlayer(player) : "";
    }else if(field === "player_out_id" || field === "player_in_id"){
        const player = value ? getLineupPlayerById(value) : null;
        proposal.entities[field] = player?.id || "";
        proposal.entities[field.replace("_id", "_name")] = player ? formatLineupPlayer(player) : "";
    }else if(field === "event_key"){
        const mapped = COACH_VOICE_EVENT_MAP[value] || COACH_VOICE_EVENT_MAP.recovery;
        proposal.entities.event_key = value;
        proposal.entities.event_type = mapped.type;
        proposal.entities.event_label = mapped.label;
        proposal.entities.event_icon = mapped.icon;
    }else if(field === "topic"){
        const rule = getCoachVoiceThemeRule(value) || {key:"general_note", label:"Nota staff", zone:"not_specified", priority:"medium"};
        proposal.entities.topic = rule.key;
        proposal.entities.topic_label = rule.label;
        proposal.entities.zone = rule.zone;
        proposal.entities.priority = rule.priority;
    }else if(field === "home_goals" || field === "away_goals"){
        proposal.entities[field] = clampCoachVoiceNumber(value, 0, 30);
    }
    proposal.requires_confirmation = true;
    refreshCoachVoiceProposalSummary(proposal);
    saveState();
    renderCoachVoiceCoach();
}

function coachVoiceEventOptionsFromProposal(proposal){
    return {
        minute: proposal.minute,
        side: proposal.team || "home",
        playerId: proposal.entities?.player_id || "",
        player: proposal.entities?.player_name || "",
        note: proposal.transcript,
        source: "ai-voice",
        voiceObservationId: proposal.id,
        tags: [proposal.entities?.topic_label, proposal.entities?.zone, "AI Voice Coach"].filter(Boolean)
    };
}

function isCoachVoiceDuplicateEvent(type, proposal){
    const player = proposal.entities?.player_name || "";
    return coachState.events.some(event =>
        event.source === "ai-voice" &&
        event.type === type &&
        String(event.minute) === String(proposal.minute) &&
        String(event.player || "") === String(player)
    );
}

function applyCoachVoiceProposal(id, silent=false){
    const proposal = getCoachVoiceProposalById(id);
    if(!proposal){
        showNotice("Proposta AI Voice Coach non trovata.", "warn");
        return;
    }
    if(proposal.applying) return;
    proposal.applying = true;
    if(proposal.intent === "substitution"){
        applyCoachVoiceSubstitution(proposal);
    }else if(proposal.intent === "player_event"){
        const e = proposal.entities || {};
        if(isCoachVoiceDuplicateEvent(e.event_type || "nota", proposal)){
            showNotice("Evento gia registrato con AI Voice Coach: evito il doppione.", "warn");
            proposal.applying = false;
            return;
        }
        addQuickEvent(e.event_type || "nota", e.event_label || "Evento", e.event_icon || "NOTE", coachVoiceEventOptionsFromProposal(proposal));
    }else if(proposal.intent === "score_update"){
        applyCoachVoiceScoreUpdate(proposal);
    }else if(proposal.intent === "tactical_note" || proposal.intent === "player_note"){
        const topic = proposal.entities?.topic || "general_note";
        const rule = getCoachVoiceThemeRule(topic);
        const type = topic === "second_post" || topic === "right_flank" || topic === "left_flank" ? "errore_difensivo"
            : topic === "pressing" || topic === "low_press" ? "pressing"
            : topic === "build_up" ? "uscita_lato"
            : topic === "negative_transition" ? "transizione"
            : topic === "duels" ? "seconda_palla"
            : "nota";
        addQuickEvent(type, proposal.entities?.topic_label || "Nota tattica", "VOICE", coachVoiceEventOptionsFromProposal(proposal));
    }else if(proposal.intent === "match_control"){
        setCoachVoiceUiStatus("Comando partita non applicato automaticamente: usa i pulsanti timer/fase per sicurezza.", "blocked");
        proposal.applying = false;
        return;
    }else{
        showNotice("Comando non supportato. Salvo come nota staff se confermi con una frase piu chiara.", "warn");
        proposal.applying = false;
        return;
    }
    const observation = recordCoachVoiceObservation(proposal, getCoachVoiceThemeRule(proposal.entities?.topic));
    if(typeof persistCoachVoiceObservation === "function"){
        persistCoachVoiceObservation(proposal, observation).then(result => {
            observation.syncStatus = result?.local ? "local" : "synced";
            if(Array.isArray(result?.themes)) loadCoachVoiceIntelligence();
            saveState(); renderCoachVoiceCoach();
        }).catch(() => {
            observation.syncStatus = "pending";
            saveState(); renderCoachVoiceCoach();
            setCoachVoiceUiStatus("Osservazione salvata localmente, sincronizzazione in attesa.", "blocked");
        });
    }
    const vc = ensureCoachVoiceMemory();
    vc.lastProposal = null;
    saveState();
    renderAll();
    setCoachVoiceUiStatus("Evento salvato da AI Voice Coach.", "idle");
    setCoachVoiceSessionState("SUCCESS");
    setTimeout(() => {
        if(coachVoiceSession.state === COACH_VOICE_SESSION_STATES.SUCCESS){
            coachVoiceSession.startedAt = 0;
            setCoachVoiceSessionState("IDLE");
        }
    }, 1800);
    if(!silent) showNotice("AI Voice Coach ha salvato l'azione nella timeline. Puoi annullare dal pannello.", "ok", 4200);
}

function applyCoachVoiceScoreUpdate(proposal){
    const targetHome = Math.max(0, Number(proposal.entities?.home_goals || 0) || 0);
    const targetAway = Math.max(0, Number(proposal.entities?.away_goals || 0) || 0);
    const currentHome = getGoals("home");
    const currentAway = getGoals("away");
    if(targetHome < currentHome || targetAway < currentAway){
        showNotice("Punteggio incoerente: non elimino gol gia registrati. Correggi manualmente la timeline se serve.", "warn", 5000);
        return;
    }
    for(let i=currentHome; i<targetHome; i++){
        addQuickEvent("gol", "Gol", "GOL", {
            minute: proposal.minute,
            side: "home",
            note: `Aggiornamento punteggio da voce: ${targetHome}-${targetAway}.`,
            source: "ai-voice", voiceObservationId: proposal.id
        });
    }
    for(let i=currentAway; i<targetAway; i++){
        addQuickEvent("gol", "Gol", "GOL", {
            minute: proposal.minute,
            side: "away",
            note: `Aggiornamento punteggio da voce: ${targetHome}-${targetAway}.`,
            source: "ai-voice", voiceObservationId: proposal.id
        });
    }
    if(targetHome === currentHome && targetAway === currentAway){
        addQuickEvent("nota", "Conferma punteggio", "SCORE", {
            minute: proposal.minute,
            side: proposal.team || "home",
            note: `Punteggio confermato da voce: ${targetHome}-${targetAway}.`,
            source: "ai-voice", voiceObservationId: proposal.id
        });
    }
}

function applyCoachVoiceSubstitution(proposal){
    const outId = proposal.entities?.player_out_id;
    const inId = proposal.entities?.player_in_id;
    const outPlayer = outId ? getLineupPlayerById(outId) : null;
    const inPlayer = inId ? getLineupPlayerById(inId) : null;
    if(!outPlayer || !inPlayer || String(outPlayer.id) === String(inPlayer.id)){
        showNotice("Cambio non valido: controlla giocatore in uscita e in entrata.", "warn");
        return;
    }
    outPlayer.status = "Panchina";
    outPlayer.substituted = true;
    inPlayer.status = "Titolare";
    inPlayer.substituted = false;
    inPlayer.side = outPlayer.side || inPlayer.side;
    inPlayer.team = getTeamName(inPlayer.side);
    addQuickEvent("cambio", "Cambio", "CAMBIO", {
        minute: proposal.minute,
        side: outPlayer.side || proposal.team || "home",
        player: `${formatLineupPlayer(outPlayer)} -> ${formatLineupPlayer(inPlayer)}`,
        note: proposal.normalized_summary,
        source: "ai-voice", voiceObservationId: proposal.id
    });
}

function recordCoachVoiceObservation(proposal, rule=null){
    const vc = ensureCoachVoiceMemory();
    const existing = vc.observations.find(item => String(item.id) === String(proposal.id));
    if(existing) return existing;
    const topic = proposal.tactical_topic || proposal.entities?.topic || proposal.entities?.event_key || proposal.intent || "general_note";
    const label = proposal.entities?.topic_label || proposal.entities?.event_label || rule?.label || COACH_VOICE_INTENTS[proposal.intent] || "Nota staff";
    const match = coachState.match || {};
    const elapsedSeconds = typeof getCoachLiveElapsedSeconds === "function" ? getCoachLiveElapsedSeconds() : 0;
    const observation = {
        id: proposal.id,
        matchId: match.id || match.createdAt || "",
        matchLabel: match.homeTeam && match.awayTeam ? `${match.homeTeam} vs ${match.awayTeam}` : "",
        minute: proposal.minute,
        matchElapsedSeconds: elapsedSeconds,
        videoContext: {
            ready: false,
            videoSessionId: "",
            frameId: "",
            clipId: ""
        },
        intent: proposal.intent,
        topic,
        label,
        zone: proposal.zone || proposal.entities?.zone || rule?.zone || "not_specified",
        priority: proposal.priority || proposal.entities?.priority || rule?.priority || "medium",
        sentiment: proposal.polarity || proposal.entities?.sentiment || "neutral",
        player: [proposal.entities?.player_name, proposal.entities?.player_out_name, proposal.entities?.player_in_name].filter(Boolean).join(" / "),
        note: proposal.transcript,
        explanation: proposal.explanation || "",
        syncStatus: navigator.onLine === false ? "pending" : "local",
        status: "confirmed",
        createdAt: new Date().toISOString()
    };
    vc.observations.unshift(observation);
    vc.observations = vc.observations.slice(0, 80);
    const current = vc.themes[topic] || { label, count: 0, minutes: [], priority: proposal.entities?.priority || "medium" };
    current.label = label;
    current.count += 1;
    current.minutes = [...(current.minutes || []), proposal.minute].slice(-8);
    current.priority = proposal.entities?.priority || current.priority || "medium";
    vc.themes[topic] = current;
    if(observation.player){
        const key = observation.player;
        vc.players[key] = (Number(vc.players[key] || 0) || 0) + 1;
    }
    return observation;
}

async function undoLastCoachVoiceObservation(){
    const vc = ensureCoachVoiceMemory();
    const observation = vc.observations[0];
    if(!observation){ showNotice("Nessuna osservazione Voice Coach da annullare.", "warn"); return; }
    vc.observations.shift();
    coachState.events = (coachState.events || []).filter(event => String(event.voiceObservationId || "") !== String(observation.id));
    const current = vc.themes[observation.topic];
    if(current){
        current.count = Math.max(0, Number(current.count || 0) - 1);
        current.minutes = (current.minutes || []).filter((_, index, list) => index !== list.length - 1);
        if(!current.count) delete vc.themes[observation.topic];
    }
    saveState(); renderAll();
    try{ if(typeof cancelPersistedCoachVoiceObservation === "function") await cancelPersistedCoachVoiceObservation(observation.id); }catch{}
    showNotice("Ultima osservazione Voice Coach annullata.", "ok");
}

function applyCoachVoiceClarification(id, option){
    const proposal = getCoachVoiceProposalById(id);
    if(!proposal) return;
    proposal.entities = proposal.entities || {};
    if(option === "Calcio d'angolo" || option === "Punizione laterale" || option === "Azione aperta"){
        proposal.entities.context_detail = option;
        proposal.evidence = [...(proposal.evidence || []), `Chiarimento staff: ${option}`];
    }else if(option !== "Salva senza specificare"){
        proposal.entities.context_detail = option;
    }
    proposal.clarification_question = "";
    proposal.clarification_options = [];
    proposal.requires_confirmation = true;
    saveState(); renderCoachVoiceCoach();
}

function dismissCoachVoiceSuggestion(key){
    const vc = ensureCoachVoiceMemory();
    vc.notifications[key] = Date.now();
    saveState(); renderCoachVoiceCoach();
}

function openCoachVoiceThemeDetails(key){
    const item = ensureCoachVoiceMemory().themes?.[key];
    if(!item) return;
    const minutes = Array.isArray(item.minutes) && item.minutes.length ? ` Minuti: ${item.minutes.join("', ")}'.` : "";
    const examples = Array.isArray(item.examples) && item.examples.length ? ` Esempi staff: ${item.examples.slice(0,2).join(" / ")}.` : "";
    showNotice(`${item.label}: ${item.count || 0} segnalazioni.${minutes}${examples}`, "ok", 7000);
}

function cancelCoachVoiceProposal(){
    const vc = ensureCoachVoiceMemory();
    vc.lastProposal = null;
    saveState();
    renderCoachVoiceCoach();
    coachVoiceSession.startedAt = 0;
    setCoachVoiceSessionState("IDLE");
    setCoachVoiceUiStatus("Proposta scartata. Nessun evento e stato salvato.", "idle");
}

function editCoachVoiceProposal(){
    const proposal = ensureCoachVoiceMemory().lastProposal;
    if(!proposal) return;
    const input = document.getElementById("coachVoiceTranscriptEditor") || document.getElementById("coachVoiceInput");
    if(input) input.focus();
    setCoachVoiceUiStatus("Correggi trascrizione e dettagli, poi premi Conferma.", "idle");
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
    if(document.body.dataset.voiceVisibilityBound !== "1"){
        document.body.dataset.voiceVisibilityBound = "1";
        document.addEventListener("visibilitychange", () => {
            if(document.hidden && coachVoiceSession.state === COACH_VOICE_SESSION_STATES.RECORDING){
                failCoachVoiceSession("Registrazione interrotta quando l'app e passata in background. Nessun dato e stato salvato.");
            }
        });
    }
    renderCoachVoiceSession();
}

window.stopCoachVoiceRecording = stopCoachVoiceRecording;
window.cancelCoachVoiceRecording = cancelCoachVoiceRecording;
