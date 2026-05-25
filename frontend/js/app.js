const API = window.location.origin;

const matchesContainer = document.getElementById("matches");
const topBtn = document.getElementById("topLeaguesBtn");
const allBtn = document.getElementById("allLiveBtn");

let topOnly = false;
let refreshTimer = null;
let isLoading = false;
let firstLoadDone = false;

let API_USAGE_PERCENT = 40;

const CACHE_TOP = "matchiq_live_matches_top_v5";
const CACHE_ALL = "matchiq_live_matches_all_v5";
const CACHE_LAST_VALID = "matchiq_last_valid_live_matches_v5";

const FINISHED_STATUSES = [
    "FT",
    "AET",
    "PEN",
    "CANC",
    "PST",
    "ABD",
    "AWD",
    "WO"
];

let currentMatchesMap = new Map();

function getRefreshSeconds() {

    if (API_USAGE_PERCENT < 50) return 45;
    if (API_USAGE_PERCENT < 70) return 60;
    if (API_USAGE_PERCENT < 85) return 90;
    if (API_USAGE_PERCENT < 95) return 120;

    return 300;
}

function getSafeModeLabel() {

    if (API_USAGE_PERCENT < 50)
        return "🟢 NORMAL MODE";

    if (API_USAGE_PERCENT < 70)
        return "🟡 SMART SAFE MODE";

    if (API_USAGE_PERCENT < 85)
        return "🟠 API SAFE MODE";

    if (API_USAGE_PERCENT < 95)
        return "🔴 CRITICAL SAFE MODE";

    return "⛔ CACHE ONLY MODE";
}

function getCacheKey() {
    return topOnly ? CACHE_TOP : CACHE_ALL;
}

function getMatchId(match) {

    return (
        match.match_id ||
        match.id ||
        match.fixture_id ||
        match.fixture?.id ||
        match.fixtureId ||
        null
    );
}

function getMatchStatus(match) {

    return String(
        match.status ||
        match.fixture_status ||
        match.elapsed_status ||
        match.fixture?.status?.short ||
        ""
    ).toUpperCase();
}

function getScore(match) {

    if (typeof match.score === "string") {
        return match.score;
    }

    if (
        typeof match.score === "object" &&
        match.score
    ) {
        return `${match.score.home ?? 0}-${match.score.away ?? 0}`;
    }

    return `${match.home_goals ?? 0}-${match.away_goals ?? 0}`;
}

function getMinute(match) {
    return match.minute || match.elapsed || 0;
}

function isFinishedMatch(match) {

    const status = getMatchStatus(match);

    if (FINISHED_STATUSES.includes(status))
        return true;

    const minute = Number(getMinute(match));

    if (
        minute >= 100 &&
        status !== "LIVE" &&
        status !== "1H" &&
        status !== "2H"
    ) {
        return true;
    }

    return false;
}

function normalizeMatches(matches) {

    return (matches || [])
        .filter(match => match && getMatchId(match))
        .filter(match => !isFinishedMatch(match));
}

function matchSignature(match) {

    return JSON.stringify({
        id: getMatchId(match),
        score: getScore(match),
        minute: getMinute(match),
        status: getMatchStatus(match),
        memory_mode: Boolean(match.memory_mode)
    });
}

function saveCache(matches) {

    try {

        const cleanMatches =
            normalizeMatches(matches);

        const payload = {
            timestamp: Date.now(),
            matches: cleanMatches
        };

        localStorage.setItem(
            getCacheKey(),
            JSON.stringify(payload)
        );

        localStorage.setItem(
            CACHE_LAST_VALID,
            JSON.stringify(payload)
        );

    } catch (e) {

        console.warn("Cache non salvata:", e);
    }
}

function loadCache() {

    try {

        const raw =
            localStorage.getItem(getCacheKey()) ||
            localStorage.getItem(CACHE_LAST_VALID);

        if (!raw) return null;

        const parsed = JSON.parse(raw);

        const ageSeconds =
            (Date.now() -
                Number(parsed.timestamp || 0)) / 1000;

        if (ageSeconds > 240)
            return null;

        return normalizeMatches(
            parsed.matches || []
        );

    } catch {

        return null;
    }
}

