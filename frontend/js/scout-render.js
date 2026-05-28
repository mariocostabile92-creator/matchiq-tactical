/* MatchIQ Scout - Render Module V1.3
   SaaS Free/Pro + Free Match Limit + Copy Polish
*/

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

  window.location.href = "/account.html";
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
      title: "🔒 Scout Pro sblocca l’analisi completa",
      desc: "Stai vedendo una preview limitata. Con Pro accedi a tutte le player cards, watchlist, export report e segnali avanzati durante il match."
    },
    hidden: {
      title: "🔒 Altri player disponibili con Pro",
      desc: "La preview Free mostra solo una parte dei giocatori. Passa a Pro per vedere l’intera lettura live della partita."
    },
    watchlist: {
      title: "🔒 Watchlist Pro",
      desc: "Salva i giocatori più interessanti, monitorali durante il match e costruisci report scout più rapidi."
    },
    modal: {
      title: "🔒 Scheda Player Pro",
      desc: "Radar, AI coach commentary, probabilità live, tactical zone ed export player report sono disponibili con MatchIQ Pro."
    },
    matches: {
      title: "🔒 Tutte le partite con Pro",
      desc: "Con Free puoi usare Scout su un numero limitato di partite live. Con Pro sblocchi tutte le partite, player cards complete, watchlist ed export."
    }
  };

  const c = textByMode[mode] || textByMode.players;

  return `
    <div class="empty" style="grid-column:1/-1;border-color:#ffb020;background:rgba(255,176,32,.08);">
      <strong>${c.title}</strong>
      <span>${c.desc}</span>

      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:14px 0;">
        <div style="padding:9px;border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;font-weight:900;">✅ Player cards complete</div>
        <div style="padding:9px;border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;font-weight:900;">✅ Watchlist</div>
        <div style="padding:9px;border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;font-weight:900;">✅ Export report</div>
        <div style="padding:9px;border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;font-weight:900;">✅ Tutti i live</div>
      </div>

      <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:14px;">
        <button class="btn btn-green" onclick="goToProRequest()">Sblocca Pro</button>
        <button class="btn" onclick="goToAccount()">Vedi piano</button>
      </div>
    </div>
  `;
}

/* =========================
   FREE / PRO MATCH LIMIT
========================= */

function getScoutMatchLimit(){
  const isPro = typeof isScoutPro === "function"
    ? isScoutPro()
    : Boolean(state.account?.is_pro);

  const isOwner = typeof isScoutOwner === "function"
    ? isScoutOwner()
    : Boolean(state.account?.is_owner);

  if(isPro || isOwner){
    return 999;
  }

  const apiLimit =
    state.account?.limits?.max_live_matches ??
    state.account?.max_live_matches ??
    state.account?.scout_max_matches ??
    3;

  const n = Number(apiLimit);

  if(!Number.isFinite(n) || n <= 0){
    return 3;
  }

  return Math.min(n, 3);
}

function isScoutMatchAllowed(matchId, visibleMatches){
  const isPro = typeof isScoutPro === "function"
    ? isScoutPro()
    : Boolean(state.account?.is_pro);

  const isOwner = typeof isScoutOwner === "function"
    ? isScoutOwner()
    : Boolean(state.account?.is_owner);

  if(isPro || isOwner){
    return true;
  }

  return visibleMatches.some(m => String(m.id) === String(matchId));
}

function openScoutLockedMatch(){
  if(typeof toast === "function"){
    toast(
      "Partita bloccata",
      "Con il piano Free puoi usare Scout solo sulle prime 3 partite live. Passa a Pro per sbloccarle tutte."
    );
    return;
  }

  alert("Con il piano Free puoi usare Scout solo sulle prime 3 partite live. Passa a Pro per sbloccarle tutte.");
}

function scoutMatchesProLockHtml(total, visible){
  const hidden = Math.max(total - visible, 0);

  if(hidden <= 0){
    return "";
  }

  return `
    <div class="empty" style="border-color:#ffb020;background:rgba(255,176,32,.08);">
      <strong>🔒 ${hidden} partite Scout disponibili con Pro</strong>
      <span>
        Con MatchIQ Free puoi selezionare massimo ${visible} partite live.
        Con Pro sblocchi tutte le partite, Scout completo, player cards, watchlist ed export.
      </span>

      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:14px 0;">
        <div style="padding:9px;border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;font-weight:900;">✅ Tutte le partite</div>
        <div style="padding:9px;border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;font-weight:900;">✅ Scout completo</div>
        <div style="padding:9px;border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;font-weight:900;">✅ Watchlist</div>
        <div style="padding:9px;border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;font-weight:900;">✅ Export report</div>
      </div>

      <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:14px;">
        <button class="btn btn-green" onclick="goToProRequest()">Sblocca Pro</button>
        <button class="btn" onclick="goToAccount()">Vedi piano</button>
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
        <span>
          Apri Scout dalla Home live oppure aggiorna tra poco.
        </span>
      </div>
    `;
    return;
  }

  const limit = getScoutMatchLimit();
  const total = state.matches.length;
  const isLimited = limit < 999;
  const visibleMatches = isLimited ? state.matches.slice(0, limit) : state.matches;

  if(
    isLimited &&
    state.selectedMatchId &&
    !isScoutMatchAllowed(state.selectedMatchId, visibleMatches)
  ){
    state.selectedMatchId = visibleMatches?.[0]?.id || null;

    if(typeof loadScoutData === "function" && state.selectedMatchId){
      setTimeout(() => {
        loadScoutData(true)
          .then(() => {
            if(typeof renderAll === "function"){
              renderAll();
            }
          })
          .catch(() => {});
      }, 50);
    }
  }

  const matchHtml = visibleMatches.map(m => `
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

  box.innerHTML = matchHtml + scoutMatchesProLockHtml(total, visibleMatches.length);
}

function renderHero(){
  const hero = document.getElementById("hero");

  if(!hero) return;

  const m = getMatch();
  const isPro = typeof isScoutPro === "function" ? isScoutPro() : Boolean(state.account?.is_pro);

  if(!m){
    hero.innerHTML = `
      <div>
        <h3>Nessuna partita selezionata</h3>
        <p>Apri Scout dalla Home live oppure seleziona una partita disponibile.</p>
      </div>

      <div class="hero-score">
        <strong>--</strong>
        <div>In attesa</div>
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
        <strong>Player data non ancora disponibili</strong>
        <span>
          I dati dei giocatori non sono disponibili per questa partita.
          Prova un altro match live oppure aggiorna tra poco.
        </span>

        <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:14px;">
          <button class="btn btn-green" onclick="manualRefresh()">Aggiorna Scout</button>
          <button class="btn" onclick="goDashboard()">Torna alla Home</button>
        </div>
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
        <span>
          Nessun player corrisponde ai filtri selezionati.
          Prova a modificare ruolo, segnale AI o score minimo.
        </span>

        <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:14px;">
          <button class="btn btn-green" onclick="resetFilters()">Reset filtri</button>
        </div>
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
        <strong>Nessun evento live rilevato</strong>
        <span>
          Gli eventi dei giocatori compariranno appena saranno disponibili durante il match.
        </span>
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
    ticker.textContent = "MatchIQ Scout · seleziona una partita live dalla Home o dalla lista Scout";
    return;
  }

  if(!state.hasRealPlayers){
    ticker.textContent = `LIVE ${m.home} - ${m.away} · ${m.minute}' · player data non ancora disponibili per questa partita`;
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
        <span>
          Salva i player più interessanti durante il match e ritrovali qui.
        </span>
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