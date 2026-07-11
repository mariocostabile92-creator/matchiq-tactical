function renderCoachVoiceProposalCard(proposal){
    if(!proposal) return "";
    const intentLabel = COACH_VOICE_INTENTS[proposal.intent] || "Comando";
    const fields = [];
    fields.push(["Tipo", intentLabel]);
    fields.push(["Minuto", `${proposal.minute}' ${proposal.source === "speech" ? "(da voce)" : ""}`]);
    fields.push(["Squadra", getTeamName(proposal.team || "home")]);
    if(proposal.entities?.player_name) fields.push(["Giocatore", proposal.entities.player_name]);
    if(proposal.entities?.player_out_name) fields.push(["Esce", proposal.entities.player_out_name]);
    if(proposal.entities?.player_in_name) fields.push(["Entra", proposal.entities.player_in_name]);
    if(proposal.entities?.topic_label) fields.push(["Tema", proposal.entities.topic_label]);
    if(proposal.entities?.zone) fields.push(["Zona", proposal.entities.zone]);
    if(proposal.entities?.priority) fields.push(["Priorita", proposal.entities.priority]);

    const notes = [
        ...(proposal.ambiguities || []).map(x => ({type:"warn", text:x})),
        ...(proposal.warnings || []).map(x => ({type:"warn", text:x}))
    ];

    return `
        <div class="coach-voice-preview-card">
            <div class="coach-voice-preview-head">
                <span class="badge green">AI VOICE COACH</span>
                <span>${Math.round((proposal.confidence || 0) * 100)}% confidenza</span>
            </div>
            <h3>Ho capito questo</h3>
            <p>${esc(proposal.normalized_summary || proposal.transcript || "")}</p>
            <div class="coach-voice-fields">
                ${fields.map(([label, value]) => `
                    <div><span>${esc(label)}</span><strong>${esc(value)}</strong></div>
                `).join("")}
            </div>
            ${notes.length ? `<div class="coach-voice-warnings">${notes.map(n => `<span>${esc(n.text)}</span>`).join("")}</div>` : ""}
            <div class="coach-voice-actions-row">
                <button class="btn green" type="button" onclick="applyCoachVoiceProposal('${esc(proposal.id)}')">Conferma</button>
                <button class="btn dark" type="button" onclick="editCoachVoiceProposal()">Modifica</button>
                <button class="btn danger" type="button" onclick="cancelCoachVoiceProposal()">Annulla</button>
            </div>
        </div>
    `;
}

function renderCoachVoiceThemes(){
    const vc = ensureCoachVoiceMemory();
    const themes = Object.entries(vc.themes || {})
        .map(([key, item]) => ({key, ...item}))
        .sort((a,b) => Number(b.count || 0) - Number(a.count || 0))
        .slice(0, 6);
    if(!themes.length){
        return `<div class="empty">Ancora nessun tema vocale ricorrente. Detti o scrivi 2-3 osservazioni durante il Match Day.</div>`;
    }
    return themes.map(item => `
        <div class="coach-voice-theme">
            <strong>${esc(item.label || item.key)}</strong>
            <span>${esc(item.count || 0)} segnalazioni${Array.isArray(item.minutes) && item.minutes.length ? ` - min. ${item.minutes.map(m => `${esc(m)}'`).join(", ")}` : ""}</span>
        </div>
    `).join("");
}

function renderCoachVoiceCoach(){
    const vc = ensureCoachVoiceMemory();
    const panel = document.getElementById("coachVoicePanel");
    const preview = document.getElementById("coachVoicePreview");
    const themes = document.getElementById("coachVoiceThemes");
    const hint = document.getElementById("coachVoiceAutopilotHint");

    if(panel){
        panel.classList.toggle("has-proposal", Boolean(vc.lastProposal));
    }
    if(preview){
        preview.innerHTML = renderCoachVoiceProposalCard(vc.lastProposal);
    }
    if(themes){
        themes.innerHTML = renderCoachVoiceThemes();
    }
    if(hint){
        hint.textContent = "Esempi: Gol di Rossi, Cambio Rossi per Bianchi, stiamo soffrendo a destra, secondo palo libero, grande recupero di Marco.";
    }
}
