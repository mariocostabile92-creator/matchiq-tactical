function getDominantSide(){
    const homePositive =
        getEventsByType("gol").filter(e => e.side === "home").length * 4 +
        getEventsByType("occasione").filter(e => e.side === "home").length * 2 +
        getEventsByType("tiro").filter(e => e.side === "home").length +
        getEventsByType("recupero").filter(e => e.side === "home").length;

    const awayPositive =
        getEventsByType("gol").filter(e => e.side === "away").length * 4 +
        getEventsByType("occasione").filter(e => e.side === "away").length * 2 +
        getEventsByType("tiro").filter(e => e.side === "away").length +
        getEventsByType("recupero").filter(e => e.side === "away").length;

    if(homePositive > awayPositive + 2) return "home";
    if(awayPositive > homePositive + 2) return "away";
    return "balanced";
}

function buildWeaknessText(side){
    const lost = getEventsByType("palla_persa").filter(e => e.side === side).length;
    const def = getEventsByType("errore_difensivo").filter(e => e.side === side).length;
    const cards = getEventsByType("cartellino").filter(e => e.side === side).length;

    const problems = [];

    if(lost >= 2) problems.push("troppe palle perse nella costruzione o nelle transizioni");
    if(def >= 1) problems.push("attenzione agli errori difensivi e alle coperture preventive");
    if(cards >= 2) problems.push("gestione emotiva e duelli da controllare meglio");

    if(!problems.length){
        problems.push("nessuna criticità forte registrata, ma serve continuità nella gestione della partita");
    }

    return problems.join("; ");
}

function buildTrainingAdvice(){
    const lost = getEventsByType("palla_persa").length;
    const def = getEventsByType("errore_difensivo").length;
    const shots = getEventsByType("tiro").length;
    const chances = getEventsByType("occasione").length;
    const recoveries = getEventsByType("recupero").length;

    if(def >= 2){
        return "Allenamento consigliato: lavoro su linea difensiva, coperture preventive, marcature in area e uscite sotto pressione.";
    }

    if(lost >= 3){
        return "Allenamento consigliato: possesso sotto pressione, scelta della giocata semplice e transizioni dopo palla persa.";
    }

    if(shots + chances <= 2){
        return "Allenamento consigliato: sviluppo offensivo, occupazione area, attacco della profondità e finalizzazione.";
    }

    if(recoveries >= 4){
        return "Allenamento consigliato: consolidare pressing, recupero palla e ripartenza immediata dopo riconquista.";
    }

    return "Allenamento consigliato: seduta mista su intensità, transizioni, finalizzazione e gestione dei momenti della partita.";
}

function buildRatingsReportText(){
    if(!coachState.ratings.length) return "Nessuna pagella giocatore inserita.";
    const best = getBestRating();
    const positives = coachState.ratings.filter(r => Number(r.vote || 0) >= 7);
    const improve = coachState.ratings.filter(r => Number(r.vote || 0) < 6);
    const list = [...coachState.ratings].sort((a,b) => Number(b.vote || 0) - Number(a.vote || 0)).map(r => `- ${r.player} (${r.team}, ${r.role}) — voto ${r.vote}${r.note ? ": " + r.note : ""}`).join("\n");
    return `
Migliore in campo: ${best ? `${best.player} (${best.team}) con voto ${best.vote}` : "--"}.
Giocatori positivi: ${positives.length ? positives.map(r => `${r.player} ${r.vote}`).join(", ") : "nessun voto sopra il 7 registrato"}.
Giocatori da migliorare: ${improve.length ? improve.map(r => `${r.player} ${r.vote}`).join(", ") : "nessuna insufficienza registrata"}.

Pagelle complete:
${list}
`.trim();
}

function buildCoachTips(){
    const tips=[];
    const lost=getEventCount("palla_persa");
    const def=getEventCount("errore_difensivo");
    const chances=getEventCount("occasione");
    const shots=getEventCount("tiro");
    const recoveries=getEventCount("recupero");

    if(def>=1) tips.push("Curare meglio distanze tra i reparti, coperture preventive e marcature sulle seconde palle.");
    if(lost>=2) tips.push("Ridurre le palle perse forzate: chiedere più appoggi semplici e migliore orientamento del corpo in ricezione.");
    if(shots+chances<=2) tips.push("Aumentare presenza in area e attacco della profondità: servono più soluzioni negli ultimi 25 metri.");
    if(recoveries>=3) tips.push("Il recupero palla è un segnale positivo: lavorare sulla prima giocata dopo riconquista.");
    if(!tips.length) tips.push("Continuare su intensità, ordine e comunicazione: il match non mostra criticità dominanti dagli eventi inseriti.");

    return tips.map((t,i)=>`${i+1}. ${t}`).join("\n");
}

