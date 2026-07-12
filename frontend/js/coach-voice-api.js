function buildCoachVoiceContext(){
    ensureCoachStateShape();
    const voice = ensureCoachVoiceMemory();
    const lineup = getLineup();
    return {
        match_id: coachState.match?.id || null,
        home_team: getTeamName("home"),
        away_team: getTeamName("away"),
        current_minute: Number(getLiveMinuteLabel() || 0) || 0,
        period: coachState.live?.period || "1T",
        selected_team: getInputValue("eventTeamInput", "home"),
        observed_team: getInputValue("eventTeamInput", "home"),
        home_score: getGoals("home"),
        away_score: getGoals("away"),
        home_formation: coachState.match?.homeShape || "",
        away_formation: coachState.match?.awayShape || "",
        lineup: lineup.filter(player => player.status !== "Panchina").map(player => ({
            id: player.id,
            number: String(player.number || ""),
            name: String(player.name || ""),
            side: normalizeLineupSide(player.side, player),
            role: String(player.role || ""),
            status: String(player.status || ""),
            nickname: String(player.nickname || ""),
            aliases: Array.isArray(player.aliases) ? player.aliases : [],
            source: "match"
        })),
        bench: lineup.filter(player => player.status === "Panchina").map(player => ({
            id: player.id, number: String(player.number || ""), name: String(player.name || ""),
            side: normalizeLineupSide(player.side, player), role: String(player.role || ""),
            status: "Panchina", nickname: String(player.nickname || ""),
            aliases: Array.isArray(player.aliases) ? player.aliases : [], source: "match"
        })),
        substituted_player_ids: lineup.filter(player => player.substituted).map(player => String(player.id)),
        previous_events: (coachState.events || []).slice(0, 30),
        previous_observations: (voice.observations || []).slice(0, 30),
        recurring_themes: Object.entries(voice.themes || {}).slice(0, 10).map(([topic, item]) => ({topic, ...item}))
    };
}

function coachVoiceAuthHeaders(){
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
    return {"Accept":"application/json", "Content-Type":"application/json", ...(token ? {"Authorization":`Bearer ${token}`} : {})};
}

function getCoachVoiceMatchKey(){
    return String(coachState.match?.id || coachState.match?.createdAt || "").trim();
}

async function interpretCoachVoiceCommandFromServer(text, source="text"){
    const response = await fetch("/api/coach/voice/interpret", {
        method: "POST",
        headers: coachVoiceAuthHeaders(),
        body: JSON.stringify({
            transcript: String(text || ""),
            source,
            context: buildCoachVoiceContext()
        })
    });
    if(!response.ok){
        throw new Error("voice_interpret_failed");
    }
    const data = await response.json();
    return {
        id: coachVoiceNowId(),
        intent: data.intent || "unknown",
        confidence: Number(data.confidence || 0),
        requires_confirmation: Boolean(data.requires_confirmation),
        minute: Number(data.minute || 0),
        team: data.team || "home",
        source,
        transcript: String(text || ""),
        entities: data.entities || {},
        normalized_summary: data.normalized_summary || "",
        ambiguities: Array.isArray(data.ambiguities) ? data.ambiguities : [],
        warnings: Array.isArray(data.warnings) ? data.warnings : [],
        evidence: Array.isArray(data.evidence) ? data.evidence : [],
        explanation: data.explanation || "",
        match_phase: data.match_phase || coachState.live?.period || "1T",
        tactical_topic: data.tactical_topic || data.entities?.topic || "general_note",
        zone: data.zone || data.entities?.zone || "not_specified",
        polarity: data.polarity || data.entities?.sentiment || "neutral",
        priority: data.priority || data.entities?.priority || "medium",
        clarification_question: data.clarification_question || "",
        clarification_options: Array.isArray(data.clarification_options) ? data.clarification_options : [],
        server_interpreted: true
    };
}

