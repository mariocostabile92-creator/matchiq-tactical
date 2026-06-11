function getCoachLimitText(){
    const limits = getCoachLimits();

    if(isCoachPro()){
        return {
            plan: "PRO",
            ratings: "Pagelle sbloccate",
            history: `Storico ${loadHistory().length}/${limits.maxHistory}`,
            pdf: "PDF sbloccati",
            whatsapp: "WhatsApp sbloccato"
        };
    }

    return {
        plan: "FREE",
        ratings: `Pagelle ${coachState.ratings.length}/${limits.maxRatings}`,
        history: `Storico ${loadHistory().length}/${limits.maxHistory}`,
        pdf: getCoachPdfUsageText(),
        whatsapp: getCoachWhatsappUsageText()
    };
}

function renderCoachPlanBadges(){
    const data = getCoachLimitText();

    const existing = document.getElementById("coachPlanBadges");
    if(existing){
        existing.remove();
    }

    const heroCard = document.querySelector(".hero-card");
    if(!heroCard) return;

    const box = document.createElement("div");
    box.id = "coachPlanBadges";
    box.className = "micro-row";
    box.innerHTML = `
        <span>${esc(data.plan)}</span>
        <span>${esc(data.ratings)}</span>
        <span>${esc(data.history)}</span>
        <span>${esc(data.pdf)}</span>
        <span>${esc(data.whatsapp)}</span>
    `;

    heroCard.appendChild(box);
}

function renderCoachPlanCard(){
    const data = getCoachLimitText();

    const badge = document.getElementById("coachPlanBadgeLarge");
    const title = document.getElementById("coachPlanTitle");
    const desc = document.getElementById("coachPlanDescription");
    const ratings = document.getElementById("planLimitRatings");
    const history = document.getElementById("planLimitHistory");
    const pdf = document.getElementById("planLimitPdf");
    const whatsapp = document.getElementById("planLimitWhatsapp");
    const upgrade = document.getElementById("coachUpgradeBtn");

    if(badge){
        badge.textContent = isCoachPro() ? "PIANO PRO ATTIVO" : "PIANO FREE";
        badge.className = isCoachPro() ? "badge green" : "badge gold";
    }

    if(title){
        title.textContent = isCoachPro() ? "Coach Pro sbloccato" : "Stai usando Coach Free";
    }

    if(desc){
        desc.textContent = getCoachPlanDescription();
    }

    if(ratings) ratings.textContent = data.ratings;
    if(history) history.textContent = data.history;
    if(pdf) pdf.textContent = data.pdf;
    if(whatsapp) whatsapp.textContent = data.whatsapp;

    if(upgrade){
        upgrade.style.display = isCoachPro() ? "none" : "inline-flex";
    }
}

function renderReportButtonsState(){
    const pdfButtons = document.querySelectorAll('[onclick="printCoachPdf()"]');
    const whatsappButtons = document.querySelectorAll('[onclick="copyWhatsAppSummary()"]');

    pdfButtons.forEach(btn => {
        if(!canUseCoachPdf()){
            btn.innerHTML = "🔒 Scarica PDF";
            btn.title = "Prova gratuita usata. Passa a Pro per PDF sbloccati.";
        }else{
            btn.innerHTML = isCoachPro()
                ? "Scarica PDF"
                : "Scarica PDF · prova";
            btn.title = isCoachPro()
                ? ""
                : "Hai 1 esportazione PDF gratuita.";
        }
    });

    whatsappButtons.forEach(btn => {
        if(!canUseCoachWhatsapp()){
            btn.innerHTML = "🔒 Copia WhatsApp";
            btn.title = "Prova gratuita usata. Passa a Pro per WhatsApp sbloccato.";
        }else{
            btn.innerHTML = isCoachPro()
                ? "Copia WhatsApp"
                : "Copia WhatsApp · prova";
            btn.title = isCoachPro()
                ? ""
                : "Hai 1 copia WhatsApp gratuita.";
        }
    });
}

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

    renderCoachPlanBadges();
    renderCoachPlanCard();
    renderReportButtonsState();
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

    const limits = getCoachLimits();

    if(!coachState.ratings.length){
        box.innerHTML = `
            <div class="empty">
                Nessuna pagella inserita. 
                ${isCoachPro() ? "Piano Pro: pagelle sbloccate." : `Piano Free: massimo ${limits.maxRatings} pagelle.`}
            </div>
        `;
        return;
    }

    const limitHint = isCoachPro()
        ? `<div class="empty" style="padding:12px;margin-bottom:10px;">PRO attivo: pagelle sbloccate.</div>`
        : `<div class="empty" style="padding:12px;margin-bottom:10px;">FREE: ${coachState.ratings.length}/${limits.maxRatings} pagelle usate.</div>`;

    const cards = coachState.ratings.map(r => {
        const vote = Number(r.vote || 0);
        const voteClass = vote >= 7 ? "high" : vote < 6 ? "low" : "";

        return `
            <div class="rating-card">
                <div>
                    <div class="rating-player">${esc(r.player)}</div>
                    <div class="rating-meta">${esc(r.team)} · ${esc(r.role)}</div>
                    ${r.note ? `<div class="rating-note">${esc(r.note)}</div>` : ""}
                    <div class="rating-actions">
                        <button class="rating-remove" onclick="deleteRating('${esc(r.id)}')">Elimina</button>
                    </div>
                </div>
                <div class="rating-vote ${voteClass}">${esc(r.vote)}</div>
            </div>`;
    }).join("");

    box.innerHTML = limitHint + cards;
}

