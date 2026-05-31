import os
import csv
import io
import random
import string
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Query, Depends, Body, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("matchiq")
router = APIRouter()


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


@router.post("/api/beta-request")
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


@router.get("/api/beta-requests")
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


@router.patch("/api/beta-requests/{lead_id}")
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


@router.put("/api/beta-requests/{lead_id}")
def update_beta_request_put(
    lead_id: int,
    payload: BetaLeadUpdatePayload = Body(...),
    admin_ok: bool = Depends(require_admin_token)
):
    return update_beta_request(lead_id, payload, admin_ok)


@router.post("/api/beta-requests/{lead_id}/generate-code")
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


@router.get("/api/beta-requests-stats")
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


@router.get("/api/beta-stats")
def beta_stats_alias(admin_ok: bool = Depends(require_admin_token)):
    return beta_requests_stats(admin_ok)


@router.get("/api/beta-requests/export.csv")
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


@router.get("/api/beta-requests/export")
def export_beta_requests_csv_alias(
    status: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    admin_ok: bool = Depends(require_admin_token)
):
    return export_beta_requests_csv(status, profile, plan, admin_ok)


