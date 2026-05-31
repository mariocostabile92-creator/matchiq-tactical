import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
from app.routers.live import create_live_router
from app.routers.admin_beta import router as admin_beta_router
from app.routers.match import create_match_router
from app.utils.safe import safe_float, safe_int, clamp, safe_percentage, normalize_score
from datetime import datetime, timezone
from app.routers.system import create_system_router
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.services.scout_service import (
    normalize_player_for_scout,
    extract_players_for_scout,
    build_real_scout_response
)

from fastapi import FastAPI, Query, Depends, Body, HTTPException
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
from database import init_db, get_admin_analytics
from auth import create_verification_for_user
from brevo_service import send_verification_email, is_email_configured
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
            "generated_at": datetime.now(timezone.utc).isoformat(),
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


# =========================================================
# BETA REQUESTS ROUTER
# =========================================================

app.include_router(admin_beta_router)


LIVE_MATCHES_CACHE = {}
FULL_ANALYSIS_CACHE = {}
SCOUT_PLAYERS_CACHE = {}

LIVE_MATCHES_CACHE_SECONDS = 60
FULL_ANALYSIS_CACHE_SECONDS = 30
SCOUT_PLAYERS_CACHE_SECONDS = 1800

BACKGROUND_REFRESH_ENABLED = True
BACKGROUND_REFRESH_MAX_WORKERS = int(os.getenv("BACKGROUND_REFRESH_MAX_WORKERS", "10"))
BACKGROUND_REFRESH_EXECUTOR = ThreadPoolExecutor(max_workers=BACKGROUND_REFRESH_MAX_WORKERS)
BACKGROUND_REFRESH_IN_PROGRESS = set()
BACKGROUND_REFRESH_LOCK = threading.Lock()

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

            logger.info("[CACHE UPDATED] %s", match_id)

    except Exception:
        logger.exception("BACKGROUND REFRESH ERROR")

    finally:
        with BACKGROUND_REFRESH_LOCK:
            BACKGROUND_REFRESH_IN_PROGRESS.discard(match_id)


def launch_background_refresh(match_id):
    if not BACKGROUND_REFRESH_ENABLED:
        return False

    with BACKGROUND_REFRESH_LOCK:
        if match_id in BACKGROUND_REFRESH_IN_PROGRESS:
            logger.info("[BACKGROUND REFRESH SKIP] già in corso: %s", match_id)
            return False

        BACKGROUND_REFRESH_IN_PROGRESS.add(match_id)

    try:
        BACKGROUND_REFRESH_EXECUTOR.submit(background_refresh_match, match_id)
        return True

    except Exception:
        with BACKGROUND_REFRESH_LOCK:
            BACKGROUND_REFRESH_IN_PROGRESS.discard(match_id)
        logger.exception("THREAD POOL SUBMIT ERROR")
        return False

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
        cached["data"]["cache"] = True
        cached["data"]["cache_seconds"] = dynamic_seconds
        cached["data"]["cache_age"] = get_cache_age(cached)
        cached["data"]["stale"] = False
        return cached["data"]

    if cached:
        try:
            launched = launch_background_refresh(match_id)
            cached["data"]["cache"] = True
            cached["data"]["cache_seconds"] = dynamic_seconds
            cached["data"]["cache_age"] = get_cache_age(cached)
            cached["data"]["stale"] = True
            cached["data"]["background_refresh"] = bool(launched)
            return cached["data"]
        except Exception as e:
            cached["data"]["cache_warning"] = str(e)
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
            data["stale"] = False

        return data

    except Exception as e:
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
        "api_safe": True,
        "beta_crm": "v7.8",
        "beta_access_code": True
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
        "beta_crm": "V7.8 Beta Access Code",
        "beta_access_code": True,
        "background_refresh": BACKGROUND_REFRESH_ENABLED,
        "background_refresh_max_workers": BACKGROUND_REFRESH_MAX_WORKERS,
        "background_refresh_in_progress": len(BACKGROUND_REFRESH_IN_PROGRESS),
        "cache_system": {
            "live_matches_seconds": LIVE_MATCHES_CACHE_SECONDS,
            "full_analysis_dynamic": True,
            "finished_match_cache": FINISHED_MATCH_CACHE,
            "halftime_cache": HALFTIME_CACHE,
            "priority_leagues": MATCH_PRIORITY
        },
        "memory": {
            "live_matches_cached": len(LIVE_MATCHES_CACHE),
            "full_analysis_cached": len(FULL_ANALYSIS_CACHE),
            "scout_cached": len(SCOUT_PLAYERS_CACHE)
        }
    }


