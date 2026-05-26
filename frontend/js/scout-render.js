/*
    MatchIQ Scout - Render Module
    Rendering dashboard, player cards, timeline, watchlist e filtri.
    V6.4 Render
*/

function renderAll(){
  renderMatches();
  renderHero();
  renderMetrics();
  renderPlayers();
  renderTimeline();
  renderTicker();
  renderWatchlist();
  refreshModal();
  updateApiPill();
}

function renderMatches(){
  const box = document.getElementById("matchList");

  if(!box) return;

  if(!state.matches.length){
    box.innerHTML = `<div class="empty"><strong>Nessuna partita live disponibile</strong>Uso il match_id dell'URL se presente.</div>`;
    return;
  }

  box.innerHTML = state.matches.map(m => `
    <div class="match-card ${String(m.id) === String(state.selectedMatchId) ? "active" : ""}" onclick="selectMatch('${escAttr(m.id)}')">
      <div class="match-row">
        <span>${esc(m.home)}</span>
        <span>${esc(m.away)}</span>
      </div>
      <div class="match-meta">
        <span>${esc(m.league)}</span>
        <span class="score-live">${m.scoreHome}-${m.scoreAway} · ${m.minute}'</span>
      </div>
    </div>
  `).join("");
}

function renderHero(){
  const hero = document.getElementById("hero");
  if(!hero) return;

  const m = getMatch();

  if(!m){
    hero.innerHTML = `
      <div>
        <h3>Nessun match selezionato</h3>
        <p>Apri scout.html?match_id=ID_PARTITA.</p>
      </div>
    `;
    return;
  }

  hero.innerHTML = `
    <div>
      <h3>${esc(m.home)}</h3>
      <p>${esc(m.league)} · Home Team</p>
    </div>

    <div class="hero-score">
      <strong>${m.scoreHome} - ${m.scoreAway}</strong>
      <div>${m.minute}' · ${esc(m.status)}</div>
    </div>

    <div style="text-align:right;">
      <h3>${esc(m.away)}</h3>
      <p>Away Team</p>
    </div>
  `;
}

function renderMetrics(){
  const summary = state.summary || buildLocalSummary(state.players);

  const momentum = document.getElementById("mMomentum");
  const pressure = document.getElementById("mPressure");
  const creativity = document.getElementById("mCreativity");
  const threat = document.getElementById("mThreat");

  if(momentum) momentum.textContent = valuePct(summary.avg_momentum ?? avgField(state.players,"momentum"));
  if(pressure) pressure.textContent = valuePct(summary.avg_pressure ?? avgField(state.players,"pressure"));
  if(creativity) creativity.textContent = valuePct(summary.avg_creativity ?? avgField(state.players,"creativity"));
  if(threat) threat.textContent = valuePct(summary.avg_threat ?? avgField(state.players,"threat"));
}

function renderPlayers(){
  const box = document.getElementById("players");
  if(!box) return;

  if(!state.hasRealPlayers){
    box.innerHTML = `
      <div class="empty">
        <strong>Giocatori reali non disponibili</strong>
        Scout V6.4 legge solo data.players dello schema clean.
      </div>
    `;
    return;
  }

  const list = filteredPlayers();

  if(!list.length){
    box.innerHTML = `
      <div class="empty">
        <strong>Nessun giocatore trovato</strong>
        Modifica i filtri scout.
      </div>
    `;
    return;
  }

  box.innerHTML = list.map(p => {
    const scoreClass = p.scout_score >= 82 ? "high" : p.scout_score >= 70 ? "mid" : "";
    const cardClass = p.signal_type === "hot"
      ? "hot"
      : p.signal_type === "danger"
        ? "danger"
        : p.signal_type === "pressure"
          ? "pressure"
          : "";

    const signalClass = p.signal_type === "hot"
      ? "hot-signal"
      : p.signal_type === "danger"
        ? "alert"
        : p.signal_type === "pressure"
          ? "pressure-signal"
          : "";

    const watched = isWatched(p.id);

    return `
      <article class="player ${cardClass} ${watched ? "watch" : ""}" id="card-${escAttr(p.id)}">
        <div onclick="openModal('${escAttr(p.id)}')">
          <div class="player-head">
            <div>
              <div class="player-name">${esc(p.name)}</div>
              <div class="player-sub">${esc(p.team)} · ${esc(p.role)} · ${esc(p.data_source)}</div>
            </div>
            <div class="score ${scoreClass}">${Math.round(num(p.scout_score,0))}</div>
          </div>

          <div class="signal ${watched ? "watch-signal" : signalClass}">
            ${watched ? "⭐ WATCHLIST" : "⚡ " + esc(p.signal)}
          </div>

          <div class="stats">
            <div class="stat"><small>Threat</small><strong>${Math.round(num(p.threat,0))}</strong></div>
            <div class="stat"><small>Creative</small><strong>${Math.round(num(p.creativity,0))}</strong></div>
            <div class="stat"><small>Press</small><strong>${Math.round(num(p.pressure,0))}</strong></div>
            <div class="stat"><small>Mom</small><strong>${Math.round(num(p.momentum,0))}</strong></div>
          </div>
        </div>

        <div class="player-actions">
          <button class="btn" onclick="openModal('${escAttr(p.id)}')">Analizza</button>
          <button class="btn btn-green" onclick="toggleWatchlistById('${escAttr(p.id)}')">
            ${watched ? "Salvato" : "Watch"}
          </button>
        </div>
      </article>
    `;
  }).join("");
}

