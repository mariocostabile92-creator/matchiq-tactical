import os
import time
import threading
import secrets
from concurrent.futures import ThreadPoolExecutor
import logging
import csv
import io
import random
import string
from app.routers.live import create_live_router
from app.routers.match import create_match_router
from app.utils.safe import safe_float, safe_int, clamp, safe_percentage, normalize_score
from datetime import datetime, timezone
from app.routers.system import create_system_router
from pydantic import BaseModel, EmailStr
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.services.scout_service import (
    normalize_player_for_scout,
    extract_players_for_scout,
    build_real_scout_response
)

from fastapi import FastAPI, Query, Depends, Body, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
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
# BETA REQUESTS - V7.8 BETA ACCESS CODE SAFE
# =========================================================

VALID_LEAD_STATUSES = [
    "Nuovo",
    "Contattato",
    "Interessato",
    "Convertito",
    "Scartato"
]


class BetaRequestPayload(BaseModel):
    name: str
    email: EmailStr
    profile: str
    plan: Optional[str] = "Beta gratuita"
    reason: Optional[str] = ""


class BetaLeadUpdatePayload(BaseModel):
    status: Optional[str] = None
    internal_note: Optional[str] = None
    beta_code: Optional[str] = None


def get_database_url():
    return os.getenv("DATABASE_URL")


def generate_beta_code():
    """
    Genera codice beta leggibile.
    Esempio: MATCHIQ-BETA-7F3K9
    """
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choice(chars) for _ in range(5))
    return f"MATCHIQ-BETA-{suffix}"


def normalize_beta_row(row):
    """
    Mantiene compatibilità con admin-beta.html:
    - requests[]
    - plan
    - reason

    Aggiunge:
    - status
    - internal_note
    - updated_at
    - beta_code
    """
    if not row:
        return {}

    item = dict(row)

    created_at = item.get("created_at")
    updated_at = item.get("updated_at")

    if hasattr(created_at, "isoformat"):
        item["created_at"] = created_at.isoformat()

    if hasattr(updated_at, "isoformat"):
        item["updated_at"] = updated_at.isoformat()

    item["status"] = item.get("status") or "Nuovo"
    item["internal_note"] = item.get("internal_note") or ""
    item["beta_code"] = item.get("beta_code") or ""

    return item


def validate_lead_status(status: str):
    return status in VALID_LEAD_STATUSES


def require_admin_token(x_admin_token: Optional[str] = Header(None)):
    """Protezione temporanea per endpoint admin beta.
    Configura ADMIN_API_TOKEN su Railway e invia lo stesso valore come header X-Admin-Token.
    """
    expected = os.getenv("ADMIN_API_TOKEN", "").strip()

    if not expected:
        logger.error("[ADMIN SECURITY] ADMIN_API_TOKEN non configurato")
        raise HTTPException(status_code=503, detail="ADMIN_API_TOKEN non configurato")

    supplied = (x_admin_token or "").strip()

    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Admin token non valido")

    return True