function clearOldCache() {

    try {

        localStorage.removeItem("matchiq_live_matches_top");
        localStorage.removeItem("matchiq_live_matches_all");
        localStorage.removeItem("matchiq_last_valid_live_matches");

    } catch {}
}

function setEmpty() {

    const seconds =
        getRefreshSeconds();

    matchesContainer.innerHTML = `
        <div class="empty-state">
            <strong>Nessuna partita live disponibile al momento.</strong>
            <span>${getSafeModeLabel()}</span>
            <span>Riproverò automaticamente tra ${seconds} secondi.</span>
        </div>
    `;

    currentMatchesMap.clear();
}

function setLoading() {

    matchesContainer.innerHTML = `
        <div class="empty-state">
            <strong>Caricamento partite live...</strong>
            <span>${getSafeModeLabel()}</span>
        </div>
    `;
}

function createMatchCard(match) {

    const matchId = getMatchId(match);

    const score = getScore(match);

    const minute = getMinute(match);

    const status = getMatchStatus(match);

    const isMemory =
        Boolean(match.memory_mode);

    const card =
        document.createElement("div");

    card.className =
        "match-card live-card-enter";

    card.dataset.matchId =
        matchId;

    card.dataset.signature =
        matchSignature(match);

    card.innerHTML = `

        <div class="league-name">
            ${match.league || "Unknown League"}
        </div>

        <div class="teams-row">

            <div class="team-box">
                <img
                    class="team-logo"
                    src="${match.home_logo || ""}"
                    alt="${match.home || "Home"}"
                >

                <div class="team-name">
                    ${match.home || "Home"}
                </div>
            </div>

            <div class="score-box">

                <div class="score" data-role="score">
                    ${score}
                </div>

                <div class="minute" data-role="minute">
                    ${minute}'
                </div>

                <div class="mini-status">
                    ${status || "LIVE"}
                </div>

            </div>

            <div class="team-box">

                <img
                    class="team-logo"
                    src="${match.away_logo || ""}"
                    alt="${match.away || "Away"}"
                >

                <div class="team-name">
                    ${match.away || "Away"}
                </div>

            </div>

        </div>

        <div class="match-footer">

            <div
                class="live-label ${isMemory ? "memory-label" : ""}"
                data-role="liveLabel"
            >
                ${isMemory ? "● LIVE MEMORY" : "● LIVE"}
            </div>

            <div class="match-buttons">

                <button
                    class="analysis-btn"
                    onclick="openAnalysis('${matchId}')"
                >
                    OPEN ANALYSIS
                </button>

                <button
                    class="analysis-btn"
                    onclick="openScout('${matchId}')"
                >
                    SCOUT LIVE
                </button>

            </div>

        </div>
    `;

    setTimeout(() => {

        card.classList.remove(
            "live-card-enter"
        );

    }, 500);

    return card;
}
function updateMatchCard(card, oldMatch, newMatch) {

    const oldScore = getScore(oldMatch);
    const newScore = getScore(newMatch);

    const oldMinute = getMinute(oldMatch);
    const newMinute = getMinute(newMatch);

    const oldStatus = getMatchStatus(oldMatch);
    const newStatus = getMatchStatus(newMatch);

    const wasMemory = Boolean(oldMatch.memory_mode);
    const isMemory = Boolean(newMatch.memory_mode);

    const scoreEl =
        card.querySelector('[data-role="score"]');

    const minuteEl =
        card.querySelector('[data-role="minute"]');

    const liveLabelEl =
        card.querySelector('[data-role="liveLabel"]');

    const statusEl =
        card.querySelector(".mini-status");

    if (scoreEl && oldScore !== newScore) {

        scoreEl.textContent = newScore;
        card.classList.add("score-changed");

        setTimeout(() => {
            card.classList.remove("score-changed");
        }, 1200);
    }

    if (minuteEl && oldMinute !== newMinute) {

        minuteEl.textContent = `${newMinute}'`;
        minuteEl.classList.add("minute-pulse");

        setTimeout(() => {
            minuteEl.classList.remove("minute-pulse");
        }, 900);
    }

    if (statusEl && oldStatus !== newStatus) {
        statusEl.textContent = newStatus || "LIVE";
    }

    if (liveLabelEl && wasMemory !== isMemory) {

        liveLabelEl.textContent =
            isMemory ? "● LIVE MEMORY" : "● LIVE";

        liveLabelEl.classList.toggle(
            "memory-label",
            isMemory
        );
    }

    card.dataset.signature =
        matchSignature(newMatch);

    card.classList.add("live-updated");

    setTimeout(() => {
        card.classList.remove("live-updated");
    }, 800);
}

