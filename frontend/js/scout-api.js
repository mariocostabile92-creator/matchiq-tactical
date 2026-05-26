/*
    MatchIQ Scout - API Module
    Gestione caricamento partite live, dati scout e normalizzazione match.
*/

async function loadLiveMatches(force=false){
  const now = Date.now();

  if(!force && now - state.lastLiveMatchesFetch < API_SAFE.liveMatchesRefreshMs && state.matches.length){
    return;
  }

  try{
    let data = null;

    try{
      const res = await fetch(`${API_BASE}/api/live-matches?top_only=false&_=${Date.now()}`);

      if(!res.ok){
        throw new Error("live-matches ko");
      }

      data = await res.json();

    }catch{
      const alt = await fetch(`${API_BASE}/api/live?top_only=false&_=${Date.now()}`);

      if(!alt.ok){
        throw new Error("live ko");
      }

      data = await alt.json();
    }

    state.matches = normalizeMatches(data);

    if(state.selectedMatchId && !state.matches.some(m => String(m.id) === String(state.selectedMatchId))){
      state.matches.unshift(buildPlaceholderMatch(state.selectedMatchId));
    }

    clearNotice();

  }catch{
    state.matches = state.selectedMatchId
      ? [buildPlaceholderMatch(state.selectedMatchId)]
      : [];

    showNotice("Lista partite live non disponibile: uso comunque il match_id dell'URL e provo a leggere /api/scout-live.");
  }

  state.lastLiveMatchesFetch = now;
}

async function loadScoutData(force=false){
  const matchId = state.selectedMatchId;

  if(!matchId){
    showNotice("Nessun match_id trovato nell'URL. Apri scout.html?match_id=ID_PARTITA");
    return;
  }

  const now = Date.now();

  if(!force && state.playerCache[matchId] && now - (state.lastScoutFetch[matchId] || 0) < API_SAFE.scoutRefreshMs){
    const cached = state.playerCache[matchId];

    state.players = clone(cached.players);
    state.events = clone(cached.events);
    state.currentMatch = clone(cached.match);
    state.summary = clone(cached.summary || {});
    state.hasRealPlayers = state.players.length > 0;

    return;
  }

  try{
    let data = null;

    try{
      const res = await fetch(`${API_BASE}/api/scout-live?match_id=${encodeURIComponent(matchId)}`);

      if(!res.ok){
        throw new Error("scout-live ko");
      }

      data = await res.json();

    }catch{
      const alt = await fetch(`${API_BASE}/api/match/${encodeURIComponent(matchId)}/full-analysis`);

      if(!alt.ok){
        throw new Error("full-analysis ko");
      }

      data = await alt.json();
    }

    state.currentMatch = normalizeScoutMatch(data, matchId);
    upsertCurrentMatch();

    state.players = normalizePlayers(data.players || []);
    state.events = normalizeEvents(data.events || []);
    state.summary = data.summary || buildLocalSummary(state.players);
    state.schemaVersion = data.version || "5.9";
    state.hasRealPlayers = state.players.length > 0;

    if(state.hasRealPlayers){
      clearNotice();
    }else{
      showNotice("Il backend ha risposto, ma non ha restituito players reali in data.players.");
    }

  }catch{
    state.players = [];
    state.events = [];
    state.summary = {};
    state.hasRealPlayers = false;

    if(!state.currentMatch){
      state.currentMatch = buildPlaceholderMatch(matchId);
      upsertCurrentMatch();
    }

    showNotice("Dati Scout non disponibili. Controlla /api/scout-live?match_id=...");
  }

  state.playerCache[matchId] = {
    players: clone(state.players),
    events: clone(state.events),
    match: clone(state.currentMatch),
    summary: clone(state.summary)
  };

  state.lastScoutFetch[matchId] = now;

  if(typeof updateLastRefresh === "function"){
    updateLastRefresh();
  }
}

function normalizeScoutMatch(data, fallbackId){
  const m = data.match || {};
  const goals = m.score || m.goals || data.score || data.goals || {};

  return {
    id:String(m.id || m.fixture_id || m.match_id || fallbackId),
    league:cleanText(m.league?.name || m.league || data.league?.name || data.league || "Live"),
    home:cleanText(m.home || m.home_team || data.home || data.home_team || "Home"),
    away:cleanText(m.away || m.away_team || data.away || data.away_team || "Away"),
    scoreHome:num(m.scoreHome ?? m.home_goals ?? goals.home ?? goals.home_goals,0),
    scoreAway:num(m.scoreAway ?? m.away_goals ?? goals.away ?? goals.away_goals,0),
    minute:num(m.minute ?? m.elapsed ?? data.minute,0),
    status:cleanText(m.status || data.status || "LIVE")
  };
}

function upsertCurrentMatch(){
  if(!state.currentMatch){
    return;
  }

  const idx = state.matches.findIndex(m => String(m.id) === String(state.currentMatch.id));

  if(idx >= 0){
    state.matches[idx] = {
      ...state.matches[idx],
      ...state.currentMatch
    };
  }else{
    state.matches.unshift(state.currentMatch);
  }
}

function normalizeMatches(data){
  const list = Array.isArray(data)
    ? data
    : data.matches || data.response || data.data || [];

  return list.map((m,i) => ({
    id:String(m.id || m.fixture_id || m.match_id || m.fixture?.id || `match_${i}`),
    league:cleanText(m.league || m.competition || m.league_name || m.league?.name || "Live"),
    home:cleanText(m.home || m.home_team || m.teams?.home?.name || "Home"),
    away:cleanText(m.away || m.away_team || m.teams?.away?.name || "Away"),
    scoreHome:num(m.scoreHome ?? m.home_goals ?? m.goals?.home ?? m.score?.home,0),
    scoreAway:num(m.scoreAway ?? m.away_goals ?? m.goals?.away ?? m.score?.away,0),
    minute:num(m.minute ?? m.elapsed ?? m.fixture?.status?.elapsed,0),
    status:cleanText(m.status || m.fixture?.status?.short || "LIVE")
  }));
}

function buildPlaceholderMatch(id){
  return {
    id:String(id),
    league:"MatchIQ",
    home:"Match",
    away:"Live",
    scoreHome:0,
    scoreAway:0,
    minute:0,
    status:"LIVE"
  };
}