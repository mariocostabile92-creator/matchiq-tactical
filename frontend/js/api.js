/*
    MatchIQ - Match API Module
    Gestisce caricamento partita, cache locale, refresh live e fallback API.
*/

function calculateAdaptiveRefresh(data){
    /*
        Refresh adattivo con protezione consumo API.
        Non aggiunge nuove chiamate: decide solo ogni quanti secondi aggiornare.
    */
    const m=data?.match||{};
    const minute=safeNumber(m.minute,0);
    const status=String(m.status||m.fixture_status||m.elapsed_status||"").toUpperCase();

    if(API_USAGE_PERCENT>=95)return 300;
    if(API_USAGE_PERCENT>=85)return 120;
    if(API_USAGE_PERCENT>=70)return 75;
    if(API_USAGE_PERCENT>=50)return 45;

    if(status.includes("FT")||status.includes("FINISHED")||minute>=90)return 120;
    if(status.includes("HT")||status.includes("BREAK"))return 60;
    if(minute>=80)return 18;
    if(minute>=60)return 25;
    return 30;
}

function updateLiveBadge(){
    const liveText=document.getElementById("liveUpdateText");
    const timerText=document.getElementById("refreshTimerText");
    const badge=document.querySelector(".live-badge");

    if(badge){
        badge.classList.toggle("cache-mode",cacheModeActive && API_USAGE_PERCENT<95);
        badge.classList.toggle("critical-mode",API_USAGE_PERCENT>=95);
    }

    let modeLabel="LIVE UPDATE";
    if(API_USAGE_PERCENT>=95)modeLabel="CACHE ONLY MODE";
    else if(cacheModeActive)modeLabel="OFFLINE CACHE MODE";
    else if(API_USAGE_PERCENT>=85)modeLabel="CRITICAL SAFE MODE";
    else if(API_USAGE_PERCENT>=70)modeLabel="API SAFE MODE";
    else if(API_USAGE_PERCENT>=50)modeLabel="SMART SAFE MODE";

    if(liveText){
        liveText.textContent=lastUpdateAt
            ? `${modeLabel} • Updated ${Math.max(0,Math.round((Date.now()-lastUpdateAt)/1000))}s ago`
            : modeLabel;
    }

    if(timerText){
        timerText.textContent=`Next refresh ${countdownValue}s`;
    }
}

function restartSmartRefresh(seconds){
    countdownValue=seconds;

    if(refreshInterval)clearInterval(refreshInterval);
    if(countdownInterval)clearInterval(countdownInterval);

    refreshInterval=setInterval(()=>{
        if(!document.hidden)loadMatch({silent:true});
    },seconds*1000);

    countdownInterval=setInterval(()=>{
        if(document.hidden)return;
        countdownValue=Math.max(0,countdownValue-1);
        updateLiveBadge();
        if(countdownValue===0)countdownValue=seconds;
    },1000);

    updateLiveBadge();
}

function saveLastValidData(data){
    try{
        const payload={
            savedAt:Date.now(),
            data
        };
        localStorage.setItem(CACHE_KEY,JSON.stringify(payload));
        localStorage.setItem(CACHE_TIME_KEY,String(Date.now()));
        lastValidData=data;
    }catch(e){
        console.warn("Cache MatchIQ non salvata:",e);
    }
}

function loadLastValidData(){
    try{
        const raw=localStorage.getItem(CACHE_KEY);
        if(!raw)return null;
        const payload=JSON.parse(raw);
        return payload?.data||null;
    }catch(e){
        console.warn("Cache MatchIQ non leggibile:",e);
        return null;
    }
}

function renderCachedDataIfAvailable(){
    const cached=lastValidData||loadLastValidData();
    if(!cached)return false;

    cacheModeActive=true;
    render(cached);
    lastUpdateAt=Number(localStorage.getItem(CACHE_TIME_KEY))||Date.now();
    updateLiveBadge();

    return true;
}

async function manualRefresh(){
    await loadMatch({silent:false,force:true});
}

async function loadMatch({silent=false,force=false}={}){
    if(!matchId){
        showError("ID partita mancante.");
        return;
    }

    if(isRefreshing&&!force)return;

    /*
        Se consumo API è critico, non chiamiamo il backend:
        usiamo direttamente cache/fallback.
    */
    if(API_USAGE_PERCENT>=95&&!force){
        if(renderCachedDataIfAvailable()){
            restartSmartRefresh(calculateAdaptiveRefresh(lastValidData));
            return;
        }
    }

    isRefreshing=true;
    cacheModeActive=false;
    updateLiveBadge();

    try{
        const r=await fetch(`${API_BASE}/match/${matchId}/full-analysis`,{
            cache:"no-store"
        });

        if(!r.ok)throw new Error("HTTP "+r.status);

        const data=await r.json();

        if(data.error){
            throw new Error(data.error);
        }

        saveLastValidData(data);
        cacheModeActive=false;
        render(data);
        lastUpdateAt=Date.now();
        restartSmartRefresh(calculateAdaptiveRefresh(data));

    }catch(e){
        console.error("MatchIQ live API fallback:",e);

        const hasCache=renderCachedDataIfAvailable();

        if(!hasCache){
            if(!silent)showError("Errore caricamento match e nessuna cache disponibile. Controlla backend/API.");
        }else{
            restartSmartRefresh(60);
        }
    }finally{
        isRefreshing=false;
        updateLiveBadge();
    }
}

function showError(msg){
    const app=document.getElementById("app");
    if(app){
        const box=document.createElement("div");
        box.className="error-box";
        box.textContent=`Errore: ${String(msg||"Operazione non riuscita")}`;
        app.replaceChildren(box);
    }
}
