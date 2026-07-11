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
                    ${Array.isArray(e.tags) && e.tags.length ? `<div class="event-tags">${e.tags.map(tag => `<span>${esc(tag)}</span>`).join("")}</div>` : ""}
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
                    ${esc(m.category || "Dilettanti")} · Risultato eventi ${esc(item.homeGoals - 0)}-${esc(item.awayGoals - 0)} ·
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

function buildCoachLiveInsights(){
    ensureCoachStateShape();
    const tips = [];
    const lastEvents = coachState.events.slice(0,8);
    const lostHome = getEventCount("palla_persa","home");
    const lostAway = getEventCount("palla_persa","away");
    const defHome = getEventCount("errore_difensivo","home");
    const defAway = getEventCount("errore_difensivo","away");
    const shotsHome = getEventCount("tiro","home") + getEventCount("occasione","home");
    const shotsAway = getEventCount("tiro","away") + getEventCount("occasione","away");
    const recoveries = getEventCount("recupero");
    const recentLost = lastEvents.filter(e => e.type === "palla_persa").length;
    const recentDef = lastEvents.filter(e => e.type === "errore_difensivo").length;

    if(recentLost >= 2) tips.push({level:"warn", title:"Transizioni da controllare", text:"Negli ultimi eventi ci sono piu palle perse. Segna zona e lato: servira nel report."});
    if(recentDef >= 1) tips.push({level:"danger", title:"Coperture preventive", text:"Hai registrato un errore difensivo recente. Controlla distanze tra difesa e centrocampo."});
    if(lostHome >= 3) tips.push({level:"warn", title:getTeamName("home"), text:"Troppe palle perse registrate: utile lavorare su scelta semplice e sostegno vicino."});
    if(lostAway >= 3) tips.push({level:"warn", title:getTeamName("away"), text:"Troppe palle perse registrate: probabile fase di uscita o transizione da rivedere."});
    if(defHome >= 2) tips.push({level:"danger", title:getTeamName("home"), text:"Due errori difensivi: inserisci nota su marcature, seconde palle o linea."});
    if(defAway >= 2) tips.push({level:"danger", title:getTeamName("away"), text:"Due errori difensivi: possibile tema forte per il report post partita."});
    if(shotsHome + shotsAway <= 1 && coachState.events.length >= 5) tips.push({level:"info", title:"Produzione offensiva bassa", text:"Poche occasioni registrate. Valuta ampiezza, riempimento area e ultimo passaggio."});
    if(recoveries >= 4) tips.push({level:"ok", title:"Pressing utile", text:"Molti recuperi palla: segnalo come punto positivo e tema da consolidare."});

    if(!tips.length){
        tips.push({level:"info", title:"Assistente pronto", text:"Registra 4-5 eventi e MatchIQ iniziera a leggere pattern utili per il mister."});
    }

    return tips.slice(0,4);
}

function getCoachEventSummary(){
    return {
        lostHome:getEventCount("palla_persa","home"),
        lostAway:getEventCount("palla_persa","away"),
        defHome:getEventCount("errore_difensivo","home"),
        defAway:getEventCount("errore_difensivo","away"),
        chancesHome:getEventCount("occasione","home") + getEventCount("tiro","home"),
        chancesAway:getEventCount("occasione","away") + getEventCount("tiro","away"),
        recoveriesHome:getEventCount("recupero","home"),
        recoveriesAway:getEventCount("recupero","away"),
        pressing:getEventCount("pressing"),
        transitions:getEventCount("transizione"),
        width:getEventCount("ampiezza"),
        secondBalls:getEventCount("seconda_palla"),
        longTeam:getEventCount("squadra_lunga"),
        sideBuild:getEventCount("uscita_lato"),
        depth:getEventCount("profondita"),
        communication:getEventCount("comunicazione")
    };
}

