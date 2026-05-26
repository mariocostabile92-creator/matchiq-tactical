/*
    MatchIQ - Match Flow Module
    Logica AI/tattica per Live Flow, simulazione, identità tattica,
    previsioni offensive, momentum cinematico ed eventi live.
*/

function calculateLiveFlowVisual(data){
    const match=data.match||{};
    const tactical=data.tactical_analysis||{};
    const pressure=data.pressure_engine||{};
    const liveFlow=data.live_flow||{};
    const aiCore=data.ai_core||{};
    const xg=getXg(data);
    const score=getScore(match);

    const homePressure=clamp(pressure.home?.pressure??tactical.home_pressure??0);
    const awayPressure=clamp(pressure.away?.pressure??tactical.away_pressure??0);
    const homeDanger=clamp(pressure.home?.danger??tactical.home_danger??0);
    const awayDanger=clamp(pressure.away?.danger??tactical.away_danger??0);
    const homeMomentum=clamp(liveFlow.home?.momentum??homePressure);
    const awayMomentum=clamp(liveFlow.away?.momentum??awayPressure);

    const momentumGap=Math.abs(homeMomentum-awayMomentum);
    const pressureGap=Math.abs(homePressure-awayPressure);
    const dangerMax=Math.max(homeDanger,awayDanger);
    const pressureMax=Math.max(homePressure,awayPressure);
    const xgGap=Math.abs(safeNumber(xg.home_xg,0)-safeNumber(xg.away_xg,0));
    const goalShock=Math.abs(score.home-score.away)>=2&&safeNumber(match.minute,0)<60;

    let chaosIndex=clamp(dangerMax*.35+pressureMax*.22+momentumGap*.18+xgGap*12+(goalShock?12:0));

    let status="🔵 BALANCED";
    let statusClass="status-balanced";
    let subtitle="Match equilibrato: nessuna squadra sta prendendo il controllo totale.";

    if(chaosIndex>=72){
        status="⚡ CHAOTIC MATCH";
        statusClass="status-chaos pulse-danger";
        subtitle="Partita instabile: intensità, pericolo e transizioni stanno aumentando.";
    }else if(dangerMax>=72||pressureMax>=75){
        status="🔥 HIGH PRESSURE";
        statusClass="status-pressure pulse-danger";
        subtitle="Pressione alta rilevata: una fase critica può cambiare il match.";
    }else if(homeMomentum-awayMomentum>=18||homePressure-awayPressure>=22){
        status="🔴 DOMINATING HOME";
        statusClass="status-home";
        subtitle="La squadra di casa sta imponendo ritmo, territorio e pressione.";
    }else if(awayMomentum-homeMomentum>=18||awayPressure-homePressure>=22){
        status="🟣 DOMINATING AWAY";
        statusClass="status-away";
        subtitle="Gli ospiti stanno prendendo campo e aumentando la pericolosità.";
    }else if(momentumGap<=12&&pressureGap<=14&&chaosIndex>=35){
        status="🧠 TACTICAL BATTLE";
        statusClass="status-tactical";
        subtitle="Battaglia tattica aperta: equilibrio ma con segnali di instabilità.";
    }

    const chaosLabel=chaosIndex<30?"CONTROLLED":chaosIndex<60?"VOLATILE":"CHAOTIC";
    const chaosClass=chaosIndex<30?"chaos-low":chaosIndex<60?"chaos-mid":"chaos-high";

    const dominant=homeMomentum>awayMomentum
        ? match.home||match.home_team||"Home"
        : awayMomentum>homeMomentum
            ? match.away||match.away_team||"Away"
            : "Equilibrio";

    const confidenceHome=clamp(50+(homeMomentum-awayMomentum)/2+(homePressure-awayPressure)/3);
    const confidenceAway=clamp(50+(awayMomentum-homeMomentum)/2+(awayPressure-homePressure)/3);
    const panicHome=clamp(awayDanger*.55+awayPressure*.25+(score.away>score.home?18:0));
    const panicAway=clamp(homeDanger*.55+homePressure*.25+(score.home>score.away?18:0));
    const fatiguePressure=clamp((safeNumber(match.minute,0)*.45)+((homePressure+awayPressure)/4));
    const emotionalControl=clamp(100-((panicHome+panicAway)/2)+(100-chaosIndex)*.15);

    const story=generateLiveStory({
        dominant,chaosIndex,homeDanger,awayDanger,homeMomentum,awayMomentum,
        home:match.home||match.home_team||"Home",
        away:match.away||match.away_team||"Away",
        backendStory:liveFlow.story||aiCore.live_flow_story
    });

    const alerts=generateFlowAlerts({
        chaosIndex,homeDanger,awayDanger,homeMomentum,awayMomentum,homePressure,awayPressure,
        home:match.home||match.home_team||"Home",
        away:match.away||match.away_team||"Away"
    });

    return{
        status,statusClass,subtitle,chaosIndex,chaosLabel,chaosClass,dominant,
        confidenceHome,confidenceAway,panicHome,panicAway,fatiguePressure,
        emotionalControl,story,alerts,homeMomentum,awayMomentum
    };
}