function renderMatchesSmart(matches) {

    const liveMatches =
        normalizeMatches(matches);

    if (!liveMatches || liveMatches.length === 0) {
        setEmpty();
        return;
    }

    const emptyState =
        matchesContainer.querySelector(".empty-state");

    if (emptyState)
        matchesContainer.innerHTML = "";

    const newIds = new Set();

    liveMatches.forEach(match => {

        const matchId =
            String(getMatchId(match));

        newIds.add(matchId);

        const existing =
            matchesContainer.querySelector(
                `[data-match-id="${matchId}"]`
            );

        const previous =
            currentMatchesMap.get(matchId);

        if (!existing) {

            const card =
                createMatchCard(match);

            matchesContainer.appendChild(card);
            currentMatchesMap.set(matchId, match);

            return;
        }

        if (
            previous &&
            matchSignature(previous) !== matchSignature(match)
        ) {
            updateMatchCard(existing, previous, match);
        }

        currentMatchesMap.set(matchId, match);
    });

    [...currentMatchesMap.keys()].forEach(matchId => {

        if (!newIds.has(matchId)) {

            const card =
                matchesContainer.querySelector(
                    `[data-match-id="${matchId}"]`
                );

            if (card) {

                card.classList.add("live-card-exit");

                setTimeout(() => {
                    card.remove();
                }, 500);
            }

            currentMatchesMap.delete(matchId);
        }
    });
}

function injectSmartStyles() {

    if (
        document.getElementById(
            "matchiq-smart-refresh-styles"
        )
    ) return;

    const style =
        document.createElement("style");

    style.id =
        "matchiq-smart-refresh-styles";

    style.innerHTML = `

        .live-card-enter {
            animation: liveCardEnter .45s ease;
        }

        .live-card-exit {
            animation: liveCardExit .45s ease forwards;
        }

        .live-updated {
            box-shadow: 0 0 28px rgba(47,107,255,.42) !important;
            border-color: rgba(47,107,255,.55) !important;
        }

        .score-changed {
            animation: scoreChanged .95s ease;
        }

        .minute-pulse {
            animation: minutePulse .8s ease;
        }

        .memory-label {
            color: #ffcc00 !important;
            text-shadow: 0 0 12px rgba(255,204,0,.45);
        }

        .mini-status {
            margin-top: 8px;
            font-size: 11px;
            color: #9db4dc;
            font-weight: 900;
            letter-spacing: .7px;
        }

        .match-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
            justify-content: flex-end;
        }

        @keyframes liveCardEnter {

            from {
                opacity: 0;
                transform: translateY(14px) scale(.98);
            }

            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        @keyframes liveCardExit {

            from {
                opacity: 1;
                transform: translateY(0) scale(1);
            }

            to {
                opacity: 0;
                transform: translateY(10px) scale(.97);
            }
        }

        @keyframes scoreChanged {

            0% {
                transform: scale(1);
                text-shadow: none;
            }

            40% {
                transform: scale(1.14);
                text-shadow: 0 0 26px rgba(255,49,92,.75);
            }

            100% {
                transform: scale(1);
                text-shadow: none;
            }
        }

        @keyframes minutePulse {

            0% {
                transform: scale(1);
                box-shadow: 0 0 0 rgba(239,45,53,0);
            }

            50% {
                transform: scale(1.08);
                box-shadow: 0 0 20px rgba(239,45,53,.55);
            }

            100% {
                transform: scale(1);
                box-shadow: 0 0 0 rgba(239,45,53,0);
            }
        }
    `;

    document.head.appendChild(style);
}

