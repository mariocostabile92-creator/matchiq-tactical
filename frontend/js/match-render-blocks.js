/*
    MatchIQ - Match Render Blocks Module
    Blocchi di rendering UI per card, sezioni, grafici e pannelli della pagina match.
    Copy polish: testi più puliti, meno tecnici, più italiani.
*/

function renderLiveFlowVisual(flow){
    return`
    <div class="live-flow-hero ${flow.statusClass}">
        <div class="live-flow-inner">
            <div class="match-status-row">
                <div class="status-main">
                    <div class="status-kicker">STATO LIVE PARTITA</div>
                    <div class="status-title">${flow.status}</div>
                    <div class="status-subtitle">${flow.subtitle}</div>
                </div>
                <div class="status-chip">
                    <div class="status-chip-label">FLUSSO DOMINANTE</div>
                    <div class="status-chip-value">${flow.dominant}</div>
                    <div class="status-chip-small">pressione, pericolo e momentum</div>
                </div>
                <div class="status-chip">
                    <div class="status-chip-label">INTENSITÀ MATCH</div>
                    <div class="status-chip-value">${Math.round(flow.chaosIndex)}</div>
                    <div class="status-chip-small">${flow.chaosLabel}</div>
                </div>
            </div>

            <div class="chaos-wrapper">
                <div class="chaos-top">
                    <div class="chaos-label">INDICE INTENSITÀ</div>
                    <div class="chaos-value">${Math.round(flow.chaosIndex)} / 100</div>
                </div>
                <div class="chaos-track">
                    <div class="chaos-fill ${flow.chaosClass}" style="width:${flow.chaosIndex}%"></div>
                </div>
            </div>

            <div class="flow-alert-grid">
                ${flow.alerts.map(a=>`
                    <div class="flow-alert ${a.type}">
                        <strong>${a.title}</strong><br>${a.text}
                    </div>
                `).join("")}
            </div>

            <div class="story-box">
                <div class="story-title">LETTURA LIVE</div>
                <div class="story-text">${flow.story}</div>
            </div>
        </div>
    </div>`;
}

function renderPsychologicalEngine(flow,home,away){
    return`
    <div class="psych-grid">
        <div class="psych-card">
            <div class="psych-label">FIDUCIA ${home}</div>
            <div class="psych-value">${Math.round(flow.confidenceHome)}%</div>
            <div class="psych-bar"><div class="psych-fill" style="width:${flow.confidenceHome}%"></div></div>
        </div>

        <div class="psych-card">
            <div class="psych-label">FIDUCIA ${away}</div>
            <div class="psych-value">${Math.round(flow.confidenceAway)}%</div>
            <div class="psych-bar"><div class="psych-fill" style="width:${flow.confidenceAway}%"></div></div>
        </div>

        <div class="psych-card">
            <div class="psych-label">STRESS ${home}</div>
            <div class="psych-value">${Math.round(flow.panicHome)}%</div>
            <div class="psych-bar"><div class="psych-fill danger" style="width:${flow.panicHome}%"></div></div>
        </div>

        <div class="psych-card">
            <div class="psych-label">STRESS ${away}</div>
            <div class="psych-value">${Math.round(flow.panicAway)}%</div>
            <div class="psych-bar"><div class="psych-fill danger" style="width:${flow.panicAway}%"></div></div>
        </div>

        <div class="psych-card">
            <div class="psych-label">PRESSIONE FISICA</div>
            <div class="psych-value">${Math.round(flow.fatiguePressure)}%</div>
            <div class="psych-bar"><div class="psych-fill danger" style="width:${flow.fatiguePressure}%"></div></div>
        </div>

        <div class="psych-card">
            <div class="psych-label">CONTROLLO EMOTIVO</div>
            <div class="psych-value">${Math.round(flow.emotionalControl)}%</div>
            <div class="psych-bar"><div class="psych-fill" style="width:${flow.emotionalControl}%"></div></div>
        </div>
    </div>`;
}

