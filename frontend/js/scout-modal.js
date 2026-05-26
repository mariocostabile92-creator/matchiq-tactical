/*
    MatchIQ Scout - Modal Module
    Modal PRO player analysis, radar, tactical profile e AI commentary.
    V6.5 Modal
*/

function openModal(id){
  state.openPlayerId = id;
  renderModal();
  document.getElementById("modalBg").classList.add("show");
}

function closeModal(clear=true){
  const modalBg = document.getElementById("modalBg");

  if(modalBg){
    modalBg.classList.remove("show");
  }

  if(clear){
    state.openPlayerId = null;
  }
}

function refreshModal(){
  const modalBg = document.getElementById("modalBg");

  if(state.openPlayerId && modalBg && modalBg.classList.contains("show")){
    renderModal();
  }
}

function renderModal(){
  const p = state.players.find(x => String(x.id) === String(state.openPlayerId));
  if(!p) return;

  const threat = clamp(num(p.threat,0),1,99);
  const creativity = clamp(num(p.creativity,0),1,99);
  const pressure = clamp(num(p.pressure,0),1,99);
  const momentum = clamp(num(p.momentum,0),1,99);
  const stamina = clamp(num(p.stamina,0),1,100);
  const fatigue = clamp(num(p.fatigue,0),1,99);
  const impact = clamp(num(p.impact_score,0),1,99);
  const score = clamp(num(p.scout_score,0),1,99);

  const goalProb = clamp((threat * .48) + (num(p.shots,0) * 9) + (num(p.goals,0) * 20),0,99);
  const assistProb = clamp((creativity * .55) + (num(p.key_passes,0) * 8) + (num(p.assists,0) * 15),0,99);
  const nextImpact = clamp((impact * .55) + (momentum * .25) + (threat * .2),0,99);
  const watchFit = clamp((score * .6) + (impact * .25) + (stamina * .15),0,99);
  const watched = isWatched(p.id);

  renderAvatar(p);

  const modalName = document.getElementById("modalName");
  const modalSub = document.getElementById("modalSub");
  const modalBadges = document.getElementById("modalBadges");

  if(modalName) modalName.textContent = p.name;
  if(modalSub) modalSub.textContent = `${p.team} · ${p.role} · ${p.signal}`;

  if(modalBadges){
    modalBadges.innerHTML = `
      <span class="badge ${watched ? "yellow" : "green"}">${watched ? "⭐ Watchlist" : esc(p.signal)}</span>
      <span class="badge ${impact >= 80 ? "green" : impact >= 60 ? "yellow" : ""}">Impact ${Math.round(impact)}</span>
      <span class="badge ${p.is_estimated ? "yellow" : "cyan"}">${esc(p.data_source)}</span>
      <span class="badge ${stamina < 45 ? "red" : "green"}">Stamina ${Math.round(stamina)}%</span>
    `;
  }

  setText("modalScore",Math.round(score));
  setText("modalThreat",Math.round(threat) + "%");
  setText("modalCreativity",Math.round(creativity) + "%");
  setText("modalStamina",Math.round(stamina) + "%");

  const impactRing = document.getElementById("impactRing");
  if(impactRing){
    impactRing.style.setProperty("--impact",impact + "%");
  }

  setText("impactValue",Math.round(impact));
  setText("impactLabel",impact >= 85 ? "Elite Impact" : impact >= 70 ? "High Impact" : "Monitoring");

  setBar("barThreat","barThreatText",threat);
  setBar("barCreativity","barCreativityText",creativity);
  setBar("barPressure","barPressureText",pressure);
  setBar("barFatigue","barFatigueText",fatigue);

  setText(
    "modalComment",
    p.ai_summary || aiComment({
      ...p,
      threat,
      creativity,
      pressure,
      momentum,
      stamina,
      impact_score:impact,
      scout_score:score
    })
  );

  setText("commentSource",p.data_source);

  setText("goalProb",Math.round(goalProb) + "%");
  setText("assistProb",Math.round(assistProb) + "%");
  setText("nextImpact",Math.round(nextImpact) + "%");
  setText("watchFit",Math.round(watchFit) + "%");

  renderRadar({
    ...p,
    threat,
    creativity,
    pressure,
    momentum,
    stamina,
    impact_score:impact,
    scout_score:score
  });

  renderTacticalZone({
    ...p,
    threat,
    creativity,
    pressure,
    stamina
  });

  renderProfileGrid({
    ...p,
    threat,
    creativity,
    pressure,
    stamina,
    impact_score:impact
  });

  renderModalEvents(p);
}

