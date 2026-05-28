const APP_VERSION = "10085";
const STORAGE_KEY = "matchiq_coach_v13";
const HISTORY_KEY = "matchiq_coach_history_v14";

let coachState = {
    match: null,
    events: [],
    ratings: [],
    report: ""
};

function todayISO(){
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2,"0");
    const day = String(d.getDate()).padStart(2,"0");
    return `${y}-${m}-${day}`;
}

function esc(value){
    return String(value ?? "")
        .replaceAll("&","&amp;")
        .replaceAll("<","&lt;")
        .replaceAll(">","&gt;")
        .replaceAll('"',"&quot;")
        .replaceAll("'","&#039;");
}

function showNotice(message,type="ok",timeout=4500){
    const el = document.getElementById("pageNotice");
    if(!el) return;

    el.textContent = message;
    el.className = `notice show ${type}`;

    if(timeout){
        setTimeout(() => {
            el.className = "notice";
        }, timeout);
    }
}

function isMobileDevice(){
    return window.matchMedia && window.matchMedia("(max-width: 900px)").matches;
}

function goHome(){
    window.location.href = isMobileDevice()
        ? `/mobile.html?v=${APP_VERSION}`
        : `/index.html?v=${APP_VERSION}`;
}

function goScout(){
    window.location.href = `/scout.html?v=${APP_VERSION}`;
}

function goAccount(){
    window.location.href = `/account.html?v=${APP_VERSION}`;
}

function getInputValue(id,fallback=""){
    return document.getElementById(id)?.value?.trim() || fallback;
}

function setInputValue(id,value){
    const el = document.getElementById(id);
    if(el) el.value = value || "";
}

function getTeamName(side){
    if(!coachState.match){
        return side === "home" ? "Casa" : "Trasferta";
    }

    return side === "home"
        ? coachState.match.homeTeam || "Casa"
        : coachState.match.awayTeam || "Trasferta";
}

function getGoals(side){
    return coachState.events.filter(e => e.type === "gol" && e.side === side).length;
}

function getEventsByType(type){
    return coachState.events.filter(e => e.type === type);
}

function getEventCount(type, side=null){
    return coachState.events.filter(e => e.type === type && (!side || e.side === side)).length;
}
