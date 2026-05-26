/*
    MatchIQ - Match State Module
    Stato globale e configurazione della pagina match.
*/

const API_BASE=`${window.location.origin}/api`;
const matchId=new URLSearchParams(window.location.search).get("id");

let momentumChart=null;
let isRefreshing=false;
let previousSnapshot=null;
let refreshInterval=null;
let countdownInterval=null;
let countdownValue=30;
let lastUpdateAt=null;
let cinematicEvents=[];
let momentumHistory=[];
let lastMomentumSignature=null;

/*
    API SAFE MODE v1.3.7
    Cambia questo valore quando vuoi simulare/proteggere il consumo API.
    40 = consumo attuale circa 40%.
*/
const API_USAGE_PERCENT=40;
const CACHE_VERSION="v1.3.7";
const CACHE_KEY=`matchiq_match_${matchId||"unknown"}_last_valid_${CACHE_VERSION}`;
const CACHE_TIME_KEY=`matchiq_match_${matchId||"unknown"}_last_valid_time_${CACHE_VERSION}`;

let lastValidData=null;
let cacheModeActive=false;

let sectionState={
    psych:true,
    sim:true,
    identity:true,
    attack:true,
    events:true,
    win:true,
    future:true,
    xg:true,
    alerts:true,
    coach:true,
    momentum:true,
    tactical:false,
    heatmap:false,
    players:false,
    commentary:false,
    timeline:false,
    report:false
};