function generateLiveStory(ctx){
    if(ctx.backendStory)return ctx.backendStory;

    if(ctx.chaosIndex>=72)return`Il match è entrato in una fase caotica: transizioni rapide, pressione crescente e margine d’errore sempre più basso. ${ctx.dominant} sta vivendo il momento più influente della partita.`;
    if(ctx.homeDanger>=75)return`${ctx.home} sta creando una zona di pericolo costante. La difesa ospite è sotto stress e il prossimo episodio può pesare molto.`;
    if(ctx.awayDanger>=75)return`${ctx.away} sta aumentando la minaccia offensiva. La squadra di casa sta perdendo controllo emotivo e territoriale.`;
    if(ctx.homeMomentum-ctx.awayMomentum>=18)return`${ctx.home} sta imponendo il proprio ritmo: più intensità, più controllo e maggiore fiducia nella fase live.`;
    if(ctx.awayMomentum-ctx.homeMomentum>=18)return`Momentum invertito: ${ctx.away} sta reagendo e sta spostando il flusso tattico dalla propria parte.`;
    if(ctx.chaosIndex>=45)return`Partita tatticamente instabile: nessuna squadra domina del tutto, ma il livello di pressione può generare un cambio improvviso.`;

    return`Match in equilibrio controllato: le squadre stanno gestendo ritmo, pressione e rischio senza esporsi troppo.`;
}

function generateFlowAlerts(ctx){
    const alerts=[];

    if(ctx.chaosIndex>=75)alerts.push({type:"critical",title:"⚡ MOMENTUM SHIFT DETECTED",text:"Il flusso del match è altamente instabile."});

    if(Math.max(ctx.homeDanger,ctx.awayDanger)>=78){
        const team=ctx.homeDanger>ctx.awayDanger?ctx.home:ctx.away;
        alerts.push({type:"critical",title:"🚨 DANGER ZONE",text:`${team} è entrata in una fase offensiva ad alto rischio.`});
    }

    if(Math.max(ctx.homePressure,ctx.awayPressure)>=76){
        const team=ctx.homePressure>ctx.awayPressure?ctx.home:ctx.away;
        alerts.push({type:"warning",title:"🔥 PRESSURE SPIKE",text:`Pressione elevata rilevata per ${team}.`});
    }

    if(Math.abs(ctx.homeMomentum-ctx.awayMomentum)>=25){
        const team=ctx.homeMomentum>ctx.awayMomentum?ctx.home:ctx.away;
        alerts.push({type:"info",title:"💥 FLOW BREAK",text:`${team} sta rompendo l’equilibrio del match.`});
    }

    if(!alerts.length)alerts.push({type:"info",title:"🧠 TACTICAL CONTROL",text:"Nessuno shock live rilevato in questo aggiornamento."});

    return alerts;
}

