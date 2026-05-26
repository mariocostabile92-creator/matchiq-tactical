"""
main.py - MatchIQ Tactical Backend
Versione: V7.6 Mini CRM

Funzioni principali:
- Serve frontend statico
- Salva richieste beta
- Admin legge richieste beta
- Mini CRM lead:
  - status lead
  - nota interna
  - filtro per stato/profilo/interesse
  - aggiornamento status/note
  - statistiche rapide CRM
- Compatibilità Railway/PostgreSQL
"""

import os
import csv
import io
import json
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field


# ============================================================
# APP CONFIG
# ============================================================

APP_VERSION = "7.6-mini-crm"
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

DATABASE_URL = os.environ.get("DATABASE_URL")

app = FastAPI(
    title="MatchIQ Tactical API",
    version=APP_VERSION,
    description="Backend MatchIQ Tactical - Dashboard, Scout Mode, Beta CRM"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE POOL
# ============================================================

db_pool: Optional[SimpleConnectionPool] = None


def init_db_pool():
    """
    Inizializza pool PostgreSQL.
    Railway/Neon usano DATABASE_URL.
    """
    global db_pool

    if not DATABASE_URL:
        print("⚠️ DATABASE_URL non configurato. Alcune funzioni DB non saranno disponibili.")
        return

    try:
        db_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=DATABASE_URL,
            sslmode="require"
        )
        print("✅ Database pool inizializzato correttamente.")
    except Exception as e:
        print("❌ Errore inizializzazione database pool:", e)
        db_pool = None


def get_db_connection():
    if db_pool is None:
        raise HTTPException(
            status_code=500,
            detail="Database non configurato o non disponibile."
        )

    try:
        return db_pool.getconn()
    except Exception as e:
        print("❌ Errore get_db_connection:", e)
        raise HTTPException(status_code=500, detail="Errore connessione database.")


def release_db_connection(conn):
    if db_pool and conn:
        try:
            db_pool.putconn(conn)
        except Exception as e:
            print("⚠️ Errore rilascio connessione DB:", e)


# ============================================================
# DATABASE SCHEMA
# ============================================================

VALID_LEAD_STATUSES = [
    "Nuovo",
    "Contattato",
    "Interessato",
    "Convertito",
    "Scartato"
]


