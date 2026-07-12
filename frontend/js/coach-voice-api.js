function buildCoachVoiceContext(){
    ensureCoachStateShape();
    return {
        match_id: coachState.match?.id || null,
        home_team: getTeamName("home"),
        away_team: getTeamName("away"),
        current_minute: Number(getLiveMinuteLabel() || 0) || 0,
        period: coachState.live?.period || "1T",
        selected_team: getInputValue("eventTeamInput", "home"),
        lineup: getLineup().map(player => ({
            id: player.id,
            number: String(player.number || ""),
            name: String(player.name || ""),
            side: normalizeLineupSide(player.side, player),
            role: String(player.role || ""),
            status: String(player.status || "")
        }))
    };
}

async function interpretCoachVoiceCommandFromServer(text, source="text"){
    const response = await fetch("/api/coach/voice/interpret", {
        method: "POST",
        headers: {
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
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
        server_interpreted: true
    };
}
