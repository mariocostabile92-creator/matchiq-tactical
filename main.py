import os
import time
import threading
import logging
from app.routers.live import create_live_router
from app.routers.match import create_match_router
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
    build_safe_ai_commentary,
    build_safe_live_brain,
    build_full_analysis
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
        data = build_full_analysis(
    match_id,
    get_match_live_data_func=get_match_live_data,
    analyze_match_tactical_func=analyze_match_tactical,
    generate_live_engine_func=generate_live_engine,
    analyze_pressure_func=analyze_pressure,
    generate_xg_analysis_func=generate_xg_analysis,
    generate_live_flow_func=generate_live_flow,
    generate_tactical_coach_func=generate_tactical_coach,
    generate_future_prediction_func=generate_future_prediction,
    analyze_ai_core_func=analyze_ai_core,
    generate_player_ratings_func=generate_player_ratings,
    generate_win_probability_func=generate_win_probability,
    generate_tactical_events_func=generate_tactical_events,
    generate_live_alerts_func=generate_live_alerts,
    build_live_events_func=build_live_events,
    generate_ai_report_func=generate_ai_report,
    generate_timeline_func=generate_timeline,
    build_live_match_brain_func=build_live_match_brain,
    live_match_brain_available=LIVE_MATCH_BRAIN_AVAILABLE
)

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








    data = get_cached_full_analysis(match_id)

    return attach_usage_info(
        response=data,
        user=user,
        feature="full_analysis"
    )






















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
match_router = create_match_router(
    get_cached_full_analysis_func=get_cached_full_analysis,
    generate_match_pdf_func=generate_match_pdf,
    get_optional_user_func=get_optional_user,
    is_owner_or_paid_user_func=is_owner_or_paid_user,
    enforce_premium_feature_func=enforce_premium_feature,
    enforce_guest_or_user_limit_func=enforce_guest_or_user_limit,
    logger=logger,
    pdf_public_beta=PDF_PUBLIC_BETA,
)

app.include_router(match_router)
live_router = create_live_router(
    get_live_matches_func=get_live_matches,
    live_matches_cache=LIVE_MATCHES_CACHE,
    live_matches_cache_seconds=LIVE_MATCHES_CACHE_SECONDS,

    build_real_scout_response_func=build_real_scout_response,
    scout_players_cache=SCOUT_PLAYERS_CACHE,
    scout_players_cache_seconds=SCOUT_PLAYERS_CACHE_SECONDS,
    get_match_live_data_func=get_match_live_data,
    get_cached_full_analysis_func=get_cached_full_analysis,
    build_live_scout_func=build_live_scout,
    scout_engine_available=SCOUT_ENGINE_AVAILABLE,

    get_optional_user_func=get_optional_user,
    enforce_premium_feature_func=enforce_premium_feature,
    enforce_guest_or_user_limit_func=enforce_guest_or_user_limit,
    scout_public_beta=SCOUT_PUBLIC_BETA,
)

app.include_router(live_router)

app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR),
    name="frontend"
)