def init_db_schema():
    """
    Crea/aggiorna tabella beta_requests.
    V7.6 aggiunge:
    - status
    - internal_note
    - updated_at
    """
    if db_pool is None:
        print("⚠️ Schema DB non inizializzato: pool assente.")
        return

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS beta_requests (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                profile TEXT,
                interest TEXT,
                message TEXT,
                source TEXT DEFAULT 'dashboard',
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
            CREATE INDEX IF NOT EXISTS idx_beta_requests_created_at
            ON beta_requests(created_at DESC);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_beta_requests_status
            ON beta_requests(status);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_beta_requests_email
            ON beta_requests(email);
        """)

        conn.commit()
        cur.close()
        print("✅ Schema beta_requests aggiornato a V7.6 Mini CRM.")

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ Errore init_db_schema:", e)
        traceback.print_exc()

    finally:
        release_db_connection(conn)


@app.on_event("startup")
def startup_event():
    init_db_pool()
    init_db_schema()


@app.on_event("shutdown")
def shutdown_event():
    global db_pool
    if db_pool:
        try:
            db_pool.closeall()
            print("✅ Database pool chiuso.")
        except Exception as e:
            print("⚠️ Errore chiusura pool:", e)


# ============================================================
# MODELS
# ============================================================

class BetaRequestCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    profile: Optional[str] = Field(default="", max_length=120)
    interest: Optional[str] = Field(default="", max_length=120)
    message: Optional[str] = Field(default="", max_length=1000)
    source: Optional[str] = Field(default="dashboard", max_length=80)


class BetaRequestUpdate(BaseModel):
    status: Optional[str] = None
    internal_note: Optional[str] = None


class BetaRequestOut(BaseModel):
    id: int
    name: str
    email: str
    profile: Optional[str]
    interest: Optional[str]
    message: Optional[str]
    source: Optional[str]
    status: str
    internal_note: str
    created_at: Optional[str]
    updated_at: Optional[str]


# ============================================================
# HELPERS
# ============================================================

def row_to_beta_request(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "name": row.get("name") or "",
        "email": row.get("email") or "",
        "profile": row.get("profile") or "",
        "interest": row.get("interest") or "",
        "message": row.get("message") or "",
        "source": row.get("source") or "dashboard",
        "status": row.get("status") or "Nuovo",
        "internal_note": row.get("internal_note") or "",
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip()


def validate_status(status: str):
    if status not in VALID_LEAD_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Status non valido. Valori consentiti: {', '.join(VALID_LEAD_STATUSES)}"
        )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "ok": True,
        "app": "MatchIQ Tactical",
        "version": APP_VERSION,
        "database": bool(db_pool),
        "time": datetime.utcnow().isoformat()
    }


@app.get("/api/version")
def version():
    return {
        "version": APP_VERSION,
        "label": "V7.6 Mini CRM"
    }


# ============================================================
# BETA REQUESTS - CREATE
# ============================================================

@app.post("/api/beta-request")
def create_beta_request(payload: BetaRequestCreate):
    """
    Salva nuova richiesta beta.
    Default status: Nuovo.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        name = normalize_text(payload.name)
        email = normalize_text(payload.email).lower()
        profile = normalize_text(payload.profile)
        interest = normalize_text(payload.interest)
        message = normalize_text(payload.message)
        source = normalize_text(payload.source) or "dashboard"

        cur.execute("""
            INSERT INTO beta_requests
            (name, email, profile, interest, message, source, status, internal_note, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'Nuovo', '', NOW(), NOW())
            RETURNING *;
        """, (
            name,
            email,
            profile,
            interest,
            message,
            source
        ))

        row = cur.fetchone()
        conn.commit()
        cur.close()

        return {
            "ok": True,
            "message": "Richiesta beta salvata correttamente.",
            "lead": row_to_beta_request(row)
        }

    except HTTPException:
        raise

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ Errore create_beta_request:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Errore salvataggio richiesta beta.")

    finally:
        release_db_connection(conn)


# ============================================================
# BETA REQUESTS - LIST / FILTER
# ============================================================

@app.get("/api/beta-requests")
def get_beta_requests(
    status: Optional[str] = Query(default=None),
    profile: Optional[str] = Query(default=None),
    interest: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000)
):
    """
    Lista richieste beta.
    V7.6:
    - filtro status
    - filtro profile
    - filtro interest
    - ricerca libera name/email/message
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        where = []
        params = []

        if status and status != "Tutti":
            validate_status(status)
            where.append("status = %s")
            params.append(status)

        if profile and profile != "Tutti":
            where.append("LOWER(COALESCE(profile, '')) = LOWER(%s)")
            params.append(profile)

        if interest and interest != "Tutti":
            where.append("LOWER(COALESCE(interest, '')) = LOWER(%s)")
            params.append(interest)

        if search:
            q = f"%{search.strip()}%"
            where.append("""
                (
                    name ILIKE %s OR
                    email ILIKE %s OR
                    COALESCE(message, '') ILIKE %s OR
                    COALESCE(internal_note, '') ILIKE %s
                )
            """)
            params.extend([q, q, q, q])

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
                interest,
                message,
                source,
                status,
                internal_note,
                created_at,
                updated_at
            FROM beta_requests
            {where_sql}
            ORDER BY created_at DESC
            LIMIT %s;
        """, params)

        rows = cur.fetchall()
        cur.close()

        leads = [row_to_beta_request(row) for row in rows]

        return {
            "ok": True,
            "count": len(leads),
            "leads": leads,
            "items": leads,
            "version": APP_VERSION
        }

    except HTTPException:
        raise

    except Exception as e:
        print("❌ Errore get_beta_requests:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Errore lettura richieste beta.")

    finally:
        release_db_connection(conn)