function renderMatchSimulation(sim){
    return`
    <div class="simulation-grid">
        <div class="sim-card">
            <div class="sim-label">PROSSIMO ATTACCO</div>
            <div class="sim-value">${sim.attackingTeam}</div>
            <div class="sim-desc">Squadra più probabile a generare pressione offensiva.</div>
        </div>

        <div class="sim-card">
            <div class="sim-label">PROBABILITÀ TIRO</div>
            <div class="sim-value">${Math.round(sim.shotProbability)}%</div>
            <div class="sim-bar"><div class="sim-fill" style="width:${sim.shotProbability}%"></div></div>
        </div>

        <div class="sim-card">
            <div class="sim-label">PROBABILITÀ GOL</div>
            <div class="sim-value">${Math.round(sim.goalProbability)}%</div>
            <div class="sim-bar"><div class="sim-fill danger" style="width:${sim.goalProbability}%"></div></div>
        </div>

        <div class="sim-card">
            <div class="sim-label">ONDA DI PRESSIONE</div>
            <div class="sim-value">${Math.round(sim.pressureWave)}%</div>
            <div class="sim-bar"><div class="sim-fill" style="width:${sim.pressureWave}%"></div></div>
        </div>

        <div class="sim-card">
            <div class="sim-label">RISCHIO CROLLO</div>
            <div class="sim-value">${Math.round(sim.collapseRisk)}%</div>
            <div class="sim-bar"><div class="sim-fill danger" style="width:${sim.collapseRisk}%"></div></div>
        </div>

        <div class="sim-card sim-main-card">
            <div class="sim-label">SCENARIO</div>
            <div class="sim-value">Prossimi 5 minuti</div>
            <div class="sim-desc">${sim.scenario}</div>
        </div>
    </div>`;
}

function renderTacticalIdentity(identity){
    const card=(id)=>`
    <div class="identity-card">
        <div class="identity-team">${id.teamName}</div>
        <div class="identity-label">IDENTITÀ TATTICA</div>
        <div class="identity-value">${id.icon} ${id.style}</div>
        <div class="identity-desc">${id.desc}</div>
        <div class="identity-bar">
            <div class="identity-fill" style="width:${id.identityScore}%"></div>
        </div>
        <div class="identity-tags">
            ${id.tags.map(t=>`<span class="identity-tag">${t}</span>`).join("")}
        </div>
    </div>`;

    return`
    <div class="identity-grid">
        <div class="identity-card identity-card-main">
            <div class="identity-label">DNA TATTICO PARTITA</div>
            <div class="identity-value">${identity.matchDNA}</div>
            <div class="identity-desc">
                Identità live calcolata da pressione, pericolo, momentum, stress, fiducia e xG già presenti nella pagina.
            </div>
            <div class="identity-tags">
                <span class="identity-tag">DATI LIVE</span>
                <span class="identity-tag">LETTURA TATTICA</span>
                <span class="identity-tag">MATCHIQ</span>
            </div>
        </div>
        ${card(identity.homeId)}
        ${card(identity.awayId)}
    </div>`;
}

function renderAttackPrediction(a){
    return`
    <div class="attack-wrapper">
        <div class="attack-map">
            <div class="attack-zone zone-left ${a.lane==="left"?"active":""}">FASCIA SINISTRA<br>Zona laterale</div>
            <div class="attack-zone zone-center ${a.lane==="center"?"active":""}">ZONA CENTRALE<br>Rifinitura</div>
            <div class="attack-zone zone-right ${a.lane==="right"?"active":""}">FASCIA DESTRA<br>Zona laterale</div>
            <div class="attack-arrow arrow-${a.lane}"></div>
        </div>

        <div class="attack-side-panel">
            <div class="attack-card">
                <div class="attack-label">FLUSSO OFFENSIVO</div>
                <div class="attack-value">${a.label}</div>
                <div class="attack-desc">${a.desc}</div>
                <div class="attack-tags">
                    <span class="attack-tag">SQUADRA: ${a.team}</span>
                    <span class="attack-tag">DATI LIVE</span>
                </div>
            </div>

            <div class="attack-card">
                <div class="attack-label">INTENSITÀ OFFENSIVA</div>
                <div class="attack-value">${Math.round(a.power)}%</div>
                <div class="attack-bar"><div class="attack-fill" style="width:${a.power}%"></div></div>
            </div>

            <div class="attack-card">
                <div class="attack-label">RISCHIO INGRESSO AREA</div>
                <div class="attack-value">${Math.round(a.box)}%</div>
                <div class="attack-bar"><div class="attack-fill danger" style="width:${a.box}%"></div></div>
            </div>

            <div class="attack-card">
                <div class="attack-label">PROBABILITÀ SOVRACCARICO</div>
                <div class="attack-value">${Math.round(a.overload)}%</div>
                <div class="attack-bar"><div class="attack-fill" style="width:${a.overload}%"></div></div>
            </div>
        </div>
    </div>`;
}
function renderCinematicEvents(){
    if(!cinematicEvents.length){
        return`
        <div class="event-card info">
            <div class="event-label">FEED EVENTI LIVE</div>
            <div class="event-value">Monitoraggio attivo</div>
            <div class="event-desc">Nessuno shock live rilevato nell’ultimo aggiornamento.</div>
        </div>`;
    }

    return`
    <div class="event-grid">
        ${cinematicEvents.map(e=>`
            <div class="event-card ${e.level}">
                <div class="event-time">${e.time}</div>
                <div class="event-title">${e.title}</div>
                <div class="event-desc">${e.text}</div>
            </div>
        `).join("")}
    </div>`;
}

