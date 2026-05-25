import os
import time
import threading
import logging
from app.utils.safe import safe_float, safe_int, clamp, safe_percentage, normalize_score
from datetime import datetime
from app.routers.system import create_system_router
from app.services.scout_service import (
    normalize_player_for_scout,
    extract_players_for_scout
)

from fastapi import FastAPI, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.utils.cache import (
    cache_valid,
    build_cache_item,
    get_cache_age,
    clear_expired_cache
)

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

logger = logging.getLogger("matchiq")
logging.basicConfig(level=logging.INFO)

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
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "https://matchiq-tactical-production.up.railway.app,http://127.0.0.1:8000,http://localhost:8000"
    ).split(","),
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

        logger.info("[BACKGROUND REFRESH] %s", match_id)

        data = build_full_analysis(match_id)

        if "error" not in data:

            FULL_ANALYSIS_CACHE[match_id] = {
                "timestamp": time.time(),
                "data": data
            }

            logger.info("[CACHE UPDATED] %s", match_id)

    except Exception as e:

        logger.exception("BACKGROUND REFRESH ERROR")


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

        logger.exception("THREAD ERROR")



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
    """
    Risposta Scout V6 compatibile con scout.html V5.5.
    - Usa player reali quando disponibili.
    - Se API-Football non fornisce players, genera profili ruolo stimati.
    - Non restituisce mai players vuoto per match valido.
    - Evita cache vuote vecchie.
    """
    cache_key = f"scout_{match_id}"
    cached = SCOUT_PLAYERS_CACHE.get(cache_key)

    if cache_valid(cached, SCOUT_PLAYERS_CACHE_SECONDS):
        data = cached["data"].copy()
        cached_players = data.get("players", [])

        # Non bloccare lo Scout con vecchie cache vuote.
        if isinstance(cached_players, list) and len(cached_players) > 0:
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

            if isinstance(match_data, dict) and "error" not in match_data:
                real_players = (
                    match_data.get("players")
                    or match_data.get("lineups")
                    or match_data.get("player_statistics")
                    or []
                )

                players = extract_players_for_scout(
                    real_players,
                    match_data=match_data
                )

                source_mode = "live_real_players" if players else "live_no_players"
            else:
                error_message = match_data.get("error") if isinstance(match_data, dict) else "match_data non valido"

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

            if isinstance(full, dict) and "error" not in full:
                match_data = full.get("match", match_data) or match_data

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

    if not isinstance(match_data, dict):
        match_data = {}

    home = (
        match_data.get("home")
        or match_data.get("home_team")
        or "Home"
    )

    away = (
        match_data.get("away")
        or match_data.get("away_team")
        or "Away"
    )

    league = match_data.get("league") or "Live"
    minute = safe_int(match_data.get("minute", match_data.get("elapsed", 0)), 0)
    status = match_data.get("status") or "LIVE"

    score_raw = match_data.get("score", {})

    if isinstance(score_raw, str):
        parts = score_raw.replace(" ", "").split("-")
        score = {
            "home": safe_int(parts[0], 0) if len(parts) > 0 else 0,
            "away": safe_int(parts[1], 0) if len(parts) > 1 else 0
        }
    elif isinstance(score_raw, dict):
        score = score_raw
    else:
        score = {
            "home": safe_int(match_data.get("home_goals", 0), 0),
            "away": safe_int(match_data.get("away_goals", 0), 0)
        }

    home_goals = safe_int(score.get("home", match_data.get("home_goals", 0)), 0)
    away_goals = safe_int(score.get("away", match_data.get("away_goals", 0)), 0)

    def make_virtual_player(team, role_code, role_label, index, side):
        is_home = side == "home"
        team_goals = home_goals if is_home else away_goals
        opp_goals = away_goals if is_home else home_goals

        role_bonus = {
            "ATT": 16,
            "MID": 12,
            "DEF": 8,
            "GK": 5
        }.get(role_code, 8)

        match_bonus = clamp((team_goals - opp_goals) * 8, -12, 18)
        minute_bonus = clamp(minute * 0.35, 0, 35)

        scout_score = clamp(58 + role_bonus + match_bonus + minute_bonus - (index * 2), 45, 94)
        threat = clamp((team_goals * 18) + (role_bonus * 2) + (minute * 0.25) - (index * 3), 5, 88)
        creativity = clamp(role_bonus * 3 + minute * 0.18 + team_goals * 10 - index, 8, 86)
        pressure = clamp(30 + minute * 0.22 + abs(team_goals - opp_goals) * 8 + (6 - index), 10, 90)
        momentum = clamp(scout_score * 0.65 + threat * 0.2 + creativity * 0.15, 0, 99)
        fatigue = clamp(minute * 0.55 + index * 3, 10, 88)
        stamina = clamp(100 - fatigue, 0, 100)
        impact_score = clamp(momentum * 0.55 + threat * 0.25 + creativity * 0.20, 1, 99)

        if impact_score >= 82:
            signal_type = "hot"
            signal = "Hot Player"
            level = "ELITE"
        elif threat >= 65:
            signal_type = "danger"
            signal = "Danger Creator"
            level = "TOP PLAYER"
        elif creativity >= 62:
            signal_type = "gem"
            signal = "Hidden Gem"
            level = "GOOD TALENT"
        else:
            signal_type = "watch"
            signal = "AI Watch"
            level = "STANDARD"

        return {
            "id": f"virtual_{side}_{index}_{role_code.lower()}",
            "name": f"{team} {role_label}",
            "photo": None,
            "team": team,
            "team_logo": match_data.get("home_logo") if is_home else match_data.get("away_logo"),
            "role": role_code,
            "position": role_code,

            "rating": round(6.3 + scout_score / 40, 1),
            "goals": 0,
            "assists": 0,
            "shots": 0,
            "shots_on_target": 0,
            "key_passes": 0,
            "dribbles": 0,
            "tackles": 0,
            "interceptions": 0,
            "duels_won": 0,
            "minutes": minute,
            "pass_accuracy": 0,
            "xg": 0.0,

            "momentum": int(momentum),
            "fatigue": int(fatigue),
            "stamina": int(stamina),
            "scout_score": int(scout_score),
            "scoutScore": int(scout_score),
            "impact_score": int(impact_score),
            "impact": int(impact_score),
            "threat": int(threat),
            "danger": int(threat),
            "creativity": int(creativity),
            "creative_score": int(creativity),
            "pressure": int(pressure),
            "pressure_score": int(pressure),
            "keyPasses": 0,

            "hidden_gem": signal_type == "gem",
            "danger_creator": signal_type == "danger",
            "level": level,
            "signal_type": signal_type,
            "signalType": signal_type,
            "signal": signal,
            "ai_signal": signal,

            "real_data": False,
            "is_estimated": True,
            "data_quality": "fallback_role_profile",
            "data_source": "matchiq_virtual_scout",
            "source": "matchiq_virtual_scout",
            "ai_summary": f"Profilo ruolo stimato per {team}: {role_label}. Utile quando API-Football non fornisce player reali per campionati minori.",
            "generated_at": datetime.utcnow().isoformat()
        }

    if not players:
        role_plan = [
            ("ATT", "Attaccante"),
            ("MID", "Regista"),
            ("MID", "Mezzala"),
            ("DEF", "Difensore"),
            ("GK", "Portiere"),
        ]

        generated_players = []

        for i, (role_code, role_label) in enumerate(role_plan):
            generated_players.append(
                make_virtual_player(home, role_code, role_label, i, "home")
            )

        for i, (role_code, role_label) in enumerate(role_plan):
            generated_players.append(
                make_virtual_player(away, role_code, role_label, i, "away")
            )

        players = sorted(
            generated_players,
            key=lambda x: x.get("scout_score", 0),
            reverse=True
        )

        source_mode = "fallback_virtual_roles"

    players = sorted(
        players,
        key=lambda x: x.get("scout_score", 0),
        reverse=True
    )[:16]

    try:
        scout = build_live_scout(
            players=players,
            match_data=match_data
        )
    except Exception as e:
        scout = {
            "available": False,
            "source": "scout_engine_exception",
            "error": str(e),
            "players": players
        }

    if not isinstance(scout, dict):
        scout = {
            "available": False,
            "source": "scout_engine_invalid",
            "players": players
        }

    scout["available"] = True
    scout["source"] = "scout_engine" if SCOUT_ENGINE_AVAILABLE else "fallback"
    scout["match_id"] = match_id
    scout["mode"] = "live" if match_id else "demo"
    scout["data_mode"] = source_mode
    scout["real_players"] = source_mode in ["live_real_players", "live_full_analysis"]
    scout["fallback_players"] = source_mode == "fallback_virtual_roles"
    scout["premium_feature"] = True
    scout["required_plan"] = "scout"
    scout["cache"] = False
    scout["cache_seconds"] = SCOUT_PLAYERS_CACHE_SECONDS
    scout["api_safe"] = True
    scout["players"] = players
    scout["total_players"] = len(players)
    scout["events"] = scout.get("events", [])
    scout["error"] = error_message
    scout["version"] = "6.0-scout-fallback"

    scout["match"] = {
        "id": match_id,
        "match_id": match_id,
        "fixture_id": match_id,
        "home": home,
        "away": away,
        "home_logo": match_data.get("home_logo"),
        "away_logo": match_data.get("away_logo"),
        "score": {
            "home": home_goals,
            "away": away_goals
        },
        "home_goals": home_goals,
        "away_goals": away_goals,
        "minute": minute,
        "elapsed": minute,
        "status": status,
        "league": league,
    }

    scout["summary"] = {
        "mode": source_mode,
        "message": (
            "Giocatori reali disponibili"
            if scout["real_players"]
            else "Profili ruolo generati da MatchIQ per match senza dati player reali"
        ),
        "total_players": len(players),
        "top_player": players[0].get("name") if players else None,
        "avg_scout_score": round(sum(p.get("scout_score", 0) for p in players) / len(players), 1) if players else 0,
        "avg_threat": round(sum(p.get("threat", 0) for p in players) / len(players), 1) if players else 0,
        "avg_creativity": round(sum(p.get("creativity", 0) for p in players) / len(players), 1) if players else 0,
        "avg_pressure": round(sum(p.get("pressure", 0) for p in players) / len(players), 1) if players else 0,
        "avg_momentum": round(sum(p.get("momentum", 0) for p in players) / len(players), 1) if players else 0,
        "avg_stamina": round(sum(p.get("stamina", 0) for p in players) / len(players), 1) if players else 0,
    }

    if match_id and players:
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