function renderAvatar(p){
  const avatar = document.getElementById("modalAvatar");
  if(!avatar) return;

  if(p.photo){
    avatar.innerHTML = `<img src="${escAttr(p.photo)}" alt="${escAttr(p.name)}">`;
  }else{
    avatar.textContent = String(p.name || "AI")
      .split(" ")
      .map(x => x[0])
      .join("")
      .slice(0,2)
      .toUpperCase();
  }
}

function renderProfileGrid(p){
  const profileGrid = document.getElementById("profileGrid");
  if(!profileGrid) return;

  const profile = tacticalProfile(p);

  profileGrid.innerHTML = `
    <div class="profile-item">
      <small>Archetipo</small>
      <strong>${esc(profile.type)}</strong>
    </div>

    <div class="profile-item">
      <small>Zona Forte</small>
      <strong>${esc(profile.zone)}</strong>
    </div>

    <div class="profile-item">
      <small>Decisione AI</small>
      <strong>${esc(profile.decision)}</strong>
    </div>

    <div class="profile-item">
      <small>Qualità Dato</small>
      <strong>${esc(p.data_quality)}</strong>
    </div>

    <div class="profile-item">
      <small>Live Impact</small>
      <strong>${Math.round(num(p.impact_score,0))}%</strong>
    </div>

    <div class="profile-item">
      <small>Stamina</small>
      <strong>${Math.round(num(p.stamina,0))}%</strong>
    </div>
  `;
}

function renderModalEvents(p){
  const modalEvents = document.getElementById("modalEvents");
  if(!modalEvents) return;

  const list = state.events
    .filter(e => String(e.playerId) === String(p.id) || e.playerName === p.name)
    .sort((a,b) => num(b.minute,0) - num(a.minute,0));

  modalEvents.innerHTML = list.length
    ? list.map(e => `
        <div class="event ${e.className || ""}">
          <div class="event-top">
            <span class="minute">${esc(e.minute)}'</span>
            <span class="tag">${esc(e.label)}</span>
          </div>
          <div class="event-title">${esc(e.title)}</div>
          <div class="event-desc">${esc(e.desc)}</div>
        </div>
      `).join("")
    : `
        <div class="empty">
          <strong>Nessun evento specifico</strong>
          In attesa di eventi live del player.
        </div>
      `;
}

function setBar(id,textId,value){
  const v = clamp(Math.round(value),0,100);
  const bar = document.getElementById(id);
  const text = document.getElementById(textId);

  if(bar) bar.style.width = v + "%";
  if(text) text.textContent = v + "%";
}