function generateMatchSimulation(data,flow){
    const match=data.match||{};
    const pressure=data.pressure_engine||{};
    const xg=getXg(data);

    const home=match.home||match.home_team||"Home";
    const away=match.away||match.away_team||"Away";

    const homePressure=clamp(pressure.home?.pressure||0);
    const awayPressure=clamp(pressure.away?.pressure||0);
    const homeDanger=clamp(pressure.home?.danger||0);
    const awayDanger=clamp(pressure.away?.danger||0);

    const homeXg=safeNumber(xg.home_xg,0);
    const awayXg=safeNumber(xg.away_xg,0);

    const homePower=homePressure*.35+homeDanger*.42+homeXg*12+(flow.confidenceHome||0)*.12;
    const awayPower=awayPressure*.35+awayDanger*.42+awayXg*12+(flow.confidenceAway||0)*.12;

    const attackingTeam=homePower>=awayPower?home:away;
    const attackPower=clamp(Math.max(homePower,awayPower));

    const shotProbability=clamp(attackPower*.55+(flow.chaosIndex||0)*.18+(flow.fatiguePressure||0)*.08);
    const goalProbability=clamp(attackPower*.28+(flow.chaosIndex||0)*.12+Math.max(homeXg,awayXg)*8);
    const pressureWave=clamp(Math.max(homePressure,awayPressure)*.5+Math.max(homeDanger,awayDanger)*.35+(flow.chaosIndex||0)*.15);
    const collapseRisk=clamp((flow.chaosIndex||0)*.35+(flow.fatiguePressure||0)*.25+Math.max(flow.panicHome||0,flow.panicAway||0)*.35);

    let scenario="Fase equilibrata: probabile gestione del ritmo senza grande rischio immediato.";

    if(goalProbability>=45)scenario=`Possibile grande occasione per ${attackingTeam} nei prossimi 5 minuti.`;
    else if(shotProbability>=55)scenario=`${attackingTeam} potrebbe produrre almeno un tiro o una situazione pericolosa.`;
    else if(pressureWave>=60)scenario=`Pressione crescente: ${flow.dominant} può alzare il baricentro e forzare l’errore.`;
    else if(collapseRisk>=65)scenario="Rischio instabilità: una delle due squadre può perdere controllo emotivo o tattico.";

    return{attackingTeam,shotProbability,goalProbability,pressureWave,collapseRisk,scenario};
}

function detectTeamIdentity(teamName,side,pressure,danger,xg,flow,score){
    const confidence=side==="home"?flow.confidenceHome:flow.confidenceAway;
    const panic=side==="home"?flow.panicHome:flow.panicAway;
    const momentum=side==="home"?flow.homeMomentum:flow.awayMomentum;
    const losing=side==="home"?score.home<score.away:score.away<score.home;

    let style="Balanced Control";
    let icon="🧠";
    let desc="Squadra in equilibrio: alterna gestione, pressione e fasi di controllo senza un’identità dominante.";
    let tags=["BALANCED","CONTROL","STABLE"];

    if(pressure>=78&&danger>=70){
        style="High Pressing Machine";
        icon="🔥";
        desc="Pressione alta e recupero aggressivo: la squadra sta cercando di soffocare l’avversario nella sua metà campo.";
        tags=["HIGH PRESS","AGGRESSIVE","TERRITORIAL"];
    }else if(danger>=78&&pressure<65){
        style="Direct Attack";
        icon="⚡";
        desc="Approccio verticale: poche fasi di possesso, ma forte capacità di generare pericolo in modo rapido.";
        tags=["DIRECT","FAST ATTACK","RISK"];
    }else if(pressure>=70&&danger<55){
        style="Possession Control";
        icon="🔵";
        desc="Controllo territoriale e gestione del ritmo: la squadra sta costruendo superiorità senza forzare troppo.";
        tags=["POSSESSION","CONTROL","TEMPO"];
    }else if(momentum>=70&&danger>=60){
        style="Momentum Surge";
        icon="🚀";
        desc="Momento favorevole evidente: intensità e fiducia stanno spostando il flusso tattico dalla sua parte.";
        tags=["MOMENTUM","CONFIDENCE","PUSH"];
    }else if(losing&&pressure>=65){
        style="Chasing Mode";
        icon="🚨";
        desc="La squadra sta inseguendo il risultato e aumenta pressione e rischio per rientrare nel match.";
        tags=["CHASING","HIGH RISK","REACTION"];
    }else if(panic>=72&&pressure<55){
        style="Defensive Stress";
        icon="🧱";
        desc="Fase di sofferenza: la squadra sembra più reattiva che propositiva e sta assorbendo pressione.";
        tags=["LOW BLOCK","STRESS","DEFENSIVE"];
    }else if(flow.chaosIndex>=70){
        style="Chaos Football";
        icon="🌪️";
        desc="Match instabile: transizioni, errori e ritmo alto stanno creando una partita poco controllabile.";
        tags=["CHAOS","TRANSITIONS","UNSTABLE"];
    }

    const identityScore=clamp((pressure*.32)+(danger*.36)+(momentum*.22)+(confidence*.10));

    return{teamName,style,icon,desc,tags,identityScore,pressure,danger,xg,momentum,confidence,panic};
}

