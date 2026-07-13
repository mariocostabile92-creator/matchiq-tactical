import os
import logging
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from fastapi import APIRouter, Query, Depends, Body, HTTPException

from auth import create_verification_for_user
from brevo_service import send_verification_email, is_email_configured
from app.routers.admin_beta import require_admin_token, get_database_url

logger = logging.getLogger("matchiq")

router = APIRouter()

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
    item["video_reports_total"] = int(item.get("video_reports_total") or 0)
    item["video_reports_last_7_days"] = int(item.get("video_reports_last_7_days") or 0)
    item["video_usage_today"] = int(item.get("video_usage_today") or 0)

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
            0 AS total_usage_today,
            0 AS video_reports_total,
            0 AS video_reports_last_7_days,
            0 AS video_usage_today
        FROM users
        WHERE id = %s;
    """, (user_id,))
    row = cur.fetchone()
    return normalize_admin_user_row(row) if row else None


@router.get("/api/admin/users", tags=["Admin"])
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
            elif status_value == "video_today":
                where.append("COALESCE(video_usage.video_usage_today, 0) > 0")
            elif status_value == "video_7d":
                where.append("COALESCE(video_stats.video_reports_last_7_days, 0) > 0")
            elif status_value == "video_any":
                where.append("COALESCE(video_stats.video_reports_total, 0) > 0")
            elif status_value == "free_video_lead":
                where.append("COALESCE(users.plan, 'free') = 'free'")
                where.append("COALESCE(video_stats.video_reports_total, 0) > 0")

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
                COALESCE(usage_today.total_usage_today, 0) AS total_usage_today,
                COALESCE(video_stats.video_reports_total, 0) AS video_reports_total,
                COALESCE(video_stats.video_reports_last_7_days, 0) AS video_reports_last_7_days,
                COALESCE(video_usage.video_usage_today, 0) AS video_usage_today
            FROM users
            LEFT JOIN (
                SELECT user_id, COALESCE(SUM(count), 0) AS total_usage_today
                FROM api_usage
                WHERE usage_date = CURRENT_DATE::text
                GROUP BY user_id
            ) usage_today ON usage_today.user_id = users.id
            LEFT JOIN (
                SELECT
                    user_id,
                    COUNT(*) AS video_reports_total,
                    COUNT(*) FILTER (WHERE created_at::timestamptz >= NOW() - INTERVAL '7 days') AS video_reports_last_7_days
                FROM video_reports
                GROUP BY user_id
            ) video_stats ON video_stats.user_id = users.id
            LEFT JOIN (
                SELECT user_id, COALESCE(SUM(count), 0) AS video_usage_today
                FROM api_usage
                WHERE usage_date = CURRENT_DATE::text
                  AND feature = 'video_report'
                GROUP BY user_id
            ) video_usage ON video_usage.user_id = users.id
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


@router.patch("/api/admin/users/{user_id}/plan", tags=["Admin"])
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


@router.post("/api/admin/users/{user_id}/activate", tags=["Admin"])
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


@router.post("/api/admin/users/{user_id}/deactivate", tags=["Admin"])
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


@router.post("/api/admin/users/{user_id}/resend-verification", tags=["Admin"])
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
            "verification_link": verification_link if os.getenv("EMAIL_VERIFICATION_EXPOSE_LINK", "0") == "1" else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[ADMIN USERS] Errore reinvio verifica email")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn: conn.close()
