/* MatchIQ Scout - Render Module V8.1.2 SaaS Free/Pro */

function renderAll(){
  renderAccessUI();
  renderMatches();
  renderHero();
  renderMetrics();
  renderPlayers();
  renderTimeline();
  renderTicker();
  renderWatchlist();
  refreshModal();
  updateApiPill();
  applyScoutAccessUI();
}

function renderAccessUI(){
  const actions = document.querySelector(".topbar .actions");

  if(actions){
    actions.querySelectorAll(".mi-plan-pill").forEach(x => x.remove());

    const label = state.account?.label || "FREE PREVIEW";
    const isPro = typeof isScoutPro === "function" ? isScoutPro() : Boolean(state.account?.is_pro);
    const isOwner = typeof isScoutOwner === "function" ? isScoutOwner() : Boolean(state.account?.is_owner);

    actions.insertAdjacentHTML(
      "afterbegin",
      `<div class="pill mi-plan-pill ${isPro ? "pill-live" : "pill-clean"}">${esc(label)}</div>`
    );

    [...actions.children].forEach(el => {
      const t = (el.textContent || "").toLowerCase();

      if(t.includes("admin actions")){
        el.style.display = isOwner ? "" : "none";
      }

      if(t.includes("export report")){
        el.style.display = isPro ? "" : "none";
      }

      if(t.includes("simula evento")){
        el.style.display = isPro ? "" : "none";
      }
    });
  }

  const sub = document.querySelector(".subtitle");

  if(sub){
    const isPro = typeof isScoutPro === "function" ? isScoutPro() : Boolean(state.account?.is_pro);

    sub.textContent = isPro
      ? "Scout completo · Live Player Intelligence · Tactical Signals · Export Report"
      : "Scout Preview · player cards limitate · export, watchlist e simulazioni disponibili con Pro";
  }
}

function goToProRequest(){
  if(typeof openScoutProUpgrade === "function"){
    openScoutProUpgrade();
    return;
  }

  window.location.href = "/index.html#pricing";
}

function goToAccount(){
  if(typeof goAccount === "function"){
    goAccount();
    return;
  }

  window.location.href = "/account.html";
}

function proCtaHtml(mode = "players"){
  const textByMode = {
    players: {
      title: "🔒 Sblocca MatchIQ Scout Pro",
      desc: "Stai vedendo una preview limitata. Con Pro sblocchi tutte le player cards, export report, watchlist, simulazione eventi e schede player complete."
    },
    hidden: {
      title: "🔒 Player nascosti",
      desc: "Altri giocatori sono disponibili solo con Scout Pro. Passa a Pro per vedere l’intera analisi live della partita."
    },
    watchlist: {
      title: "🔒 Watchlist Pro",
      desc: "La watchlist è disponibile solo per Pro/Owner. Salva i giocatori più interessanti e crea report scout più rapidi."
    },
    modal: {
      title: "🔒 Scheda Player Pro",
      desc: "La scheda completa include radar, AI coach commentary, probabilità live, tactical zone e report player esportabile."
    }
  };

  const c = textByMode[mode] || textByMode.players;

  return `
    <div class="empty" style="grid-column:1/-1;border-color:#ffb020;background:rgba(255,176,32,.08);">
      <strong>${c.title}</strong>
      <br>
      <span>${c.desc}</span>
      <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:14px;">
        <button class="btn btn-green" onclick="goToProRequest()">Passa a Pro</button>
        <button class="btn" onclick="goToAccount()">Account</button>
        <button class="btn" onclick="goDashboard()">Dashboard</button>
      </div>
    </div>
  `;
}