function renderMomentumCinematic(momentum){
    const heatClass=momentum.temperature>=65?"hot":"cold";
    const spikeLevel=momentum.dangerPulse>=70?"critical":momentum.pressurePulse>=60?"warning":"";
    const spikeText=momentum.dangerPulse>=70
        ? "Picco di pericolo attivo"
        : momentum.pressurePulse>=60
            ? "Pressione in crescita"
            : "Flusso stabile";

    return`
    <div class="momentum-cinematic-wrap">
        <div class="momentum-panel">
            <div class="momentum-pro-header">
                <div>
                    <div class="momentum-pro-title">📈 Grafico momentum live</div>
                    <div class="momentum-pro-subtitle">
                        Grafico dinamico basato su momentum, pressione, pericolo live e temperatura partita.
                    </div>
                </div>
                <div class="momentum-pro-badges">
                    <span class="momentum-pro-badge ${heatClass}">TEMP ${Math.round(momentum.temperature)}/100</span>
                    <span class="momentum-pro-badge">MIN ${Math.round(momentum.minute)}'</span>
                    <span class="momentum-pro-badge ${spikeLevel}">${spikeText}</span>
                </div>
            </div>

            <div class="momentum-temp">
                <div class="temp-top">
                    <div>
                        <div class="temp-label">TEMPERATURA MATCH</div>
                        <div class="temp-status">${momentum.tempLabel}</div>
                    </div>
                    <div class="temp-status">${Math.round(momentum.temperature)} / 100</div>
                </div>
                <div class="temp-track">
                    <div class="temp-fill" style="width:${momentum.temperature}%"></div>
                </div>
                <div class="momentum-desc">${momentum.tempText}</div>
            </div>

            <div class="chart-box momentum-pro-chart">
                <canvas id="momentumChart"></canvas>
            </div>

            <div class="momentum-live-strip">
                <div class="momentum-live-chip">
                    <div class="momentum-live-label">MOMENTUM CASA</div>
                    <div class="momentum-live-value">${Math.round(momentum.homeM)}%</div>
                    <div class="momentum-live-note">Momentum casa aggiornato live.</div>
                </div>
                <div class="momentum-live-chip">
                    <div class="momentum-live-label">MOMENTUM TRASFERTA</div>
                    <div class="momentum-live-value">${Math.round(momentum.awayM)}%</div>
                    <div class="momentum-live-note">Momentum trasferta aggiornato live.</div>
                </div>
                <div class="momentum-live-chip">
                    <div class="momentum-live-label">DIFFERENZA INERZIA</div>
                    <div class="momentum-live-value">${Math.round(momentum.gap)}</div>
                    <div class="momentum-live-note">Differenza di spinta tra le due squadre.</div>
                </div>
            </div>

            <div class="momentum-spike-feed">
                <div class="momentum-spike-item ${spikeLevel}">
                    <span><strong>${momentum.swing}</strong> — ${momentum.swingText}</span>
                    <span>${Math.round(momentum.pressurePulse)}%</span>
                </div>
                <div class="momentum-spike-item ${momentum.dangerPulse>=70?"critical":""}">
                    <span><strong>Pericolo live</strong> — rischio fase offensiva improvvisa</span>
                    <span>${Math.round(momentum.dangerPulse)}%</span>
                </div>
            </div>
        </div>

        <div class="momentum-stats-grid">
            <div class="momentum-stat">
                <div class="momentum-label">INERZIA MATCH</div>
                <div class="momentum-value">${momentum.swing}</div>
                <div class="momentum-desc">${momentum.swingText}</div>
            </div>

            <div class="momentum-stat">
                <div class="momentum-label">PRESSIONE LIVE</div>
                <div class="momentum-value">${Math.round(momentum.pressurePulse)}%</div>
                <div class="momentum-bar">
                    <div class="momentum-fill" style="width:${momentum.pressurePulse}%"></div>
                </div>
            </div>

            <div class="momentum-stat">
                <div class="momentum-label">PERICOLO LIVE</div>
                <div class="momentum-value">${Math.round(momentum.dangerPulse)}%</div>
                <div class="momentum-bar">
                    <div class="momentum-fill danger" style="width:${momentum.dangerPulse}%"></div>
                </div>
            </div>
        </div>
    </div>`;
}