function renderRadar(p){
  const radarSvg = document.getElementById("radarSvg");
  if(!radarSvg) return;

  const values = [
    clamp(p.scout_score,0,99),
    clamp(p.threat,0,99),
    clamp(p.momentum,0,99),
    clamp(p.pressure,0,99),
    clamp(p.creativity,0,99),
    clamp(p.stamina,0,99)
  ];

  const labels = ["Score","Threat","Momentum","Press","Creative","Stamina"];
  const cx = 150;
  const cy = 150;
  const maxR = 105;
  const sides = values.length;

  function point(i,r){
    const angle = (-Math.PI / 2) + (i * 2 * Math.PI / sides);
    return [
      cx + Math.cos(angle) * r,
      cy + Math.sin(angle) * r
    ];
  }

  const grid = [.25,.5,.75,1]
    .map(scale => `
      <polygon
        points="${labels.map((_,i) => point(i,maxR * scale).join(",")).join(" ")}"
        fill="none"
        stroke="rgba(255,255,255,.12)"
        stroke-width="1"
      />
    `).join("");

  const axes = labels.map((label,i) => {
    const [x,y] = point(i,maxR);
    const [tx,ty] = point(i,maxR + 24);

    return `
      <line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="rgba(255,255,255,.1)" />
      <text
        x="${tx}"
        y="${ty}"
        text-anchor="middle"
        dominant-baseline="middle"
        fill="#8f9bb3"
        font-size="11"
        font-weight="700"
      >${label}</text>
    `;
  }).join("");

  const polyPoints = values
    .map((v,i) => point(i,maxR * (v / 100)).join(","))
    .join(" ");

  radarSvg.innerHTML = `
    ${grid}
    ${axes}
    <polygon points="${polyPoints}" fill="rgba(0,229,255,.24)" stroke="#00e5ff" stroke-width="3" />
    ${values.map((v,i) => {
      const [x,y] = point(i,maxR * (v / 100));
      return `<circle cx="${x}" cy="${y}" r="4" fill="#00f5a0" />`;
    }).join("")}
  `;
}

function renderTacticalZone(p){
  const zone = document.getElementById("tacticalZone");
  const label = document.getElementById("zoneLabel");
  if(!zone || !label) return;

  const profile = tacticalProfile(p);
  label.textContent = profile.zone;

  let x = 50;
  let y = 50;

  if(p.role === "ATT"){
    x = 78;
    y = p.threat >= 70 ? 38 : 50;
  }else if(p.role === "MID"){
    x = 54;
    y = num(p.key_passes,0) >= 2 ? 38 : 55;
  }else if(p.role === "DEF"){
    x = 27;
    y = p.pressure >= 65 ? 42 : 55;
  }else if(p.role === "GK"){
    x = 12;
    y = 50;
  }

  zone.style.left = x + "%";
  zone.style.top = y + "%";
}

function tacticalProfile(p){
  if(p.role === "ATT" && p.threat >= 70){
    return {
      type:"Finalizzatore dinamico",
      zone:"Half-space offensivo",
      decision:"Monitorare goal"
    };
  }

  if(p.role === "MID" && p.creativity >= 70){
    return {
      type:"Creatore di gioco",
      zone:"Rifinitura centrale",
      decision:"Watchlist assist"
    };
  }

  if(p.pressure >= 70){
    return {
      type:"Pressing trigger",
      zone:"Zona recupero alto",
      decision:"Valore tattico"
    };
  }

  if(p.role === "DEF"){
    return {
      type:"Stabilizzatore difensivo",
      zone:"Linea bassa/media",
      decision:"Controllo rischio"
    };
  }

  if(p.role === "GK"){
    return {
      type:"Portiere reattivo",
      zone:"Area difensiva",
      decision:"Monitorare clean sheet"
    };
  }

  return {
    type:"Profilo bilanciato",
    zone:"Zona mista",
    decision:"Monitoraggio live"
  };
}

function aiComment(p){
  if(p.impact_score >= 88){
    return `${p.name} sta producendo un impatto elite. Profilo prioritario da monitorare.`;
  }

  if(p.threat >= 82){
    return `${p.name} entra spesso in zone pericolose. Alta probabilità di azione decisiva.`;
  }

  if(p.creativity >= 75){
    return `${p.name} sta creando valore tra le linee: ottimo profilo per assist e chance creation.`;
  }

  if(p.pressure >= 78){
    return `${p.name} è un trigger di pressione: intensità e duelli stanno influenzando il ritmo.`;
  }

  if(p.stamina < 40){
    return `${p.name} mostra segnali di fatica. Possibile calo se il ritmo aumenta.`;
  }

  return `${p.name} è in monitoraggio live. Profilo stabile con margine di crescita.`;
}

function setText(id,value){
  const el = document.getElementById(id);
  if(el) el.textContent = value;
}