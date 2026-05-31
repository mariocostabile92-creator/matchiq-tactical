async function trackCoachFeature(feature, metadata = {}){
    try{
        const headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        };

        if(window.MatchIQAuth && typeof MatchIQAuth.authHeaders === "function"){
            Object.assign(headers, MatchIQAuth.authHeaders({
                "Content-Type": "application/json"
            }));
        }else{
            const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
            if(token){
                headers["Authorization"] = "Bearer " + token;
            }
        }

        await fetch("/api/coach/track", {
            method: "POST",
            headers,
            body: JSON.stringify({
                feature,
                metadata: {
                    source: "coach",
                    path: window.location.pathname,
                    is_pwa: Boolean(window.matchMedia && window.matchMedia("(display-mode: standalone)").matches),
                    timestamp: new Date().toISOString(),
                    ...metadata
                }
            }),
            keepalive: true
        });
    }catch(e){
        console.warn("[Coach Tracking] Tracking non disponibile:", e);
    }
}

function saveState(){
    try{
        localStorage.setItem(STORAGE_KEY, JSON.stringify(coachState));
    }catch(e){
        console.warn("Salvataggio Coach non disponibile:", e);
    }
}

function loadState(){
    try{
        const raw = localStorage.getItem(STORAGE_KEY);
        if(!raw) return;

        const data = JSON.parse(raw);
        if(!data || typeof data !== "object") return;

        coachState = {
            match: data.match || null,
            events: Array.isArray(data.events) ? data.events : [],
            ratings: Array.isArray(data.ratings) ? data.ratings : [],
            report: data.report || ""
        };
    }catch(e){
        console.warn("Caricamento Coach non disponibile:", e);
    }
}

function loadHistory(){
    try{
        const raw = localStorage.getItem(HISTORY_KEY);
        const data = raw ? JSON.parse(raw) : [];
        return Array.isArray(data) ? data : [];
    }catch(e){
        console.warn("Storico Coach non disponibile:", e);
        return [];
    }
}

function saveHistory(list){
    try{
        const max = getCoachLimits().maxHistory || 1;
        localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, max)));
    }catch(e){
        console.warn("Salvataggio storico non disponibile:", e);
    }
}

function buildHistoryItem(){
    const match = coachState.match;
    if(!match) return null;

    return {
        id: Date.now() + "-" + Math.round(Math.random() * 9999),
        savedAt: new Date().toISOString(),
        match: JSON.parse(JSON.stringify(match)),
        events: JSON.parse(JSON.stringify(coachState.events || [])),
        ratings: JSON.parse(JSON.stringify(coachState.ratings || [])),
        report: coachState.report || "",
        homeGoals: getGoals("home"),
        awayGoals: getGoals("away")
    };
}

function saveCurrentMatchToHistory(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }

    const history = loadHistory();
    const limits = getCoachLimits();

    if(!isCoachPro() && history.length >= limits.maxHistory){
        showCoachProNotice("Storico Coach completo");
        return;
    }

    if(!coachState.report){
        generateCoachReport();
    }

    const item = buildHistoryItem();
    if(!item) return;

    history.unshift(item);
    saveHistory(history);

    trackCoachFeature("coach_history", {
        events: coachState.events.length,
        ratings: coachState.ratings.length,
        has_report: Boolean(coachState.report)
    });

    renderHistory();
    renderStatus();

    if(isCoachPro()){
        showNotice("Partita salvata nello storico Coach.", "ok");
    }else{
        showNotice(`Partita salvata nello storico Coach. Free: ${loadHistory().length}/${limits.maxHistory}.`, "ok", 4500);
    }
}

function clearCoachHistory(){
    if(!confirm("Vuoi svuotare tutto lo storico Coach?")) return;

    localStorage.removeItem(HISTORY_KEY);

    renderHistory();
    renderStatus();
    showNotice("Storico Coach svuotato.", "ok");
}

async function copyHistoryReport(historyId){
    const item = loadHistory().find(x => String(x.id) === String(historyId));

    if(!item || !item.report){
        showNotice("Report storico non disponibile.", "warn");
        return;
    }

    const plain = String(item.report).replace(/<[^>]*>/g, "");

    try{
        await navigator.clipboard.writeText(plain);
        showNotice("Report storico copiato.", "ok");
    }catch{
        showNotice("Non riesco a copiare automaticamente.", "warn");
    }
}

function reopenHistoryMatch(historyId){
    const item = loadHistory().find(x => String(x.id) === String(historyId));

    if(!item){
        showNotice("Partita storica non trovata.", "warn");
        return;
    }

    coachState = {
        match: item.match || null,
        events: Array.isArray(item.events) ? item.events : [],
        ratings: Array.isArray(item.ratings) ? item.ratings : [],
        report: item.report || ""
    };

    saveState();
    renderAll();

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

    showNotice("Partita riaperta dallo storico.", "ok");
}

function deleteHistoryMatch(historyId){
    if(!confirm("Vuoi eliminare questa partita dallo storico?")) return;

    const history = loadHistory().filter(x => String(x.id) !== String(historyId));
    saveHistory(history);

    renderHistory();
    renderStatus();
    showNotice("Partita eliminata dallo storico.", "ok");
}