function renderXg(xg){
    const h=safeNumber(xg.home_xg,0);
    const a=safeNumber(xg.away_xg,0);
    const t=h+a||1;

    return`
    <div class="xg-grid">
        <div class="xg-card"><div class="xg-title">xG casa</div><div class="xg-value">${h.toFixed(2)}</div></div>
        <div class="xg-card"><div class="xg-title">xG trasferta</div><div class="xg-value">${a.toFixed(2)}</div></div>
        <div class="xg-card"><div class="xg-title">Grandi occasioni casa</div><div class="xg-value">${xg.home_big_chances??0}</div></div>
        <div class="xg-card"><div class="xg-title">Grandi occasioni trasferta</div><div class="xg-value">${xg.away_big_chances??0}</div></div>
        <div class="xg-card"><div class="xg-title">Qualità tiri casa</div><div class="xg-value">${xg.home_shot_quality??0}</div></div>
        <div class="xg-card"><div class="xg-title">Qualità tiri trasferta</div><div class="xg-value">${xg.away_shot_quality??0}</div></div>
        <div class="xg-card"><div class="xg-title">Pericolo xT casa</div><div class="xg-value">${xg.home_xthreat??0}</div></div>
        <div class="xg-card"><div class="xg-title">Pericolo xT trasferta</div><div class="xg-value">${xg.away_xthreat??0}</div></div>
    </div>

    <div class="xg-bar">
        <div class="xg-home-bar" style="width:${(h/t)*100}%"></div>
        <div class="xg-away-bar" style="width:${(a/t)*100}%"></div>
    </div>

    <div class="dominant-box">
        Dominio xG: <strong>${xg.dominance||"Equilibrio"}</strong>
    </div>`;
}

function renderFuture(f){
    return`
    <div class="future-grid">
        <div class="future-card">
            <div class="future-title">PROSSIMO GOL</div>
            <div class="future-value">${f.next_goal_probability??"--"}%</div>
        </div>

        <div class="future-card">
            <div class="future-title">CONTROPIEDE</div>
            <div class="future-value">${f.counter_attack_risk??"--"}</div>
        </div>

        <div class="future-card">
            <div class="future-title">RISCHIO CROLLO</div>
            <div class="future-value">${f.collapse_risk??"--"}</div>
        </div>

        <div class="future-card">
            <div class="future-title">FATICA</div>
            <div class="future-value">${f.fatigue_warning??"--"}</div>
        </div>

        <div class="future-card prediction-card">
            <div class="future-title">PREVISIONE</div>
            <div class="future-prediction">${f.prediction??"Previsione non disponibile."}</div>
            <div class="future-confidence">Affidabilità: ${f.confidence??"--"}%</div>
        </div>
    </div>`;
}

function renderCoach(items){
    if(!items.length){
        return`
        <div class="coach-card coach-low">
            <div class="coach-message">Coach tattico non disponibile.</div>
        </div>`;
    }

    return`
    <div class="coach-grid">
        ${items.map(i=>{
            const p=String(i.priority||"LOW").toUpperCase();
            const cls=p==="HIGH"?"coach-high":p==="MEDIUM"?"coach-medium":"coach-low";

            return`
            <div class="coach-card ${cls}">
                <div class="coach-top">
                    <span class="coach-type">${i.type||"TACTICO"}</span>
                    <span class="coach-priority">${p}</span>
                </div>
                <div class="coach-team">${i.team||"MATCH"}</div>
                <div class="coach-message">${i.message||""}</div>
            </div>`;
        }).join("")}
    </div>`;
}
function renderPlayers(players){
    if(!players.length)return"Pagelle giocatori non disponibili.";

    return`
    <div class="players-grid">
        ${players.slice(0,12).map((p,i)=>{
            const r=safeNumber(p.rating,6.5);
            let cls="rating-mid";

            if(r>=8)cls="rating-elite";
            else if(r>=7)cls="rating-good";
            else if(r<6)cls="rating-low";

            return`
            <div class="player-card">
                ${i===0?`<div class="mvp-badge">MVP</div>`:""}
                <div class="player-top">
                    <div>
                        <div class="player-name">${p.name||"Giocatore"}</div>
                        <div class="player-role">${p.role||p.position||"N/A"} • ${p.team||""}</div>
                    </div>
                    <div class="player-rating ${cls}">${r.toFixed(1)}</div>
                </div>

                <div class="player-stats">
                    <div class="player-stat">
                        <span class="player-stat-label">Pericolo</span>
                        <span class="player-stat-value">${Math.round(safeNumber(p.danger))}</span>
                    </div>
                    <div class="player-stat">
                        <span class="player-stat-label">Fatica</span>
                        <span class="player-stat-value">${Math.round(safeNumber(p.fatigue))}%</span>
                    </div>
                    <div class="player-stat">
                        <span class="player-stat-label">Aggressività</span>
                        <span class="player-stat-value">${Math.round(safeNumber(p.aggression))}</span>
                    </div>
                    <div class="player-stat">
                        <span class="player-stat-label">Stato</span>
                        <span class="player-stat-value">${p.status||"STABILE"}</span>
                    </div>
                </div>
            </div>`;
        }).join("")}
    </div>`;
}