async function persistCoachVoiceObservation(proposal, observation){
    const matchKey = getCoachVoiceMatchKey();
    if(!matchKey || !proposal || !observation) return {local:true};
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
    if(!token) return {local:true};
    const entities = proposal.entities || {};
    const ids = [entities.player_id, entities.player_out_id, entities.player_in_id].filter(Boolean).map(String);
    const names = [entities.player_name, entities.player_out_name, entities.player_in_name].filter(Boolean);
    const response = await fetch("/api/coach/voice/observations", {
        method:"POST", headers:coachVoiceAuthHeaders(),
        body:JSON.stringify({
            client_id:String(proposal.id), match_key:matchKey, match_id:String(coachState.match?.id || "") || null,
            intent:proposal.intent, confidence:Number(proposal.confidence || 0), original_text:String(proposal.transcript || ""),
            normalized_summary:String(proposal.normalized_summary || ""), minute:Number(proposal.minute || 0),
            match_phase:proposal.match_phase || coachState.live?.period || "1T", team:proposal.team || "home",
            player_ids:ids, player_names:names, tactical_topic:proposal.tactical_topic || entities.topic || entities.event_key || proposal.intent,
            topic_label:entities.topic_label || entities.event_label || COACH_VOICE_INTENTS[proposal.intent] || "Nota staff",
            zone:proposal.zone || entities.zone || "not_specified", polarity:proposal.polarity || entities.sentiment || "neutral",
            priority:proposal.priority || entities.priority || "medium", source:proposal.source === "speech" ? "speech" : "text",
            requires_confirmation:Boolean(proposal.requires_confirmation), ambiguities:proposal.ambiguities || [], warnings:proposal.warnings || [],
            evidence:proposal.evidence || [], explanation:proposal.explanation || "", status:"confirmed",
            metadata:{home_team:getTeamName("home"), away_team:getTeamName("away"), score:`${getGoals("home")}-${getGoals("away")}`}
        })
    });
    if(!response.ok) throw new Error("voice_observation_sync_failed");
    return response.json();
}

async function loadCoachVoiceIntelligence(){
    const matchKey = getCoachVoiceMatchKey();
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
    if(!matchKey || !token) return;
    try{
        const response = await fetch(`/api/coach/voice/matches/${encodeURIComponent(matchKey)}`, {headers:coachVoiceAuthHeaders()});
        if(!response.ok) return;
        const data = await response.json();
        const vc = ensureCoachVoiceMemory();
        if(Array.isArray(data.observations) && data.observations.length){
            vc.observations = data.observations.map(item => ({
                id:item.client_id, minute:item.minute, intent:item.intent, topic:item.tactical_topic, label:item.topic_label,
                zone:item.zone, priority:item.priority, sentiment:item.polarity, player:(item.player_names || []).join(", "),
                note:item.original_text, createdAt:item.created_at, syncStatus:"synced", status:item.status
            })).reverse();
        }
        if(Array.isArray(data.themes)){
            vc.themes = Object.fromEntries(data.themes.map(item => [item.topic, {
                id:item.id, label:item.label, count:item.count, minutes:[item.first_minute, item.last_minute], zone:item.zone,
                priority:item.highest_priority, polarity:item.polarity, players:item.involved_players || [], examples:item.examples || [], status:item.status
            }]));
        }
        vc.proactiveSuggestions = Array.isArray(data.proactive_suggestions) ? data.proactive_suggestions : [];
        vc.halftime = data.halftime || {};
        vc.postMatch = data.post_match || {};
        saveState(); renderAll();
    }catch(error){ console.warn("[Voice Coach] Archivio cloud non disponibile:", error); }
}

async function cancelPersistedCoachVoiceObservation(clientId){
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
    if(!token) return;
    await fetch(`/api/coach/voice/observations/${encodeURIComponent(clientId)}`, {method:"DELETE", headers:coachVoiceAuthHeaders()});
}

async function deleteCoachVoiceMatchIntelligence(matchKey){
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
    if(!token || !matchKey) return;
    await fetch(`/api/coach/voice/matches/${encodeURIComponent(matchKey)}`, {method:"DELETE", headers:coachVoiceAuthHeaders()});
}