function buildCoachHalftimeTalk(){
    ensureCoachStateShape();
    const s = getCoachEventSummary();
    const talk = [];
    const home = getTeamName("home");
    const away = getTeamName("away");

    if(s.lostHome >= 2) talk.push(`${home}: uscita palla da semplificare, serve piu sostegno vicino e meno forzature centrali.`);
    if(s.lostAway >= 2) talk.push(`${away}: perdita palla ricorrente, possibile tema da attaccare con pressione orientata.`);
    if(s.defHome >= 1) talk.push(`${home}: controllare linea difensiva, marcature preventive e distanza tra difesa e centrocampo.`);
    if(s.defAway >= 1) talk.push(`${away}: spazio alle spalle o coperture fragili, insistiamo sulle corse in profondita.`);
    if(s.chancesHome + s.chancesAway <= 1 && coachState.events.length >= 4) talk.push("Poche occasioni: chiedere piu ampiezza, attacco area e ultimo passaggio piu pulito.");
    if(s.recoveriesHome >= 3) talk.push(`${home}: pressing utile, dopo recupero serve prima giocata in avanti.`);
    if(s.recoveriesAway >= 3) talk.push(`${away}: recupera molti palloni, serve uscire dalla pressione con appoggio e cambio lato.`);
    if(s.width >= 1) talk.push("Tema ampiezza presente: verificare se il vantaggio nasce su lato forte o cambio gioco.");
    if(s.secondBalls >= 1) talk.push("Seconde palle decisive: alzare aggressivita e accorciare subito dopo il duello.");
    if(s.longTeam >= 1) talk.push("Squadra lunga: accorciare reparti e proteggere meglio la zona centrale.");
    if(s.sideBuild >= 1) talk.push("Uscita laterale da pulire: dare sostegno vicino e terzo uomo.");
    if(s.depth >= 1) talk.push("Profondita efficace: continuare a minacciare lo spazio alle spalle.");
    if(s.communication >= 1) talk.push("Comunicazione da alzare: guida della linea e chiamate preventive.");

    if(!talk.length){
        talk.push("Primo messaggio: restare ordinati, comunicare di piu e registrare 3-4 episodi chiave per far leggere meglio la gara a MatchIQ.");
    }

    return talk.slice(0,5);
}

function buildCoachAssistantQuestions(){
    ensureCoachStateShape();
    const questions = [];
    const last = coachState.events[0];
    if(last?.aiPrompt) questions.push(last.aiPrompt);

    const s = getCoachEventSummary();
    if(s.lostHome + s.lostAway >= 2) questions.push("Vuoi segnare il lato dove perdiamo piu palloni: destra, sinistra o centrale?");
    if(s.defHome + s.defAway >= 1) questions.push("Vuoi aggiungere se il problema e linea bassa, marcatura o copertura preventiva?");
    if(s.pressing >= 1) questions.push("Il pressing funziona meglio alto, medio o dopo palla persa?");
    if(s.chancesHome + s.chancesAway === 0 && coachState.events.length >= 5) questions.push("Vuoi segnare perche non arrivano occasioni: ampiezza, profondita o rifinitura?");

    if(!questions.length){
        questions.push("Registra una nota vocale naturale: MatchIQ prova a trasformarla in evento tattico.");
    }

    return [...new Set(questions)].slice(0,4);
}

function buildCoachReminders(){
    const s = getCoachEventSummary();
    const reminders = [];
    if(s.lostHome + s.lostAway >= 3) reminders.push("Tema ricorrente: troppe palle perse. Inseriscilo nelle priorita allenamento.");
    if(s.defHome + s.defAway >= 2) reminders.push("Tema ricorrente: errori difensivi. Aggiungi lavoro su coperture preventive.");
    if(s.secondBalls >= 2) reminders.push("Tema ricorrente: seconde palle. Programma esercizio su duelli e riaggressione.");
    if(s.longTeam >= 1) reminders.push("Tema tattico: squadra lunga. Lavora su distanze tra reparti e coperture.");
    if(s.sideBuild >= 1) reminders.push("Tema tattico: uscita laterale. Prepara esercizio su sostegno, terzo uomo e cambio gioco.");
    if(s.communication >= 1) reminders.push("Tema mentale: comunicazione. Inserisci richiami su guida, marcature e responsabilita.");
    if(s.chancesHome + s.chancesAway <= 1 && coachState.events.length >= 6) reminders.push("Tema ricorrente: poca produzione offensiva. Lavora su ampiezza e riempimento area.");
    if(s.pressing >= 2 || s.recoveriesHome + s.recoveriesAway >= 4) reminders.push("Punto forte: pressing e recupero palla. Trasformalo in principio stabile.");
    if(!reminders.length) reminders.push("Nessun tema ricorrente forte: continua a registrare eventi e note vocali.");
    return reminders.slice(0,5);
}