# ============================================================
# BETA REQUESTS - SINGLE
# ============================================================

@app.get("/api/beta-requests/{lead_id}")
def get_beta_request_by_id(lead_id: int):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT *
            FROM beta_requests
            WHERE id = %s;
        """, (lead_id,))

        row = cur.fetchone()
        cur.close()

        if not row:
            raise HTTPException(status_code=404, detail="Lead non trovato.")

        return {
            "ok": True,
            "lead": row_to_beta_request(row)
        }

    except HTTPException:
        raise

    except Exception as e:
        print("❌ Errore get_beta_request_by_id:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Errore lettura lead.")

    finally:
        release_db_connection(conn)


# ============================================================
# BETA REQUESTS - UPDATE CRM
# ============================================================

@app.patch("/api/beta-requests/{lead_id}")
def update_beta_request(
    lead_id: int,
    payload: BetaRequestUpdate = Body(...)
):
    """
    Aggiorna status e/o nota interna lead.
    Usato da admin-beta.html V7.6.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        fields = []
        params = []

        if payload.status is not None:
            status = normalize_text(payload.status)
            validate_status(status)
            fields.append("status = %s")
            params.append(status)

        if payload.internal_note is not None:
            note = normalize_text(payload.internal_note)
            fields.append("internal_note = %s")
            params.append(note)

        if not fields:
            raise HTTPException(
                status_code=400,
                detail="Nessun campo da aggiornare."
            )

        fields.append("updated_at = NOW()")

        params.append(lead_id)

        cur.execute(f"""
            UPDATE beta_requests
            SET {", ".join(fields)}
            WHERE id = %s
            RETURNING *;
        """, params)

        row = cur.fetchone()

        if not row:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Lead non trovato.")

        conn.commit()
        cur.close()

        return {
            "ok": True,
            "message": "Lead aggiornato correttamente.",
            "lead": row_to_beta_request(row)
        }

    except HTTPException:
        raise

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ Errore update_beta_request:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Errore aggiornamento lead.")

    finally:
        release_db_connection(conn)


@app.put("/api/beta-requests/{lead_id}")
def update_beta_request_put(
    lead_id: int,
    payload: BetaRequestUpdate = Body(...)
):
    """
    Alias PUT per compatibilità frontend.
    """
    return update_beta_request(lead_id, payload)


# ============================================================
# BETA REQUESTS - DELETE OPTIONAL
# ============================================================

@app.delete("/api/beta-requests/{lead_id}")
def delete_beta_request(lead_id: int):
    """
    Elimina lead.
    Utile ma da usare con attenzione.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            DELETE FROM beta_requests
            WHERE id = %s
            RETURNING id, email, name;
        """, (lead_id,))

        row = cur.fetchone()

        if not row:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Lead non trovato.")

        conn.commit()
        cur.close()

        return {
            "ok": True,
            "message": "Lead eliminato.",
            "deleted": dict(row)
        }

    except HTTPException:
        raise

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ Errore delete_beta_request:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Errore eliminazione lead.")

    finally:
        release_db_connection(conn)


# ============================================================
# CRM STATS
# ============================================================

