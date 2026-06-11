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

    const list = [...coachState.ratings]
        .sort((a,b) => Number(b.vote || 0) - Number(a.vote || 0))
        .map(r => `- ${r.player} (${r.team}, ${r.role}) — voto ${r.vote}${r.note ? ": " + r.note : ""}`)
        .join("\n");

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

    return `MATCHIQ COACH - SINTESI
${m.homeTeam} vs ${m.awayTeam} (${homeGoals}-${awayGoals})
Categoria: ${m.category || "Dilettanti"}
Eventi registrati: ${coachState.events.length}
Migliore: ${best ? `${best.player} (${best.vote})` : "non inserito"}
Focus allenamento: ${buildTrainingAdvice().replace("Allenamento consigliato: ","")}

Report generato con MatchIQ Coach.`;
}

async function copyWhatsAppSummary(){
    if(!canUseCoachWhatsapp()){
        showCoachProNotice("Sintesi WhatsApp");
        return;
    }

    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }

    const text=buildWhatsAppSummary();

    try{
        await navigator.clipboard.writeText(text);

        if(!isCoachPro()){
            incrementCoachUsageCount(COACH_USAGE_KEYS.whatsappCopies);
            renderAll();
        }

        showNotice(
            isCoachPro()
                ? "Sintesi WhatsApp copiata."
                : "Sintesi WhatsApp copiata. Prova gratuita usata.",
            "ok"
        );
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
Formazione inserita: ${getLineup().length} giocatori

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
Report generato localmente da MatchIQ Coach V1.7.2: utile come base per analisi post-partita, confronto staff e lavoro settimanale sul campo.
`.trim();

    coachState.report = report;
    saveState();
    renderReport();
    renderStatus();

    showNotice("Report Coach generato.", "ok");
}

async function copyReport(){
    if(!coachState.report){
        showNotice("Prima genera un report.", "warn");
        return;
    }

    const plain = stripReportHtml(coachState.report);

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

    const plain = stripReportHtml(coachState.report);
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

function stripReportHtml(html){
    const div = document.createElement("div");
    div.innerHTML = String(html || "");
    return div.textContent || div.innerText || "";
}

function escapePrintHtml(value){
    return String(value ?? "")
        .replaceAll("&","&amp;")
        .replaceAll("<","&lt;")
        .replaceAll(">","&gt;")
        .replaceAll('"',"&quot;")
        .replaceAll("'","&#039;");
}

function splitReportSections(reportHtml){
    const text = stripReportHtml(reportHtml);
    const lines = text.split("\n").map(x => x.trim()).filter(Boolean);

    const sections = [];
    let current = {
        title: "Report",
        lines: []
    };

    const knownTitles = [
        "REPORT MATCHIQ COACH",
        "Sintesi partita",
        "Produzione offensiva",
        "Pressione e recupero palla",
        "Punti forti",
        "Aree da migliorare",
        "Momenti chiave",
        "Pagelle giocatori",
        "Consigli per il mister",
        "Criticità tattiche",
        "Allenamento consigliato",
        "Sintesi WhatsApp",
        "Messaggio per la squadra",
        "Nota"
    ];

    lines.forEach(line => {
        if(knownTitles.includes(line)){
            if(current.lines.length || current.title !== "Report"){
                sections.push(current);
            }
            current = {
                title: line,
                lines: []
            };
        }else{
            current.lines.push(line);
        }
    });

    if(current.lines.length || current.title !== "Report"){
        sections.push(current);
    }

    return sections;
}

function buildPrintableCoachReport(){
    if(!coachState.match || !coachState.report){
        return "";
    }

    const m = coachState.match;
    const homeGoals = getGoals("home");
    const awayGoals = getGoals("away");
    const generatedAt = new Date().toLocaleString("it-IT");
    const best = getBestRating();

    const events = [...(coachState.events || [])]
        .sort((a,b) => Number(a.minute || 0) - Number(b.minute || 0));

    const ratings = [...(coachState.ratings || [])]
        .sort((a,b) => Number(b.vote || 0) - Number(a.vote || 0));

    const sections = splitReportSections(coachState.report);

    const eventsHtml = events.length ? events.map(e => `
        <tr>
            <td>${escapePrintHtml(e.minute)}'</td>
            <td>${escapePrintHtml(e.icon)} ${escapePrintHtml(e.label)}</td>
            <td>${escapePrintHtml(e.team)}</td>
            <td>${escapePrintHtml(e.player || "-")}</td>
            <td>${escapePrintHtml(e.note || "-")}</td>
        </tr>
    `).join("") : `
        <tr><td colspan="5">Nessun evento registrato.</td></tr>
    `;

    const ratingsHtml = ratings.length ? ratings.map(r => `
        <tr>
            <td><strong>${escapePrintHtml(r.player)}</strong></td>
            <td>${escapePrintHtml(r.team)}</td>
            <td>${escapePrintHtml(r.role)}</td>
            <td class="vote">${escapePrintHtml(r.vote)}</td>
            <td>${escapePrintHtml(r.note || "-")}</td>
        </tr>
    `).join("") : `
        <tr><td colspan="5">Nessuna pagella inserita.</td></tr>
    `;

    const sectionHtml = sections
        .filter(section => !["REPORT MATCHIQ COACH", "Sintesi WhatsApp"].includes(section.title))
        .map(section => `
            <section class="print-section">
                <h2>${escapePrintHtml(section.title)}</h2>
                ${section.lines.map(line => `<p>${escapePrintHtml(line)}</p>`).join("")}
            </section>
        `).join("");

    return `
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>MatchIQ Coach Report</title>
<style>
@page{
    size:A4;
    margin:14mm;
}

*{
    box-sizing:border-box;
}

body{
    margin:0;
    font-family:Arial,Helvetica,sans-serif;
    color:#101828;
    background:#ffffff;
}

.print-wrap{
    max-width:800px;
    margin:0 auto;
}

.cover{
    border-radius:22px;
    padding:24px;
    background:linear-gradient(135deg,#06111c,#102a43);
    color:white;
    margin-bottom:18px;
}

.brand-row{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap:16px;
    margin-bottom:28px;
}

.brand-title{
    font-size:30px;
    font-weight:900;
    letter-spacing:-.7px;
}

.brand-sub{
    color:#c8d8ff;
    font-size:12px;
    margin-top:5px;
    font-weight:700;
}

.badge-print{
    background:#18f08b;
    color:#06111c;
    border-radius:999px;
    padding:8px 12px;
    font-size:11px;
    font-weight:900;
    white-space:nowrap;
}

.match-title{
    font-size:28px;
    font-weight:900;
    letter-spacing:-.5px;
    margin-bottom:8px;
}

.score-line{
    font-size:44px;
    font-weight:900;
    color:#18f08b;
    margin-bottom:14px;
}

.cover-meta{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:9px;
    margin-top:18px;
}

.cover-card{
    background:rgba(255,255,255,.08);
    border:1px solid rgba(255,255,255,.13);
    border-radius:14px;
    padding:11px;
}

.cover-label{
    color:#b7c7ef;
    font-size:10px;
    text-transform:uppercase;
    font-weight:900;
    margin-bottom:5px;
}

.cover-value{
    font-size:13px;
    font-weight:900;
}

.summary-grid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:10px;
    margin-bottom:14px;
}

.summary-card{
    border:1px solid #e4e7ec;
    border-radius:16px;
    padding:13px;
    background:#f9fafb;
}

.summary-label{
    color:#667085;
    font-size:10px;
    text-transform:uppercase;
    font-weight:900;
    margin-bottom:6px;
}

.summary-value{
    color:#101828;
    font-size:14px;
    font-weight:900;
    line-height:1.35;
}

.print-section{
    break-inside:avoid;
    page-break-inside:avoid;
    border:1px solid #e4e7ec;
    border-radius:16px;
    padding:15px 17px;
    margin-bottom:12px;
}

.print-section h2{
    margin:0 0 9px;
    font-size:17px;
    color:#06111c;
    letter-spacing:-.2px;
}

.print-section p{
    margin:0 0 6px;
    color:#344054;
    font-size:12.5px;
    line-height:1.48;
}

.table-section{
    break-inside:avoid;
    page-break-inside:avoid;
    margin-bottom:14px;
}

.table-title{
    font-size:17px;
    font-weight:900;
    margin-bottom:8px;
    color:#06111c;
}

table{
    width:100%;
    border-collapse:collapse;
    border:1px solid #e4e7ec;
    border-radius:14px;
    overflow:hidden;
    font-size:11.5px;
}

th{
    text-align:left;
    background:#f2f4f7;
    color:#475467;
    padding:9px;
    text-transform:uppercase;
    font-size:10px;
    font-weight:900;
}

td{
    border-top:1px solid #e4e7ec;
    padding:9px;
    color:#344054;
    vertical-align:top;
}

.vote{
    font-size:16px;
    font-weight:900;
    color:#05603a;
}

.training-box{
    border:2px solid #18f08b;
    background:#ecfff5;
    border-radius:18px;
    padding:16px;
    margin-bottom:14px;
    break-inside:avoid;
}

.training-box h2{
    color:#05603a;
    margin:0 0 8px;
    font-size:18px;
}

.training-box p{
    color:#064e3b;
    font-size:13px;
    line-height:1.5;
    margin:0;
    font-weight:700;
}

.print-footer{
    margin-top:18px;
    padding-top:10px;
    border-top:1px solid #e4e7ec;
    color:#667085;
    font-size:11px;
    display:flex;
    justify-content:space-between;
    gap:12px;
}

@media print{
    body{
        print-color-adjust:exact;
        -webkit-print-color-adjust:exact;
    }
}
</style>
</head>

<body>
<div class="print-wrap">

    <section class="cover">
        <div class="brand-row">
            <div>
                <div class="brand-title">MatchIQ Coach</div>
                <div class="brand-sub">Report tecnico professionale per calcio dilettantistico</div>
            </div>
            <div class="badge-print">COACH REPORT V1.6.2</div>
        </div>

        <div class="match-title">${escapePrintHtml(m.homeTeam)} vs ${escapePrintHtml(m.awayTeam)}</div>
        <div class="score-line">${homeGoals} - ${awayGoals}</div>

        <div class="cover-meta">
            <div class="cover-card">
                <div class="cover-label">Categoria</div>
                <div class="cover-value">${escapePrintHtml(m.category || "Dilettanti")}</div>
            </div>
            <div class="cover-card">
                <div class="cover-label">Data</div>
                <div class="cover-value">${escapePrintHtml(m.date || "--")}</div>
            </div>
            <div class="cover-card">
                <div class="cover-label">Modulo casa</div>
                <div class="cover-value">${escapePrintHtml(m.homeShape || "--")}</div>
            </div>
            <div class="cover-card">
                <div class="cover-label">Modulo trasferta</div>
                <div class="cover-value">${escapePrintHtml(m.awayShape || "--")}</div>
            </div>
        </div>
    </section>

    <section class="summary-grid">
        <div class="summary-card">
            <div class="summary-label">Eventi registrati</div>
            <div class="summary-value">${coachState.events.length}</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">Formazione</div>
            <div class="summary-value">${getLineup().length} giocatori</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">Pagelle inserite</div>
            <div class="summary-value">${coachState.ratings.length}</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">Migliore</div>
            <div class="summary-value">${best ? `${escapePrintHtml(best.player)} · ${escapePrintHtml(best.vote)}` : "Non inserito"}</div>
        </div>
    </section>

    <section class="training-box">
        <h2>Focus allenamento consigliato</h2>
        <p>${escapePrintHtml(buildTrainingAdvice())}</p>
    </section>

    ${sectionHtml}

    <section class="table-section">
        <div class="table-title">Timeline eventi</div>
        <table>
            <thead>
                <tr>
                    <th>Min.</th>
                    <th>Evento</th>
                    <th>Squadra</th>
                    <th>Giocatore</th>
                    <th>Nota</th>
                </tr>
            </thead>
            <tbody>${eventsHtml}</tbody>
        </table>
    </section>

    <section class="table-section">
        <div class="table-title">Pagelle giocatori</div>
        <table>
            <thead>
                <tr>
                    <th>Giocatore</th>
                    <th>Squadra</th>
                    <th>Ruolo</th>
                    <th>Voto</th>
                    <th>Nota</th>
                </tr>
            </thead>
            <tbody>${ratingsHtml}</tbody>
        </table>
    </section>

    <footer class="print-footer">
        <span>Generated by MatchIQ Tactical · Coach Mode</span>
        <span>${escapePrintHtml(generatedAt)}</span>
    </footer>

</div>
</body>
</html>
`;
}

function printCoachPdf(){
    if(!canUseCoachPdf()){
        showCoachProNotice("Export PDF Coach");
        return;
    }

    if(!coachState.match){
        showNotice("Prima crea una partita manuale.", "warn");
        return;
    }

    if(!coachState.report){
        generateCoachReport();
    }

    const printable = buildPrintableCoachReport();

    if(!printable){
        showNotice("Non riesco a creare il PDF. Genera prima il report.", "warn");
        return;
    }

    const printWindow = window.open("", "_blank", "width=920,height=1100");

    if(!printWindow){
        showNotice("Popup bloccato. Consenti i popup per scaricare il PDF.", "warn");
        return;
    }

    printWindow.document.open();
    printWindow.document.write(printable);
    printWindow.document.close();
    printWindow.focus();

    setTimeout(() => {
        printWindow.print();

        if(!isCoachPro()){
            incrementCoachUsageCount(COACH_USAGE_KEYS.pdfExports);
            renderAll();
        }
    }, 650);
}
