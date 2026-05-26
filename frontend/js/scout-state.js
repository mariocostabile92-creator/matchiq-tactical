/*
    MatchIQ Scout - State Module
    Stato globale e configurazione Scout Mode.
    V6.2 Stable
*/

const API_BASE = "";
const STORAGE_KEY = "matchiq_scout_watchlist_v62_stable";
const SCOUT_VERSION = "6.2";

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

  schemaVersion: SCOUT_VERSION,

  playerCache: {},
  openPlayerId: null,

  timers: {
    soft: null,
    events: null
  },

  tick: 0,

  lastLiveMatchesFetch: 0,
  lastScoutFetch: {},

  hasRealPlayers: false,

  watchlist: []
};