@app.get("/api/account/limits")
def account_limits(user=Depends(get_optional_user)):
    return build_account_limits_response(user)


# =========================================================
# ADMIN USERS - V8.7 ADMIN UX + EMAIL ACTIONS
# =========================================================

ADMIN_ALLOWED_PLANS = ["free", "pro", "scout", "owner"]


def admin_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ["1", "true", "t", "yes", "y", "attivo", "active"]


def normalize_admin_user_row(row):
    if not row:
        return {}

    item = dict(row)

    for key in ["created_at", "email_verified_at"]:
        value = item.get(key)
        if hasattr(value, "isoformat"):
            item[key] = value.isoformat()

    plan = str(item.get("plan") or item.get("piano") or "free").lower().strip()
    if plan not in ADMIN_ALLOWED_PLANS:
        plan = "free"

    item["plan"] = plan
    item["piano"] = plan
    item["is_active"] = admin_bool(item.get("is_active"), True)
    item["email_verified"] = admin_bool(item.get("email_verified"), False)
    item["subscription_status"] = item.get("subscription_status") or ""
    item["provider"] = item.get("provider") or ""
    item["total_usage_today"] = int(item.get("total_usage_today") or 0)

    return item


def admin_fetch_user(cur, user_id: int):
    cur.execute("""
        SELECT
            id,
            email,
            COALESCE(plan, 'free') AS plan,
            COALESCE(plan, 'free') AS piano,
            COALESCE(is_active, 1) AS is_active,
            COALESCE(email_verified, 0) AS email_verified,
            email_verified_at,
            created_at,
            '' AS subscription_status,
            '' AS provider,
            '' AS provider_customer_id,
            '' AS provider_subscription_id,
            '' AS subscription_plan,
            NULL AS current_period_start,
            NULL AS current_period_end,
            0 AS total_usage_today
        FROM users
        WHERE id = %s;
    """, (user_id,))
    row = cur.fetchone()
    return normalize_admin_user_row(row) if row else None


