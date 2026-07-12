APP_VERSION = "10496";
const STORAGE_KEY = "matchiq_coach_v13";
const HISTORY_KEY = "matchiq_coach_history_v14";
const OWNER_EMAIL = "mario.costabile92@outlook.it";
const COACH_FREE_LIMITS = { maxRatings: 5, maxHistory: 2, maxPdfExports: 1, maxWhatsappCopies: 1 };
const COACH_PRO_LIMITS = { maxRatings: 999, maxHistory: 50, maxPdfExports: 999, maxWhatsappCopies: 999 };
const COACH_USAGE_KEYS = { pdfExports: "matchiq_coach_pdf_exports_v16", whatsappCopies: "matchiq_coach_whatsapp_copies_v16" };

let coachState = { match: null, events: [], ratings: [], lineup: [], report: "", live: null, memory: null, phase: "pre" };
let coachLiveTimer = null;

function ensureCoachStateShape(){
    if(!coachState || typeof coachState !== "object") coachState = { match:null, events:[], ratings:[], lineup:[], report:"", memory:null };
    coachState.match = normalizeCoachMatch(coachState.match);
    if(!Array.isArray(coachState.events)) coachState.events = [];
    if(!Array.isArray(coachState.ratings)) coachState.ratings = [];
    if(!Array.isArray(coachState.lineup)) coachState.lineup = [];
    if(typeof coachState.report !== "string") coachState.report = coachState.report || "";
    coachState.live = normalizeCoachLive(coachState.live);
    coachState.memory = normalizeCoachMemory(coachState.memory);
    coachState.phase = normalizeCoachPhase(coachState.phase);
}
function normalizeCoachMatch(match){
    if(!match || typeof match !== "object") return null;
    const field = match.field || match.matchField || match.campo || match.stadium || match.venue || "";
    return {
        ...match,
        field
    };
}
function todayISO(){ const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`; }
function normalizeCoachLive(live){
    const base = live && typeof live === "object" ? live : {};
    return {
        running: Boolean(base.running),
        startedAt: base.startedAt || null,
        elapsed: Math.max(0, Number(base.elapsed || 0) || 0),
        period: base.period || "1T"
    };
}
function normalizeCoachMemory(memory){
    const base = memory && typeof memory === "object" ? memory : {};
    const precheck = base.precheck && typeof base.precheck === "object" ? base.precheck : {};
    const voiceCoach = base.voiceCoach && typeof base.voiceCoach === "object" ? base.voiceCoach : {};
    return {
        precheck: {
            objective: String(precheck.objective || ""),
            risk: String(precheck.risk || ""),
            observe: String(precheck.observe || ""),
            opponent: String(precheck.opponent || ""),
            trainingFocus: String(precheck.trainingFocus || "")
        },
        tags: Array.isArray(base.tags) ? base.tags : [],
        teamNotes: Array.isArray(base.teamNotes) ? base.teamNotes : [],
        trainingPlan: Array.isArray(base.trainingPlan) ? base.trainingPlan : [],
        voiceCoach: {
            observations: Array.isArray(voiceCoach.observations) ? voiceCoach.observations : [],
            themes: voiceCoach.themes && typeof voiceCoach.themes === "object" ? voiceCoach.themes : {},
            players: voiceCoach.players && typeof voiceCoach.players === "object" ? voiceCoach.players : {},
            lastProposal: voiceCoach.lastProposal && typeof voiceCoach.lastProposal === "object" ? voiceCoach.lastProposal : null,
            lastStatus: String(voiceCoach.lastStatus || "")
        }
    };
}
function normalizeCoachPhase(phase){
    const value = String(phase || "").toLowerCase();
    return ["pre","match","post"].includes(value) ? value : "pre";
}
function getCoachSuggestedPhase(){
    ensureCoachStateShape();
    if(!coachState.match) return "pre";
    if(coachState.live?.running) return "match";
    if(coachState.phase === "match" || coachState.phase === "post") return coachState.phase;
    return "pre";
}
function getCoachLiveElapsedSeconds(){
    ensureCoachStateShape();
    const live = coachState.live;
    const base = Math.max(0, Number(live.elapsed || 0) || 0);
    if(!live.running || !live.startedAt) return base;
    return base + Math.max(0, Math.floor((Date.now() - new Date(live.startedAt).getTime()) / 1000));
}
function formatCoachClock(totalSeconds){
    const total = Math.max(0, Math.floor(Number(totalSeconds || 0)));
    const minutes = String(Math.floor(total / 60)).padStart(2,"0");
    const seconds = String(total % 60).padStart(2,"0");
    return `${minutes}:${seconds}`;
}
function getCoachLiveMinute(){
    const elapsedMinutes = Math.max(0, Math.floor(getCoachLiveElapsedSeconds() / 60));
    const period = coachState.live?.period || "1T";
    const offset = period === "INT" ? 45 : period === "2T" ? 45 : period === "ET1" ? 90 : period === "ET2" ? 105 : 0;
    return Math.min(130, offset + elapsedMinutes);
}
function getLiveMinuteLabel(){
    const minute = getCoachLiveMinute();
    return minute > 0 ? minute : 0;
}
function esc(value){ return String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;"); }
function showNotice(message,type="ok",timeout=4500){ const el=document.getElementById("pageNotice"); if(!el)return; el.textContent=message; el.className=`notice show ${type}`; if(timeout){ setTimeout(()=>{ el.className="notice"; },timeout); } }
function isMobileDevice(){ return window.matchMedia && window.matchMedia("(max-width: 900px)").matches; }
function goHome(){ window.location.href=isMobileDevice()?`/mobile.html?v=${APP_VERSION}`:`/index.html?v=${APP_VERSION}`; }
function goScout(){ window.location.href=`/scout.html?v=${APP_VERSION}`; }
function goAccount(){ window.location.href=`/account.html?v=${APP_VERSION}`; }
function getInputValue(id,fallback=""){ return document.getElementById(id)?.value?.trim() || fallback; }
function setInputValue(id,value){ const el=document.getElementById(id); if(el) el.value=value || ""; }
function getTeamName(side){ ensureCoachStateShape(); if(!coachState.match) return side==="home"?"Casa":"Trasferta"; return side==="home" ? coachState.match.homeTeam || "Casa" : coachState.match.awayTeam || "Trasferta"; }
function getMatchField(){ ensureCoachStateShape(); return coachState.match?.field || "Campo non indicato"; }
function getGoals(side){ ensureCoachStateShape(); return coachState.events.filter(e=>e.type==="gol" && e.side===side).length; }
function getEventsByType(type){ ensureCoachStateShape(); return coachState.events.filter(e=>e.type===type); }
function getEventCount(type, side=null){ ensureCoachStateShape(); return coachState.events.filter(e=>e.type===type && (!side || e.side===side)).length; }
function getStoredUser(){ try{ return JSON.parse(localStorage.getItem("matchiq_auth_user") || sessionStorage.getItem("matchiq_auth_user") || "null"); }catch{return null;} }
function getStoredPlan(){ const user=getStoredUser(); const email=String(user?.email || localStorage.getItem("matchiq_user_email") || "").toLowerCase().trim(); if(email===OWNER_EMAIL)return "owner"; return String(user?.plan || user?.piano || localStorage.getItem("matchiq_user_plan") || sessionStorage.getItem("matchiq_user_plan") || "free").toLowerCase().trim(); }
function isCoachPro(){ return ["pro","scout","owner","owner_pro","admin"].includes(getStoredPlan()); }
function getCoachLimits(){ return isCoachPro()?COACH_PRO_LIMITS:COACH_FREE_LIMITS; }
function getCoachUsageCount(key){ try{return Number(localStorage.getItem(key)||"0")||0;}catch{return 0;} }
function incrementCoachUsageCount(key){ try{ localStorage.setItem(key,String(getCoachUsageCount(key)+1)); }catch{} }
function canUseCoachPdf(){ return isCoachPro() || getCoachUsageCount(COACH_USAGE_KEYS.pdfExports) < getCoachLimits().maxPdfExports; }
function canUseCoachWhatsapp(){ return isCoachPro() || getCoachUsageCount(COACH_USAGE_KEYS.whatsappCopies) < getCoachLimits().maxWhatsappCopies; }
function getCoachPdfUsageText(){ return isCoachPro() ? "PDF sbloccati" : `PDF prova ${getCoachUsageCount(COACH_USAGE_KEYS.pdfExports)}/${getCoachLimits().maxPdfExports}`; }
function getCoachWhatsappUsageText(){ return isCoachPro() ? "WhatsApp sbloccato" : `WhatsApp prova ${getCoachUsageCount(COACH_USAGE_KEYS.whatsappCopies)}/${getCoachLimits().maxWhatsappCopies}`; }
function canAddCoachRating(){ ensureCoachStateShape(); return coachState.ratings.length < getCoachLimits().maxRatings; }
function canSaveCoachHistory(){ return loadHistory().length < getCoachLimits().maxHistory; }
function getCoachPlanLabel(){ return isCoachPro() ? "PRO" : "FREE"; }
function getCoachPlanDescription(){ return isCoachPro() ? "Coach Pro attivo: PDF, WhatsApp, pagelle e storico sono sbloccati per uso continuativo." : "Piano Free: puoi provare Coach Mode con 5 pagelle, 2 partite nello storico, 1 PDF e 1 sintesi WhatsApp."; }
function goCoachUpgrade(){ window.location.href=`/account.html?v=${APP_VERSION}&from=coach-pro-lock`; }
function showCoachProNotice(feature){ showNotice(`🔒 Hai usato la prova gratuita di ${feature}. Passa a Pro per usarla in modo continuativo.`,"warn",3500); setTimeout(()=>goCoachUpgrade(),1200); }

function normalizeLineupSide(value, player=null){
    const raw=String(value || player?.side || "").toLowerCase().trim();
    if(raw==="away" || raw==="trasferta") return "away";
    if(raw==="home" || raw==="casa") return "home";
    const team=String(player?.team || "").toLowerCase().trim();
    const homeTeam=String(coachState.match?.homeTeam || "").toLowerCase().trim();
    const awayTeam=String(coachState.match?.awayTeam || "").toLowerCase().trim();
    if(team && awayTeam && team===awayTeam) return "away";
    if(team && homeTeam && team===homeTeam) return "home";
    return "home";
}
function normalizeLineupPlayer(player){
    const p=player && typeof player==="object" ? player : {};
    const side=normalizeLineupSide(p.side,p);
    return { id:p.id || Date.now()+Math.random(), number:p.number || "", name:p.name || p.player || "", side, team:side==="home"?getTeamName("home"):getTeamName("away"), role:p.role || "Jolly", status:p.status==="Panchina"?"Panchina":"Titolare", createdAt:p.createdAt || new Date().toISOString() };
}
function getLineup(){ ensureCoachStateShape(); coachState.lineup=coachState.lineup.filter(p=>p && typeof p==="object").map(normalizeLineupPlayer); return coachState.lineup; }
function getLineupBySide(side){ const normalizedSide=side==="away"?"away":"home"; return getLineup().filter(p=>normalizeLineupSide(p.side,p)===normalizedSide); }
function getLineupPlayerById(playerId){ return getLineup().find(p=>String(p.id)===String(playerId)) || null; }
function formatLineupPlayer(p){ if(!p)return ""; const number=p.number?`#${p.number} `:""; return `${number}${p.name}`; }
window.activePitchSide=window.activePitchSide || "home";
function setPitchSide(side){ window.activePitchSide=side==="away"?"away":"home"; if(typeof renderLineupPitch==="function") renderLineupPitch(); }
