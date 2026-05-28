function renderStatus(){
    const match = coachState.match;

    const activeMatchName = document.getElementById("activeMatchName");
    const scoreHomeName = document.getElementById("scoreHomeName");
    const scoreAwayName = document.getElementById("scoreAwayName");
    const scoreValue = document.getElementById("scoreValue");
    const activeCategory = document.getElementById("activeCategory");
    const lastEventText = document.getElementById("lastEventText");

    const homeGoals = getGoals("home");
    const awayGoals = getGoals("away");

    if(activeMatchName){
        activeMatchName.textContent = match
            ? `${match.homeTeam} vs ${match.awayTeam}`
            : "Nessuna partita creata";
    }

    if(scoreHomeName) scoreHomeName.textContent = match?.homeTeam || "Casa";
    if(scoreAwayName) scoreAwayName.textContent = match?.awayTeam || "Trasferta";
    if(scoreValue) scoreValue.textContent = `${homeGoals} - ${awayGoals}`;
    if(activeCategory) activeCategory.textContent = match?.category || "--";

    if(lastEventText){
        const last = coachState.events[0];
        lastEventText.textContent = last
            ? `${last.icon} ${last.label} · ${last.team} · ${last.minute}'`
            : "Nessun evento";
    }

    const kpiEvents = document.getElementById("kpiEvents");
    const kpiHomeGoals = document.getElementById("kpiHomeGoals");
    const kpiAwayGoals = document.getElementById("kpiAwayGoals");
    const kpiSavedMatches = document.getElementById("kpiSavedMatches");

    if(kpiEvents) kpiEvents.textContent = coachState.events.length;
    if(kpiHomeGoals) kpiHomeGoals.textContent = homeGoals;
    if(kpiAwayGoals) kpiAwayGoals.textContent = awayGoals;
    if(kpiSavedMatches) kpiSavedMatches.textContent = loadHistory().length;
}

function renderTimeline(){
    const box = document.getElementById("eventsTimeline");
    if(!box) return;

    if(!coachState.events.length){
        box.innerHTML = `
            <div class="empty">
                Nessun evento registrato. Crea una partita e usa i bottoni rapidi durante il match.
            </div>
        `;
        return;
    }

    box.innerHTML = coachState.events
        .map(e => `
            <div class="event-card">
                <div class="event-minute">${esc(e.minute)}'</div>

                <div>
                    <div class="event-title">${esc(e.icon)} ${esc(e.label)}</div>
                    <div class="event-meta">
                        ${esc(e.team)}${e.player ? " · " + esc(e.player) : ""}
                    </div>
                    ${e.note ? `<div class="event-note">${esc(e.note)}</div>` : ""}
                </div>

                <button class="delete-event" onclick="deleteEvent('${esc(e.id)}')">×</button>
            </div>
        `)
        .join("");
}

function renderRatings(){
    const box = document.getElementById("ratingsList");
    if(!box) return;
    if(!coachState.ratings.length){
        box.innerHTML = `<div class="empty">Nessuna pagella inserita. Aggiungi almeno un giocatore per arricchire il report.</div>`;
        return;
    }
    box.innerHTML = coachState.ratings.map(r => {
        const vote = Number(r.vote || 0);
        const voteClass = vote >= 7 ? "high" : vote < 6 ? "low" : "";
        return `
            <div class="rating-card">
                <div>
                    <div class="rating-player">${esc(r.player)}</div>
                    <div class="rating-meta">${esc(r.team)} · ${esc(r.role)}</div>
                    ${r.note ? `<div class="rating-note">${esc(r.note)}</div>` : ""}
                    <div class="rating-actions"><button class="rating-remove" onclick="deleteRating('${esc(r.id)}')">Elimina</button></div>
                </div>
                <div class="rating-vote ${voteClass}">${esc(r.vote)}</div>
            </div>`;
    }).join("");
}

function renderReport(){
    const box = document.getElementById("coachReport");
    if(!box) return;

    box.innerHTML = coachState.report || "Crea una partita, registra alcuni eventi e premi “Genera report”.";
}

function renderHistory(){
    const box = document.getElementById("coachHistoryList");
    if(!box) return;

    const history = loadHistory();
    if(!history.length){
        box.innerHTML = `<div class="empty">Nessuna partita salvata. Genera un report e premi “Salva nello storico”.</div>`;
        return;
    }

    box.innerHTML = history.map(item => {
        const m = item.match || {};
        const saved = item.savedAt ? new Date(item.savedAt).toLocaleDateString("it-IT") : "--";
        const title = `${m.homeTeam || "Casa"} vs ${m.awayTeam || "Trasferta"}`;
        return `
            <div class="history-card">
                <div class="history-top">
                    <div class="history-title">${esc(title)}</div>
                    <div class="history-date">${esc(saved)}</div>
                </div>
                <div class="history-meta">
                    ${esc(m.category || "Dilettanti")} · Risultato eventi ${esc(item.homeGoals ?? 0)}-${esc(item.awayGoals ?? 0)} ·
                    ${esc((item.events || []).length)} eventi · ${esc((item.ratings || []).length)} pagelle
                </div>
                <div class="history-actions">
                    <button class="green" onclick="openHistoryMatch('${esc(item.id)}')">Riapri</button>
                    <button onclick="copyHistoryReport('${esc(item.id)}')">Copia report</button>
                    <button class="red" onclick="deleteHistoryMatch('${esc(item.id)}')">Elimina</button>
                </div>
            </div>
        `;
    }).join("");
}

function renderAll(){
    fillFormFromState();
    renderStatus();
    renderTimeline();
    renderRatings();
    renderReport();
    renderHistory();
}