function renderMatches(){
  const box = document.getElementById("matchList");

  if(!box) return;

  if(!state.matches.length){
    box.innerHTML = `
      <div class="empty">
        <strong>Nessuna partita live disponibile</strong>
        Uso il match_id dell'URL se presente.
      </div>
    `;
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
  const isPro = typeof isScoutPro === "function" ? isScoutPro() : Boolean(state.account?.is_pro);

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
      <div style="margin-top:8px;font-size:12px;color:${isPro ? "#00f5a0" : "#ffb020"};font-weight:900;">
        ${isPro ? "Scout Pro completo" : "Scout Free Preview"}
      </div>
    </div>

    <div style="text-align:right;">
      <h3>${esc(m.away)}</h3>
      <p>Away Team</p>
    </div>
  `;
}

function renderMetrics(){
  const summary = state.summary || buildLocalSummary(state.players);

  const ids = {
    mMomentum: summary.avg_momentum ?? avgField(state.players, "momentum"),
    mPressure: summary.avg_pressure ?? avgField(state.players, "pressure"),
    mCreativity: summary.avg_creativity ?? avgField(state.players, "creativity"),
    mThreat: summary.avg_threat ?? avgField(state.players, "threat")
  };

  Object.entries(ids).forEach(([id, v]) => {
    const el = document.getElementById(id);
    if(el) el.textContent = valuePct(v);
  });
}

function renderPlayers(){
  const box = document.getElementById("players");

  if(!box) return;

  if(!state.hasRealPlayers){
    box.innerHTML = `
      <div class="empty">
        <strong>Giocatori reali non disponibili</strong>
        Scout legge solo data.players dello schema clean.
      </div>
    `;
    return;
  }

  let list = filteredPlayers();

  const isPro = typeof isScoutPro === "function" ? isScoutPro() : Boolean(state.account?.is_pro);
  const limited = !isPro;
  const max = typeof scoutPlayerLimit === "function" ? scoutPlayerLimit() : Number(state.account?.scout_max_players || 4);
  const total = list.length;

  if(limited){
    list = list.slice(0, max);
  }

  if(!list.length){
    box.innerHTML = `
      <div class="empty">
        <strong>Nessun giocatore trovato</strong>
        Modifica i filtri scout.
      </div>
    `;
    return;
  }

  box.innerHTML =
    (limited ? proCtaHtml("players") : "") +
    list.map(p => {
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
      const canWatch = typeof canUseWatchlist === "function" ? canUseWatchlist() : Boolean(state.account?.watchlist_enabled);

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
            <button class="btn" onclick="openModal('${escAttr(p.id)}')">
              ${isPro ? "Analizza" : "Preview"}
            </button>
            <button class="btn btn-green" onclick="toggleWatchlistById('${escAttr(p.id)}')">
              ${canWatch ? (watched ? "Salvato" : "Watch") : "PRO"}
            </button>
          </div>
        </article>
      `;
    }).join("") +
    (
      limited && total > max
        ? proCtaHtml("hidden")
        : ""
    );

  applyScoutAccessUI();
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
  const isPro = typeof isScoutPro === "function" ? isScoutPro() : Boolean(state.account?.is_pro);

  if(!m){
    ticker.textContent = "MatchIQ Scout V8.1.2 · nessuna partita live ricevuta";
    return;
  }

  if(!state.hasRealPlayers){
    ticker.textContent = `LIVE ${m.home} - ${m.away} · ${m.minute}' · giocatori reali non disponibili`;
    return;
  }

  const top = [...state.players].sort((a,b) => num(b.scout_score,0) - num(a.scout_score,0))[0];

  ticker.textContent = isPro
    ? `LIVE ${m.home} - ${m.away} · ${m.minute}' · PRO · Top Scout: ${top?.name || "--"} · Threat ${Math.round(num(top?.threat,0))} · Source ${top?.data_source || "--"}`
    : `LIVE ${m.home} - ${m.away} · ${m.minute}' · FREE PREVIEW · ${state.players.length} player analizzati, preview limitata attiva`;
}

function renderWatchlist(){
  const box = document.getElementById("watchlist");
  const count = document.getElementById("watchCount");

  if(!box) return;

  if(count) count.textContent = `${state.watchlist.length} salvati`;

  const canWatch = typeof canUseWatchlist === "function" ? canUseWatchlist() : Boolean(state.account?.watchlist_enabled);

  if(!canWatch){
    box.innerHTML = proCtaHtml("watchlist");
    return;
  }

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
  const q = (document.getElementById("searchInput")?.value || "").toLowerCase().trim();
  const roleVal = document.getElementById("roleFilter")?.value || "all";
  const signalVal = document.getElementById("signalFilter")?.value || "all";
  const minScore = Number(document.getElementById("scoreFilter")?.value || 0);

  return state.players
    .filter(p =>
      (!q || String(p.name || "").toLowerCase().includes(q) || String(p.team || "").toLowerCase().includes(q)) &&
      (roleVal === "all" || p.role === roleVal) &&
      (signalVal === "all" || p.signal_type === signalVal) &&
      num(p.scout_score,0) >= minScore
    )
    .sort((a,b) => num(b.scout_score,0) - num(a.scout_score,0));
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