async function loadMatches({
    useLoading = false,
    force = false
} = {}) {

    if (isLoading) return;

    if (document.hidden && !force)
        return;

    const cached = loadCache();

    if (useLoading && !firstLoadDone) {

        if (cached && cached.length > 0) {
            renderMatchesSmart(cached);
        } else {
            setLoading();
        }
    }

    if (API_USAGE_PERCENT >= 95 && !force) {

        if (cached && cached.length > 0) {
            renderMatchesSmart(cached);
        } else {
            setEmpty();
        }

        return;
    }

    isLoading = true;

    try {

        const response = await fetch(
            `${API}/api/live-matches?top_only=${topOnly}&t=${Date.now()}`,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                "HTTP " + response.status
            );
        }

        const data =
            await response.json();

        console.log(
            "LIVE MATCHES RESPONSE:",
            data
        );

        const matches =
            normalizeMatches(
                data.matches ||
                data.live_matches ||
                data.data ||
                []
            );

        if (matches.length > 0) {

            saveCache(matches);
            renderMatchesSmart(matches);

        } else {

            localStorage.removeItem(
                getCacheKey()
            );

            setEmpty();
        }

        firstLoadDone = true;

    } catch (error) {

        console.error(
            "Errore caricamento live matches:",
            error
        );

        if (cached && cached.length > 0) {
            renderMatchesSmart(cached);
        } else {
            setEmpty();
        }

    } finally {

        isLoading = false;
    }
}

function openAnalysis(matchId) {

    if (
        !matchId ||
        matchId === "undefined" ||
        matchId === "null"
    ) {
        alert("ID partita non valido. Aggiorna la pagina.");
        return;
    }

    window.location.href =
        `match.html?id=${encodeURIComponent(matchId)}`;
}

function openScout(matchId) {

    if (
        !matchId ||
        matchId === "undefined" ||
        matchId === "null"
    ) {
        alert("ID partita non valido. Aggiorna la pagina.");
        return;
    }

    window.location.href =
        `scout.html?match_id=${encodeURIComponent(matchId)}`;
}

function startSmartRefresh() {

    stopSmartRefresh();

    const seconds =
        getRefreshSeconds();

    refreshTimer = setInterval(() => {

        if (!document.hidden) {
            loadMatches();
        }

    }, seconds * 1000);
}

function stopSmartRefresh() {

    if (refreshTimer) {

        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

function resetView() {

    currentMatchesMap.clear();
    matchesContainer.innerHTML = "";
    firstLoadDone = false;
}

function setupButtons() {

    if (topBtn && allBtn) {

        if (topOnly) {
            topBtn.classList.add("active");
            allBtn.classList.remove("active");
        } else {
            allBtn.classList.add("active");
            topBtn.classList.remove("active");
        }

        topBtn.onclick = () => {

            topOnly = true;

            topBtn.classList.add("active");
            allBtn.classList.remove("active");

            resetView();

            loadMatches({
                useLoading: true,
                force: true
            });

            startSmartRefresh();
        };

        allBtn.onclick = () => {

            topOnly = false;

            allBtn.classList.add("active");
            topBtn.classList.remove("active");

            resetView();

            loadMatches({
                useLoading: true,
                force: true
            });

            startSmartRefresh();
        };
    }
}

document.addEventListener(
    "visibilitychange",
    () => {

        if (document.hidden) {

            stopSmartRefresh();

        } else {

            loadMatches({
                force: true
            });

            startSmartRefresh();
        }
    }
);

injectSmartStyles();
clearOldCache();
setupButtons();

loadMatches({
    useLoading: true,
    force: true
});

startSmartRefresh();