@app.get("/api/live")
def api_live(top_only: bool = Query(False)):
    return get_live_matches(top_only=top_only)


@app.get("/api/live-matches")
def live_matches(top_only: bool = Query(False)):
    """
    Endpoint production-ready per la dashboard live.

    Migliorie:
    - default ALL LIVE, così la home mostra partite anche se non sono top leagues
    - normalizza risposta per frontend: matches / data / live_matches
    - gestisce score sia dict sia stringa tipo "1-0"
    - gestisce league sia stringa sia dict
    - gestisce nested fixture/teams/goals API-Football
    - evita crash con .get() su stringhe
    - usa cache se la live API fallisce
    """
    cache_key = f"top_only_{top_only}"
    cached = LIVE_MATCHES_CACHE.get(cache_key)

    if cache_valid(cached, LIVE_MATCHES_CACHE_SECONDS):
        data = cached["data"]
        data["cache"] = True
        data["api_safe"] = True
        return data

    try:
        data = get_live_matches(top_only=top_only)

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

        matches = []

        for m in raw_matches:
            if not isinstance(m, dict):
                continue

            fixture_obj = m.get("fixture") if isinstance(m.get("fixture"), dict) else {}
            teams_obj = m.get("teams") if isinstance(m.get("teams"), dict) else {}
            goals_obj = m.get("goals") if isinstance(m.get("goals"), dict) else {}
            league_obj = m.get("league") if isinstance(m.get("league"), dict) else {}

            home_obj = teams_obj.get("home") if isinstance(teams_obj.get("home"), dict) else {}
            away_obj = teams_obj.get("away") if isinstance(teams_obj.get("away"), dict) else {}

            status_obj = fixture_obj.get("status") if isinstance(fixture_obj.get("status"), dict) else {}

            match_id = (
                m.get("match_id")
                or m.get("fixture_id")
                or m.get("id")
                or fixture_obj.get("id")
            )

            home = (
                m.get("home")
                or m.get("home_team")
                or home_obj.get("name")
                or "Home"
            )

            away = (
                m.get("away")
                or m.get("away_team")
                or away_obj.get("name")
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
                if m.get("home_goals") is not None
                else goals_obj.get("home")
                if goals_obj.get("home") is not None
                else score.get("home")
                if score.get("home") is not None
                else 0
            )

            away_goals = (
                m.get("away_goals")
                if m.get("away_goals") is not None
                else goals_obj.get("away")
                if goals_obj.get("away") is not None
                else score.get("away")
                if score.get("away") is not None
                else 0
            )

            minute = (
                m.get("minute")
                if m.get("minute") is not None
                else m.get("elapsed")
                if m.get("elapsed") is not None
                else status_obj.get("elapsed")
                if status_obj.get("elapsed") is not None
                else 0
            )

            status = (
                m.get("status")
                or m.get("fixture_status")
                or status_obj.get("short")
                or "LIVE"
            )

            status_long = (
                m.get("status_long")
                or status_obj.get("long")
                or status
            )

            league_name = (
                league_obj.get("name")
                if league_obj
                else m.get("league")
                or m.get("league_name")
                or "Live"
            )

            country = (
                m.get("country")
                or league_obj.get("country")
                or ""
            )

            home_logo = (
                m.get("home_logo")
                or home_obj.get("logo")
                or ""
            )

            away_logo = (
                m.get("away_logo")
                or away_obj.get("logo")
                or ""
            )

            if not match_id:
                continue

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

                "score": f"{safe_int(home_goals)}-{safe_int(away_goals)}",
                "score_obj": {
                    "home": safe_int(home_goals),
                    "away": safe_int(away_goals)
                },

                "home_goals": safe_int(home_goals),
                "away_goals": safe_int(away_goals),

                "minute": safe_int(minute),
                "elapsed": safe_int(minute),
                "status": str(status),
                "status_long": str(status_long),
                "league": league_name,
                "country": country,

                "memory_mode": bool(m.get("memory_mode", False)),
                "live_label": m.get("live_label", "LIVE"),
                "last_seen_live": m.get("last_seen_live"),

                "url_match": f"/match.html?id={match_id}",
                "url_scout": f"/scout.html?match_id={match_id}"
            }

            matches.append(item)

        response = {
            "source": "api-football",
            "top_only": top_only,
            "total_matches": len(matches),
            "matches": matches,
            "data": matches,
            "live_matches": matches,
            "cache": False,
            "api_safe": True,
            "generated_at": datetime.utcnow().isoformat()
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
            "api_safe": True,
            "generated_at": datetime.utcnow().isoformat()
        }


