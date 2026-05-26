/*
    MatchIQ - Match Render Module
    Rendering principale pagina match + momentum chart.
*/

function render(data){
    const match=data.match||{};
    const tactical=data.tactical_analysis||{};
    const pressure=data.pressure_engine||{};
    const aiCore=data.ai_core||{};
    const winProb=getWinProbability(data);
    const players=getPlayers(data);
    const coach=getCoach(data);
    const future=getFuture(data);
    const xg=getXg(data);

    const homePressure=clamp(pressure.home?.pressure??tactical.home_pressure??0);
    const awayPressure=clamp(pressure.away?.pressure??tactical.away_pressure??0);
    const homeDanger=clamp(pressure.home?.danger??tactical.home_danger??0);
    const awayDanger=clamp(pressure.away?.danger??tactical.away_danger??0);

    const score=getScore(match);
    const alerts=getAlerts(data);
    const timeline=getTimeline(data);
    const commentary=getCommentaryLines(data,aiCore);

    const homeGlow=clamp(Math.max(homePressure,homeDanger),8,100);
    const awayGlow=clamp(Math.max(awayPressure,awayDanger),8,100);

    const home=match.home||match.home_team||"Home";
    const away=match.away||match.away_team||"Away";

    const flow=calculateLiveFlowVisual(data);
    const simulation=generateMatchSimulation(data,flow);
    const identity=generateTacticalIdentity(data,flow);
    const attack=generateAttackPrediction(data,flow);
    const momentum=generateMomentumCinematic(data,flow,simulation);

    const snapshot=buildSnapshot(data,flow,simulation,momentum);
    const change=detectCinematicEvents(snapshot);
    const scorePulse=change.scoreChanged?"score-pulse":"";

    if(change.major){
        showLiveOverlay(
            change.messages[0]||"⚡ LIVE CHANGE",
            `Aggiornamento rilevato: ${change.messages.join(" • ")}`
        );
    }

    previousSnapshot=snapshot;

    const app=document.getElementById("app");
    if(!app)return;

    app.innerHTML=`
    <div class="card ${change.changed?"live-flash":""}">
        <div class="section-content">${renderLiveFlowVisual(flow)}</div>
    </div>

    <div class="card match-header ${change.scoreChanged?"live-flash":""}">
        <div class="match-row">
            <div class="team">
                <img src="${match.home_logo||""}" alt="${home}">
                <div class="team-name">${home}</div>
            </div>

            <div class="score-center">
                <div class="score ${scorePulse}">${score.home}-${score.away}</div>
                <div class="minute">${safeNumber(match.minute,0)}'</div>
                <div class="league">${match.league||""}</div>
            </div>

            <div class="team">
                <img src="${match.away_logo||""}" alt="${away}">
                <div class="team-name">${away}</div>
            </div>
        </div>
    </div>

    ${renderSection("psych","🧠","Psychological Live Engine",renderPsychologicalEngine(flow,home,away))}
    ${renderSection("sim","🔥","Match Simulation Engine — Next 5 Minutes",renderMatchSimulation(simulation))}
    ${renderSection("identity","🧬","Team Tactical Identity Engine",renderTacticalIdentity(identity))}
    ${renderSection("attack","🗺️","Attack Prediction Map Engine",renderAttackPrediction(attack))}
    ${renderSection("events","⚡","Live Event Cinematic System",renderCinematicEvents(),change.changed)}
    ${renderSection("momentum","📈","Momentum Engine Cinematico",renderMomentumCinematic(momentum),change.changed)}
    ${renderSection("win","🔥","AI Win Probability",renderWinProbability(winProb))}
    ${renderSection("future","🔮","AI Future Prediction",renderFuture(future))}
    ${renderSection("xg","⚽","Live xG Analysis",renderXg(xg))}

    ${renderSection("alerts","🚨","Live Tactical Alerts",`
        <div class="alert-grid">
            ${
                alerts.length
                ? alerts.map(a=>`
                    <div class="alert-box ${
                        String(a.level||a.type||"").toUpperCase().includes("HIGH")
                            ?"high"
                            :String(a.level||a.type||"").toUpperCase().includes("MEDIUM")
                                ?"medium"
                                :""
                    }">
                        <strong>${a.title||a.type||"AI Alert"}</strong><br>
                        ${a.message||a.detail||""}
                    </div>
                `).join("")
                : `<div class="alert-box"><strong>Nessun alert critico</strong><br>Match sotto controllo.</div>`
            }
        </div>
    `)}

    ${renderSection("coach","🧠","Tactical Coach AI",renderCoach(coach))}

    ${renderSection("tactical","📊","Tactical Analysis",`
        <div class="analysis-grid">
            <div>
                ${renderBar("Home Pressure",homePressure,"")}
                ${renderBar("Away Pressure",awayPressure,"away")}
                ${renderBar("Home Danger",homeDanger,"")}
                ${renderBar("Away Danger",awayDanger,"away")}
            </div>

            <div class="side-stats">
                <div>Dominant Team: <strong>${pressure.dominant_team||"Equilibrio"}</strong></div>
                <div>Dominance: <strong>${pressure.dominance_label||"N/A"}</strong></div>
                <div>Goal Prob. Home: <strong>${pressure.home?.goal_probability??"N/A"}</strong></div>
                <div>Goal Prob. Away: <strong>${pressure.away?.goal_probability??"N/A"}</strong></div>
                <div>Match Tempo: <strong>${getTempoLabel(tactical.match_tempo||aiCore.match_tempo)}</strong></div>
                <div>AI Confidence: <strong>${aiCore.confidence_score||"N/A"}</strong></div>
            </div>
        </div>
    `)}

    ${renderSection("heatmap","🔥","Tactical Heatmap PRO",`
        <div class="heatmap-wrapper">
            <div class="pitch">
                <div class="pitch-lines"></div>
                <div class="center-circle"></div>

                <div
                    class="glow home-glow"
                    style="opacity:${homeGlow/100};width:${280+homeGlow*4}px;height:${280+homeGlow*4}px;">
                </div>

                <div
                    class="glow away-glow"
                    style="opacity:${awayGlow/100};width:${280+awayGlow*4}px;height:${280+awayGlow*4}px;">
                </div>

                <div class="zone-label" style="left:16%;top:12%;">HOME PRESSURE</div>
                <div class="zone-label" style="left:44%;top:12%;">CENTRAL ZONE</div>
                <div class="zone-label" style="right:16%;top:12%;">AWAY PRESSURE</div>
                <div class="zone-label" style="left:43%;bottom:10%;">TRANSITION ZONE</div>
            </div>

            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background:#2f6bff"></div>
                    ${home}: ${Math.round(homePressure)} pressure / ${Math.round(homeDanger)} danger
                </div>

                <div class="legend-item">
                    <div class="legend-color" style="background:#ff315c"></div>
                    ${away}: ${Math.round(awayPressure)} pressure / ${Math.round(awayDanger)} danger
                </div>
            </div>
        </div>
    `)}

    ${renderSection("players","⭐","AI Player Ratings",renderPlayers(players))}
    ${renderSection("commentary","🧠","AI Commentary",renderAICommentary(commentary,match),change.changed)}

    ${renderSection(
        "timeline",
        "⏱️",
        "AI Timeline",
        timeline.length
            ? `<div class="timeline-scroll">
                ${timeline.slice(0,8).map(ev=>`
                    <div class="timeline-event">
                        <div class="timeline-minute">${safeNumber(ev.minute,0)}'</div>
                        <div>${ev.icon||"🧠"} ${ev.title||ev.type||"Evento"}</div>
                        <div style="color:#dce7ff;margin-top:5px;">
                            ${ev.message||ev.detail||ev.text||""}
                        </div>
                    </div>
                `).join("")}
            </div>`
            : "Timeline non disponibile."
    )}

    ${renderSection("report","📑","AI Match Report",`<div class="report-box">${getReport(data)}</div>`)}
    `;

    initToggles();
    buildMomentumChart(momentum);
}