function generateTacticalIdentity(data,flow){
    const match=data.match||{};
    const pressure=data.pressure_engine||{};
    const xg=getXg(data);
    const score=getScore(match);

    const home=match.home||match.home_team||"Home";
    const away=match.away||match.away_team||"Away";

    const homePressure=clamp(pressure.home?.pressure||0);
    const awayPressure=clamp(pressure.away?.pressure||0);
    const homeDanger=clamp(pressure.home?.danger||0);
    const awayDanger=clamp(pressure.away?.danger||0);

    const homeId=detectTeamIdentity(home,"home",homePressure,homeDanger,safeNumber(xg.home_xg,0),flow,score);
    const awayId=detectTeamIdentity(away,"away",awayPressure,awayDanger,safeNumber(xg.away_xg,0),flow,score);

    const dominant=homeId.identityScore>=awayId.identityScore?homeId:awayId;

    let matchDNA="Balanced Tactical Battle";

    if(flow.chaosIndex>=70)matchDNA="Chaotic Transition Game";
    else if(Math.max(homePressure,awayPressure)>=75)matchDNA="High Pressure Match";
    else if(Math.abs(homeId.identityScore-awayId.identityScore)<=8)matchDNA="Tactical Chess Match";
    else if(dominant.style.includes("Possession"))matchDNA="Territorial Control Match";

    return{homeId,awayId,dominant,matchDNA};
}

function generateAttackPrediction(data,flow){
    const match=data.match||{};
    const pressure=data.pressure_engine||{};
    const xg=getXg(data);

    const home=match.home||match.home_team||"Home";
    const away=match.away||match.away_team||"Away";

    const hp=clamp(pressure.home?.pressure||0);
    const ap=clamp(pressure.away?.pressure||0);
    const hd=clamp(pressure.home?.danger||0);
    const ad=clamp(pressure.away?.danger||0);

    const hx=safeNumber(xg.home_xg,0);
    const ax=safeNumber(xg.away_xg,0);

    const homePower=hp*.32+hd*.42+hx*13+flow.confidenceHome*.1;
    const awayPower=ap*.32+ad*.42+ax*13+flow.confidenceAway*.1;

    const team=homePower>=awayPower?home:away;
    const power=clamp(Math.max(homePower,awayPower));
    const chaos=flow.chaosIndex;

    let lane="center";
    let label="⚡ CENTRAL BUILDUP";
    let desc=`${team} sta sviluppando la manovra prevalentemente per vie centrali, cercando superiorità tra le linee.`;

    if(power>=70&&chaos>=55){
        lane="right";
        label="🟥 RIGHT SIDE PRESSURE";
        desc=`${team} sta aumentando la pressione sulla corsia destra con un flusso offensivo molto intenso.`;
    }else if(power>=60&&hd+ad>hp+ap){
        lane="left";
        label="🔥 LEFT SIDE OVERLOAD";
        desc=`${team} sta creando un possibile sovraccarico sulla fascia sinistra, con rischio di cross o attacco rapido.`;
    }else if(power>=55){
        lane="center";
        label="⚡ CENTRAL BUILDUP";
        desc=`${team} sta cercando di costruire per vie centrali e forzare la linea difensiva avversaria.`;
    }

    const shot=clamp(power*.55+chaos*.12);
    const box=clamp(power*.42+Math.max(hx,ax)*12);
    const overload=clamp(power*.48+Math.max(hd,ad)*.28);

    return{team,lane,label,desc,power,shot,box,overload};
}

function generateMomentumCinematic(data,flow,simulation){
    const match=data.match||{};
    const minute=safeNumber(match.minute,0);

    const homeM=clamp(flow.homeMomentum);
    const awayM=clamp(flow.awayMomentum);
    const gap=Math.abs(homeM-awayM);

    const temperature=clamp(
        flow.chaosIndex*.38+
        simulation.pressureWave*.24+
        simulation.goalProbability*.20+
        gap*.18
    );

    let tempLabel="COLD";
    let tempText="Ritmo basso, poche variazioni nel flusso della partita.";

    if(temperature>=80){
        tempLabel="CHAOTIC";
        tempText="Partita in fase altamente instabile: ogni episodio può cambiare il match.";
    }else if(temperature>=65){
        tempLabel="VOLATILE";
        tempText="Il match è molto vivo: pressione, transizioni e rischio stanno aumentando.";
    }else if(temperature>=48){
        tempLabel="INTENSE";
        tempText="Ritmo intenso: una squadra sta provando ad alzare pressione e baricentro.";
    }else if(temperature>=30){
        tempLabel="BALANCED";
        tempText="Partita equilibrata con fasi alterne e controllo distribuito.";
    }

    let swing="STABLE";
    let swingText="Nessun cambio netto di inerzia rilevato.";

    if(gap>=28){
        swing="STRONG MOMENTUM";
        swingText=`${flow.dominant} sta vivendo una fase di dominio tattico evidente.`;
    }else if(gap>=15){
        swing="MOMENTUM EDGE";
        swingText=`${flow.dominant} ha un vantaggio nel flusso recente della partita.`;
    }

    const dangerPulse=clamp((simulation.goalProbability*.55)+(simulation.collapseRisk*.45));
    const pressurePulse=clamp(simulation.pressureWave);

    return{
        minute,
        homeM,
        awayM,
        gap,
        temperature,
        tempLabel,
        tempText,
        swing,
        swingText,
        dangerPulse,
        pressurePulse
    };
}