@app.get("/api/admin/users", tags=["Admin"])
def admin_users(
    search: Optional[str] = Query(None),
    plan: Optional[str] = Query("all"),
    status: Optional[str] = Query("all"),
    limit: int = Query(300, ge=1, le=1000),
    admin_ok: bool = Depends(require_admin_token)
):
    database_url = get_database_url()

    if not database_url:
        return {"ok": False, "users": [], "items": [], "data": [], "count": 0, "message": "DATABASE_URL non configurato"}

    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        where = []
        params = []

        if search:
            q = f"%{search.strip()}%"
            where.append("email ILIKE %s")
            params.append(q)

        if plan and plan not in ["all", "tutti", "Tutti"]:
            plan_value = plan.strip().lower()
            if plan_value in ADMIN_ALLOWED_PLANS:
                where.append("COALESCE(plan, 'free') = %s")
                params.append(plan_value)

        if status and status not in ["all", "tutti", "Tutti"]:
            status_value = status.strip().lower()
            if status_value in ["active", "attivo"]:
                where.append("COALESCE(is_active, 1) <> 0")
            elif status_value in ["inactive", "disabled", "disattivato"]:
                where.append("COALESCE(is_active, 1) = 0")
            elif status_value in ["verified", "verificato"]:
                where.append("COALESCE(email_verified, 0) <> 0")
            elif status_value in ["unverified", "non_verificato", "non verificato"]:
                where.append("COALESCE(email_verified, 0) = 0")
            elif status_value == "sub_active":
                where.append("FALSE")
            elif status_value == "sub_missing":
                where.append("TRUE")

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        params.append(limit)

        cur.execute(f"""
            SELECT
                id,
                email,
                COALESCE(plan, 'free') AS plan,
                COALESCE(plan, 'free') AS piano,
                COALESCE(is_active, 1) AS is_active,
                COALESCE(email_verified, 0) AS email_verified,
                email_verified_at,
                created_at,
                '' AS subscription_status,
                '' AS provider,
                '' AS provider_customer_id,
                '' AS provider_subscription_id,
                '' AS subscription_plan,
                NULL AS current_period_start,
                NULL AS current_period_end,
                0 AS total_usage_today
            FROM users
            {where_sql}
            ORDER BY created_at DESC NULLS LAST, id DESC
            LIMIT %s;
        """, params)

        rows = cur.fetchall()
        users = [normalize_admin_user_row(row) for row in rows]

        cur.execute("SELECT COUNT(*) AS total FROM users;")
        total = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS verified FROM users WHERE COALESCE(email_verified, 0) <> 0;")
        verified = cur.fetchone()["verified"]

        cur.execute("SELECT COUNT(*) AS free FROM users WHERE COALESCE(plan, 'free') = 'free';")
        free = cur.fetchone()["free"]

        cur.execute("SELECT COUNT(*) AS pro FROM users WHERE COALESCE(plan, 'free') = 'pro';")
        pro = cur.fetchone()["pro"]

        cur.execute("SELECT COUNT(*) AS scout_owner FROM users WHERE COALESCE(plan, 'free') IN ('scout', 'owner');")
        scout_owner = cur.fetchone()["scout_owner"]

        cur.close()

        return {
            "ok": True,
            "count": len(users),
            "total": total,
            "verified": verified,
            "unverified": max(int(total) - int(verified), 0),
            "free": free,
            "pro": pro,
            "scout_owner": scout_owner,
            "subscription_active": 0,
            "users": users,
            "items": users,
            "data": users
        }

    except Exception as e:
        logger.exception("[ADMIN USERS] Errore caricamento utenti")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if conn:
            conn.close()