function getCoachTagMemory(){
    ensureCoachStateShape();
    const counts = new Map();
    const addTag = tag => {
        const clean = String(tag || "").trim();
        if(!clean) return;
        counts.set(clean, (counts.get(clean) || 0) + 1);
    };
    const readTags = e => {
        const tags = Array.isArray(e.tags) && e.tags.length ? e.tags : (typeof getCoachEventTags === "function" ? getCoachEventTags(e) : []);
        tags.forEach(addTag);
    };
    coachState.events.forEach(readTags);
    loadHistory().forEach(h => (h.events || []).forEach(readTags));
    return [...counts.entries()].sort((a,b) => b[1] - a[1]).slice(0,8).map(([tag,count]) => ({tag,count}));
}

function buildTeamMemory(){
    const tags = getCoachTagMemory();
    const history = loadHistory();
    const notes = [];
    if(tags.length) notes.push(`Tema piu ricorrente: ${tags[0].tag} (${tags[0].count} segnali tra partita e storico).`);
    if(history.length) notes.push(`Storico attivo: ${history.length} partite salvate, utile per capire se il problema si ripete.`);
    if(coachState.events.length >= 6) notes.push("Partita corrente gia leggibile: gli eventi sono sufficienti per una prima sintesi staff.");
    if(!notes.length) notes.push("Inserisci eventi e note vocali: MatchIQ iniziera a costruire memoria squadra.");
    return {tags, notes};
}

function buildTrainingPlan(){
    const s = getCoachEventSummary();
    const plan = [];
    const push = (title, drill, target) => plan.push({title, drill, target});
    if(s.lostHome + s.lostAway >= 2) push("Possesso sotto pressione", "Rondo posizionale 6v3 con uscita pulita e terzo uomo.", "Ridurre palla persa e forzature centrali.");
    if(s.defHome + s.defAway >= 1 || s.longTeam >= 1) push("Linea e coperture", "Reparto difensivo + centrocampo su scivolamenti, palla scoperta e copertura preventiva.", "Tenere squadra corta e proteggere profondita.");
    if(s.secondBalls >= 1) push("Seconde palle", "Duello, accorcio immediato e prima giocata dopo recupero.", "Vincere rimbalzi e riaggressione.");
    if(s.width >= 1 || s.chancesHome + s.chancesAway <= 1) push("Ampiezza e rifinitura", "Sviluppo lato forte, cambio lato e attacco area con tre riferimenti.", "Creare piu soluzioni negli ultimi metri.");
    if(s.pressing >= 1 || s.recoveriesHome + s.recoveriesAway >= 3) push("Pressing organizzato", "Trigger di pressione su retropassaggio, controllo orientato male e palla laterale.", "Trasformare recupero in occasione.");
    if(s.communication >= 1) push("Comunicazione reparto", "Situazionale con chiamate obbligatorie: uomo, solo, sali, copri.", "Aumentare guida e responsabilita.");
    if(!plan.length) push("Seduta base MatchIQ", "20 minuti possesso, 20 transizioni, 20 finalizzazione.", "Dare continuita ai principi senza sovraccaricare.");
    return plan.slice(0,4);
}

function renderCoachPrecheck(){
    if(typeof fillCoachPrecheckFromState === "function") fillCoachPrecheckFromState();
    const box = document.getElementById("coachPrecheckStatus");
    if(!box) return;
    const pre = coachState.memory?.precheck || {};
    const filled = Object.values(pre).filter(Boolean).length;
    const starters = getLineup().filter(p => p.status === "Titolare").length;
    const bench = getLineup().filter(p => p.status === "Panchina").length;
    const ready = Boolean(coachState.match) && starters > 0 && filled >= 2;
    box.innerHTML = filled
        ? `<strong>${ready ? "Pronto per il Match Day" : `${filled}/5`}</strong><span>${ready ? `Partita creata, ${starters} titolari e ${bench} riserve inserite. Puoi avviare la console live.` : " punti pre-partita salvati nella memoria MatchIQ. Completa setup e formazione prima della gara."}</span>`
        : `<strong>0/5</strong><span>Completa la checklist prima della gara per guidare meglio l'AI.</span>`;
}

