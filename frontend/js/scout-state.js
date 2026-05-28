/*
    MatchIQ Scout - State Module
    Stato globale e configurazione Scout Mode.
    V8.0.3 Hotfix 3 - Account limits only
*/

const API_BASE = "";
const STORAGE_KEY = "matchiq_scout_watchlist_v803_hotfix3";
const SCOUT_VERSION = "8.0.3-hotfix3";

const API_SAFE = {
  liveMatchesRefreshMs: 30000,
  scoutRefreshMs: 45000,
  localEventMs: 7000
};

const DEFAULT_ACCOUNT_LIMITS = {
  ok: true,
  plan: "guest",
  effective_plan: "guest",
  label: "GUEST PREVIEW",
  is_owner: false,
  is_pro: false,
  limits: {
    max_live_matches: 3,
    scout_enabled: true,
    scout_preview: true,
    scout_max_players: 4,
    export_enabled: false,
    pdf_enabled: false,
    watchlist_enabled: false,
    admin_enabled: false,
    simulate_enabled: false
  }
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
  timers: { soft:null, events:null },
  tick: 0,
  lastLiveMatchesFetch: 0,
  lastScoutFetch: {},
  hasRealPlayers: false,
  watchlist: [],
  account: structuredClone ? structuredClone(DEFAULT_ACCOUNT_LIMITS) : JSON.parse(JSON.stringify(DEFAULT_ACCOUNT_LIMITS)),
  plan: "guest",
  isOwner: false,
  isPro: false
};

function normalizeAccountLimits(data){
  const raw = data && typeof data === "object" ? data : {};
  const plan = String(raw.effective_plan || raw.plan || "guest").toLowerCase();
  const limits = Object.assign({}, DEFAULT_ACCOUNT_LIMITS.limits, raw.limits || raw.features || {});
  const isOwner = plan === "owner" || raw.is_owner === true;
  const isPro = isOwner || plan === "pro" || plan === "scout" || raw.is_pro === true;
  if(isOwner || isPro){
    limits.scout_enabled = true;
    limits.scout_preview = false;
    limits.scout_max_players = 999;
    limits.export_enabled = true;
    limits.pdf_enabled = true;
    limits.watchlist_enabled = true;
    limits.simulate_enabled = true;
  }
  limits.admin_enabled = isOwner;
  return { ok:true, plan, effective_plan:plan, label:isOwner?"OWNER PRO":isPro?"PRO":"GUEST PREVIEW", is_owner:isOwner, is_pro:isPro, limits };
}

function applyAccountLimits(account){
  state.account = normalizeAccountLimits(account);
  state.plan = state.account.effective_plan;
  state.isOwner = !!state.account.is_owner;
  state.isPro = !!state.account.is_pro;
}

function getScoutLimit(key, fallback=null){
  return state.account?.limits?.[key] ?? fallback;
}

function canUseScoutPro(){ return !!state.isPro || !!state.isOwner; }
function canUseAdmin(){ return !!state.isOwner; }
function canExportScout(){ return !!getScoutLimit("export_enabled", false); }
function canUseWatchlist(){ return !!getScoutLimit("watchlist_enabled", false); }
function canSimulateScout(){ return !!getScoutLimit("simulate_enabled", false); }
function scoutPlayerLimit(){ return Number(getScoutLimit("scout_max_players", 4)) || 4; }