def ensure_beta_requests_table():
    database_url = get_database_url()

    if not database_url:
        logger.warning("[BETA REQUEST] DATABASE_URL non configurato")
        return False

    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS beta_requests (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                profile TEXT NOT NULL,
                plan TEXT DEFAULT 'Beta gratuita',
                reason TEXT,
                source TEXT DEFAULT 'matchiq_frontend',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        cur.execute("""
            ALTER TABLE beta_requests
            ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Nuovo';
        """)

        cur.execute("""
            ALTER TABLE beta_requests
            ADD COLUMN IF NOT EXISTS internal_note TEXT DEFAULT '';
        """)

        cur.execute("""
            ALTER TABLE beta_requests
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
        """)

        cur.execute("""
            ALTER TABLE beta_requests
            ADD COLUMN IF NOT EXISTS beta_code TEXT DEFAULT '';
        """)

        cur.execute("""
            UPDATE beta_requests
            SET status = 'Nuovo'
            WHERE status IS NULL OR status = '';
        """)

        cur.execute("""
            UPDATE beta_requests
            SET internal_note = ''
            WHERE internal_note IS NULL;
        """)

        cur.execute("""
            UPDATE beta_requests
            SET updated_at = created_at
            WHERE updated_at IS NULL;
        """)

        cur.execute("""
            UPDATE beta_requests
            SET beta_code = ''
            WHERE beta_code IS NULL;
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_beta_requests_email
            ON beta_requests(email);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_beta_requests_created_at
            ON beta_requests(created_at DESC);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_beta_requests_status
            ON beta_requests(status);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_beta_requests_beta_code
            ON beta_requests(beta_code);
        """)

        conn.commit()
        cur.close()

        logger.info("[BETA REQUEST] Tabella beta_requests pronta V7.8 Beta Access Code")
        return True

    except Exception:
        logger.exception("[BETA REQUEST] Errore creazione/aggiornamento tabella")
        return False

    finally:
        if conn:
            conn.close()


def save_beta_request_to_db(payload: BetaRequestPayload):
    database_url = get_database_url()

    if not database_url:
        return {
            "saved": False,
            "reason": "DATABASE_URL non configurato"
        }

    conn = None

    try:
        ensure_beta_requests_table()

        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO beta_requests
            (name, email, profile, plan, reason, source, status, internal_note, beta_code, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'Nuovo', '', '', NOW(), NOW())
            RETURNING
                id,
                name,
                email,
                profile,
                plan,
                reason,
                source,
                status,
                internal_note,
                beta_code,
                created_at,
                updated_at;
        """, (
            payload.name.strip(),
            payload.email.strip().lower(),
            payload.profile.strip(),
            (payload.plan or "Beta gratuita").strip(),
            (payload.reason or "").strip(),
            "matchiq_v78_beta_access_code"
        ))

        row = cur.fetchone()
        conn.commit()
        cur.close()

        return {
            "saved": True,
            "request": normalize_beta_row(row)
        }

    except Exception as e:
        logger.exception("[BETA REQUEST] Errore salvataggio")
        return {
            "saved": False,
            "reason": str(e)
        }

    finally:
        if conn:
            conn.close()


@app.post("/api/beta-request")
def create_beta_request(payload: BetaRequestPayload):
    if not payload.name.strip():
        return {
            "ok": False,
            "saved": False,
            "message": "Nome obbligatorio"
        }

    if not payload.profile.strip():
        return {
            "ok": False,
            "saved": False,
            "message": "Profilo obbligatorio"
        }

    result = save_beta_request_to_db(payload)

    if result.get("saved"):
        return {
            "ok": True,
            "saved": True,
            "message": "Richiesta beta salvata nel database",
            "data": result.get("request"),
            "request": result.get("request")
        }

    return {
        "ok": False,
        "saved": False,
        "message": "Database non disponibile, usa fallback frontend",
        "reason": result.get("reason")
    }


@app.get("/api/beta-requests")
def list_beta_requests(
    status: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    admin_ok: bool = Depends(require_admin_token)
):

    database_url = get_database_url()

    if not database_url:
        return {
            "ok": False,
            "requests": [],
            "message": "DATABASE_URL non configurato"
        }

    conn = None

    try:
        ensure_beta_requests_table()

        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        where = []
        params = []

        if status and status not in ["all", "Tutti", "tutti"]:
            if not validate_lead_status(status):
                return {
                    "ok": False,
                    "requests": [],
                    "message": f"Status non valido: {status}"
                }
            where.append("status = %s")
            params.append(status)

        if profile and profile not in ["all", "Tutti", "tutti"]:
            where.append("profile = %s")
            params.append(profile)

        if plan and plan not in ["all", "Tutti", "tutti"]:
            where.append("plan = %s")
            params.append(plan)

        if search:
            q = f"%{search.strip()}%"
            where.append("""
                (
                    name ILIKE %s OR
                    email ILIKE %s OR
                    profile ILIKE %s OR
                    plan ILIKE %s OR
                    COALESCE(reason, '') ILIKE %s OR
                    COALESCE(internal_note, '') ILIKE %s OR
                    COALESCE(beta_code, '') ILIKE %s
                )
            """)
            params.extend([q, q, q, q, q, q, q])

        where_sql = ""
        if where:
            where_sql = "WHERE " + " AND ".join(where)

        params.append(limit)

        cur.execute(f"""
            SELECT
                id,
                name,
                email,
                profile,
                plan,
                reason,
                source,
                status,
                internal_note,
                beta_code,
                created_at,
                updated_at
            FROM beta_requests
            {where_sql}
            ORDER BY created_at DESC
            LIMIT %s;
        """, params)

        rows = cur.fetchall()
        cur.close()

        requests = [normalize_beta_row(r) for r in rows]

        return {
            "ok": True,
            "count": len(requests),
            "requests": requests,
            "data": requests,
            "items": requests,
            "leads": requests
        }

    except Exception as e:
        logger.exception("[BETA REQUEST] Errore lettura")
        return {
            "ok": False,
            "requests": [],
            "message": str(e)
        }

    finally:
        if conn:
            conn.close()


@app.patch("/api/beta-requests/{lead_id}")
def update_beta_request(
    lead_id: int,
    payload: BetaLeadUpdatePayload = Body(...),
    admin_ok: bool = Depends(require_admin_token)
):

    database_url = get_database_url()

    if not database_url:
        return {
            "ok": False,
            "message": "DATABASE_URL non configurato"
        }

    conn = None

    try:
        ensure_beta_requests_table()

        fields = []
        params = []

        if payload.status is not None:
            status = payload.status.strip()
            if not validate_lead_status(status):
                return {
                    "ok": False,
                    "message": f"Status non valido: {status}"
                }
            fields.append("status = %s")
            params.append(status)

        if payload.internal_note is not None:
            fields.append("internal_note = %s")
            params.append((payload.internal_note or "").strip())

        if payload.beta_code is not None:
            fields.append("beta_code = %s")
            params.append((payload.beta_code or "").strip().upper())

        if not fields:
            return {
                "ok": False,
                "message": "Nessun campo da aggiornare"
            }

        fields.append("updated_at = NOW()")
        params.append(lead_id)

        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(f"""
            UPDATE beta_requests
            SET {", ".join(fields)}
            WHERE id = %s
            RETURNING
                id,
                name,
                email,
                profile,
                plan,
                reason,
                source,
                status,
                internal_note,
                beta_code,
                created_at,
                updated_at;
        """, params)

        row = cur.fetchone()

        if not row:
            conn.rollback()
            cur.close()
            return {
                "ok": False,
                "message": "Lead non trovato"
            }

        conn.commit()
        cur.close()

        lead = normalize_beta_row(row)

        return {
            "ok": True,
            "message": "Lead aggiornato",
            "lead": lead,
            "request": lead,
            "data": lead
        }

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("[BETA REQUEST] Errore aggiornamento lead")
        return {
            "ok": False,
            "message": str(e)
        }

    finally:
        if conn:
            conn.close()


@app.put("/api/beta-requests/{lead_id}")
def update_beta_request_put(
    lead_id: int,
    payload: BetaLeadUpdatePayload = Body(...),
    admin_ok: bool = Depends(require_admin_token)
):
    return update_beta_request(lead_id, payload, admin_ok)


@app.post("/api/beta-requests/{lead_id}/generate-code")
def generate_beta_code_for_lead(
    lead_id: int,
    admin_ok: bool = Depends(require_admin_token)
):
    """
    Genera e salva codice beta per un lead.
    Se il lead ha già un codice, lo mantiene e lo restituisce.
    """

    database_url = get_database_url()

    if not database_url:
        return {
            "ok": False,
            "message": "DATABASE_URL non configurato"
        }

    conn = None

    try:
        ensure_beta_requests_table()

        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                id,
                name,
                email,
                profile,
                plan,
                reason,
                source,
                status,
                internal_note,
                beta_code,
                created_at,
                updated_at
            FROM beta_requests
            WHERE id = %s;
        """, (lead_id,))

        row = cur.fetchone()

        if not row:
            cur.close()
            return {
                "ok": False,
                "message": "Lead non trovato"
            }

        current_code = (row.get("beta_code") or "").strip()

        if current_code:
            lead = normalize_beta_row(row)
            cur.close()
            return {
                "ok": True,
                "message": "Lead già associato a un codice beta",
                "beta_code": current_code,
                "lead": lead,
                "request": lead,
                "data": lead
            }

        code = generate_beta_code()

        # Evita collisioni in modo semplice
        for _ in range(10):
            cur.execute("""
                SELECT id
                FROM beta_requests
                WHERE beta_code = %s
                LIMIT 1;
            """, (code,))
            exists = cur.fetchone()

            if not exists:
                break

            code = generate_beta_code()

        cur.execute("""
            UPDATE beta_requests
            SET beta_code = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING
                id,
                name,
                email,
                profile,
                plan,
                reason,
                source,
                status,
                internal_note,
                beta_code,
                created_at,
                updated_at;
        """, (code, lead_id))

        updated = cur.fetchone()
        conn.commit()
        cur.close()

        lead = normalize_beta_row(updated)

        return {
            "ok": True,
            "message": "Codice beta generato",
            "beta_code": code,
            "lead": lead,
            "request": lead,
            "data": lead
        }

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("[BETA REQUEST] Errore generazione beta code")
        return {
            "ok": False,
            "message": str(e)
        }

    finally:
        if conn:
            conn.close()