function renderTeamMemory(){
    const box = document.getElementById("teamMemoryList");
    if(!box) return;
    const memory = buildTeamMemory();
    const tagHtml = memory.tags.length
        ? `<div class="memory-tags">${memory.tags.map(item => `<span>${esc(item.tag)} <strong>${esc(item.count)}</strong></span>`).join("")}</div>`
        : `<div class="empty">Nessun tag tattico ancora disponibile.</div>`;
    box.innerHTML = `${tagHtml}<div class="memory-note-list">${memory.notes.map(note => `<div class="coach-ai-tip ok"><strong>Memoria squadra</strong><span>${esc(note)}</span></div>`).join("")}</div>`;
}

function renderTrainingPlan(){
    const box = document.getElementById("trainingPlanList");
    if(!box) return;
    box.innerHTML = buildTrainingPlan().map((item,index) => `
        <div class="training-plan-card">
            <strong>${index + 1}. ${esc(item.title)}</strong>
            <span>${esc(item.drill)}</span>
            <small>${esc(item.target)}</small>
        </div>
    `).join("");
}

function buildPlayerArchive(){
    ensureCoachStateShape();
    const map = new Map();
    const add = (key, payload) => {
        if(!key) return;
        const clean = String(key).toLowerCase().trim();
        if(!clean) return;
        if(!map.has(clean)){
            map.set(clean, {name:key, matches:0, ratings:[], events:0, notes:[]});
        }
        const item = map.get(clean);
        if(payload.rating !== undefined) item.ratings.push(Number(payload.rating || 0));
        if(payload.event) item.events += 1;
        if(payload.note) item.notes.push(payload.note);
        if(payload.match) item.matches += 1;
    };

    coachState.ratings.forEach(r => add(r.player, {rating:r.vote, note:r.note, match:true}));
    coachState.events.forEach(e => {
        if(e.player) add(e.player, {event:true, note:e.note});
    });
    loadHistory().forEach(h => {
        (h.ratings || []).forEach(r => add(r.player, {rating:r.vote, note:r.note, match:true}));
        (h.events || []).forEach(e => { if(e.player) add(e.player, {event:true, note:e.note}); });
    });

    return [...map.values()]
        .map(item => {
            const avg = item.ratings.length
                ? item.ratings.reduce((a,b) => a + b, 0) / item.ratings.length
                : 0;
            return {...item, avg};
        })
        .sort((a,b) => b.avg - a.avg || b.events - a.events)
        .slice(0,10);
}

function renderPlayerArchive(){
    const box = document.getElementById("playerArchiveList");
    if(!box) return;
    const archive = buildPlayerArchive();
    if(!archive.length){
        box.innerHTML = `<div class="empty">Ancora nessuno storico giocatore. Aggiungi pagelle o eventi con nome giocatore.</div>`;
        return;
    }
    box.innerHTML = archive.map(player => `
        <div class="player-archive-card">
            <div>
                <strong>${esc(player.name)}</strong>
                <span>${player.matches || player.ratings.length} partite - ${player.ratings.length} pagelle - ${player.events} eventi collegati</span>
                <small>${esc(player.notes.filter(Boolean).slice(0,1)[0] || "Nessuna nota recente")}</small>
            </div>
            <div class="player-archive-score">${player.avg ? esc(player.avg.toFixed(1)) : "--"}</div>
        </div>
    `).join("");
}

