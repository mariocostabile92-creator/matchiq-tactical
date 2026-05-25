import os
import time
import threading
from datetime import datetime

from fastapi import FastAPI, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from live_data import get_live_matches, get_match_live_data
from tactical_engine import analyze_match_tactical
from report_engine import generate_ai_report
from event_engine import generate_tactical_events
from alert_engine import generate_live_alerts
from live_timeline import generate_timeline
from live_events import build_live_events
from matchiq_ai_core import analyze_ai_core
from pressure_engine import analyze_pressure
from win_probability import generate_win_probability
from player_engine import generate_player_ratings
from live_event_engine import generate_live_engine
from tactical_coach import generate_tactical_coach
from future_prediction import generate_future_prediction
from xg_engine import generate_xg_analysis
from pdf_report import generate_match_pdf
from live_flow_engine import generate_live_flow
from ai_commentary_engine import generate_ai_commentary
from payments import router as payments_router

from auth import router as auth_router
from database import init_db
from usage_guard import (
    get_optional_user,
    enforce_guest_or_user_limit,
    enforce_premium_feature,
    attach_usage_info,
    build_account_limits_response
)

try:
    from scout_engine import build_live_scout
    SCOUT_ENGINE_AVAILABLE = True
except Exception:
    SCOUT_ENGINE_AVAILABLE = False

    def build_live_scout(players, match_data=None):
        return {
            "available": False,
            "source": "fallback",
            "error": "scout_engine.py non disponibile",
            "generated_at": datetime.utcnow().isoformat(),
            "players": players or [],
            "top_performer": players[0] if players else None,
            "hidden_gems": [p for p in players or [] if p.get("hidden_gem")],
            "danger_creators": [p for p in players or [] if p.get("danger_creator")],
            "total_players": len(players or [])
        }


try:
    from live_data import LIVE_MATCH_MEMORY, LIVE_MEMORY_SECONDS
except Exception:
    LIVE_MATCH_MEMORY = {}
    LIVE_MEMORY_SECONDS = 0


try:
    from live_match_brain import build_live_match_brain
    LIVE_MATCH_BRAIN_AVAILABLE = True
except Exception:
    LIVE_MATCH_BRAIN_AVAILABLE = False

    def build_live_match_brain(**kwargs):
        return {
            "available": False,
            "error": "live_match_brain.py non disponibile",
            "commentary": [],
            "prediction": {},
        }