SCOUT_PUBLIC_BETA = os.getenv("SCOUT_PUBLIC_BETA", "1") == "1"
PDF_PUBLIC_BETA = os.getenv("PDF_PUBLIC_BETA", "1") == "1"


def is_owner_or_paid_user(user):
    """
    Controllo piano robusto per funzioni PRO/PDF.
    Supporta sia schema frontend (plan) sia backend italiano (piano),
    oltre a role/owner e all'email owner.
    """
    if not isinstance(user, dict):
        return False

    email = str(user.get("email") or "").lower().strip()

    plan = str(
        user.get("plan")
        or user.get("piano")
        or user.get("subscription")
        or user.get("role")
        or "guest"
    ).lower().strip()

    role = str(user.get("role") or "").lower().strip()

    return (
        email == "mario.costabile92@outlook.it"
        or plan in ["pro", "scout", "owner"]
        or role in ["owner", "admin", "pro", "scout"]
        or bool(user.get("is_owner"))
        or bool(user.get("is_pro"))
    )


@app.get("/api/scout/live")
def api_scout_live(
    match_id: int = Query(None),
    user=Depends(get_optional_user)
):
    """
    Scout Live.

    In beta resta pubblico se SCOUT_PUBLIC_BETA=1.
    In produzione imposta SCOUT_PUBLIC_BETA=0 per richiedere piano Scout.
    """
    if not SCOUT_PUBLIC_BETA:
        enforce_premium_feature(user, "scout")
        enforce_guest_or_user_limit(
            user=user,
            feature="scout",
            endpoint="/api/scout/live"
        )

    return build_real_scout_response(match_id=match_id)


