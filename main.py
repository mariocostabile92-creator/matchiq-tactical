import os
import time
import threading
import logging
from app.utils.safe import safe_float, safe_int, clamp, safe_percentage, normalize_score
from datetime import datetime
from app.routers.system import create_system_router
from app.services.scout_service import (
    normalize_player_for_scout,
    extract_players_for_scout,
    build_real_scout_response
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
from app.services.full_analysis_service import (
    merge_pressure,
    build_safe_ai_commentary
)

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

    return build_real_scout_response(
    match_id=match_id,
    scout_players_cache=SCOUT_PLAYERS_CACHE,
    scout_players_cache_seconds=SCOUT_PLAYERS_CACHE_SECONDS,
    get_match_live_data_func=get_match_live_data,
    get_cached_full_analysis_func=get_cached_full_analysis,
    build_live_scout_func=build_live_scout,
    scout_engine_available=SCOUT_ENGINE_AVAILABLE
)


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

    return build_real_scout_response(
    match_id=match_id,
    scout_players_cache=SCOUT_PLAYERS_CACHE,
    scout_players_cache_seconds=SCOUT_PLAYERS_CACHE_SECONDS,
    get_match_live_data_func=get_match_live_data,
    get_cached_full_analysis_func=get_cached_full_analysis,
    build_live_scout_func=build_live_scout,
    scout_engine_available=SCOUT_ENGINE_AVAILABLE
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