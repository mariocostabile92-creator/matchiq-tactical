/*
    MatchIQ - Utils Module
    Funzioni comuni riutilizzabili tra match, scout e dashboard.
*/

function safeNumber(v, f = 0){
    const n = Number(v);
    return Number.isFinite(n) ? n : f;
}

function clamp(v, min = 0, max = 100){
    return Math.max(min, Math.min(max, safeNumber(v, 0)));
}

function getScore(m){
    return m.score && typeof m.score === "object"
        ? {
            home: safeNumber(m.score.home),
            away: safeNumber(m.score.away)
        }
        : {
            home: safeNumber(m.home_goals),
            away: safeNumber(m.away_goals)
        };
}

function getAlerts(d){
    if(Array.isArray(d.live_alerts)) return d.live_alerts;
    if(Array.isArray(d.live_alerts?.alerts)) return d.live_alerts.alerts;
    if(Array.isArray(d.pressure_engine?.alerts)) return d.pressure_engine.alerts;
    return [];
}

function getTimeline(d){
    if(Array.isArray(d.timeline)) return d.timeline;
    if(Array.isArray(d.timeline?.events)) return d.timeline.events;
    return [];
}

function getPlayers(d){
    if(Array.isArray(d.players_analysis?.players)) return d.players_analysis.players;
    if(Array.isArray(d.players)) return d.players;
    return [];
}

function getCoach(d){
    return Array.isArray(d.tactical_coach?.tactical_advice)
        ? d.tactical_coach.tactical_advice
        : [];
}

function getFuture(d){
    return d.future_prediction?.prediction_engine || d.future_prediction || {};
}

function getXg(d){
    return d.xg_analysis || {};
}

function getReport(d){
    return (
        d.ai_report?.ai_report ||
        d.ai_report?.summary ||
        d.ai_report?.report ||
        "Report AI non disponibile."
    );
}

function getWinProbability(d){
    return d.win_probability || {
        home_win: 33.3,
        draw: 33.4,
        away_win: 33.3,
        dominant_outcome: "draw"
    };
}

function getTempoLabel(v){
    if(!v) return "N/A";
    if(typeof v === "string") return v;
    if(typeof v === "object") return v.label || v.value || "N/A";
    return String(v);
}