@app.get("/api/scout-live")
def api_scout_live_alias(
    match_id: int = Query(None),
    user=Depends(get_optional_user)
):
    """
    Alias compatibile con scout.html.
    Ritorna sempre match + players, inclusi fallback virtual roles
    se API-Football non fornisce giocatori reali.
    """
    if not SCOUT_PUBLIC_BETA:
        enforce_premium_feature(user, "scout")
        enforce_guest_or_user_limit(
            user=user,
            feature="scout",
            endpoint="/api/scout-live"
        )

    return build_real_scout_response(match_id=match_id)


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




@app.get("/api/match/{match_id}/full-analysis")
def full_analysis(match_id: int):
    return get_cached_full_analysis(match_id)



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
    """
    Download PDF report.

    In beta può essere pubblico se PDF_PUBLIC_BETA=1.
    In produzione metti PDF_PUBLIC_BETA=0 su Railway per richiedere piano PRO/SCOUT.
    Include anche controllo robusto owner/pro per evitare falsi "guest".
    """
    if not PDF_PUBLIC_BETA:
        if not is_owner_or_paid_user(user):
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
        pdf_path = pdf.get("pdf_path") if isinstance(pdf, dict) else None

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
        logger.exception("PDF DOWNLOAD ERROR")
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

logger.info("FRONTEND_DIR: %s", FRONTEND_DIR)
logger.info("FRONTEND EXISTS: %s", os.path.exists(FRONTEND_DIR))

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
def get_services_status():
    return {
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
        "live_match_brain": "online",
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
        "static_files": "online",
    }


system_router = create_system_router(
    live_matches_cache=LIVE_MATCHES_CACHE,
    full_analysis_cache=FULL_ANALYSIS_CACHE,
    scout_players_cache=SCOUT_PLAYERS_CACHE,
    live_matches_cache_seconds=LIVE_MATCHES_CACHE_SECONDS,
    full_analysis_cache_seconds=FULL_ANALYSIS_CACHE_SECONDS,
    scout_players_cache_seconds=SCOUT_PLAYERS_CACHE_SECONDS,
    services_provider=get_services_status,
)

app.include_router(system_router)

app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR),
    name="frontend"
)