app = FastAPI(
    title="MatchIQ Tactical API",
    version="3.5.0",
    description="MatchIQ Tactical PRO con Scout Mode Real Players Only e API Safe Cache"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app.include_router(auth_router)
app.include_router(payments_router)

LIVE_MATCHES_CACHE = {}
FULL_ANALYSIS_CACHE = {}
SCOUT_PLAYERS_CACHE = {}

LIVE_MATCHES_CACHE_SECONDS = 60
FULL_ANALYSIS_CACHE_SECONDS = 30
SCOUT_PLAYERS_CACHE_SECONDS = 1800

BACKGROUND_REFRESH_ENABLED = True

MATCH_PRIORITY = {
    "Serie A": 15,
    "Premier League": 15,
    "Champions League": 15,
    "Bundesliga": 20,
    "La Liga": 20,
    "Ligue 1": 25,
}

DEFAULT_MATCH_CACHE = 35
FINISHED_MATCH_CACHE = 600
HALFTIME_CACHE = 60

def cache_valid(cache_item, seconds):
    if not cache_item:
        return False
    return time.time() - cache_item["timestamp"] < seconds

def get_dynamic_match_cache(match_data):
    if not isinstance(match_data, dict):
        return DEFAULT_MATCH_CACHE

    status = str(match_data.get("status", "")).upper()
    league = str(match_data.get("league", ""))

    if status in ["FT", "FINISHED"]:
        return FINISHED_MATCH_CACHE

    if status in ["HT", "HALFTIME"]:
        return HALFTIME_CACHE

    return MATCH_PRIORITY.get(
        league,
        DEFAULT_MATCH_CACHE
    )



def background_refresh_match(match_id):

    try:

        print(f"[BACKGROUND REFRESH] {match_id}")

        data = build_full_analysis(match_id)

        if "error" not in data:

            FULL_ANALYSIS_CACHE[match_id] = {
                "timestamp": time.time(),
                "data": data
            }

            print(f"[CACHE UPDATED] {match_id}")

    except Exception as e:

        print("BACKGROUND REFRESH ERROR:", e)


def launch_background_refresh(match_id):

    if not BACKGROUND_REFRESH_ENABLED:
        return

    try:

        thread = threading.Thread(
            target=background_refresh_match,
            args=(match_id,),
            daemon=True
        )

        thread.start()

    except Exception as e:

        print("THREAD ERROR:", e)



def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def clamp(value, min_value=0, max_value=100):
    try:
        return max(min_value, min(max_value, int(value)))
    except Exception:
        return min_value


def merge_pressure(base_pressure, live_engine):
    if not isinstance(base_pressure, dict):
        base_pressure = {}

    return {
        "generated_at": live_engine.get("generated_at"),
        "minute": live_engine.get("minute"),
        "dominance_score": base_pressure.get("dominance_score", 50),
        "dominance_label": live_engine.get(
            "dominance_label",
            base_pressure.get("dominance_label", "Equilibrio")
        ),
        "dominant_team": live_engine.get(
            "dominant_team",
            base_pressure.get("dominant_team", "Equilibrio")
        ),
        "home": {
            **base_pressure.get("home", {}),
            **live_engine.get("home", {})
        },
        "away": {
            **base_pressure.get("away", {}),
            **live_engine.get("away", {})
        },
        "alerts": live_engine.get("alerts", base_pressure.get("alerts", []))
    }


def build_safe_ai_commentary(match_data, pressure, live_flow):
    try:
        commentary = generate_ai_commentary(
            match_data=match_data,
            pressure_data=pressure,
            live_flow=live_flow
        )

        if isinstance(commentary, dict):
            commentary["available"] = True
            commentary["source"] = "ai_commentary_engine"
            return commentary

        return {
            "available": False,
            "source": "ai_commentary_engine",
            "error": "Risposta ai_commentary non valida",
            "commentary": []
        }

    except Exception as e:
        return {
            "available": False,
            "source": "ai_commentary_engine",
            "error": str(e),
            "commentary": []
        }


def build_safe_live_brain(
    match_data,
    pressure,
    xg_analysis,
    live_flow,
    future_prediction,
    timeline
):
    try:
        timeline_events = []

        if isinstance(timeline, dict):
            timeline_events = timeline.get("events", [])
        elif isinstance(timeline, list):
            timeline_events = timeline

        brain = build_live_match_brain(
            match=match_data,
            pressure_engine=pressure,
            xg_analysis=xg_analysis,
            live_flow=live_flow,
            future_prediction=future_prediction,
            timeline=timeline_events,
        )

        if isinstance(brain, dict):
            brain["available"] = LIVE_MATCH_BRAIN_AVAILABLE
            brain["source"] = "live_match_brain"
            return brain

        return {
            "available": False,
            "source": "live_match_brain",
            "error": "Risposta live_brain non valida",
            "commentary": [],
            "prediction": {},
        }

    except Exception as e:
        return {
            "available": False,
            "source": "live_match_brain",
            "error": str(e),
            "commentary": [],
            "prediction": {},
        }


def normalize_player_for_scout(player, match_data=None):
    if not isinstance(player, dict):
        return None

    match_data = match_data or {}

    name = (
        player.get("name")
        or player.get("player_name")
        or player.get("player")
        or player.get("nome")
    )

    if isinstance(name, dict):
        name = name.get("name")

    if not name:
        return None

    rating = safe_float(
        player.get("rating_api")
        or player.get("rating")
        or player.get("vote")
        or player.get("score"),
        6.5
    )

    goals = safe_int(player.get("goals", 0))
    assists = safe_int(player.get("assists", 0))
    shots = safe_int(player.get("shots", 0))
    key_passes = safe_int(player.get("key_passes", 0))
    dribbles = safe_int(player.get("dribbles", player.get("dribbles_success", 0)))
    tackles = safe_int(player.get("tackles", 0))
    duels_won = safe_int(player.get("duels_won", 0))
    minutes = safe_int(player.get("minutes", match_data.get("minute", 0)))
    xg = safe_float(player.get("xg", 0.0))
    pass_accuracy = safe_int(player.get("pass_accuracy", 0))
    fouls = safe_int(player.get("fouls", player.get("fouls_committed", 0)))
    cards_yellow = safe_int(player.get("cards_yellow", 0))
    cards_red = safe_int(player.get("cards_red", 0))

    momentum = clamp(
        rating * 10
        + shots * 3
        + key_passes * 4
        + dribbles * 3
        + goals * 10
        + assists * 7
    )

    fatigue = clamp(
        minutes * 0.85
        + fouls * 4
        + tackles * 2
        + dribbles * 1.5
        + cards_yellow * 5
        + cards_red * 15
    )

    scout_score = clamp(
        rating * 12
        + key_passes * 3
        + dribbles * 2
        + duels_won
        + goals * 8
        + assists * 6
        + xg * 10
    )

    hidden_gem = (
        rating >= 7.0
        and dribbles >= 2
        and key_passes >= 1
        and goals == 0
    )

    danger_creator = (
        shots >= 2
        or key_passes >= 3
        or xg >= 0.35
        or goals >= 1
        or assists >= 1
    )

    if scout_score >= 90:
        level = "WORLD CLASS"
    elif scout_score >= 75:
        level = "ELITE"
    elif scout_score >= 60:
        level = "TOP PLAYER"
    else:
        level = "STANDARD"

    if scout_score >= 82:
        signal_type = "hot"
        signal = "Hot Player"
    elif danger_creator:
        signal_type = "danger"
        signal = "Danger Creator"
    elif hidden_gem:
        signal_type = "gem"
        signal = "Hidden Gem"
    elif tackles >= 3 or duels_won >= 5:
        signal_type = "pressure"
        signal = "Pressure Trigger"
    else:
        signal_type = "gem"
        signal = "AI Watch"

    return {
        "id": player.get("id"),
        "name": name,
        "photo": player.get("photo"),
        "team": player.get("team") or player.get("team_name") or player.get("squadra") or "Unknown",
        "team_logo": player.get("team_logo"),
        "role": player.get("role") or player.get("position"),
        "position": player.get("position") or player.get("role"),

        "rating": round(rating, 1),
        "goals": goals,
        "assists": assists,
        "shots": shots,
        "key_passes": key_passes,
        "dribbles": dribbles,
        "tackles": tackles,
        "duels_won": duels_won,
        "minutes": minutes,
        "pass_accuracy": pass_accuracy,
        "xg": round(xg, 2),

        "momentum": momentum,
        "fatigue": fatigue,
        "scout_score": scout_score,
        "scoutScore": scout_score,
        "threat": clamp(shots * 12 + key_passes * 10 + xg * 30 + goals * 20 + assists * 15),
        "pressure": clamp(tackles * 10 + duels_won * 6 + pass_accuracy * 0.25),
        "keyPasses": key_passes,

        "hidden_gem": hidden_gem,
        "danger_creator": danger_creator,
        "level": level,
        "signalType": signal_type,
        "signal": signal,

        "real_data": bool(player.get("rating_api") or player.get("id")),
        "generated_at": datetime.utcnow().isoformat()
    }


def extract_players_for_scout(players_analysis, match_data=None):
    if not players_analysis:
        return []

    raw_players = []

    if isinstance(players_analysis, dict):
        if isinstance(players_analysis.get("players"), list):
            raw_players = players_analysis.get("players", [])
        elif isinstance(players_analysis.get("top_players"), list):
            raw_players = players_analysis.get("top_players", [])
        elif isinstance(players_analysis.get("ratings"), list):
            raw_players = players_analysis.get("ratings", [])
    elif isinstance(players_analysis, list):
        raw_players = players_analysis

    normalized = []

    for p in raw_players:
        item = normalize_player_for_scout(p, match_data=match_data)
        if item:
            normalized.append(item)

    return sorted(
        normalized,
        key=lambda x: x.get("scout_score", 0),
        reverse=True
    )


def build_full_analysis(match_id: int):
    match_data = get_match_live_data(match_id)

    if "error" in match_data:
        return match_data

    tactical = analyze_match_tactical(match_data)
    live_engine = generate_live_engine(match_data)

    pressure_base = analyze_pressure(match_data)
    pressure = merge_pressure(pressure_base, live_engine)

    xg_analysis = generate_xg_analysis(
        match_data=match_data,
        tactical_data={
            "home_pressure": pressure.get("home", {}).get("pressure", 50),
            "away_pressure": pressure.get("away", {}).get("pressure", 50),
        }
    )

    live_flow = generate_live_flow(
        match_data=match_data,
        pressure_data=pressure,
        xg_data=xg_analysis
    )

    ai_commentary = build_safe_ai_commentary(
        match_data=match_data,
        pressure=pressure,
        live_flow=live_flow
    )

    tactical_coach = generate_tactical_coach(
        match_data=match_data,
        pressure_data=pressure
    )

    future_prediction = generate_future_prediction(
        match_data=match_data,
        pressure_data=pressure
    )

    ai_core = analyze_ai_core(match_data)

    if isinstance(ai_core, dict):
        commentary_lines = ai_commentary.get("commentary", [])

        ai_core["commentary"] = (
            commentary_lines
            or live_engine.get("commentary")
            or ai_core.get("commentary", [])
        )

        ai_core["confidence_score"] = live_engine.get(
            "confidence_score",
            ai_core.get("confidence_score", 70)
        )

        ai_core["live_flow_story"] = live_flow.get("story")

    players = generate_player_ratings(match_data)

    win_probability = generate_win_probability({
        "goals": match_data.get("score", {}),
        "minute": match_data.get("minute", 0),
        "tactical_analysis": {
            "home_pressure": pressure.get("home", {}).get("pressure", 0),
            "away_pressure": pressure.get("away", {}).get("pressure", 0),
            "home_danger": pressure.get("home", {}).get("danger", 0),
            "away_danger": pressure.get("away", {}).get("danger", 0),
            "home_win_momentum": live_flow.get("home", {}).get("momentum", 50),
            "away_win_momentum": live_flow.get("away", {}).get("momentum", 50),
        }
    })

    events = generate_tactical_events(match_data)
    alerts = generate_live_alerts(events)
    live_events = build_live_events(match_data)
    report = generate_ai_report(match_data, tactical, players)

    try:
        timeline = generate_timeline(
            match_data=match_data,
            tactical_data={
                "tactical": tactical,
                "events": events
            },
            alerts_data={
                "live_alerts": alerts
            }
        )
    except Exception:
        timeline = {
            "events": live_engine.get("timeline", [])
        }

    live_brain = build_safe_live_brain(
        match_data=match_data,
        pressure=pressure,
        xg_analysis=xg_analysis,
        live_flow=live_flow,
        future_prediction=future_prediction,
        timeline=timeline,
    )

    if isinstance(ai_core, dict) and isinstance(live_brain, dict):
        prediction = live_brain.get("prediction", {})
        if isinstance(prediction, dict):
            ai_core["live_brain_prediction"] = prediction.get("next_5_minutes")

    return {
        "match": match_data,
        "tactical_analysis": tactical,
        "ai_core": ai_core,
        "ai_commentary": ai_commentary,
        "pressure_engine": pressure,
        "live_engine": live_engine,
        "live_flow": live_flow,
        "live_brain": live_brain,
        "tactical_coach": tactical_coach,
        "future_prediction": future_prediction,
        "xg_analysis": xg_analysis,
        "win_probability": win_probability,
        "players_analysis": players,
        "event_analysis": events,
        "live_alerts": pressure.get("alerts", alerts),
        "live_events": live_events,
        "timeline": timeline,
        "ai_report": report
    }

def get_cached_full_analysis(match_id: int):
    cached = FULL_ANALYSIS_CACHE.get(match_id)

    dynamic_seconds = FULL_ANALYSIS_CACHE_SECONDS

    if cached:
        try:
            cached_match = cached["data"].get("match", {})
            dynamic_seconds = get_dynamic_match_cache(cached_match)
        except Exception:
            pass

    if cache_valid(cached, dynamic_seconds):
        try:
            launch_background_refresh(match_id)
        except Exception:
            pass

        cached["data"]["cache"] = True
        cached["data"]["cache_seconds"] = dynamic_seconds

        return cached["data"]

    try:
        data = build_full_analysis(match_id)

        if "error" not in data:
            FULL_ANALYSIS_CACHE[match_id] = {
                "timestamp": time.time(),
                "data": data
            }

            data["cache"] = False
            data["cache_seconds"] = dynamic_seconds

        elif cached:
            cached["data"]["cache_warning"] = data.get("error")
            return cached["data"]

        return data

    except Exception as e:
        if cached:
            cached["data"]["cache_warning"] = str(e)
            return cached["data"]

        return {
            "error": str(e),
            "match_id": match_id
        }

       
def build_real_scout_response(match_id: int = None):
    cache_key = f"scout_{match_id}"

    cached = SCOUT_PLAYERS_CACHE.get(cache_key)

    if cache_valid(cached, SCOUT_PLAYERS_CACHE_SECONDS):
        data = cached["data"].copy()
        data["cache"] = True
        data["cache_seconds"] = SCOUT_PLAYERS_CACHE_SECONDS
        return data

    match_data = {}
    players = []
    source_mode = "real_players_unavailable"
    error_message = None

    if match_id:
        try:
            match_data = get_match_live_data(match_id)

            if "error" not in match_data:
                real_players = match_data.get("players", [])
                players = extract_players_for_scout(
                    real_players,
                    match_data=match_data
                )
                source_mode = "live_real_players" if players else "live_no_players"
            else:
                error_message = match_data.get("error")

        except Exception as e:
            error_message = str(e)
            match_data = {
                "error": str(e),
                "match_id": match_id
            }
            players = []

    if not players and match_id:
        try:
            full = get_cached_full_analysis(match_id)

            if "error" not in full:
                match_data = full.get("match", match_data)

                players = extract_players_for_scout(
                    full.get("match", {}).get("players", []),
                    match_data=match_data
                )

                if not players:
                    players = extract_players_for_scout(
                        full.get("players_analysis", {}),
                        match_data=match_data
                    )

                if players:
                    source_mode = "live_full_analysis"

        except Exception as e:
            error_message = str(e)

    if not players:
        players = []
        source_mode = "real_players_unavailable"

    players = sorted(
        players,
        key=lambda x: x.get("scout_score", 0),
        reverse=True
    )[:16]

    scout = build_live_scout(
        players=players,
        match_data=match_data
    )

    if not isinstance(scout, dict):
        scout = {
            "available": False,
            "source": "scout_engine_invalid",
            "players": players
        }

    scout["available"] = SCOUT_ENGINE_AVAILABLE
    scout["source"] = "scout_engine" if SCOUT_ENGINE_AVAILABLE else "fallback"
    scout["match_id"] = match_id
    scout["mode"] = "live" if match_id else "demo"
    scout["data_mode"] = source_mode
    scout["real_players"] = source_mode in ["live_real_players", "live_full_analysis"]
    scout["premium_feature"] = True
    scout["required_plan"] = "scout"
    scout["cache"] = False
    scout["cache_seconds"] = SCOUT_PLAYERS_CACHE_SECONDS
    scout["api_safe"] = True
    scout["players"] = players
    scout["total_players"] = len(players)
    scout["error"] = error_message

    scout["match"] = {
        "home": match_data.get("home"),
        "away": match_data.get("away"),
        "home_logo": match_data.get("home_logo"),
        "away_logo": match_data.get("away_logo"),
        "score": match_data.get("score"),
        "minute": match_data.get("minute"),
        "status": match_data.get("status"),
        "league": match_data.get("league"),
    }

    if match_id:
        SCOUT_PLAYERS_CACHE[cache_key] = {
            "timestamp": time.time(),
            "data": scout
        }

    return scout


@app.get("/api")
def api_home():
    return {
        "app": "MatchIQ Tactical",
        "status": "online",
        "version": "3.5.0",
        "auth": "enabled",
        "scout_mode": "real_players_only",
        "api_safe": True
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "version": "3.5.0",
        "auth": "online",
        "cache": {
            "live_matches_seconds": LIVE_MATCHES_CACHE_SECONDS,
            "full_analysis_seconds": FULL_ANALYSIS_CACHE_SECONDS,
            "scout_players_seconds": SCOUT_PLAYERS_CACHE_SECONDS,
            "live_matches_cached": len(LIVE_MATCHES_CACHE),
            "full_analysis_cached": len(FULL_ANALYSIS_CACHE),
            "scout_players_cached": len(SCOUT_PLAYERS_CACHE)
        },
        "services": {
            "auth_system": "online",
            "database": "online",
            "live_data": "online",
            "scout_engine": "online" if SCOUT_ENGINE_AVAILABLE else "fallback",
            "tactical_engine": "online",
            "matchiq_ai_core": "online",
            "ai_commentary_engine": "online",
            "pressure_engine": "online",
            "live_event_engine": "online",
            "live_flow_engine": "online",
            "live_match_brain": "online" if LIVE_MATCH_BRAIN_AVAILABLE else "fallback",
            "tactical_coach": "online",
            "future_prediction_engine": "online",
            "xg_engine": "online",
            "pdf_report_engine": "online",
            "pdf_download": "online",
            "win_probability_engine": "online",
            "player_ratings_engine": "online",
            "event_engine": "online",
            "alert_engine": "online",
            "timeline_engine": "online",
            "live_events_engine": "online",
            "live_memory": "online",
            "static_files": "online"
        }
    }


@app.get("/api/live")
def api_live(top_only: bool = Query(False)):
    return get_live_matches(top_only=top_only)


@app.get("/api/live-matches")
def live_matches(top_only: bool = Query(True)):
    cache_key = f"top_only_{top_only}"
    cached = LIVE_MATCHES_CACHE.get(cache_key)

    if cache_valid(cached, LIVE_MATCHES_CACHE_SECONDS):
        data = cached["data"]
        data["cache"] = True
        data["api_safe"] = True
        return data

    try:
        data = get_live_matches(top_only=top_only)

        matches = []

        if isinstance(data, dict):
            raw_matches = (
                data.get("matches")
                or data.get("data")
                or data.get("live_matches")
                or []
            )
        elif isinstance(data, list):
            raw_matches = data
        else:
            raw_matches = []

        for m in raw_matches:
            if not isinstance(m, dict):
                continue

            match_id = (
                m.get("id")
                or m.get("match_id")
                or m.get("fixture_id")
                or m.get("fixture", {}).get("id")
            )

            home = (
                m.get("home")
                or m.get("home_team")
                or m.get("teams", {}).get("home", {}).get("name")
                or "Home"
            )

            away = (
                m.get("away")
                or m.get("away_team")
                or m.get("teams", {}).get("away", {}).get("name")
                or "Away"
            )

            score = m.get("score", {})
if isinstance(score, str):
    parts = score.replace(" ", "").split("-")
    score = {
        "home": safe_int(parts[0], 0) if len(parts) > 0 else 0,
        "away": safe_int(parts[1], 0) if len(parts) > 1 else 0
    }

if not isinstance(score, dict):
    score = {}

            home_goals = (
                m.get("home_goals")
                or m.get("goals", {}).get("home")
                or score.get("home")
                or 0
            )

            away_goals = (
                m.get("away_goals")
                or m.get("goals", {}).get("away")
                or score.get("away")
                or 0
            )

            minute = (
                m.get("minute")
                or m.get("elapsed")
                or m.get("fixture", {}).get("status", {}).get("elapsed")
                or 0
            )

            status = (
                m.get("status")
                or m.get("fixture", {}).get("status", {}).get("short")
                or "LIVE"
            )

            league = (
                m.get("league")
                or m.get("league_name")
                or m.get("league", {}).get("name")
                or "Live"
            )

            home_logo = (
                m.get("home_logo")
                or m.get("teams", {}).get("home", {}).get("logo")
                or ""
            )

            away_logo = (
                m.get("away_logo")
                or m.get("teams", {}).get("away", {}).get("logo")
                or ""
            )

            item = {
                "id": match_id,
                "match_id": match_id,
                "fixture_id": match_id,

                "home": home,
                "away": away,
                "home_team": home,
                "away_team": away,

                "home_logo": home_logo,
                "away_logo": away_logo,

                "score": {
                    "home": home_goals,
                    "away": away_goals
                },

                "home_goals": home_goals,
                "away_goals": away_goals,

                "minute": minute,
                "status": status,
                "league": league,

                "url_match": f"/match.html?id={match_id}",
                "url_scout": f"/scout.html?match_id={match_id}"
            }

            if match_id:
                matches.append(item)

        response = {
            "source": "api-football",
            "top_only": top_only,
            "total_matches": len(matches),
            "matches": matches,
            "data": matches,
            "live_matches": matches,
            "cache": False,
            "api_safe": True
        }

        if matches:
            LIVE_MATCHES_CACHE[cache_key] = {
                "timestamp": time.time(),
                "data": response
            }
            return response

        if cached:
            cached["data"]["cache"] = True
            cached["data"]["cache_warning"] = "Nessuna partita live nuova, uso cache precedente"
            return cached["data"]

        return response

    except Exception as e:
        if cached:
            cached["data"]["cache"] = True
            cached["data"]["cache_warning"] = str(e)
            return cached["data"]

        return {
            "source": "api-football",
            "top_only": top_only,
            "total_matches": 0,
            "matches": [],
            "data": [],
            "live_matches": [],
            "error": str(e),
            "api_safe": True
        }

@app.get("/api/scout/live")
def api_scout_live(
    match_id: int = Query(None),
    user=Depends(get_optional_user)
):
    enforce_guest_or_user_limit(
        user=user,
        feature="scout",
        endpoint="/api/scout/live"
    )

    data = build_real_scout_response(match_id=match_id)

    return attach_usage_info(
        response=data,
        user=user,
        feature="scout"
    )


@app.get("/api/scout-live")
def api_scout_live_alias(
    match_id: int = Query(None),
    user=Depends(get_optional_user)
):
    enforce_guest_or_user_limit(
        user=user,
        feature="scout",
        endpoint="/api/scout-live"
    )

    data = build_real_scout_response(match_id=match_id)

    return attach_usage_info(
        response=data,
        user=user,
        feature="scout"
    )


@app.get("/api/live-memory-status")
def live_memory_status():
    items = []

    now = datetime.now()

    for match_id, item in LIVE_MATCH_MEMORY.items():
        match = item.get("match", {})
        last_seen = item.get("last_seen")

        age_seconds = None
        if last_seen:
            age_seconds = int((now - last_seen).total_seconds())

        items.append({
            "match_id": match_id,
            "home": match.get("home"),
            "away": match.get("away"),
            "score": match.get("score"),
            "minute": match.get("minute"),
            "status": match.get("status"),
            "league": match.get("league"),
            "memory_mode": match.get("memory_mode", False),
            "age_seconds": age_seconds
        })

    return {
        "live_memory_enabled": True,
        "memory_seconds": LIVE_MEMORY_SECONDS,
        "total_memory_matches": len(items),
        "matches": items
    }


@app.get("/api/cache-status")
def cache_status():
    return {
        "live_matches_cache": {
            "seconds": LIVE_MATCHES_CACHE_SECONDS,
            "keys": list(LIVE_MATCHES_CACHE.keys()),
            "count": len(LIVE_MATCHES_CACHE)
        },
        "full_analysis_cache": {
            "seconds": FULL_ANALYSIS_CACHE_SECONDS,
            "keys": list(FULL_ANALYSIS_CACHE.keys()),
            "count": len(FULL_ANALYSIS_CACHE)
        },
        "scout_players_cache": {
            "seconds": SCOUT_PLAYERS_CACHE_SECONDS,
            "keys": list(SCOUT_PLAYERS_CACHE.keys()),
            "count": len(SCOUT_PLAYERS_CACHE)
        },
        "live_memory": {
            "seconds": LIVE_MEMORY_SECONDS,
            "count": len(LIVE_MATCH_MEMORY)
        }
    }

@app.get("/api/backend-status")
def backend_status():

    return {

        "online": True,

        "version": "4.0 ONLINE READY",

        "api_safe": True,

        "background_refresh": BACKGROUND_REFRESH_ENABLED,

        "cache_system": {

            "live_matches_seconds":
                LIVE_MATCHES_CACHE_SECONDS,

            "full_analysis_dynamic": True,

            "finished_match_cache":
                FINISHED_MATCH_CACHE,

            "halftime_cache":
                HALFTIME_CACHE,

            "priority_leagues":
                MATCH_PRIORITY
        },

        "memory": {

            "live_matches_cached":
                len(LIVE_MATCHES_CACHE),

            "full_analysis_cached":
                len(FULL_ANALYSIS_CACHE),

            "scout_cached":
                len(SCOUT_PLAYERS_CACHE)
        }
    }

@app.get("/api/account/limits")
def account_limits(user=Depends(get_optional_user)):
    return build_account_limits_response(user)

@app.post("/api/clear-cache")
def clear_cache():
    LIVE_MATCHES_CACHE.clear()
    FULL_ANALYSIS_CACHE.clear()
    SCOUT_PLAYERS_CACHE.clear()

    return {
        "success": True,
        "message": "Cache backend pulita correttamente"
    }


@app.get("/api/match/{match_id}/full-analysis")
def full_analysis(
    match_id: int,
    user=Depends(get_optional_user)
):
    enforce_guest_or_user_limit(
        user=user,
        feature="full_analysis",
        endpoint="/api/match/full-analysis"
    )

    data = get_cached_full_analysis(match_id)

    return attach_usage_info(
        response=data,
        user=user,
        feature="full_analysis"
    )


@app.get("/api/match/{match_id}/ai-commentary")
def ai_commentary_analysis(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "ai_commentary": full.get("ai_commentary", {})
    }


@app.get("/api/match/{match_id}/players")
def player_ratings(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "players_analysis": full["players_analysis"]
    }


@app.get("/api/match/{match_id}/win-probability")
def win_probability_analysis(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "win_probability": full["win_probability"]
    }


@app.get("/api/match/{match_id}/pressure")
def pressure_analysis(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "pressure_engine": full["pressure_engine"]
    }


@app.get("/api/match/{match_id}/live-engine")
def live_engine_analysis(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "live_engine": full["live_engine"]
    }


@app.get("/api/match/{match_id}/live-flow")
def live_flow_analysis(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "live_flow": full["live_flow"]
    }


@app.get("/api/match/{match_id}/live-brain")
def live_brain_analysis(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "live_brain": full.get("live_brain", {})
    }


@app.get("/api/match/{match_id}/tactical-coach")
def tactical_coach_analysis(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "tactical_coach": full["tactical_coach"]
    }


@app.get("/api/match/{match_id}/future-prediction")
def future_prediction_analysis(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "future_prediction": full["future_prediction"]
    }


@app.get("/api/match/{match_id}/xg")
def xg_analysis(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "xg_analysis": full["xg_analysis"]
    }


@app.get("/api/match/{match_id}/pdf-report")
def pdf_report(match_id: int):
    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    try:
        pdf = generate_match_pdf(full)
        return {
            "match_id": match_id,
            "success": True,
            "pdf_report": pdf
        }

    except Exception as e:
        return {
            "match_id": match_id,
            "success": False,
            "error": str(e)
        }


@app.get("/api/match/{match_id}/download-pdf")
def download_pdf_report(
    match_id: int,
    user=Depends(get_optional_user)
):
    enforce_premium_feature(
        user=user,
        feature="pdf_export"
    )

    enforce_guest_or_user_limit(
        user=user,
        feature="pdf_export",
        endpoint="/api/match/download-pdf"
    )

    full = get_cached_full_analysis(match_id)

    if "error" in full:
        return full

    try:
        pdf = generate_match_pdf(full)
        pdf_path = pdf.get("pdf_path")

        if not pdf_path:
            return {
                "match_id": match_id,
                "success": False,
                "error": "PDF path non trovato"
            }

        absolute_path = os.path.abspath(pdf_path)

        if not os.path.exists(absolute_path):
            return {
                "match_id": match_id,
                "success": False,
                "error": "PDF non trovato"
            }

        filename = os.path.basename(absolute_path)

        return FileResponse(
            path=absolute_path,
            media_type="application/pdf",
            filename=filename
        )

    except Exception as e:
        return {
            "match_id": match_id,
            "success": False,
            "error": str(e)
        }

# =========================================================
# FRONTEND STATIC
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

print("FRONTEND_DIR:", FRONTEND_DIR)
print("FRONTEND EXISTS:", os.path.exists(FRONTEND_DIR))

if os.path.exists(FRONTEND_DIR):

    @app.get("/")
    def serve_home():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/scout.html")
    def serve_scout():
        return FileResponse(os.path.join(FRONTEND_DIR, "scout.html"))

    @app.get("/match.html")
    def serve_match():
        return FileResponse(os.path.join(FRONTEND_DIR, "match.html"))

    @app.get("/login.html")
    def serve_login():
        return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

    @app.get("/register.html")
    def serve_register():
        return FileResponse(os.path.join(FRONTEND_DIR, "register.html"))

    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIR),
        name="frontend"
    )