function renderCoachAutopilot(){
    const talkBox = document.getElementById("coachHalftimeTalk");
    const questionsBox = document.getElementById("coachAssistantQuestions");
    const remindersBox = document.getElementById("coachAutoReminders");
    const voiceHint = document.getElementById("coachVoiceAutopilotHint");

    if(talkBox){
        talkBox.innerHTML = buildCoachHalftimeTalk().map((line,index) => `
            <div class="coach-ai-tip ok">
                <strong>${index + 1}. Messaggio intervallo</strong>
                <span>${esc(line)}</span>
            </div>
        `).join("");
    }

    if(questionsBox){
        const quickAnswers = ["Lato destro", "Lato sinistro", "Problema centrale", "Serve comunicazione"];
        questionsBox.innerHTML = buildCoachAssistantQuestions().map(question => `
            <button class="coach-question-chip" type="button" data-question="${esc(question)}" onclick="applyCoachAssistantQuestion(this)">${esc(question)}</button>
        `).join("") + `<div class="coach-answer-row">${quickAnswers.map(answer => `<button type="button" data-answer="${esc(answer)}" onclick="answerCoachFollowUp(this)">${esc(answer)}</button>`).join("")}</div>`;
    }

    if(remindersBox){
        remindersBox.innerHTML = buildCoachReminders().map(reminder => `
            <div class="coach-ai-tip warn">
                <strong>Promemoria staff</strong>
                <span>${esc(reminder)}</span>
            </div>
        `).join("");
    }

    if(voiceHint){
        voiceHint.textContent = "Puoi dire: palla persa nostra al 18, pressing alto loro, linea troppo bassa, seconda palla persa, occasione loro.";
    }
}

function renderLiveAssistant(){
    ensureCoachStateShape();

    const clock = document.getElementById("coachLiveClock");
    const period = document.getElementById("coachLivePeriod");
    const toggle = document.getElementById("coachLiveToggle");
    const minute = document.getElementById("coachLiveMinute");
    const last = document.getElementById("coachLiveLast");
    const insights = document.getElementById("coachLiveInsights");

    if(clock) clock.textContent = formatCoachClock(getCoachLiveElapsedSeconds());
    if(period) period.value = coachState.live?.period || "1T";
    if(toggle) toggle.textContent = coachState.live?.running ? "Pausa timer" : "Avvia timer";
    if(minute) minute.textContent = `${getLiveMinuteLabel()}'`;

    if(last){
        const event = coachState.events[0];
        last.textContent = event ? `${event.minute}' ${event.label} - ${event.team}` : "Nessun evento live";
    }

    if(insights){
        insights.innerHTML = buildCoachLiveInsights().map(item => `
            <div class="coach-ai-tip ${esc(item.level)}">
                <strong>${esc(item.title)}</strong>
                <span>${esc(item.text)}</span>
            </div>
        `).join("");
    }

    renderCoachAutopilot();
}

function findCoachBlockByText(selector, text){
    const needle = String(text || "").toLowerCase();
    return [...document.querySelectorAll(selector)].find(el => String(el.textContent || "").toLowerCase().includes(needle)) || null;
}

function moveCoachBlock(target, block){
    if(target && block && block.parentElement !== target){
        target.appendChild(block);
    }
}

function organizeCoachPhaseBlocks(){
    const pre = document.getElementById("coachPhasePre");
    const match = document.getElementById("coachPhaseMatch");
    const post = document.getElementById("coachPhasePost");
    if(!pre || !match || !post || pre.dataset.organized === "1") return;

    const setup = document.querySelector(".setup-section");
    const precheck = findCoachBlockByText(".section", "Piano partita");
    const lineup = findCoachBlockByText(".section", "Campo e formazione");
    const onboarding = document.querySelector(".coach-onboarding");
    const live = document.querySelector(".coach-live-board");
    const ratings = findCoachBlockByText(".grid.section", "Pagelle giocatori");
    const playerArchive = findCoachBlockByText(".section", "Storico prestazioni");
    const memoryTraining = findCoachBlockByText(".grid.section", "Pattern che si ripetono");
    const timelineReportGrid = findCoachBlockByText(".grid.section", "Report tecnico automatico");
    const timelinePanel = findCoachBlockByText(".panel", "Eventi partita");
    const reportPanel = findCoachBlockByText(".panel", "Report tecnico automatico");
    const history = findCoachBlockByText(".grid.section", "Archivio partite");

    [setup, precheck, lineup, onboarding].forEach(block => moveCoachBlock(pre, block));
    [live, timelinePanel].forEach(block => moveCoachBlock(match, block));
    [reportPanel, ratings, playerArchive, memoryTraining, history].forEach(block => moveCoachBlock(post, block));
    if(timelineReportGrid && !timelineReportGrid.children.length){
        timelineReportGrid.remove();
    }

    pre.dataset.organized = "1";
}