function updateMomentumHistory(momentum){
    const minute=Math.round(clamp(momentum.minute,0,120));
    const signature=`${minute}-${Math.round(momentum.homeM)}-${Math.round(momentum.awayM)}-${Math.round(momentum.temperature)}`;

    if(lastMomentumSignature===signature && momentumHistory.length>0)return;

    lastMomentumSignature=signature;

    momentumHistory.push({
        minute,
        home:clamp(momentum.homeM),
        away:clamp(momentum.awayM),
        temp:clamp(momentum.temperature),
        pressure:clamp(momentum.pressurePulse),
        danger:clamp(momentum.dangerPulse),
        swing:momentum.swing
    });

    const seen=new Map();

    momentumHistory.forEach(p=>{
        seen.set(p.minute,p);
    });

    momentumHistory=[...seen.values()]
        .sort((a,b)=>a.minute-b.minute)
        .slice(-14);
}

function createMomentumSeries(momentum){
    updateMomentumHistory(momentum);

    if(momentumHistory.length>=3){
        return {
            labels:momentumHistory.map(p=>`${p.minute}'`),
            home:momentumHistory.map(p=>p.home),
            away:momentumHistory.map(p=>p.away),
            temp:momentumHistory.map(p=>p.temp),
            danger:momentumHistory.map(p=>p.danger),
            pressure:momentumHistory.map(p=>p.pressure),
            spikePoints:momentumHistory.map(p=>p.danger>=70||p.pressure>=72?p.temp:null)
        };
    }

    const h=clamp(momentum.homeM);
    const a=clamp(momentum.awayM);
    const temp=clamp(momentum.temperature);
    const pressure=clamp(momentum.pressurePulse);
    const danger=clamp(momentum.dangerPulse);
    const minute=Math.round(clamp(momentum.minute,0,90));
    const labels=[0,15,30,45,60,75,90].map(m=>`${m}'`);

    return {
        labels,
        home:[
            clamp(h-16+temp*.05),
            clamp(h-10+pressure*.03),
            clamp(h-5+danger*.03),
            clamp(h+3),
            clamp(h+8-temp*.02),
            clamp(h+4),
            clamp(h)
        ],
        away:[
            clamp(a+12-temp*.03),
            clamp(a+7-danger*.02),
            clamp(a+3),
            clamp(a-2+pressure*.03),
            clamp(a-7+temp*.03),
            clamp(a-3),
            clamp(a)
        ],
        temp:[
            clamp(temp-24),
            clamp(temp-17),
            clamp(temp-10),
            clamp(temp-2),
            clamp(temp+5),
            clamp(temp+2),
            clamp(temp)
        ],
        danger:[
            clamp(danger-20),
            clamp(danger-14),
            clamp(danger-8),
            clamp(danger-2),
            clamp(danger+4),
            clamp(danger+2),
            clamp(danger)
        ],
        pressure:[
            clamp(pressure-18),
            clamp(pressure-12),
            clamp(pressure-6),
            clamp(pressure),
            clamp(pressure+5),
            clamp(pressure+2),
            clamp(pressure)
        ],
        spikePoints:labels.map((_,i)=>
            i===Math.min(6,Math.max(0,Math.round(minute/15))) && (danger>=70||pressure>=72)
                ? temp
                : null
        )
    };
}