@app.get("/api/beta-requests-stats")
def beta_requests_stats(admin_ok: bool = Depends(require_admin_token)):

    database_url = get_database_url()

    if not database_url:
        return {
            "ok": False,
            "message": "DATABASE_URL non configurato",
            "total": 0,
            "by_status": [],
            "by_profile": [],
            "by_plan": []
        }

    conn = None

    try:
        ensure_beta_requests_table()

        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT COUNT(*) AS total FROM beta_requests;")
        total = cur.fetchone()["total"]

        cur.execute("""
            SELECT COALESCE(status, 'Nuovo') AS status, COUNT(*) AS count
            FROM beta_requests
            GROUP BY COALESCE(status, 'Nuovo')
            ORDER BY count DESC;
        """)
        by_status = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT COALESCE(NULLIF(profile, ''), 'Non specificato') AS profile, COUNT(*) AS count
            FROM beta_requests
            GROUP BY COALESCE(NULLIF(profile, ''), 'Non specificato')
            ORDER BY count DESC;
        """)
        by_profile = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT COALESCE(NULLIF(plan, ''), 'Non specificato') AS plan, COUNT(*) AS count
            FROM beta_requests
            GROUP BY COALESCE(NULLIF(plan, ''), 'Non specificato')
            ORDER BY count DESC;
        """)
        by_plan = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT COUNT(*) AS today
            FROM beta_requests
            WHERE created_at::date = NOW()::date;
        """)
        today = cur.fetchone()["today"]

        cur.execute("""
            SELECT COUNT(*) AS last_7_days
            FROM beta_requests
            WHERE created_at >= NOW() - INTERVAL '7 days';
        """)
        last_7_days = cur.fetchone()["last_7_days"]

        cur.execute("""
            SELECT COUNT(*) AS with_code
            FROM beta_requests
            WHERE beta_code IS NOT NULL AND beta_code <> '';
        """)
        with_code = cur.fetchone()["with_code"]

        cur.close()

        return {
            "ok": True,
            "total": total,
            "today": today,
            "last_7_days": last_7_days,
            "with_code": with_code,
            "statuses": VALID_LEAD_STATUSES,
            "by_status": by_status,
            "by_profile": by_profile,
            "by_plan": by_plan
        }

    except Exception as e:
        logger.exception("[BETA REQUEST] Errore statistiche")
        return {
            "ok": False,
            "message": str(e),
            "total": 0,
            "by_status": [],
            "by_profile": [],
            "by_plan": []
        }

    finally:
        if conn:
            conn.close()


@app.get("/api/beta-stats")
def beta_stats_alias(admin_ok: bool = Depends(require_admin_token)):
    return beta_requests_stats(admin_ok)


@app.get("/api/beta-requests/export.csv")
def export_beta_requests_csv(
    status: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    admin_ok: bool = Depends(require_admin_token)
):

    database_url = get_database_url()

    if not database_url:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["error"])
        writer.writerow(["DATABASE_URL non configurato"])
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=matchiq_beta_requests_error.csv"}
        )

    conn = None

    try:
        ensure_beta_requests_table()

        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        where = []
        params = []

        if status and status not in ["all", "Tutti", "tutti"]:
            if validate_lead_status(status):
                where.append("status = %s")
                params.append(status)

        if profile and profile not in ["all", "Tutti", "tutti"]:
            where.append("profile = %s")
            params.append(profile)

        if plan and plan not in ["all", "Tutti", "tutti"]:
            where.append("plan = %s")
            params.append(plan)

        where_sql = ""
        if where:
            where_sql = "WHERE " + " AND ".join(where)

        cur.execute(f"""
            SELECT
                id,
                name,
                email,
                profile,
                plan,
                reason,
                source,
                status,
                internal_note,
                beta_code,
                created_at,
                updated_at
            FROM beta_requests
            {where_sql}
            ORDER BY created_at DESC;
        """, params)

        rows = cur.fetchall()
        cur.close()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "id",
            "name",
            "email",
            "profile",
            "plan",
            "reason",
            "source",
            "status",
            "internal_note",
            "beta_code",
            "created_at",
            "updated_at"
        ])

        for row in rows:
            r = normalize_beta_row(row)
            writer.writerow([
                r.get("id", ""),
                r.get("name", ""),
                r.get("email", ""),
                r.get("profile", ""),
                r.get("plan", ""),
                r.get("reason", ""),
                r.get("source", ""),
                r.get("status", "Nuovo"),
                r.get("internal_note", ""),
                r.get("beta_code", ""),
                r.get("created_at", ""),
                r.get("updated_at", "")
            ])

        output.seek(0)

        filename = f"matchiq_beta_requests_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.exception("[BETA REQUEST] Errore export CSV")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["error"])
        writer.writerow([str(e)])
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=matchiq_beta_requests_error.csv"}
        )

    finally:
        if conn:
            conn.close()


@app.get("/api/beta-requests/export")
def export_beta_requests_csv_alias(
    status: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    admin_ok: bool = Depends(require_admin_token)
):
    return export_beta_requests_csv(status, profile, plan, admin_ok)


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
# ADMIN USERS - V8.3 HOTFIX SAFE
# =========================================================

class AdminUserPlanPayload(BaseModel):
    plan: str
    deactivate: Optional[bool] = False


@app.get("/api/admin/users")
def admin_list_users(
    plan: Optional[str] = Query("all"),
    search: Optional[str] = Query(""),
    status: Optional[str] = Query("all"),
    limit: int = Query(300, ge=1, le=1000),
    admin_ok: bool = Depends(require_admin_token)
):
    try:
        from database import get_admin_users
        users = get_admin_users(
            plan=plan or "all",
            search=search or "",
            status=status or "all",
            limit=limit
        )
        return {"ok": True, "count": len(users), "users": users, "data": users}
    except ImportError:
        database_url = get_database_url()
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL non configurato")
        conn = None
        try:
            conn = psycopg2.connect(database_url)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            where = []
            params = []
            if plan and plan not in ["all", "tutti", "Tutti"]:
                where.append("LOWER(u.plan) = %s")
                params.append(str(plan).lower())
            if search:
                q = f"%{search.strip()}%"
                where.append("(u.email ILIKE %s OR COALESCE(u.stripe_customer_id,'') ILIKE %s OR COALESCE(s.provider_customer_id,'') ILIKE %s OR COALESCE(s.provider_subscription_id,'') ILIKE %s)")
                params.extend([q, q, q, q])
            if status and status not in ["all", "tutti", "Tutti"]:
                if status == "active":
                    where.append("u.is_active = 1")
                elif status == "disabled":
                    where.append("u.is_active = 0")
                elif status == "sub_active":
                    where.append("COALESCE(s.status,'') = 'active'")
                elif status == "sub_missing":
                    where.append("(s.id IS NULL OR COALESCE(s.status,'') <> 'active')")
            where_sql = "WHERE " + " AND ".join(where) if where else ""
            params.append(limit)
            cur.execute(f"""
                SELECT
                    u.id, u.email, u.plan, u.is_active, u.stripe_customer_id, u.created_at, u.updated_at,
                    s.id AS subscription_id, s.plan AS subscription_plan, s.status AS subscription_status,
                    s.provider, s.provider_customer_id, s.provider_subscription_id,
                    s.current_period_start, s.current_period_end,
                    s.created_at AS subscription_created_at, s.updated_at AS subscription_updated_at,
                    COALESCE(usage_today.total_usage_today, 0) AS total_usage_today
                FROM users u
                LEFT JOIN LATERAL (
                    SELECT * FROM subscriptions s2
                    WHERE s2.user_id = u.id
                    ORDER BY CASE WHEN s2.status = 'active' THEN 0 ELSE 1 END, s2.created_at DESC
                    LIMIT 1
                ) s ON TRUE
                LEFT JOIN (
                    SELECT user_id, COALESCE(SUM(count),0) AS total_usage_today
                    FROM api_usage
                    WHERE usage_date = %s
                    GROUP BY user_id
                ) usage_today ON usage_today.user_id = u.id
                {where_sql}
                ORDER BY u.created_at DESC
                LIMIT %s
            """, [datetime.now(timezone.utc).date().isoformat()] + params)
            rows = [dict(r) for r in cur.fetchall()]
            cur.close()
            def norm(r):
                for k,v in list(r.items()):
                    if hasattr(v, 'isoformat'):
                        r[k]=v.isoformat()
                    elif v is None:
                        r[k]=''
                r['plan'] = str(r.get('plan') or 'free').lower()
                r['is_active'] = int(r.get('is_active') or 0)
                return r
            users=[norm(r) for r in rows]
            return {"ok": True, "count": len(users), "users": users, "data": users}
        except Exception as e:
            logger.exception("[ADMIN USERS] Errore caricamento utenti fallback")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if conn:
                conn.close()
    except Exception as e:
        logger.exception("[ADMIN USERS] Errore caricamento utenti")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/admin/users/{user_id}/plan")
def admin_patch_user_plan(
    user_id: int,
    payload: AdminUserPlanPayload = Body(...),
    admin_ok: bool = Depends(require_admin_token)
):
    try:
        from database import admin_update_user_plan
        updated = admin_update_user_plan(
            user_id=user_id,
            plan=payload.plan,
            deactivate=bool(payload.deactivate)
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        return {"ok": True, "message": "Utente aggiornato", "user": updated, "data": updated}
    except ImportError:
        plan_value = (payload.plan or "free").lower().strip()
        if plan_value not in ["free", "pro", "scout", "owner"]:
            raise HTTPException(status_code=400, detail="Piano non valido")
        database_url = get_database_url()
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL non configurato")
        conn = None
        try:
            now = datetime.now(timezone.utc).isoformat()
            conn = psycopg2.connect(database_url)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                UPDATE users
                SET plan = %s, is_active = %s, updated_at = %s
                WHERE id = %s
                RETURNING id, email, plan, is_active, stripe_customer_id, created_at, updated_at
            """, (plan_value, 0 if payload.deactivate else 1, now, user_id))
            user = cur.fetchone()
            if not user:
                conn.rollback()
                raise HTTPException(status_code=404, detail="Utente non trovato")
            if plan_value in ["pro", "scout", "owner"]:
                cur.execute("""
                    INSERT INTO subscriptions (user_id, plan, status, provider, provider_customer_id, provider_subscription_id, current_period_start, current_period_end, created_at, updated_at)
                    VALUES (%s, %s, 'active', 'manual_admin', '', '', %s, '', %s, %s)
                """, (user_id, plan_value, now, now, now))
            elif plan_value == "free":
                cur.execute("""
                    UPDATE subscriptions
                    SET status = 'cancelled', updated_at = %s
                    WHERE user_id = %s AND status = 'active' AND provider = 'manual_admin'
                """, (now, user_id))
            conn.commit()
            updated = dict(user)
            for k,v in list(updated.items()):
                if hasattr(v, 'isoformat'):
                    updated[k]=v.isoformat()
                elif v is None:
                    updated[k]=''
            return {"ok": True, "message": "Utente aggiornato", "user": updated, "data": updated}
        except HTTPException:
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.exception("[ADMIN USERS] Errore aggiornamento piano fallback")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if conn:
                conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[ADMIN USERS] Errore aggiornamento piano")
        raise HTTPException(status_code=500, detail=str(e))


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


    @app.get("/admin-users.html")
    def serve_admin_users():
        return FileResponse(os.path.join(FRONTEND_DIR, "admin-users.html"))

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

    @app.get("/reset-password.html")
    def serve_reset_password():
        return FileResponse(os.path.join(FRONTEND_DIR, "reset-password.html"))

    @app.get("/register.html")
    def serve_register():
        return FileResponse(os.path.join(FRONTEND_DIR, "register.html"))

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