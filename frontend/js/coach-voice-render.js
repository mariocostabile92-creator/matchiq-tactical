function renderCoachVoiceSelect(value, options, field, proposalId){
    return `
        <select onchange="updateCoachVoiceProposalField('${esc(proposalId)}','${esc(field)}',this.value)">
            ${options.map(option => `
                <option value="${esc(option.value)}" ${String(option.value) === String(value || "") ? "selected" : ""}>${esc(option.label)}</option>
            `).join("")}
        </select>
    `;
}

function renderCoachVoicePlayerOptions(){
    return [{value:"", label:"Non indicato"}].concat(getLineup().map(player => ({
        value: player.id,
        label: formatLineupPlayer(player) + (player.status ? ` - ${player.status}` : "")
    })));
}

function renderCoachVoiceProposalEditor(proposal){
    const players = renderCoachVoicePlayerOptions();
    const themes = [{value:"general_note", label:"Nota staff"}].concat(COACH_VOICE_THEME_RULES.map(rule => ({value: rule.key, label: rule.label})));
    const events = Object.entries(COACH_VOICE_EVENT_MAP).map(([key, item]) => ({value: key, label: item.label}));
    const cells = [
        `<label><span>Minuto</span><input type="number" min="0" max="130" value="${esc(proposal.minute || 0)}" onchange="updateCoachVoiceProposalField('${esc(proposal.id)}','minute',this.value)"></label>`,
        `<label><span>Squadra</span>${renderCoachVoiceSelect(proposal.team || "home", [{value:"home",label:getTeamName("home")},{value:"away",label:getTeamName("away")}], "team", proposal.id)}</label>`
    ];
    if(proposal.intent === "player_event"){
        cells.push(`<label><span>Evento</span>${renderCoachVoiceSelect(proposal.entities?.event_key || "", events, "event_key", proposal.id)}</label>`);
        cells.push(`<label><span>Giocatore</span>${renderCoachVoiceSelect(proposal.entities?.player_id || "", players, "player_id", proposal.id)}</label>`);
    }
    if(proposal.intent === "substitution"){
        cells.push(`<label><span>Esce</span>${renderCoachVoiceSelect(proposal.entities?.player_out_id || "", players, "player_out_id", proposal.id)}</label>`);
        cells.push(`<label><span>Entra</span>${renderCoachVoiceSelect(proposal.entities?.player_in_id || "", players, "player_in_id", proposal.id)}</label>`);
    }
    if(proposal.intent === "score_update"){
        cells.push(`<label><span>Gol ${esc(getTeamName("home"))}</span><input type="number" min="0" max="30" value="${esc(proposal.entities?.home_goals || 0)}" onchange="updateCoachVoiceProposalField('${esc(proposal.id)}','home_goals',this.value)"></label>`);
        cells.push(`<label><span>Gol ${esc(getTeamName("away"))}</span><input type="number" min="0" max="30" value="${esc(proposal.entities?.away_goals || 0)}" onchange="updateCoachVoiceProposalField('${esc(proposal.id)}','away_goals',this.value)"></label>`);
    }
    if(proposal.intent === "tactical_note" || proposal.intent === "player_note"){
        cells.push(`<label><span>Tema</span>${renderCoachVoiceSelect(proposal.entities?.topic || "general_note", themes, "topic", proposal.id)}</label>`);
        cells.push(`<label><span>Giocatore</span>${renderCoachVoiceSelect(proposal.entities?.player_id || "", players, "player_id", proposal.id)}</label>`);
    }
    return `
        <div class="coach-voice-transcript-review">
            <label for="coachVoiceTranscriptEditor">Trascrizione da verificare</label>
            <textarea id="coachVoiceTranscriptEditor" rows="3" onchange="updateCoachVoiceProposalField('${esc(proposal.id)}','transcript',this.value)">${esc(proposal.transcript || "")}</textarea>
            <small>Correggi eventuali parole, nomi o dettagli prima di confermare.</small>
        </div>
        <div class="coach-voice-editor">${cells.join("")}</div>
    `;
}

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
            ${proposal.explanation ? `<div class="coach-voice-explanation"><strong>Perche</strong><span>${esc(proposal.explanation)}</span></div>` : ""}
            ${Array.isArray(proposal.evidence) && proposal.evidence.length ? `<div class="coach-voice-evidence">${proposal.evidence.map(item => `<span>${esc(item)}</span>`).join("")}</div>` : ""}
            ${renderCoachVoiceProposalEditor(proposal)}
            <div class="coach-voice-fields">
                ${fields.map(([label, value]) => `
                    <div><span>${esc(label)}</span><strong>${esc(value)}</strong></div>
                `).join("")}
            </div>
            ${notes.length ? `<div class="coach-voice-warnings">${notes.map(n => `<span>${esc(n.text)}</span>`).join("")}</div>` : ""}
            ${proposal.clarification_question ? `
                <div class="coach-voice-clarification">
                    <strong>${esc(proposal.clarification_question)}</strong>
                    <div>${(proposal.clarification_options || []).map(option => `<button type="button" onclick="applyCoachVoiceClarification('${esc(proposal.id)}','${esc(option)}')">${esc(option)}</button>`).join("")}</div>
                </div>` : ""}
            <div class="coach-voice-actions-row">
                <button class="btn green" type="button" onclick="applyCoachVoiceProposal('${esc(proposal.id)}')">Conferma</button>
                <button class="btn dark" type="button" onclick="editCoachVoiceProposal()">Modifica</button>
                <button class="btn danger" type="button" onclick="cancelCoachVoiceProposal()">Scarta</button>
            </div>
        </div>
    `;
}

function renderCoachVoiceThemes(){
    const vc = ensureCoachVoiceMemory();
    const themes = Object.entries(vc.themes || {})
        .map(([key, item]) => ({key, ...item}))
        .sort((a,b) => Number(b.count || 0) - Number(a.count || 0))
        .filter(item => item.status !== "ignored" && item.status !== "resolved")
        .slice(0, 5);
    if(!themes.length){
        return `<div class="empty">Ancora nessun tema emerso. Detti o scrivi osservazioni durante il Match Day.</div>`;
    }
    return themes.map(item => `
        <div class="coach-voice-theme">
            <strong>${esc(item.label || item.key)}</strong>
            <span>${esc(item.count || 0)} segnalazioni${Array.isArray(item.minutes) && item.minutes.length ? ` - ${esc(item.minutes[0])}'-${esc(item.minutes[item.minutes.length - 1])}'` : ""}${item.zone ? ` - ${esc(item.zone)}` : ""}</span>
            ${Array.isArray(item.players) && item.players.length ? `<small>${item.players.map(esc).join(", ")}</small>` : ""}
            <button type="button" onclick="openCoachVoiceThemeDetails('${esc(item.key)}')">Apri dettagli</button>
        </div>
    `).join("");
}

function renderCoachVoiceProactive(){
    const vc = ensureCoachVoiceMemory();
    const now = Date.now();
    return (vc.proactiveSuggestions || []).filter(item => {
        const dismissed = Number(vc.notifications?.[item.key] || 0);
        return !dismissed || now - dismissed > Number(item.cooldown_seconds || 600) * 1000;
    }).slice(0, 2).map(item => `
        <div class="coach-voice-proactive">
            <span>${esc(item.message)}</span>
            <button type="button" onclick="${item.type === 'halftime' ? 'prepareCoachHalftimeSummary()' : `document.getElementById('coachVoiceThemes')?.scrollIntoView({behavior:'smooth'})`}">Apri</button>
            <button type="button" onclick="dismissCoachVoiceSuggestion('${esc(item.key)}')">Non ora</button>
        </div>
    `).join("");
}

function renderCoachVoiceCoach(){
    const vc = ensureCoachVoiceMemory();
    const panel = document.getElementById("coachVoicePanel");
    const preview = document.getElementById("coachVoicePreview");
    const themes = document.getElementById("coachVoiceThemes");
    const hint = document.getElementById("coachVoiceAutopilotHint");
    const proactive = document.getElementById("coachVoiceProactive");
    const undo = document.getElementById("coachVoiceUndo");

    if(panel){
        panel.classList.toggle("has-proposal", Boolean(vc.lastProposal));
    }
    if(preview){
        preview.innerHTML = renderCoachVoiceProposalCard(vc.lastProposal);
    }
    if(themes){
        themes.innerHTML = renderCoachVoiceThemes();
    }
    if(proactive) proactive.innerHTML = renderCoachVoiceProactive();
    if(undo) undo.hidden = !(vc.observations || []).length;
    if(hint){
        hint.textContent = "Esempi: Gol di Rossi, Cambio Rossi per Bianchi, stiamo soffrendo a destra, secondo palo libero, grande recupero di Marco.";
    }
}