function renderTimeline(){
  const box = document.getElementById("timeline");
  const count = document.getElementById("eventCount");

  if(!box) return;
  if(count) count.textContent = `${state.events.length} eventi`;

  if(!state.events.length){
    box.innerHTML = `
      <div class="empty">
        <strong>Nessun evento player reale</strong>
        La timeline si popolerà con eventi live.
      </div>
    `;
    return;
  }

  box.innerHTML = [...state.events]
    .sort((a,b) => num(b.minute,0) - num(a.minute,0))
    .slice(0,30)
    .map(e => `
      <div class="event ${e.className || ""}">
        <div class="event-top">
          <span class="minute">${esc(e.minute)}'</span>
          <span class="tag">${esc(e.label)}</span>
        </div>
        <div class="event-title">${esc(e.title)}</div>
        <div class="event-desc">${esc(e.desc)}</div>
      </div>
    `).join("");
}

function renderTicker(){
  const ticker = document.getElementById("tickerText");
  if(!ticker) return;

  const m = getMatch();

  if(!m){
    ticker.textContent = "MatchIQ Scout V6.4 · nessuna partita live ricevuta";
    return;
  }

  if(!state.hasRealPlayers){
    ticker.textContent = `LIVE ${m.home} - ${m.away} · ${m.minute}' · giocatori reali non disponibili`;
    return;
  }

  const top = [...state.players].sort((a,b) => num(b.scout_score,0) - num(a.scout_score,0))[0];

  ticker.textContent =
    `LIVE ${m.home} - ${m.away} · ${m.minute}' · Top Scout: ${top?.name || "--"} · Threat ${Math.round(num(top?.threat,0))} · Source ${top?.data_source || "--"}`;
}

function renderWatchlist(){
  const box = document.getElementById("watchlist");
  const count = document.getElementById("watchCount");

  if(!box) return;
  if(count) count.textContent = `${state.watchlist.length} salvati`;

  if(!state.watchlist.length){
    box.innerHTML = `
      <div class="empty">
        <strong>Watchlist vuota</strong>
        Salva i player da monitorare.
      </div>
    `;
    return;
  }

  box.innerHTML = state.watchlist.map(p => `
    <div class="watch-item">
      <div class="watch-item-top">
        <div>
          <div class="watch-name">${esc(p.name)}</div>
          <div class="watch-meta">
            ${esc(p.team)} · ${esc(p.role)} · Score ${Math.round(num(p.scout_score,0))}
          </div>
        </div>
        <button class="watch-remove" onclick="removeWatchlist('${escAttr(p.id)}'); renderAll();">×</button>
      </div>
    </div>
  `).join("");
}

function filteredPlayers(){
  const searchInput = document.getElementById("searchInput");
  const roleFilter = document.getElementById("roleFilter");
  const signalFilter = document.getElementById("signalFilter");
  const scoreFilter = document.getElementById("scoreFilter");

  const q = (searchInput?.value || "").toLowerCase().trim();
  const roleVal = roleFilter?.value || "all";
  const signalVal = signalFilter?.value || "all";
  const minScore = Number(scoreFilter?.value || 0);

  return state.players.filter(p =>
    (!q || String(p.name || "").toLowerCase().includes(q) || String(p.team || "").toLowerCase().includes(q)) &&
    (roleVal === "all" || p.role === roleVal) &&
    (signalVal === "all" || p.signal_type === signalVal) &&
    num(p.scout_score,0) >= minScore
  ).sort((a,b) => num(b.scout_score,0) - num(a.scout_score,0));
}

function resetFilters(){
  const searchInput = document.getElementById("searchInput");
  const roleFilter = document.getElementById("roleFilter");
  const signalFilter = document.getElementById("signalFilter");
  const scoreFilter = document.getElementById("scoreFilter");

  if(searchInput) searchInput.value = "";
  if(roleFilter) roleFilter.value = "all";
  if(signalFilter) signalFilter.value = "all";
  if(scoreFilter) scoreFilter.value = "0";

  renderPlayers();
}