function buildSnapshot(data,flow,sim,momentum){
    const m=data.match||{};
    const s=getScore(m);
    const p=data.pressure_engine||{};
    const x=getXg(data);

    return{
        score:`${s.home}-${s.away}`,
        minute:safeNumber(m.minute,0),
        homePressure:Math.round(clamp(p.home?.pressure)),
        awayPressure:Math.round(clamp(p.away?.pressure)),
        homeDanger:Math.round(clamp(p.home?.danger)),
        awayDanger:Math.round(clamp(p.away?.danger)),
        homeXg:safeNumber(x.home_xg,0).toFixed(2),
        awayXg:safeNumber(x.away_xg,0).toFixed(2),
        chaos:Math.round(flow.chaosIndex),
        status:flow.status,
        dominant:flow.dominant,
        goalProb:Math.round(sim.goalProbability),
        shotProb:Math.round(sim.shotProbability),
        collapseRisk:Math.round(sim.collapseRisk),
        temperature:Math.round(momentum.temperature),
        swing:momentum.swing
    };
}

function pushEvent(level,title,text){
    const now=new Date().toLocaleTimeString("it-IT",{hour:"2-digit",minute:"2-digit",second:"2-digit"});
    cinematicEvents.unshift({level,title,text,time:now});
    cinematicEvents=cinematicEvents.slice(0,6);
}

function detectCinematicEvents(snapshot){
    if(!previousSnapshot)return{changed:false,scoreChanged:false,major:false,messages:[]};

    const messages=[];
    const scoreChanged=snapshot.score!==previousSnapshot.score;

    if(scoreChanged){
        messages.push("💥 GOAL SHOCK");
        pushEvent("critical","💥 GOAL SHOCK","Il risultato è cambiato: l’AI sta ricalcolando inerzia e rischio tattico.");
    }

    if(Math.abs(snapshot.chaos-previousSnapshot.chaos)>=10){
        messages.push("⚡ CHAOS SHIFT");
        pushEvent("warning","⚡ CHAOS SHIFT","La temperatura tattica del match è cambiata in modo evidente.");
    }

    if(Math.abs(snapshot.goalProb-previousSnapshot.goalProb)>=8){
        messages.push("🔥 GOAL PROBABILITY SPIKE");
        pushEvent("critical","🔥 GOAL PROBABILITY SPIKE","Aumento improvviso della probabilità goal nei prossimi minuti.");
    }

    if(Math.abs(snapshot.collapseRisk-previousSnapshot.collapseRisk)>=10){
        messages.push("🚨 COLLAPSE RISK");
        pushEvent("critical","🚨 TACTICAL COLLAPSE RISK","Una squadra mostra segnali di perdita di controllo tattico o mentale.");
    }

    if(Math.abs(snapshot.temperature-previousSnapshot.temperature)>=12){
        messages.push("🌡️ MATCH TEMPERATURE SHIFT");
        pushEvent("warning","🌡️ MATCH TEMPERATURE SHIFT","Il livello emotivo e tattico della partita è cambiato in modo netto.");
    }

    if(snapshot.swing!==previousSnapshot.swing){
        messages.push("⚡ MOMENTUM SWING");
        pushEvent("info","⚡ MOMENTUM SWING","Cambio di inerzia rilevato: il flusso della partita si sta spostando.");
    }

    if(Math.abs(snapshot.homePressure-previousSnapshot.homePressure)>=15||Math.abs(snapshot.awayPressure-previousSnapshot.awayPressure)>=15){
        messages.push("🔥 PRESSURE OVERLOAD");
        pushEvent("warning","🔥 PRESSURE OVERLOAD","Pressione improvvisa rilevata: possibile fase di assedio.");
    }

    return{changed:messages.length>0,scoreChanged,major:scoreChanged||messages.length>=2,messages};
}