function buildCriticalIssues(){
    const issues=[];
    const homeLost=getEventCount("palla_persa","home");
    const awayLost=getEventCount("palla_persa","away");
    const homeDef=getEventCount("errore_difensivo","home");
    const awayDef=getEventCount("errore_difensivo","away");

    if(homeLost>=2) issues.push(`${getTeamName("home")}: gestione possesso da migliorare, troppe palle perse.`);
    if(awayLost>=2) issues.push(`${getTeamName("away")}: gestione possesso da migliorare, troppe palle perse.`);
    if(homeDef>=1) issues.push(`${getTeamName("home")}: attenzione a coperture e letture difensive.`);
    if(awayDef>=1) issues.push(`${getTeamName("away")}: attenzione a coperture e letture difensive.`);

    if(!issues.length) issues.push("Nessuna criticità grave registrata: lavorare sulla continuità dei principi di gioco.");
    return issues.map(x=>`- ${x}`).join("\n");
}

function buildWhatsAppSummary(){
    if(!coachState.match) return "";
    const m=coachState.match;
    const best=getBestRating();
    const homeGoals=getGoals("home");
    const awayGoals=getGoals("away");
    return `MATCHIQ COACH - SINTESI\n${m.homeTeam} vs ${m.awayTeam} (${homeGoals}-${awayGoals})\nCategoria: ${m.category || "Dilettanti"}\nEventi registrati: ${coachState.events.length}\nMigliore: ${best ? `${best.player} (${best.vote})` : "non inserito"}\nFocus allenamento: ${buildTrainingAdvice().replace("Allenamento consigliato: ","")}\n\nReport generato con MatchIQ Coach.`;
}

function copyWhatsAppSummary(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }
    const text=buildWhatsAppSummary();
    try{
        await navigator.clipboard.writeText(text);
        showNotice("Sintesi WhatsApp copiata.", "ok");
    }catch{
        showNotice("Non riesco a copiare automaticamente. Seleziona il testo manualmente.", "warn");
    }
}

function generateCoachReport(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }

    const match = coachState.match;
    const homeGoals = getGoals("home");
    const awayGoals = getGoals("away");
    const totalEvents = coachState.events.length;

    const dominantSide = getDominantSide();
    const dominantTeam = dominantSide === "balanced" ? "nessuna squadra in modo netto" : getTeamName(dominantSide);

    const chancesHome = getEventsByType("occasione").filter(e => e.side === "home").length;
    const chancesAway = getEventsByType("occasione").filter(e => e.side === "away").length;
    const shotsHome = getEventsByType("tiro").filter(e => e.side === "home").length;
    const shotsAway = getEventsByType("tiro").filter(e => e.side === "away").length;
    const recoveriesHome = getEventsByType("recupero").filter(e => e.side === "home").length;
    const recoveriesAway = getEventsByType("recupero").filter(e => e.side === "away").length;

    const importantEvents = coachState.events
        .filter(e => ["gol","occasione","errore_difensivo","palla_persa"].includes(e.type))
        .slice(0,6);

    const keyMoments = importantEvents.length
        ? importantEvents.map(e => `- ${e.minute}' ${e.icon} ${e.label} ${e.team}${e.player ? " (" + e.player + ")" : ""}${e.note ? ": " + e.note : ""}`).join("\n")
        : "- Nessun momento chiave registrato.";

    const report = `
<strong>REPORT MATCHIQ COACH</strong>

Partita: ${match.homeTeam} vs ${match.awayTeam}
Categoria: ${match.category || "Dilettanti"}
Data: ${match.date || "--"}
Risultato eventi registrati: ${homeGoals} - ${awayGoals}
Moduli: ${match.homeShape || "--"} vs ${match.awayShape || "--"}

<strong>Sintesi partita</strong>
La partita ha registrato ${totalEvents} eventi. Dal flusso manuale inserito emerge che ${dominantTeam} ha avuto il momento più influente della gara. Il report si basa sugli eventi registrati dallo staff e può essere usato come prima lettura post-partita.

<strong>Produzione offensiva</strong>
${match.homeTeam}: ${shotsHome} tiri, ${chancesHome} occasioni.
${match.awayTeam}: ${shotsAway} tiri, ${chancesAway} occasioni.

<strong>Pressione e recupero palla</strong>
${match.homeTeam}: ${recoveriesHome} recuperi registrati.
${match.awayTeam}: ${recoveriesAway} recuperi registrati.

<strong>Punti forti</strong>
- ${recoveriesHome >= recoveriesAway ? match.homeTeam : match.awayTeam} ha mostrato segnali positivi nel recupero palla e nella reazione agli episodi.
- Le occasioni registrate aiutano a individuare le zone e i giocatori più coinvolti nella fase offensiva.
- La timeline permette allo staff di rivedere i momenti chiave senza affidarsi solo alla memoria.

<strong>Aree da migliorare</strong>
- ${match.homeTeam}: ${buildWeaknessText("home")}.
- ${match.awayTeam}: ${buildWeaknessText("away")}.

<strong>Momenti chiave</strong>
${keyMoments}

<strong>Pagelle giocatori</strong>
${buildRatingsReportText()}

<strong>Consigli per il mister</strong>
${buildCoachTips()}

<strong>Criticità tattiche</strong>
${buildCriticalIssues()}

<strong>Allenamento consigliato</strong>
${buildTrainingAdvice()}

<strong>Sintesi WhatsApp</strong>
${buildWhatsAppSummary()}

<strong>Messaggio per la squadra</strong>
La partita va letta con lucidità: gli episodi registrati mostrano cosa ha funzionato e cosa va migliorato. La priorità è trasformare il report in lavoro sul campo, mantenendo atteggiamento, intensità e attenzione nei dettagli.

<strong>Nota</strong>
Report generato localmente da MatchIQ Coach V1.3: utile come base per analisi post-partita, confronto staff e lavoro settimanale sul campo.
`.trim();

    coachState.report = report;
    saveState();
    renderReport();
    renderStatus();

    showNotice("Report Coach generato.", "ok");
}