function renderReport(){
    const box = document.getElementById("coachReport");
    if(!box) return;

    box.innerHTML = coachState.report || "Crea una partita, registra alcuni eventi e premi “Genera report”.";

    renderReportButtonsState();
}

function renderHistory(){
    const box = document.getElementById("coachHistoryList");
    if(!box) return;

    const history = loadHistory();
    const limits = getCoachLimits();

    if(!history.length){
        box.innerHTML = `
            <div class="empty">
                Nessuna partita salvata. 
                ${isCoachPro() ? `Piano Pro: fino a ${limits.maxHistory} partite.` : `Piano Free: massimo ${limits.maxHistory} partite salvate.`}
            </div>
        `;
        return;
    }

    const limitHint = isCoachPro()
        ? `<div class="empty" style="padding:12px;margin-bottom:10px;">PRO attivo: storico ${history.length}/${limits.maxHistory}.</div>`
        : `<div class="empty" style="padding:12px;margin-bottom:10px;">FREE: storico ${history.length}/${limits.maxHistory}. Storico esteso incluso in Pro.</div>`;

    const cards = history.map(item => {
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
                    <button class="green" onclick="reopenHistoryMatch('${esc(item.id)}')">Riapri</button>
                    <button onclick="copyHistoryReport('${esc(item.id)}')">Copia report</button>
                    <button class="red" onclick="deleteHistoryMatch('${esc(item.id)}')">Elimina</button>
                </div>
            </div>
        `;
    }).join("");

    box.innerHTML = limitHint + cards;
}

function renderAll(){
    ensureCoachStateShape();
    fillFormFromState();
    renderStatus();
    if(typeof renderLineup === "function") renderLineup();
    renderTimeline();
    renderRatings();
    renderReport();
    renderHistory();
    renderCoachPlanCard();
}

function coachPlanRenderRetryV162(){
    try{
        renderAll();
    }catch(e){
        console.warn("Coach render retry non riuscito:", e);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(coachPlanRenderRetryV162, 150);
    setTimeout(coachPlanRenderRetryV162, 700);
});


/* Coach Lineup V1.7 */
function renderLineupList(side){
    const box = document.getElementById(side === "home" ? "homeLineupList" : "awayLineupList");
    if(!box) return;

    const list = getLineupBySide(side);

    if(!list.length){
        box.innerHTML = `<div class="lineup-empty">Nessun giocatore ${side === "home" ? "casa" : "trasferta"} inserito.</div>`;
        return;
    }

    const sorted = [...list].sort((a,b) => {
        const sa = a.status === "Titolare" ? 0 : 1;
        const sb = b.status === "Titolare" ? 0 : 1;
        if(sa !== sb) return sa - sb;
        return Number(a.number || 999) - Number(b.number || 999);
    });

    box.innerHTML = sorted.map(p => `
        <div class="lineup-player-card">
            <div class="lineup-number">${esc(p.number || "-")}</div>
            <div>
                <div class="lineup-name">${esc(p.name)}</div>
                <div class="lineup-meta">${esc(p.role || "Jolly")} · ${esc(p.status || "Titolare")}</div>
            </div>
            <button class="lineup-remove" onclick="deleteLineupPlayer('${esc(p.id)}')">×</button>
        </div>
    `).join("");
}

function renderEventPlayerSelect(){
    const select = document.getElementById("eventPlayerSelectInput");
    if(!select) return;

    const currentSide = getInputValue("eventTeamInput","home");
    const currentValue = select.value;
    const players = getLineupBySide(currentSide);

    select.innerHTML = `<option value="">Seleziona giocatore</option>` + players.map(p => `
        <option value="${esc(p.id)}">${esc(formatLineupPlayer(p))} · ${esc(p.role || "Jolly")}</option>
    `).join("");

    if(players.some(p => String(p.id) === String(currentValue))){
        select.value = currentValue;
    }
}

function renderRatingLineupHint(){
    const box = document.getElementById("ratingLineupQuickList");
    if(!box) return;

    const players = getLineup();

    if(!players.length){
        box.innerHTML = `<div class="lineup-empty">Inserisci la formazione per compilare più velocemente le pagelle.</div>`;
        return;
    }

    box.innerHTML = players.slice(0,18).map(p => `
        <button class="btn dark" type="button" onclick="syncRatingPlayerFromLineup('${esc(p.id)}')">${esc(formatLineupPlayer(p))}</button>
    `).join("");
}

function renderLineup(){
    renderLineupList("home");
    renderLineupList("away");
    renderEventPlayerSelect();
    renderRatingLineupHint();
    renderLineupPitch();
}

/* Coach Lineup Pitch V1.7.7 */
function getPitchPosition(player, index, total){
    const role = String(player.role || "Jolly").toLowerCase();
    const rowMap = {
        "portiere": 88,
        "difensore": 70,
        "centrocampista": 52,
        "esterno": 38,
        "attaccante": 20,
        "jolly": 50
    };

    let y = rowMap[role] || 50;

    const sameRole = getLineupBySide(player.side)
        .filter(p => p.status === "Titolare" && String(p.role || "Jolly").toLowerCase() === role);

    const roleIndex = sameRole.findIndex(p => String(p.id) === String(player.id));
    const roleTotal = Math.max(1, sameRole.length);

    let x = 50;
    if(roleTotal === 1) x = 50;
    else{
        const spread = Math.min(68, 18 + roleTotal * 13);
        x = 50 - (spread / 2) + (spread / (roleTotal - 1)) * roleIndex;
    }

    if(role === "esterno" && roleTotal === 1){
        x = 28;
    }

    const side = normalizeLineupSide(player.side, player);
    return {
        x,
        y: side === "away" ? 100 - y : y
    };
}

function renderLineupPitch(){
    const pitch = document.getElementById("lineupPitch");
    const bench = document.getElementById("lineupBench");
    const homeTab = document.getElementById("pitchTabHome");
    const awayTab = document.getElementById("pitchTabAway");

    if(homeTab) homeTab.classList.add("active");
    if(awayTab) awayTab.classList.add("active");

    if(!pitch) return;

    const players = typeof getLineup === "function" ? getLineup() : [];
    const starters = players.filter(p => p.status !== "Panchina");
    const benchPlayers = players.filter(p => p.status === "Panchina");

    const teamLabel = `${getTeamName("home")} vs ${getTeamName("away")}`;
    const fieldLabel = getMatchField();

    const base = `
        <div class="pitch-half-line"></div>
        <div class="pitch-box-top"></div>
        <div class="pitch-box-bottom"></div>
        <div class="pitch-empty-state" style="top:10%;font-size:12px;opacity:.78;">
            ${esc(teamLabel)} Â· ${esc(fieldLabel)}
        </div>
    `;

    if(!starters.length){
        pitch.innerHTML = base + `<div class="pitch-empty-state">Aggiungi titolari casa e trasferta per vedere la formazione sul campo.</div>`;
    }else{
        pitch.innerHTML = base + starters.map((p, index) => {
            const pos = getPitchPosition(p, index, starters.length);
            const side = normalizeLineupSide(p.side, p);
            return `
                <div class="pitch-player ${esc(side)}" style="left:${pos.x}%;top:${pos.y}%;">
                    <div class="pitch-shirt">${esc(p.number || "-")}</div>
                    <div class="pitch-name">${esc(p.name)}</div>
                    <div class="pitch-role">${esc(p.role || "Jolly")}</div>
                </div>
            `;
        }).join("");
    }

    if(bench){
        bench.innerHTML = benchPlayers.length
            ? benchPlayers.map(p => `<span class="bench-chip">${esc(formatLineupPlayer(p))} · ${esc(p.role || "Jolly")}</span>`).join("")
            : `<span class="bench-chip">Nessun panchinaro</span>`;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const teamSelect = document.getElementById("eventTeamInput");
    if(teamSelect){
        teamSelect.addEventListener("change", () => {
            setInputValue("eventPlayerSelectInput","");
            setInputValue("eventPlayerInput","");
            renderEventPlayerSelect();
        });
    }
});
