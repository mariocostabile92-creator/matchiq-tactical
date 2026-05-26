/*
    MatchIQ Scout - State Module
    Stato globale e configurazione Scout Mode.
*/

const API_BASE = "";
const STORAGE_KEY = "matchiq_scout_watchlist_v56_live_sync";

const API_SAFE = {
  liveMatchesRefreshMs: 30000,
  scoutRefreshMs: 45000,
  localEventMs: 7000
};

const state = {
  matches: [],
  selectedMatchId: null,
  currentMatch: null,
  players: [],
  events: [],
  summary: {},
  schemaVersion: "5.6",
  playerCache: {},
  openPlayerId: null,
  timers: {},
  tick: 0,
  lastLiveMatchesFetch: 0,
  lastScoutFetch: {},
  hasRealPlayers: false,
  watchlist: []
};