function buildMomentumChart(momentum){
    const canvas=document.getElementById("momentumChart");
    if(!canvas)return;

    if(momentumChart)momentumChart.destroy();

    const series=createMomentumSeries(momentum);

    momentumChart=new Chart(canvas,{
        type:"line",
        data:{
            labels:series.labels,
            datasets:[
                {
                    label:"Home Momentum",
                    data:series.home,
                    borderColor:"#2f6bff",
                    backgroundColor:"rgba(47,107,255,.20)",
                    fill:true,
                    tension:.42,
                    pointRadius:4,
                    pointHoverRadius:7,
                    borderWidth:3
                },
                {
                    label:"Away Momentum",
                    data:series.away,
                    borderColor:"#ff315c",
                    backgroundColor:"rgba(255,49,92,.18)",
                    fill:true,
                    tension:.42,
                    pointRadius:4,
                    pointHoverRadius:7,
                    borderWidth:3
                },
                {
                    label:"Match Temperature",
                    data:series.temp,
                    borderColor:"#ffb020",
                    backgroundColor:"rgba(255,176,32,.08)",
                    fill:false,
                    tension:.35,
                    pointRadius:2,
                    borderWidth:2,
                    borderDash:[8,6]
                },
                {
                    label:"Danger Pulse",
                    data:series.danger,
                    borderColor:"rgba(255,255,255,.60)",
                    backgroundColor:"rgba(255,255,255,.05)",
                    fill:false,
                    tension:.28,
                    pointRadius:0,
                    borderWidth:1,
                    borderDash:[2,6]
                },
                {
                    label:"Spike Alert",
                    data:series.spikePoints,
                    borderColor:"#ffffff",
                    backgroundColor:"#ff315c",
                    showLine:false,
                    pointRadius:7,
                    pointHoverRadius:10,
                    pointStyle:"rectRot"
                }
            ]
        },
        options:{
            responsive:true,
            maintainAspectRatio:false,
            animation:{
                duration:900,
                easing:"easeOutQuart"
            },
            interaction:{
                mode:"index",
                intersect:false
            },
            plugins:{
                legend:{
                    labels:{
                        color:"white",
                        font:{weight:"bold"},
                        boxWidth:14,
                        usePointStyle:true
                    }
                },
                tooltip:{
                    backgroundColor:"rgba(2,8,23,.95)",
                    borderColor:"rgba(255,255,255,.12)",
                    borderWidth:1,
                    titleColor:"#ffffff",
                    bodyColor:"#dbe7ff",
                    callbacks:{
                        label:function(ctx){
                            if(ctx.raw===null)return null;
                            return `${ctx.dataset.label}: ${Math.round(ctx.raw)}%`;
                        }
                    }
                }
            },
            scales:{
                x:{
                    ticks:{
                        color:"#dbe7ff",
                        font:{weight:"bold"}
                    },
                    grid:{
                        color:"rgba(255,255,255,.06)"
                    }
                },
                y:{
                    min:0,
                    max:100,
                    ticks:{
                        color:"#dbe7ff",
                        font:{weight:"bold"}
                    },
                    grid:{
                        color:"rgba(255,255,255,.06)"
                    }
                }
            }
        }
    });
}