function classifyCommentarySeverity(text){
    const t=String(text||"").toLowerCase();

    if(
        t.includes("caot")||
        t.includes("altissima intensità")||
        t.includes("momento decisivo")||
        t.includes("cambia tutto")
    ){
        return {level:"chaos",label:"INTENSITÀ",icon:"🌪️"};
    }

    if(
        t.includes("pericol")||
        t.includes("sotto forte pressione")||
        t.includes("difesa")||
        t.includes("probabilità gol")||
        t.includes("gol")
    ){
        return {level:"danger",label:"PERICOLO",icon:"🚨"};
    }

    if(
        t.includes("pressione")||
        t.includes("momentum")||
        t.includes("ritmo")||
        t.includes("intensità")||
        t.includes("transizioni")
    ){
        return {level:"warning",label:"PRESSIONE",icon:"🔥"};
    }

    return {level:"normal",label:"LIVE",icon:"🧠"};
}

function getCommentaryLines(data,aiCore){
    const fromNewEngine=Array.isArray(data.ai_commentary?.commentary)
        ? data.ai_commentary.commentary
        : [];

    const fromCore=Array.isArray(aiCore.commentary)
        ? aiCore.commentary
        : [];

    const merged=[...fromNewEngine,...fromCore]
        .filter(Boolean)
        .map(x=>String(x).trim())
        .filter(Boolean);

    return [...new Set(merged)].slice(0,6);
}

function renderAICommentary(commentary,match){
    if(!commentary||!commentary.length){
        return `<div class="ai-commentary-empty">Commento tattico non disponibile.</div>`;
    }

    const minute=safeNumber(match?.minute,0);

    return`
    <div class="ai-commentary-wrap">
        ${commentary.map((line,index)=>{
            const s=classifyCommentarySeverity(line);

            return`
            <div class="ai-commentary-card ${s.level}" style="animation-delay:${index*90}ms">
                <div class="ai-commentary-icon">${s.icon}</div>
                <div class="ai-commentary-top">
                    <div class="ai-commentary-severity">${s.label}</div>
                    <div class="ai-commentary-time">${minute}' • LIVE</div>
                </div>
                <div class="ai-commentary-text">${line}</div>
            </div>`;
        }).join("")}
    </div>`;
}

function renderWinProbability(p){
    const h=clamp(p.home_win??p.home??33.3);
    const d=clamp(p.draw??33.4);
    const a=clamp(p.away_win??p.away??33.3);
    const dom=String(p.dominant_outcome||"draw").toUpperCase();

    const readableDom =
        dom === "HOME"
            ? "Casa"
            : dom === "AWAY"
                ? "Trasferta"
                : dom === "DRAW"
                    ? "Pareggio"
                    : dom;

    return`
    <div class="win-prob-wrapper">
        <div class="prob-box">
            <div class="prob-label">VITTORIA CASA</div>
            <div class="prob-value">${h}%</div>
        </div>

        <div class="prob-box">
            <div class="prob-label">PAREGGIO</div>
            <div class="prob-value">${d}%</div>
        </div>

        <div class="prob-box">
            <div class="prob-label">VITTORIA TRASFERTA</div>
            <div class="prob-value">${a}%</div>
        </div>
    </div>

    <div class="prob-bar">
        <div class="prob-home-bar" style="width:${h}%"></div>
        <div class="prob-draw-bar" style="width:${d}%"></div>
        <div class="prob-away-bar" style="width:${a}%"></div>
    </div>

    <div class="dominant-box">
        Esito dominante: <strong>${readableDom}</strong>
    </div>`;
}

function renderBar(label,value,extraClass){
    const w=clamp(value);

    return`
    <div class="metric">
        <div class="metric-label">${label}: ${Math.round(w)}</div>
        <div class="bar">
            <div class="bar-fill ${extraClass}" style="width:${w}%"></div>
        </div>
    </div>`;
}