function copyReport(){
    if(!coachState.report){
        showNotice("Prima genera un report.", "warn");
        return;
    }

    const plain = coachState.report.replace(/<[^>]*>/g,"");

    try{
        await navigator.clipboard.writeText(plain);
        showNotice("Report copiato negli appunti.", "ok");
    }catch{
        showNotice("Non riesco a copiare automaticamente. Seleziona il testo manualmente.", "warn");
    }
}

function downloadReportTxt(){
    if(!coachState.report){
        showNotice("Prima genera un report.", "warn");
        return;
    }

    const match = coachState.match;
    const title = match
        ? `matchiq-coach-${match.homeTeam}-vs-${match.awayTeam}`.toLowerCase().replace(/[^a-z0-9]+/g,"-")
        : "matchiq-coach-report";

    const plain = coachState.report.replace(/<[^>]*>/g,"");
    const blob = new Blob([plain], {type:"text/plain;charset=utf-8"});
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `${title}.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
}


function stripReportHtml(value){
    return String(value || "")
        .replace(/<strong>/g,"\n## ")
        .replace(/<\/strong>/g,"\n")
        .replace(/<[^>]*>/g,"")
        .replace(/\n{3,}/g,"\n\n")
        .trim();
}

function splitReportSections(reportHtml){
    const raw = String(reportHtml || "");
    const parts = raw.split(/<strong>|<\/strong>/g).map(x => x.trim()).filter(Boolean);
    const sections = [];

    for(let i=0; i<parts.length; i+=2){
        const title = parts[i] || "Sezione";
        const body = parts[i+1] || "";
        if(title.toUpperCase().includes("REPORT MATCHIQ COACH")) continue;
        sections.push({title, body: body.replace(/<[^>]*>/g,"").trim()});
    }

    return sections.length ? sections : [{title:"Report", body:stripReportHtml(raw)}];
}

function buildPrintableCoachReport(){
    if(!coachState.match || !coachState.report){
        return "";
    }

    const match = coachState.match;
    const homeGoals = getGoals("home");
    const awayGoals = getGoals("away");
    const sections = splitReportSections(coachState.report);
    const dateLabel = match.date || "--";
    const generatedAt = new Date().toLocaleString("it-IT");

    const sectionsHtml = sections.map(section => `
        <section class="pdf-section">
            <h2>${esc(section.title)}</h2>
            <div class="pdf-section-body">${esc(section.body)}</div>
        </section>
    `).join("");

    return `
        <div class="pdf-report-page" id="pdfReportPage">
            <div class="pdf-header">
                <div>
                    <div class="pdf-brand">MatchIQ Coach</div>
                    <div class="pdf-subtitle">Report tecnico per calcio dilettantistico</div>
                </div>
                <div class="pdf-badge">COACH REPORT PDF</div>
            </div>

            <h1 class="pdf-title">${esc(match.homeTeam)} vs ${esc(match.awayTeam)}</h1>

            <div class="pdf-meta">
                <div class="pdf-meta-box">
                    <div class="pdf-meta-label">Risultato</div>
                    <div class="pdf-meta-value">${homeGoals} - ${awayGoals}</div>
                </div>
                <div class="pdf-meta-box">
                    <div class="pdf-meta-label">Categoria</div>
                    <div class="pdf-meta-value">${esc(match.category || "Dilettanti")}</div>
                </div>
                <div class="pdf-meta-box">
                    <div class="pdf-meta-label">Data</div>
                    <div class="pdf-meta-value">${esc(dateLabel)}</div>
                </div>
                <div class="pdf-meta-box">
                    <div class="pdf-meta-label">Eventi</div>
                    <div class="pdf-meta-value">${coachState.events.length}</div>
                </div>
            </div>

            ${sectionsHtml}

            <div class="pdf-footer">
                <span>Generato con MatchIQ Coach V1.5</span>
                <span>${esc(generatedAt)}</span>
            </div>
        </div>
    `;
}

function printCoachPdf(){
    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }

    if(!coachState.report){
        generateCoachReport();
    }

    const old = document.getElementById("pdfReportPage");
    if(old) old.remove();

    const wrapper = document.createElement("div");
    wrapper.innerHTML = buildPrintableCoachReport();
    document.body.appendChild(wrapper.firstElementChild);

    showNotice("Si apre la stampa: scegli ‘Salva come PDF’.", "ok", 3500);

    setTimeout(() => {
        window.print();
    }, 350);
}
