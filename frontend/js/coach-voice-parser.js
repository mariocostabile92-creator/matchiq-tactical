function normalizeCoachVoiceText(text){
    return String(text || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[.,;:!?]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function parseCoachVoiceMinute(text){
    const clean = normalizeCoachVoiceText(text);
    const direct = clean.match(/\b(?:minuto|min|al minuto|all)\s*(\d{1,3})\b/);
    const bare = clean.match(/\b(\d{1,3})\s*(?:minuto|min|')\b/);
    const match = direct || bare;
    if(!match) return { value: getLiveMinuteLabel(), source: "clock" };
    const value = Math.max(0, Math.min(130, Number(match[1]) || 0));
    const current = Number(getLiveMinuteLabel() || 0);
    const warning = current && Math.abs(value - current) >= 12
        ? `Minuto indicato (${value}') distante dal cronometro (${current}').`
        : "";
    return { value, source: "voice", warning };
}

function inferCoachVoiceTeam(text){
    const clean = normalizeCoachVoiceText(text);
    if(/\b(loro|avversari|avversario|ospiti|trasferta|subiamo|ci pressano|ci attaccano|gol loro)\b/.test(clean)){
        return { side: "away", confidence: 0.86 };
    }
    if(/\b(noi|nostra|nostro|casa|recuperiamo|pressiamo|gol nostro|segnamo|segnato noi)\b/.test(clean)){
        return { side: "home", confidence: 0.86 };
    }
    return { side: getInputValue("eventTeamInput", "home"), confidence: 0.55, ambiguous: true };
}

function findCoachVoicePlayers(text){
    const clean = normalizeCoachVoiceText(text);
    const players = getLineup().filter(p => p.name);
    const matches = [];
    players.forEach(player => {
        const full = normalizeCoachVoiceText(player.name);
        const parts = full.split(" ").filter(Boolean);
        const number = String(player.number || "").trim();
        const score = full && clean.includes(full) ? 1
            : parts.some(part => part.length >= 3 && clean.includes(part)) ? 0.76
            : number && new RegExp(`\\b(?:numero\\s*)?${number}\\b`).test(clean) ? 0.72
            : 0;
        if(score){
            matches.push({ player, score });
        }
    });
    return matches.sort((a,b) => b.score - a.score);
}

function resolveCoachVoicePlayer(text){
    const matches = findCoachVoicePlayers(text);
    if(!matches.length) return { player: null, confidence: 0, ambiguous: false };
    const top = matches[0];
    const close = matches.filter(item => item.score >= top.score - 0.08);
    return {
        player: top.player,
        confidence: top.score,
        ambiguous: close.length > 1,
        alternatives: close.map(item => item.player).slice(0, 4)
    };
}

function detectCoachVoiceTheme(text){
    const clean = normalizeCoachVoiceText(text);
    const rule = COACH_VOICE_THEME_RULES.find(item => item.pattern.test(clean));
    if(rule) return { topic: rule.key, label: rule.label, zone: rule.zone, priority: rule.priority };
    return { topic: "general_note", label: "Nota staff", zone: "not_specified", priority: "medium" };
}

function detectCoachVoiceSentiment(text){
    const clean = normalizeCoachVoiceText(text);
    if(/\b(bene|grande|ottimo|riusciamo|recupero|positivo|funziona|uscendo bene)\b/.test(clean)) return "positive";
    if(/\b(soffrendo|male|errore|persa|libero|troppo|problema|fatica|subiamo)\b/.test(clean)) return "negative";
    return "neutral";
}

function detectCoachVoiceEvent(text){
    const clean = normalizeCoachVoiceText(text);
    if(/\b(gol|rete|segnato)\b/.test(clean)) return { key: "goal", confidence: 0.91 };
    if(/\b(tiro|conclusione|calcia)\b/.test(clean)) return { key: "shot", confidence: 0.82 };
    if(/\b(recupero|recupera|riconquista|ruba palla|grande recupero)\b/.test(clean)) return { key: "recovery", confidence: 0.86 };
    if(/\b(palla persa|perde palla|perso palla)\b/.test(clean)) return { key: "lost_ball", confidence: 0.86 };
    if(/\b(giallo|cartellino)\b/.test(clean)) return { key: "yellow_card", confidence: 0.82 };
    return null;
}

function parseCoachVoiceSubstitution(text){
    const clean = normalizeCoachVoiceText(text);
    if(!/\b(cambio|sostituzione|esce|entra|al posto di|per)\b/.test(clean)) return null;
    const players = findCoachVoicePlayers(text);
    const outFirst = clean.match(/\b(?:cambio|esce)\s+([a-z0-9 ]{2,40})\s+(?:per|entra|con)\s+([a-z0-9 ]{2,40})\b/);
    const inFirst = clean.match(/\b(?:entra|metti)\s+([a-z0-9 ]{2,40})\s+(?:per|al posto di)\s+([a-z0-9 ]{2,40})\b/);
    let outPlayer = null;
    let inPlayer = null;
    if(outFirst || inFirst){
        const outText = outFirst ? outFirst[1] : inFirst[2];
        const inText = outFirst ? outFirst[2] : inFirst[1];
        outPlayer = resolveCoachVoicePlayer(outText).player;
        inPlayer = resolveCoachVoicePlayer(inText).player;
    }
    if(!outPlayer && players[0]) outPlayer = players[0].player;
    if(!inPlayer && players[1]) inPlayer = players[1].player;
    return { outPlayer, inPlayer, confidence: outPlayer && inPlayer ? 0.88 : 0.48 };
}

function buildCoachVoiceProposal(text, source="text"){
    const original = String(text || "").trim();
    const clean = normalizeCoachVoiceText(original);
    const minute = parseCoachVoiceMinute(original);
    const team = inferCoachVoiceTeam(original);
    const player = resolveCoachVoicePlayer(original);
    const warnings = [];
    const ambiguities = [];
    if(minute.warning) warnings.push(minute.warning);

    if(/\b(annulla|lascia perdere|non salvare)\b/.test(clean)){
        return {
            id: coachVoiceNowId(), intent: "cancel", confidence: 0.96, requires_confirmation: false,
            minute: minute.value, team: team.side, source, transcript: original,
            entities: {}, normalized_summary: "Comando annullato.", ambiguities, warnings
        };
    }

    const substitution = parseCoachVoiceSubstitution(original);
    if(substitution){
        if(!substitution.outPlayer) ambiguities.push("Giocatore in uscita non riconosciuto.");
        if(!substitution.inPlayer) ambiguities.push("Giocatore in entrata non riconosciuto.");
        return {
            id: coachVoiceNowId(), intent: "substitution", confidence: substitution.confidence,
            requires_confirmation: true, minute: minute.value, team: team.side, source, transcript: original,
            entities: {
                player_out_id: substitution.outPlayer?.id || "",
                player_out_name: substitution.outPlayer ? formatLineupPlayer(substitution.outPlayer) : "",
                player_in_id: substitution.inPlayer?.id || "",
                player_in_name: substitution.inPlayer ? formatLineupPlayer(substitution.inPlayer) : ""
            },
            normalized_summary: substitution.outPlayer && substitution.inPlayer
                ? `Cambio: ${formatLineupPlayer(substitution.outPlayer)} esce, ${formatLineupPlayer(substitution.inPlayer)} entra al ${minute.value}'.`
                : "Cambio da completare: non ho riconosciuto tutti i giocatori.",
            ambiguities, warnings
        };
    }

    const event = detectCoachVoiceEvent(original);
    if(event){
        if(player.ambiguous){
            ambiguities.push(`Giocatore ambiguo: ${player.alternatives.map(p => formatLineupPlayer(p)).join(" / ")}`);
        }
        const mapped = COACH_VOICE_EVENT_MAP[event.key];
        if(!player.player && ["goal","shot","recovery","lost_ball","yellow_card"].includes(event.key)){
            ambiguities.push("Giocatore non riconosciuto nella formazione o in panchina.");
        }
        const low = !player.player && event.key !== "goal";
        return {
            id: coachVoiceNowId(), intent: "player_event", confidence: low ? 0.58 : event.confidence,
            requires_confirmation: event.key === "goal" && team.ambiguous || player.ambiguous || low,
            minute: minute.value, team: team.side, source, transcript: original,
            entities: {
                event_key: event.key,
                event_type: mapped.type,
                event_label: mapped.label,
                event_icon: mapped.icon,
                player_id: player.player?.id || "",
                player_name: player.player ? formatLineupPlayer(player.player) : ""
            },
            normalized_summary: `${mapped.label}${player.player ? " di " + formatLineupPlayer(player.player) : ""} al ${minute.value}'.`,
            ambiguities, warnings
        };
    }

    if(/\b(inizia|intervallo|riprendi|termina|fine partita|secondo tempo)\b/.test(clean)){
        return {
            id: coachVoiceNowId(), intent: "match_control", confidence: 0.78, requires_confirmation: true,
            minute: minute.value, team: team.side, source, transcript: original,
            entities: { command: clean }, normalized_summary: "Comando partita da confermare.", ambiguities, warnings
        };
    }

    const theme = detectCoachVoiceTheme(original);
    const sentiment = detectCoachVoiceSentiment(original);
    const individual = player.player && /\b(stanco|duelli|giocando bene|male|perdendo|fatica)\b/.test(clean);
    if(player.ambiguous){
        ambiguities.push(`Giocatore ambiguo: ${player.alternatives.map(p => formatLineupPlayer(p)).join(" / ")}`);
    }
    return {
        id: coachVoiceNowId(), intent: individual ? "player_note" : "tactical_note",
        confidence: theme.topic === "general_note" ? 0.62 : 0.84,
        requires_confirmation: player.ambiguous || theme.topic === "general_note",
        minute: minute.value, team: team.side, source, transcript: original,
        entities: {
            topic: theme.topic,
            topic_label: theme.label,
            zone: theme.zone,
            priority: theme.priority,
            sentiment,
            player_id: player.player?.id || "",
            player_name: player.player ? formatLineupPlayer(player.player) : "",
            note_original: original,
            note_normalized: original
        },
        normalized_summary: `${theme.label}: ${original}`,
        ambiguities, warnings
    };
}
