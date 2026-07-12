let coachVoiceRecognition = null;

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

function beginCoachVoiceListening(){
    if(coachVoiceRecognition){
        coachVoiceRecognition.stop();
        coachVoiceRecognition = null;
        setCoachVoiceUiStatus("Ascolto interrotto. Puoi scrivere il comando nel campo.", "idle");
        return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!SpeechRecognition){
        setCoachVoiceUiStatus("Microfono non disponibile in questo browser. Scrivi il comando e premi Interpreta.", "blocked");
        const input = document.getElementById("coachVoiceInput");
        if(input) input.focus();
        return;
    }
    const recognition = new SpeechRecognition();
    coachVoiceRecognition = recognition;
    recognition.lang = "it-IT";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setCoachVoiceUiStatus("Sto ascoltando... parla in modo naturale e breve.", "listening");
    recognition.onresult = event => {
        const text = event.results?.[0]?.[0]?.transcript || "";
        setInputValue("coachVoiceInput", text);
        coachVoiceRecognition = null;
        if(text.trim()) processCoachVoiceCommand(text, "speech");
        else setCoachVoiceUiStatus("Audio ricevuto ma senza testo. Riprova o scrivi il comando.", "blocked");
    };
    recognition.onerror = event => {
        coachVoiceRecognition = null;
        const denied = event?.error === "not-allowed" || event?.error === "service-not-allowed";
        setCoachVoiceUiStatus(denied
            ? "Microfono bloccato. Abilitalo dal browser oppure usa Scrivi il comando."
            : "Non ho capito l'audio. Prova una frase piu breve o usa il testo.", "blocked");
    };
    recognition.onend = () => {
        if(coachVoiceRecognition === recognition){
            coachVoiceRecognition = null;
            setCoachVoiceUiStatus("Ascolto chiuso. Se non vedi una proposta, scrivi il comando.", "idle");
        }
    };
    try{
        recognition.start();
    }catch{
        coachVoiceRecognition = null;
        setCoachVoiceUiStatus("Il browser non ha avviato il microfono. Usa Scrivi il comando.", "blocked");
    }
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
        return proposal;
    }

    if(!proposal.requires_confirmation && proposal.confidence >= 0.78){
        applyCoachVoiceProposal(proposal.id, true);
    }else{
        setCoachVoiceUiStatus("Ho preparato una proposta. Controllala e conferma.", "idle");
        showNotice("AI Voice Coach ha bisogno di conferma prima di salvare.", "warn", 3500);
    }
    return proposal;
}

function getCoachVoiceProposalById(id){
    const proposal = ensureCoachVoiceMemory().lastProposal;
    return proposal && String(proposal.id) === String(id) ? proposal : null;
}

function coachVoiceEventOptionsFromProposal(proposal){
    return {
        minute: proposal.minute,
        side: proposal.team || "home",
        playerId: proposal.entities?.player_id || "",
        player: proposal.entities?.player_name || "",
        note: proposal.transcript,
        source: "ai-voice",
        tags: [proposal.entities?.topic_label, proposal.entities?.zone, "AI Voice Coach"].filter(Boolean)
    };
}

function applyCoachVoiceProposal(id, silent=false){
    const proposal = getCoachVoiceProposalById(id);
    if(!proposal){
        showNotice("Proposta AI Voice Coach non trovata.", "warn");
        return;
    }
    if(proposal.intent === "substitution"){
        applyCoachVoiceSubstitution(proposal);
    }else if(proposal.intent === "player_event"){
        const e = proposal.entities || {};
        addQuickEvent(e.event_type || "nota", e.event_label || "Evento", e.event_icon || "NOTE", coachVoiceEventOptionsFromProposal(proposal));
    }else if(proposal.intent === "tactical_note" || proposal.intent === "player_note"){
        const topic = proposal.entities?.topic || "general_note";
        const rule = getCoachVoiceThemeRule(topic);
        const type = topic === "second_post" || topic === "right_flank" || topic === "left_flank" ? "errore_difensivo"
            : topic === "low_press" ? "pressing"
            : topic === "build_up" ? "uscita_lato"
            : topic === "negative_transition" ? "transizione"
            : topic === "duels" ? "seconda_palla"
            : "nota";
        addQuickEvent(type, proposal.entities?.topic_label || "Nota tattica", "VOICE", coachVoiceEventOptionsFromProposal(proposal));
        recordCoachVoiceObservation(proposal, rule);
    }else if(proposal.intent === "match_control"){
        setCoachVoiceUiStatus("Comando partita non applicato automaticamente: usa i pulsanti timer/fase per sicurezza.", "blocked");
        return;
    }else{
        showNotice("Comando non supportato. Salvo come nota staff se confermi con una frase piu chiara.", "warn");
        return;
    }
    const vc = ensureCoachVoiceMemory();
    vc.lastProposal = null;
    saveState();
    renderAll();
    setCoachVoiceUiStatus("Evento salvato da AI Voice Coach.", "idle");
    if(!silent) showNotice("AI Voice Coach ha salvato l'azione nella timeline.", "ok", 3200);
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
    inPlayer.status = "Titolare";
    inPlayer.side = outPlayer.side || inPlayer.side;
    inPlayer.team = getTeamName(inPlayer.side);
    addQuickEvent("cambio", "Cambio", "CAMBIO", {
        minute: proposal.minute,
        side: outPlayer.side || proposal.team || "home",
        player: `${formatLineupPlayer(outPlayer)} -> ${formatLineupPlayer(inPlayer)}`,
        note: proposal.normalized_summary,
        source: "ai-voice"
    });
}

function recordCoachVoiceObservation(proposal, rule=null){
    const vc = ensureCoachVoiceMemory();
    const topic = proposal.entities?.topic || "general_note";
    const label = proposal.entities?.topic_label || rule?.label || "Nota staff";
    vc.observations.unshift({
        id: proposal.id,
        minute: proposal.minute,
        intent: proposal.intent,
        topic,
        label,
        zone: proposal.entities?.zone || rule?.zone || "not_specified",
        priority: proposal.entities?.priority || rule?.priority || "medium",
        sentiment: proposal.entities?.sentiment || "neutral",
        player: proposal.entities?.player_name || "",
        note: proposal.transcript,
        createdAt: new Date().toISOString()
    });
    vc.observations = vc.observations.slice(0, 80);
    const current = vc.themes[topic] || { label, count: 0, minutes: [], priority: proposal.entities?.priority || "medium" };
    current.label = label;
    current.count += 1;
    current.minutes = [...(current.minutes || []), proposal.minute].slice(-8);
    current.priority = proposal.entities?.priority || current.priority || "medium";
    vc.themes[topic] = current;
    if(proposal.entities?.player_name){
        const key = proposal.entities.player_name;
        vc.players[key] = (Number(vc.players[key] || 0) || 0) + 1;
    }
}

function cancelCoachVoiceProposal(){
    const vc = ensureCoachVoiceMemory();
    vc.lastProposal = null;
    saveState();
    renderCoachVoiceCoach();
    setCoachVoiceUiStatus("Proposta annullata. Puoi dettare o scrivere un nuovo comando.", "idle");
}

function editCoachVoiceProposal(){
    const proposal = ensureCoachVoiceMemory().lastProposal;
    if(!proposal) return;
    setInputValue("coachVoiceInput", proposal.transcript || "");
    const input = document.getElementById("coachVoiceInput");
    if(input) input.focus();
    setCoachVoiceUiStatus("Modifica il testo e premi Interpreta.", "idle");
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
