const COACH_VOICE_INTENTS = {
    player_event: "Evento giocatore",
    substitution: "Cambio",
    tactical_note: "Nota tattica",
    player_note: "Indicazione individuale",
    score_update: "Aggiornamento punteggio",
    match_control: "Controllo partita",
    cancel: "Annullamento",
    unknown: "Da chiarire"
};

const COACH_VOICE_EVENT_MAP = {
    goal: { type: "gol", label: "Gol", icon: "GOL" },
    shot: { type: "tiro", label: "Tiro", icon: "TIRO" },
    recovery: { type: "recupero", label: "Recupero palla", icon: "REC" },
    lost_ball: { type: "palla_persa", label: "Palla persa", icon: "PERSA" },
    yellow_card: { type: "cartellino", label: "Cartellino giallo", icon: "GIALLO" }
};

const COACH_VOICE_THEME_RULES = [
    { key: "second_post", label: "Secondo palo", zone: "area", priority: "high", pattern: /\b(secondo palo|palo dietro|palo libero)\b/ },
    { key: "right_flank", label: "Fascia destra", zone: "right_flank", priority: "high", pattern: /\b(destra|fascia destra|lato destro)\b/ },
    { key: "left_flank", label: "Fascia sinistra", zone: "left_flank", priority: "medium", pattern: /\b(sinistra|fascia sinistra|lato sinistro)\b/ },
    { key: "low_press", label: "Pressing basso", zone: "central", priority: "medium", pattern: /\b(pressiamo bassi|pressione bassa|troppo bassi|pressing basso)\b/ },
    { key: "build_up", label: "Costruzione dal basso", zone: "build_up", priority: "medium", pattern: /\b(usciamo dal basso|uscendo bene|costruzione|dal portiere|uscita bassa)\b/ },
    { key: "negative_transition", label: "Transizione negativa", zone: "central", priority: "high", pattern: /\b(transizione|ripartenza|contropiede|rest defense)\b/ },
    { key: "duels", label: "Duelli e seconde palle", zone: "duel", priority: "medium", pattern: /\b(duelli|seconda palla|rimbalzi|spizzata)\b/ },
    { key: "tiredness", label: "Stanchezza", zone: "individual", priority: "medium", pattern: /\b(stanco|stanchezza|non ne ha|fatica)\b/ },
    { key: "team_long", label: "Distanza tra reparti", zone: "central", priority: "high", pattern: /\b(squadra lunga|reparti|distanze|troppo lunghi)\b/ }
];

function ensureCoachVoiceMemory(){
    ensureCoachStateShape();
    if(!coachState.memory.voiceCoach || typeof coachState.memory.voiceCoach !== "object"){
        coachState.memory.voiceCoach = { observations: [], themes: {}, players: {}, lastProposal: null, lastStatus: "" };
    }
    const vc = coachState.memory.voiceCoach;
    if(!Array.isArray(vc.observations)) vc.observations = [];
    if(!vc.themes || typeof vc.themes !== "object") vc.themes = {};
    if(!vc.players || typeof vc.players !== "object") vc.players = {};
    if(vc.lastProposal && typeof vc.lastProposal !== "object") vc.lastProposal = null;
    return vc;
}

function getCoachVoiceThemeRule(topic){
    return COACH_VOICE_THEME_RULES.find(rule => rule.key === topic) || null;
}

function coachVoiceNowId(){
    return Date.now() + "-" + Math.round(Math.random() * 100000);
}