function getCoachPhaseCopy(phase){
    const m = coachState.match;
    const title = phase === "match" ? "Match Day" : phase === "post" ? "Post-partita" : "Pre-partita";
    if(phase === "match"){
        return {
            title,
            text: m ? `${getTeamName("home")} - ${getTeamName("away")} | ${getGoals("home")} - ${getGoals("away")} | minuto ${getLiveMinuteLabel()}'` : "Crea una partita prima di usare la console live.",
            action: m ? "Termina partita" : "Vai al setup",
            actionFn: m ? "finishCoachMatchDay()" : "setCoachPhase('pre')"
        };
    }
    if(phase === "post"){
        return {
            title,
            text: m ? "Completa pagelle, report, sintesi WhatsApp e salvataggio nello storico." : "Nessuna partita attiva: crea una gara nel Pre-partita.",
            action: coachState.report ? "Salva nello storico" : "Genera report",
            actionFn: coachState.report ? "saveCurrentMatchToHistory()" : "generateCoachReport()"
        };
    }
    return {
        title,
        text: m ? `${getTeamName("home")} vs ${getTeamName("away")} preparata. Controlla piano, formazione e checklist.` : "Crea la partita e prepara il lavoro dello staff.",
        action: m ? "Avvia Match Day" : "Crea partita",
        actionFn: m ? "startCoachMatchDay()" : "document.getElementById('homeTeamInput')?.focus()"
    };
}

function setCoachPhase(phase){
    ensureCoachStateShape();
    coachState.phase = normalizeCoachPhase(phase);
    saveState();
    renderCoachPhaseShell();
}

function renderCoachPhaseShell(){
    organizeCoachPhaseBlocks();
    ensureCoachStateShape();
    const phase = getCoachSuggestedPhase();
    coachState.phase = phase;

    const sections = {
        pre: document.getElementById("coachPhasePre"),
        match: document.getElementById("coachPhaseMatch"),
        post: document.getElementById("coachPhasePost")
    };
    const buttons = {
        pre: document.getElementById("coachPhasePreBtn"),
        match: document.getElementById("coachPhaseMatchBtn"),
        post: document.getElementById("coachPhasePostBtn")
    };

    Object.entries(sections).forEach(([key, el]) => {
        if(!el) return;
        el.classList.toggle("hidden", key !== phase);
        el.setAttribute("aria-hidden", key === phase ? "false" : "true");
    });
    Object.entries(buttons).forEach(([key, btn]) => {
        if(!btn) return;
        btn.classList.toggle("active", key === phase);
        btn.setAttribute("aria-selected", key === phase ? "true" : "false");
    });

    const status = document.getElementById("coachPhaseStatus");
    if(status){
        const copy = getCoachPhaseCopy(phase);
        status.innerHTML = `
            <strong>${esc(copy.title)}</strong>
            <span>${esc(copy.text)}</span>
            <button class="btn green small-btn" type="button" onclick="${copy.actionFn}">${esc(copy.action)}</button>
        `;
    }
}

function renderAll(){
    ensureCoachStateShape();
    fillFormFromState();
    renderCoachPrecheck();
    renderStatus();
    renderCoachPhaseShell();
    renderLiveAssistant();
    if(typeof renderLineup === "function") renderLineup();
    renderTimeline();
    renderRatings();
    renderPlayerArchive();
    renderTeamMemory();
    renderTrainingPlan();
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

    const teamLabel = "";
    const fieldLabel = "";

    const base = `
        <div class="pitch-half-line"></div>
        <div class="pitch-box-top"></div>
        <div class="pitch-box-bottom"></div>
        <div class="pitch-empty-state" style="display:none;top:10%;font-size:12px;opacity:.78;">
            ${esc(teamLabel)} - ${esc(fieldLabel)}
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

        if(benchPlayers.length){
            bench.innerHTML = benchPlayers.map(p => {
                const side = normalizeLineupSide(p.side, p);
                const team = side === "home" ? "Casa" : "Trasferta";
                return `<span class="bench-chip ${esc(side)}">${esc(team)} · ${esc(formatLineupPlayer(p))} · ${esc(p.role || "Jolly")}</span>`;
            }).join("");
        }
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