@app.get("/api/beta-requests-stats")
def get_beta_requests_stats():
    """
    Statistiche CRM per admin:
    - totale lead
    - lead per status
    - lead per profile
    - lead per interest
    - ultimi 7 giorni
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT COUNT(*) AS total FROM beta_requests;")
        total = cur.fetchone()["total"]

        cur.execute("""
            SELECT COALESCE(status, 'Nuovo') AS status, COUNT(*) AS count
            FROM beta_requests
            GROUP BY COALESCE(status, 'Nuovo')
            ORDER BY count DESC;
        """)
        by_status = cur.fetchall()

        cur.execute("""
            SELECT COALESCE(NULLIF(profile, ''), 'Non specificato') AS profile, COUNT(*) AS count
            FROM beta_requests
            GROUP BY COALESCE(NULLIF(profile, ''), 'Non specificato')
            ORDER BY count DESC;
        """)
        by_profile = cur.fetchall()

        cur.execute("""
            SELECT COALESCE(NULLIF(interest, ''), 'Non specificato') AS interest, COUNT(*) AS count
            FROM beta_requests
            GROUP BY COALESCE(NULLIF(interest, ''), 'Non specificato')
            ORDER BY count DESC;
        """)
        by_interest = cur.fetchall()

        cur.execute("""
            SELECT COUNT(*) AS last_7_days
            FROM beta_requests
            WHERE created_at >= NOW() - INTERVAL '7 days';
        """)
        last_7_days = cur.fetchone()["last_7_days"]

        cur.execute("""
            SELECT COUNT(*) AS today
            FROM beta_requests
            WHERE created_at::date = NOW()::date;
        """)
        today = cur.fetchone()["today"]

        cur.close()

        return {
            "ok": True,
            "total": total,
            "today": today,
            "last_7_days": last_7_days,
            "statuses": VALID_LEAD_STATUSES,
            "by_status": [dict(r) for r in by_status],
            "by_profile": [dict(r) for r in by_profile],
            "by_interest": [dict(r) for r in by_interest],
            "version": APP_VERSION
        }

    except Exception as e:
        print("❌ Errore get_beta_requests_stats:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Errore statistiche CRM.")

    finally:
        release_db_connection(conn)


# Alias compatibilità eventuale frontend precedente
@app.get("/api/beta-stats")
def get_beta_stats_alias():
    return get_beta_requests_stats()


# ============================================================
# CSV EXPORT
# ============================================================

@app.get("/api/beta-requests/export.csv")
def export_beta_requests_csv(
    status: Optional[str] = Query(default=None),
    profile: Optional[str] = Query(default=None),
    interest: Optional[str] = Query(default=None)
):
    """
    Export CSV richieste beta.
    V7.6 include status e internal_note.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        where = []
        params = []

        if status and status != "Tutti":
            validate_status(status)
            where.append("status = %s")
            params.append(status)

        if profile and profile != "Tutti":
            where.append("LOWER(COALESCE(profile, '')) = LOWER(%s)")
            params.append(profile)

        if interest and interest != "Tutti":
            where.append("LOWER(COALESCE(interest, '')) = LOWER(%s)")
            params.append(interest)

        where_sql = ""
        if where:
            where_sql = "WHERE " + " AND ".join(where)

        cur.execute(f"""
            SELECT
                id,
                name,
                email,
                profile,
                interest,
                message,
                source,
                status,
                internal_note,
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
            "interest",
            "message",
            "source",
            "status",
            "internal_note",
            "created_at",
            "updated_at"
        ])

        for row in rows:
            writer.writerow([
                row.get("id"),
                row.get("name") or "",
                row.get("email") or "",
                row.get("profile") or "",
                row.get("interest") or "",
                row.get("message") or "",
                row.get("source") or "",
                row.get("status") or "Nuovo",
                row.get("internal_note") or "",
                row.get("created_at").isoformat() if row.get("created_at") else "",
                row.get("updated_at").isoformat() if row.get("updated_at") else "",
            ])

        output.seek(0)

        filename = f"matchiq_beta_requests_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        print("❌ Errore export_beta_requests_csv:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Errore export CSV.")

    finally:
        release_db_connection(conn)


# Alias vecchio possibile
@app.get("/api/beta-requests/export")
def export_beta_requests_csv_alias(
    status: Optional[str] = Query(default=None),
    profile: Optional[str] = Query(default=None),
    interest: Optional[str] = Query(default=None)
):
    return export_beta_requests_csv(status=status, profile=profile, interest=interest)


# ============================================================
# MOCK / FALLBACK API PER FRONTEND
# Queste servono a non rompere Dashboard/Scout se alcune API live
# non sono ancora collegate o sono temporaneamente offline.
# ============================================================

@app.get("/api/live-matches")
def get_live_matches():
    """
    Endpoint fallback per dashboard/scout.
    Se hai già una tua integrazione live, puoi sostituire questa parte.
    """
    return {
        "ok": True,
        "source": "fallback",
        "matches": [
            {
                "id": "demo-001",
                "league": "Serie A",
                "home": "Inter",
                "away": "Milan",
                "minute": "Live",
                "score": "0-0",
                "status": "Demo",
                "risk": "Medio",
                "signal": "Equilibrio"
            },
            {
                "id": "demo-002",
                "league": "Premier League",
                "home": "Arsenal",
                "away": "Liverpool",
                "minute": "Pre-match",
                "score": "-",
                "status": "Demo",
                "risk": "Alto",
                "signal": "Over Potenziale"
            }
        ],
        "version": APP_VERSION
    }


@app.get("/api/scout/matches")
def get_scout_matches():
    return get_live_matches()


@app.get("/api/scout/match/{match_id}")
def get_scout_match_detail(match_id: str):
    return {
        "ok": True,
        "source": "fallback",
        "match_id": match_id,
        "match": {
            "id": match_id,
            "league": "Demo League",
            "home": "Home Team",
            "away": "Away Team",
            "minute": "Live",
            "score": "0-0",
            "status": "Demo"
        },
        "players": [
            {
                "name": "Player Home 1",
                "team": "Home Team",
                "role": "ATT",
                "score": 78,
                "signal": "Hot",
                "notes": "Buona proiezione offensiva"
            },
            {
                "name": "Player Away 1",
                "team": "Away Team",
                "role": "MID",
                "score": 72,
                "signal": "Watch",
                "notes": "Alta partecipazione al gioco"
            }
        ],
        "timeline": [
            {
                "minute": 12,
                "type": "momentum",
                "text": "Pressione crescente della squadra di casa"
            },
            {
                "minute": 28,
                "type": "risk",
                "text": "Possibile cambio ritmo offensivo"
            }
        ],
        "version": APP_VERSION
    }


# ============================================================
# FRONTEND STATIC FILES
# ============================================================

@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({
        "ok": True,
        "message": "MatchIQ Tactical API online",
        "version": APP_VERSION,
        "missing": "frontend/index.html non trovato"
    })


@app.get("/admin")
def serve_admin():
    admin_path = os.path.join(FRONTEND_DIR, "admin-beta.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    raise HTTPException(status_code=404, detail="admin-beta.html non trovato")


@app.get("/admin-beta")
def serve_admin_beta():
    return serve_admin()


@app.get("/scout")
def serve_scout():
    scout_path = os.path.join(FRONTEND_DIR, "scout.html")
    if os.path.exists(scout_path):
        return FileResponse(scout_path)
    raise HTTPException(status_code=404, detail="scout.html non trovato")


# Monta frontend statico alla fine
if os.path.isdir(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
else:
    print(f"⚠️ FRONTEND_DIR non trovato: {FRONTEND_DIR}")


# ============================================================
# DEBUG ROUTES
# ============================================================

@app.get("/api/debug/routes")
def debug_routes():
    routes = []
    for route in app.routes:
        methods = list(getattr(route, "methods", []) or [])
        path = getattr(route, "path", "")
        name = getattr(route, "name", "")
        routes.append({
            "path": path,
            "name": name,
            "methods": methods
        })

    return {
        "ok": True,
        "version": APP_VERSION,
        "routes": routes
    }


@app.get("/api/debug/db")
def debug_db():
    if db_pool is None:
        return {
            "ok": False,
            "database": False,
            "message": "DATABASE_URL non configurato o pool non disponibile."
        }

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'beta_requests'
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()

        cur.execute("SELECT COUNT(*) AS total FROM beta_requests;")
        total = cur.fetchone()["total"]

        cur.close()

        return {
            "ok": True,
            "database": True,
            "table": "beta_requests",
            "columns": [dict(c) for c in columns],
            "total": total
        }

    except Exception as e:
        print("❌ Errore debug_db:", e)
        traceback.print_exc()
        return {
            "ok": False,
            "database": True,
            "error": str(e)
        }

    finally:
        release_db_connection(conn)