@app.patch("/api/admin/users/{user_id}/plan", tags=["Admin"])
def admin_update_user_plan(
    user_id: int,
    payload: dict = Body(...),
    admin_ok: bool = Depends(require_admin_token)
):
    database_url = get_database_url()

    if not database_url:
        return {"ok": False, "message": "DATABASE_URL non configurato"}

    raw_plan = str(payload.get("plan") or "free").lower().strip()

    if raw_plan not in ADMIN_ALLOWED_PLANS:
        raise HTTPException(status_code=400, detail="Piano non valido")

    deactivate = bool(payload.get("deactivate", False))
    active_value = 0 if deactivate else 1

    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE users
            SET plan = %s,
                is_active = %s
            WHERE id = %s
            RETURNING
                id,
                email,
                COALESCE(plan, 'free') AS plan,
                COALESCE(plan, 'free') AS piano,
                COALESCE(is_active, 1) AS is_active,
                COALESCE(email_verified, 0) AS email_verified,
                email_verified_at,
                created_at;
        """, (raw_plan, active_value, user_id))

        row = cur.fetchone()

        if not row:
            conn.rollback()
            cur.close()
            raise HTTPException(status_code=404, detail="Utente non trovato")

        conn.commit()
        cur.close()

        user = normalize_admin_user_row(row)

        return {"ok": True, "message": "Utente aggiornato correttamente", "user": user, "data": user}

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("[ADMIN USERS] Errore aggiornamento piano utente")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if conn:
            conn.close()


@app.post("/api/admin/users/{user_id}/activate", tags=["Admin"])
def admin_activate_user(user_id: int, admin_ok: bool = Depends(require_admin_token)):
    database_url = get_database_url()
    if not database_url:
        return {"ok": False, "message": "DATABASE_URL non configurato"}
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("UPDATE users SET is_active = 1 WHERE id = %s RETURNING id;", (user_id,))
        if not cur.fetchone():
            conn.rollback(); cur.close(); raise HTTPException(status_code=404, detail="Utente non trovato")
        user = admin_fetch_user(cur, user_id)
        conn.commit(); cur.close()
        return {"ok": True, "message": "Utente riattivato", "user": user, "data": user}
    except HTTPException:
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.exception("[ADMIN USERS] Errore riattivazione utente")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn: conn.close()


@app.post("/api/admin/users/{user_id}/deactivate", tags=["Admin"])
def admin_deactivate_user(user_id: int, admin_ok: bool = Depends(require_admin_token)):
    database_url = get_database_url()
    if not database_url:
        return {"ok": False, "message": "DATABASE_URL non configurato"}
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("UPDATE users SET is_active = 0 WHERE id = %s RETURNING id;", (user_id,))
        if not cur.fetchone():
            conn.rollback(); cur.close(); raise HTTPException(status_code=404, detail="Utente non trovato")
        user = admin_fetch_user(cur, user_id)
        conn.commit(); cur.close()
        return {"ok": True, "message": "Utente disattivato", "user": user, "data": user}
    except HTTPException:
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.exception("[ADMIN USERS] Errore disattivazione utente")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn: conn.close()


@app.post("/api/admin/users/{user_id}/resend-verification", tags=["Admin"])
def admin_resend_user_verification(user_id: int, admin_ok: bool = Depends(require_admin_token)):
    database_url = get_database_url()
    if not database_url:
        return {"ok": False, "message": "DATABASE_URL non configurato"}

    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        user = admin_fetch_user(cur, user_id)
        cur.close()

        if not user:
            raise HTTPException(status_code=404, detail="Utente non trovato")

        if not user.get("is_active"):
            raise HTTPException(status_code=400, detail="Utente disattivato: riattivalo prima di reinviare la verifica")

        if user.get("email_verified"):
            return {"ok": True, "message": "Email già verificata", "email_sent": False, "user": user, "data": user}

        verification_link = create_verification_for_user(user)
        email_result = send_verification_email(user["email"], verification_link)
        email_sent = bool(email_result.get("success") if isinstance(email_result, dict) else email_result)

        return {
            "ok": True,
            "message": "Verifica email reinviata" if email_sent else "Token creato, ma invio email non riuscito",
            "email_sent": email_sent,
            "email_configured": bool(is_email_configured()),
            "user": user,
            "data": user,
            "verification_link": verification_link if os.getenv("EMAIL_VERIFICATION_EXPOSE_LINK", "1") == "1" else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[ADMIN USERS] Errore reinvio verifica email")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn: conn.close()

# =========================================================
# ADMIN ANALYTICS - V8.3
# =========================================================

@app.get("/api/admin/analytics")
def admin_analytics(admin_ok: bool = Depends(require_admin_token)):
    try:
        data = get_admin_analytics()
        return {
            "ok": True,
            **data
        }
    except Exception as e:
        logger.exception("[ADMIN ANALYTICS] Errore caricamento analytics")
        raise HTTPException(status_code=500, detail=str(e))


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

    @app.get("/index.html")
    def serve_index_html():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/admin-beta.html")
    def serve_admin_beta():
        return FileResponse(os.path.join(FRONTEND_DIR, "admin-beta.html"))

    @app.get("/admin")
    def serve_admin_alias():
        return FileResponse(os.path.join(FRONTEND_DIR, "admin-beta.html"))

    @app.get("/admin-analytics.html")
    def serve_admin_analytics():
        return FileResponse(os.path.join(FRONTEND_DIR, "admin-analytics.html"))

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

    @app.get("/admin-users.html")
    def serve_admin_users():
        return FileResponse(os.path.join(FRONTEND_DIR, "admin-users.html"))

    @app.get("/verify-email.html")
    def serve_verify_email():
        return FileResponse(os.path.join(FRONTEND_DIR, "verify-email.html"))

    @app.get("/reset-password.html")
    def serve_reset_password():
        return FileResponse(os.path.join(FRONTEND_DIR, "reset-password.html"))


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
        "beta_crm": "online",
        "beta_access_code": "online",
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