"""
database.py
MatchIQ Tactical - Database Layer V8.2 Pro Lock Ready

Compatibile con:
- PostgreSQL Railway/Production
- SQLite locale
- utenti free/pro/scout/owner
- usage tracking
- subscriptions Stripe/manual

Nota importante:
usa query helper con placeholder corretti per SQLite (?) e PostgreSQL (%s).
"""

import os
import json
import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone, date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "matchiq.db"
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)


# =========================================================
# PLAN LIMITS
# =========================================================

PLAN_LIMITS = {
    "free": {
        # Free = prova vera, ma limitata.
        "scout_daily": 5,
        "full_analysis_daily": 5,
        "live_matches_daily": 25,
        "pdf_export_daily": 0,
        "saved_players": 5,
        "saved_matches": 5,

        # Coach / report limits
        "coach_pdf_daily": 1,
        "coach_whatsapp_daily": 1,
        "coach_pagelle_daily": 5,
        "coach_history_limit": 2,
        "coach_reports_daily": 3,
        "video_report_daily": 1,
        "video_archive_limit": 3,

        # Feature flags
        "advanced_timeline": False,
        "advanced_scout": False,
        "pdf_export": False,
        "coach_pdf": False,
        "coach_whatsapp": False,
        "coach_pagelle": True,
        "coach_history": False,
        "scout_export": False,
        "watchlist_cloud": False,
        "video_archive_cloud": False,
    },
    "pro": {
        # Pro = uso da campo continuativo.
        "scout_daily": 250,
        "full_analysis_daily": 250,
        "live_matches_daily": 500,
        "pdf_export_daily": 30,
        "saved_players": 250,
        "saved_matches": 250,

        # Coach / report limits
        "coach_pdf_daily": 30,
        "coach_whatsapp_daily": 100,
        "coach_pagelle_daily": 999,
        "coach_history_limit": 250,
        "coach_reports_daily": 100,
        "video_report_daily": 10,
        "video_archive_limit": 50,

        # Feature flags
        "advanced_timeline": True,
        "advanced_scout": True,
        "pdf_export": True,
        "coach_pdf": True,
        "coach_whatsapp": True,
        "coach_pagelle": True,
        "coach_history": True,
        "scout_export": True,
        "watchlist_cloud": True,
        "video_archive_cloud": True,
    },
    "scout": {
        # Scout = piano avanzato / futuro piano verticale.
        "scout_daily": 1000,
        "full_analysis_daily": 1000,
        "live_matches_daily": 2000,
        "pdf_export_daily": 100,
        "saved_players": 1000,
        "saved_matches": 1000,

        "coach_pdf_daily": 100,
        "coach_whatsapp_daily": 250,
        "coach_pagelle_daily": 999,
        "coach_history_limit": 1000,
        "coach_reports_daily": 250,
        "video_report_daily": 30,
        "video_archive_limit": 200,

        "advanced_timeline": True,
        "advanced_scout": True,
        "pdf_export": True,
        "coach_pdf": True,
        "coach_whatsapp": True,
        "coach_pagelle": True,
        "coach_history": True,
        "scout_export": True,
        "watchlist_cloud": True,
        "video_archive_cloud": True,
    },
    "owner": {
        # Owner/Admin = tutto sbloccato.
        "scout_daily": 999999,
        "full_analysis_daily": 999999,
        "live_matches_daily": 999999,
        "pdf_export_daily": 999999,
        "saved_players": 999999,
        "saved_matches": 999999,

        "coach_pdf_daily": 999999,
        "coach_whatsapp_daily": 999999,
        "coach_pagelle_daily": 999999,
        "coach_history_limit": 999999,
        "coach_reports_daily": 999999,
        "video_report_daily": 999999,
        "video_archive_limit": 999999,

        "advanced_timeline": True,
        "advanced_scout": True,
        "pdf_export": True,
        "coach_pdf": True,
        "coach_whatsapp": True,
        "coach_pagelle": True,
        "coach_history": True,
        "scout_export": True,
        "watchlist_cloud": True,
        "video_archive_cloud": True,
    },
}


def get_plan_limits(plan: str):
    plan = (plan or "free").lower().strip()
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


# =========================================================
# DB HELPERS
# =========================================================

def get_connection():
    if USE_POSTGRES:
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def today_key():
    return date.today().isoformat()


def q(sql: str) -> str:
    """
    Converte i placeholder SQLite ? in %s quando siamo su PostgreSQL.
    Così il resto del file resta leggibile e compatibile.
    """
    return sql.replace("?", "%s") if USE_POSTGRES else sql


def row_to_dict(row):
    return dict(row) if row else None


def fetchone(cur):
    row = cur.fetchone()
    return row_to_dict(row)


def fetchall(cur):
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_last_insert_id(cur):
    if USE_POSTGRES:
        row = cur.fetchone()
        if isinstance(row, dict):
            return row.get("id")
        return row[0] if row else None
    return cur.lastrowid


# =========================================================
# INIT DB
# =========================================================

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free',
                is_active INTEGER NOT NULL DEFAULT 1,
                stripe_customer_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT
        """)

        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email_verified INTEGER NOT NULL DEFAULT 0
        """)

        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email_verified_at TEXT
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS saved_matches (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                match_id INTEGER NOT NULL,
                home TEXT,
                away TEXT,
                league TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS saved_players (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                team TEXT,
                role TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                endpoint TEXT NOT NULL,
                feature TEXT NOT NULL,
                usage_date TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                plan TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                provider TEXT DEFAULT 'manual',
                provider_customer_id TEXT,
                provider_subscription_id TEXT,
                current_period_start TEXT,
                current_period_end TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS scout_reports (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                match_id INTEGER,
                title TEXT,
                report_type TEXT DEFAULT 'scout',
                payload TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS video_reports (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT,
                club_name TEXT,
                category TEXT,
                focus TEXT,
                observed_team TEXT,
                report_style TEXT,
                frames_analyzed INTEGER NOT NULL DEFAULT 0,
                report TEXT,
                pdf_base64 TEXT,
                payload TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free',
                is_active INTEGER NOT NULL DEFAULT 1,
                stripe_customer_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        try:
            cur.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

        try:
            cur.execute("ALTER TABLE users ADD COLUMN email_verified_at TEXT")
        except Exception:
            pass

        cur.execute("""
            CREATE TABLE IF NOT EXISTS saved_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                match_id INTEGER NOT NULL,
                home TEXT,
                away TEXT,
                league TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS saved_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                team TEXT,
                role TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                endpoint TEXT NOT NULL,
                feature TEXT NOT NULL,
                usage_date TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                provider TEXT DEFAULT 'manual',
                provider_customer_id TEXT,
                provider_subscription_id TEXT,
                current_period_start TEXT,
                current_period_end TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS scout_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                match_id INTEGER,
                title TEXT,
                report_type TEXT DEFAULT 'scout',
                payload TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS video_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT,
                club_name TEXT,
                category TEXT,
                focus TEXT,
                observed_team TEXT,
                report_style TEXT,
                frames_analyzed INTEGER NOT NULL DEFAULT 0,
                report TEXT,
                pdf_base64 TEXT,
                payload TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_usage_user_feature_date
        ON api_usage(user_id, feature, usage_date)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_saved_players_user
        ON saved_players(user_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_saved_matches_user
        ON saved_matches(user_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status
        ON subscriptions(user_id, status)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscriptions_provider_subscription
        ON subscriptions(provider_subscription_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user
        ON password_reset_tokens(user_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_hash
        ON password_reset_tokens(token_hash)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires
        ON password_reset_tokens(expires_at)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_user
        ON email_verification_tokens(user_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_hash
        ON email_verification_tokens(token_hash)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_expires
        ON email_verification_tokens(expires_at)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_video_reports_user_created
        ON video_reports(user_id, created_at)
    """)

    conn.commit()
    conn.close()


# =========================================================
# USERS
# =========================================================

def create_user(email: str, password_hash: str, plan: str = "free"):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO users (email, password_hash, plan, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, 1, %s, %s)
            RETURNING id
        """, (email.lower().strip(), password_hash, plan, now, now))
        user_id = get_last_insert_id(cur)
    else:
        cur.execute("""
            INSERT INTO users (email, password_hash, plan, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
        """, (email.lower().strip(), password_hash, plan, now, now))
        user_id = cur.lastrowid

    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT * FROM users
        WHERE email = ?
        LIMIT 1
    """), (email.lower().strip(),))
    row = fetchone(cur)
    conn.close()
    return row


def get_user_by_id(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT * FROM users
        WHERE id = ?
        LIMIT 1
    """), (user_id,))
    row = fetchone(cur)
    conn.close()
    return row


def update_user_plan(user_id: int, plan: str):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        UPDATE users
        SET plan = ?, updated_at = ?
        WHERE id = ?
    """), (plan, now, user_id))
    conn.commit()
    conn.close()
    return True


def update_user_stripe_customer(user_id: int, stripe_customer_id: str):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        UPDATE users
        SET stripe_customer_id = ?, updated_at = ?
        WHERE id = ?
    """), (stripe_customer_id or "", now, user_id))
    conn.commit()
    conn.close()
    return True


def get_user_by_stripe_customer(stripe_customer_id: str):
    if not stripe_customer_id:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT * FROM users
        WHERE stripe_customer_id = ?
        LIMIT 1
    """), (stripe_customer_id,))
    row = fetchone(cur)
    conn.close()
    return row


def deactivate_user(user_id: int):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        UPDATE users
        SET is_active = 0, updated_at = ?
        WHERE id = ?
    """), (now, user_id))
    conn.commit()
    conn.close()
    return True




# =========================================================
# ADMIN ANALYTICS
# =========================================================

def get_admin_analytics():
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    data = {
        "total_users": 0,
        "users_today": 0,
        "users_last_7_days": 0,
        "active_subscriptions": 0,
        "usage_today": 0,
        "beta_total": 0,
        "beta_converted": 0,
        "estimated_mrr": 0.0,
        "plans": [],
        "beta_by_status": [],
        "coach": {
            "today_total": 0,
            "last_7_days_total": 0,
            "active_users_today": 0,
            "active_users_last_7_days": 0,
            "reports_today": 0,
            "pdf_today": 0,
            "whatsapp_today": 0,
            "pagelle_today": 0,
            "history_today": 0,
            "features_today": [],
            "features_last_7_days": [],
            "top_users_today": [],
            "top_users_last_7_days": [],
            "free_users_near_limit": 0,
        },
        "video": {
            "reports_today": 0,
            "reports_last_7_days": 0,
            "active_users_today": 0,
            "active_users_last_7_days": 0,
            "frames_today": 0,
            "frames_last_7_days": 0,
            "api_today": 0,
            "api_last_7_days": 0,
            "top_users_last_7_days": [],
        },
        "usage_by_feature_today": [],
        "usage_by_feature_last_7_days": [],
    }

    coach_features = [
        "coach",
        "coach_report",
        "coach_pdf",
        "coach_whatsapp",
        "coach_pagelle",
        "coach_history",
        "coach_storico",
    ]

    try:
        cur.execute("SELECT COUNT(*) AS total FROM users")
        data["total_users"] = int((fetchone(cur) or {}).get("total") or 0)

        if USE_POSTGRES:
            cur.execute("SELECT COUNT(*) AS total FROM users WHERE created_at::date = NOW()::date")
            data["users_today"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("SELECT COUNT(*) AS total FROM users WHERE created_at::timestamptz >= NOW() - INTERVAL '7 days'")
            data["users_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)
        else:
            cur.execute("SELECT COUNT(*) AS total FROM users WHERE substr(created_at,1,10) = ?", (today_key(),))
            data["users_today"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("SELECT COUNT(*) AS total FROM users WHERE datetime(created_at) >= datetime('now','-7 days')")
            data["users_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)

        cur.execute("SELECT LOWER(COALESCE(plan,'free')) AS plan, COUNT(*) AS count FROM users GROUP BY LOWER(COALESCE(plan,'free')) ORDER BY count DESC")
        data["plans"] = fetchall(cur)

        cur.execute("SELECT COUNT(*) AS total FROM subscriptions WHERE status = 'active'")
        data["active_subscriptions"] = int((fetchone(cur) or {}).get("total") or 0)

        cur.execute(q("SELECT COALESCE(SUM(count),0) AS total FROM api_usage WHERE usage_date = ?"), (today_key(),))
        data["usage_today"] = int((fetchone(cur) or {}).get("total") or 0)

        cur.execute("SELECT COUNT(*) AS total FROM users WHERE LOWER(COALESCE(plan,'free')) IN ('pro','scout')")
        paid_users = int((fetchone(cur) or {}).get("total") or 0)
        data["estimated_mrr"] = round(paid_users * 9.99, 2)

        cur.execute(q("""
            SELECT feature, COALESCE(SUM(count),0) AS total
            FROM api_usage
            WHERE usage_date = ?
            GROUP BY feature
            ORDER BY total DESC
        """), (today_key(),))
        data["usage_by_feature_today"] = fetchall(cur)

        if USE_POSTGRES:
            cur.execute("""
                SELECT feature, COALESCE(SUM(count),0) AS total
                FROM api_usage
                WHERE usage_date::date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY feature
                ORDER BY total DESC
            """)
        else:
            cur.execute("""
                SELECT feature, COALESCE(SUM(count),0) AS total
                FROM api_usage
                WHERE date(usage_date) >= date('now','-7 days')
                GROUP BY feature
                ORDER BY total DESC
            """)
        data["usage_by_feature_last_7_days"] = fetchall(cur)

        placeholders = ",".join(["?"] * len(coach_features))

        cur.execute(q(f"""
            SELECT COALESCE(SUM(count),0) AS total
            FROM api_usage
            WHERE usage_date = ? AND feature IN ({placeholders})
        """), [today_key(), *coach_features])
        data["coach"]["today_total"] = int((fetchone(cur) or {}).get("total") or 0)

        if USE_POSTGRES:
            cur.execute(f"""
                SELECT COALESCE(SUM(count),0) AS total
                FROM api_usage
                WHERE usage_date::date >= CURRENT_DATE - INTERVAL '7 days'
                  AND feature IN ({','.join(['%s'] * len(coach_features))})
            """, coach_features)
        else:
            cur.execute(f"""
                SELECT COALESCE(SUM(count),0) AS total
                FROM api_usage
                WHERE date(usage_date) >= date('now','-7 days')
                  AND feature IN ({placeholders})
            """, coach_features)
        data["coach"]["last_7_days_total"] = int((fetchone(cur) or {}).get("total") or 0)

        cur.execute(q(f"""
            SELECT COUNT(DISTINCT user_id) AS total
            FROM api_usage
            WHERE usage_date = ? AND feature IN ({placeholders}) AND user_id IS NOT NULL
        """), [today_key(), *coach_features])
        data["coach"]["active_users_today"] = int((fetchone(cur) or {}).get("total") or 0)

        if USE_POSTGRES:
            cur.execute(f"""
                SELECT COUNT(DISTINCT user_id) AS total
                FROM api_usage
                WHERE usage_date::date >= CURRENT_DATE - INTERVAL '7 days'
                  AND feature IN ({','.join(['%s'] * len(coach_features))})
                  AND user_id IS NOT NULL
            """, coach_features)
        else:
            cur.execute(f"""
                SELECT COUNT(DISTINCT user_id) AS total
                FROM api_usage
                WHERE date(usage_date) >= date('now','-7 days')
                  AND feature IN ({placeholders})
                  AND user_id IS NOT NULL
            """, coach_features)
        data["coach"]["active_users_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)

        def feature_today(feature_name):
            cur.execute(q("""
                SELECT COALESCE(SUM(count),0) AS total
                FROM api_usage
                WHERE usage_date = ? AND feature = ?
            """), (today_key(), feature_name))
            return int((fetchone(cur) or {}).get("total") or 0)

        data["coach"]["reports_today"] = feature_today("coach_report") + feature_today("coach")
        data["coach"]["pdf_today"] = feature_today("coach_pdf")
        data["coach"]["whatsapp_today"] = feature_today("coach_whatsapp")
        data["coach"]["pagelle_today"] = feature_today("coach_pagelle")
        data["coach"]["history_today"] = feature_today("coach_history") + feature_today("coach_storico")

        cur.execute(q(f"""
            SELECT feature, COALESCE(SUM(count),0) AS total
            FROM api_usage
            WHERE usage_date = ? AND feature IN ({placeholders})
            GROUP BY feature
            ORDER BY total DESC
        """), [today_key(), *coach_features])
        data["coach"]["features_today"] = fetchall(cur)

        if USE_POSTGRES:
            cur.execute(f"""
                SELECT feature, COALESCE(SUM(count),0) AS total
                FROM api_usage
                WHERE usage_date::date >= CURRENT_DATE - INTERVAL '7 days'
                  AND feature IN ({','.join(['%s'] * len(coach_features))})
                GROUP BY feature
                ORDER BY total DESC
            """, coach_features)
        else:
            cur.execute(f"""
                SELECT feature, COALESCE(SUM(count),0) AS total
                FROM api_usage
                WHERE date(usage_date) >= date('now','-7 days')
                  AND feature IN ({placeholders})
                GROUP BY feature
                ORDER BY total DESC
            """, coach_features)
        data["coach"]["features_last_7_days"] = fetchall(cur)

        cur.execute(q(f"""
            SELECT u.email, LOWER(COALESCE(u.plan,'free')) AS plan, COALESCE(SUM(a.count),0) AS total
            FROM api_usage a
            LEFT JOIN users u ON u.id = a.user_id
            WHERE a.usage_date = ? AND a.feature IN ({placeholders})
            GROUP BY u.email, LOWER(COALESCE(u.plan,'free'))
            ORDER BY total DESC
            LIMIT 8
        """), [today_key(), *coach_features])
        data["coach"]["top_users_today"] = fetchall(cur)

        if USE_POSTGRES:
            cur.execute(f"""
                SELECT u.email, LOWER(COALESCE(u.plan,'free')) AS plan, COALESCE(SUM(a.count),0) AS total
                FROM api_usage a
                LEFT JOIN users u ON u.id = a.user_id
                WHERE a.usage_date::date >= CURRENT_DATE - INTERVAL '7 days'
                  AND a.feature IN ({','.join(['%s'] * len(coach_features))})
                GROUP BY u.email, LOWER(COALESCE(u.plan,'free'))
                ORDER BY total DESC
                LIMIT 8
            """, coach_features)
        else:
            cur.execute(f"""
                SELECT u.email, LOWER(COALESCE(u.plan,'free')) AS plan, COALESCE(SUM(a.count),0) AS total
                FROM api_usage a
                LEFT JOIN users u ON u.id = a.user_id
                WHERE date(a.usage_date) >= date('now','-7 days')
                  AND a.feature IN ({placeholders})
                GROUP BY u.email, LOWER(COALESCE(u.plan,'free'))
                ORDER BY total DESC
                LIMIT 8
            """, coach_features)
        data["coach"]["top_users_last_7_days"] = fetchall(cur)

        cur.execute(q("""
            SELECT COUNT(*) AS total
            FROM (
                SELECT u.id, COALESCE(SUM(a.count),0) AS total_usage
                FROM users u
                LEFT JOIN api_usage a ON a.user_id = u.id
                    AND a.usage_date = ?
                    AND a.feature IN ('coach_pdf','coach_whatsapp','coach_pagelle','coach_history','coach_storico')
                WHERE LOWER(COALESCE(u.plan,'free')) = 'free'
                GROUP BY u.id
                HAVING COALESCE(SUM(a.count),0) >= 1
            ) t
        """), (today_key(),))
        data["coach"]["free_users_near_limit"] = int((fetchone(cur) or {}).get("total") or 0)

        if USE_POSTGRES:
            cur.execute("""
                SELECT COUNT(*) AS total
                FROM video_reports
                WHERE created_at::timestamptz::date = CURRENT_DATE
            """)
            data["video"]["reports_today"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COUNT(*) AS total
                FROM video_reports
                WHERE created_at::timestamptz >= NOW() - INTERVAL '7 days'
            """)
            data["video"]["reports_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COUNT(DISTINCT user_id) AS total
                FROM video_reports
                WHERE created_at::timestamptz::date = CURRENT_DATE
                  AND user_id IS NOT NULL
            """)
            data["video"]["active_users_today"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COUNT(DISTINCT user_id) AS total
                FROM video_reports
                WHERE created_at::timestamptz >= NOW() - INTERVAL '7 days'
                  AND user_id IS NOT NULL
            """)
            data["video"]["active_users_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COALESCE(SUM(frames_analyzed),0) AS total
                FROM video_reports
                WHERE created_at::timestamptz::date = CURRENT_DATE
            """)
            data["video"]["frames_today"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COALESCE(SUM(frames_analyzed),0) AS total
                FROM video_reports
                WHERE created_at::timestamptz >= NOW() - INTERVAL '7 days'
            """)
            data["video"]["frames_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT u.email, LOWER(COALESCE(u.plan,'free')) AS plan,
                       COUNT(v.id) AS reports, COALESCE(SUM(v.frames_analyzed),0) AS frames
                FROM video_reports v
                LEFT JOIN users u ON u.id = v.user_id
                WHERE v.created_at::timestamptz >= NOW() - INTERVAL '7 days'
                GROUP BY u.email, LOWER(COALESCE(u.plan,'free'))
                ORDER BY reports DESC, frames DESC
                LIMIT 8
            """)
        else:
            cur.execute("""
                SELECT COUNT(*) AS total
                FROM video_reports
                WHERE substr(created_at,1,10) = ?
            """, (today_key(),))
            data["video"]["reports_today"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COUNT(*) AS total
                FROM video_reports
                WHERE datetime(created_at) >= datetime('now','-7 days')
            """)
            data["video"]["reports_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COUNT(DISTINCT user_id) AS total
                FROM video_reports
                WHERE substr(created_at,1,10) = ?
                  AND user_id IS NOT NULL
            """, (today_key(),))
            data["video"]["active_users_today"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COUNT(DISTINCT user_id) AS total
                FROM video_reports
                WHERE datetime(created_at) >= datetime('now','-7 days')
                  AND user_id IS NOT NULL
            """)
            data["video"]["active_users_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COALESCE(SUM(frames_analyzed),0) AS total
                FROM video_reports
                WHERE substr(created_at,1,10) = ?
            """, (today_key(),))
            data["video"]["frames_today"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT COALESCE(SUM(frames_analyzed),0) AS total
                FROM video_reports
                WHERE datetime(created_at) >= datetime('now','-7 days')
            """)
            data["video"]["frames_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("""
                SELECT u.email, LOWER(COALESCE(u.plan,'free')) AS plan,
                       COUNT(v.id) AS reports, COALESCE(SUM(v.frames_analyzed),0) AS frames
                FROM video_reports v
                LEFT JOIN users u ON u.id = v.user_id
                WHERE datetime(v.created_at) >= datetime('now','-7 days')
                GROUP BY u.email, LOWER(COALESCE(u.plan,'free'))
                ORDER BY reports DESC, frames DESC
                LIMIT 8
            """)
        data["video"]["top_users_last_7_days"] = fetchall(cur)

        data["video"]["api_today"] = feature_today("video_report")
        if USE_POSTGRES:
            cur.execute("""
                SELECT COALESCE(SUM(count),0) AS total
                FROM api_usage
                WHERE usage_date::date >= CURRENT_DATE - INTERVAL '7 days'
                  AND feature = 'video_report'
            """)
        else:
            cur.execute("""
                SELECT COALESCE(SUM(count),0) AS total
                FROM api_usage
                WHERE date(usage_date) >= date('now','-7 days')
                  AND feature = 'video_report'
            """)
        data["video"]["api_last_7_days"] = int((fetchone(cur) or {}).get("total") or 0)

        try:
            cur.execute("SELECT COUNT(*) AS total FROM beta_requests")
            data["beta_total"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("SELECT COUNT(*) AS total FROM beta_requests WHERE status = 'Convertito'")
            data["beta_converted"] = int((fetchone(cur) or {}).get("total") or 0)

            cur.execute("SELECT COALESCE(status,'Nuovo') AS status, COUNT(*) AS count FROM beta_requests GROUP BY COALESCE(status,'Nuovo') ORDER BY count DESC")
            data["beta_by_status"] = fetchall(cur)
        except Exception:
            data["beta_total"] = 0
            data["beta_converted"] = 0
            data["beta_by_status"] = []

        return data

    finally:
        conn.close()


# =========================================================
# USAGE TRACKING
# =========================================================

def track_api_usage(user_id: int, endpoint: str, feature: str):
    now = utc_now()
    usage_date = today_key()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        SELECT * FROM api_usage
        WHERE user_id = ? AND endpoint = ? AND feature = ? AND usage_date = ?
        LIMIT 1
    """), (user_id, endpoint, feature, usage_date))

    row = fetchone(cur)

    if row:
        cur.execute(q("""
            UPDATE api_usage
            SET count = count + 1, updated_at = ?
            WHERE id = ?
        """), (now, row["id"]))
    else:
        cur.execute(q("""
            INSERT INTO api_usage (user_id, endpoint, feature, usage_date, count, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """), (user_id, endpoint, feature, usage_date, now, now))

    conn.commit()
    conn.close()
    return True


def get_today_usage(user_id: int, feature: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT COALESCE(SUM(count), 0) AS total
        FROM api_usage
        WHERE user_id = ? AND feature = ? AND usage_date = ?
    """), (user_id, feature, today_key()))
    row = fetchone(cur)
    conn.close()
    return int((row or {}).get("total") or 0)


def get_usage_summary(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT feature, COALESCE(SUM(count), 0) AS total
        FROM api_usage
        WHERE user_id = ? AND usage_date = ?
        GROUP BY feature
    """), (user_id, today_key()))
    rows = fetchall(cur)
    conn.close()
    return {row["feature"]: int(row["total"] or 0) for row in rows}


def can_use_feature(user_id: int, feature: str):
    user = get_user_by_id(user_id)

    if not user:
        return {"allowed": False, "reason": "Utente non trovato", "plan": "unknown", "used": 0, "limit": 0}

    plan = user.get("plan", "free")
    limits = get_plan_limits(plan)
    feature_key = f"{feature}_daily"
    limit = limits.get(feature_key)

    if limit is None:
        return {"allowed": True, "reason": "Feature non limitata", "plan": plan, "used": 0, "limit": None}

    used = get_today_usage(user_id, feature)

    return {
        "allowed": used < limit,
        "reason": "OK" if used < limit else "Limite giornaliero raggiunto",
        "plan": plan,
        "used": used,
        "limit": limit,
    }


def require_feature_or_raise(user_id: int, feature: str):
    result = can_use_feature(user_id, feature)
    if not result["allowed"]:
        raise Exception(f"Limite raggiunto per {feature}. Piano: {result['plan']} ({result['used']}/{result['limit']})")
    return result


# =========================================================
# SAVED MATCHES
# =========================================================

def count_saved_matches(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT COUNT(*) AS total
        FROM saved_matches
        WHERE user_id = ?
    """), (user_id,))
    row = fetchone(cur)
    conn.close()
    return int((row or {}).get("total") or 0)


def save_match(user_id: int, match_id: int, home: str, away: str, league: str):
    user = get_user_by_id(user_id)
    limits = get_plan_limits(user.get("plan", "free") if user else "free")

    if count_saved_matches(user_id) >= limits["saved_matches"]:
        return {"success": False, "error": "Limite match salvati raggiunto", "limit": limits["saved_matches"]}

    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        INSERT INTO saved_matches (user_id, match_id, home, away, league, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """), (user_id, match_id, home, away, league, now))
    conn.commit()
    conn.close()
    return {"success": True}


def get_saved_matches(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT * FROM saved_matches
        WHERE user_id = ?
        ORDER BY created_at DESC
    """), (user_id,))
    rows = fetchall(cur)
    conn.close()
    return rows


# =========================================================
# SAVED PLAYERS
# =========================================================

def count_saved_players(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT COUNT(*) AS total
        FROM saved_players
        WHERE user_id = ?
    """), (user_id,))
    row = fetchone(cur)
    conn.close()
    return int((row or {}).get("total") or 0)


def save_player(user_id: int, player_name: str, team: str = "", role: str = "", notes: str = ""):
    user = get_user_by_id(user_id)
    limits = get_plan_limits(user.get("plan", "free") if user else "free")

    if count_saved_players(user_id) >= limits["saved_players"]:
        return {"success": False, "error": "Limite player salvati raggiunto", "limit": limits["saved_players"]}

    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        INSERT INTO saved_players (user_id, player_name, team, role, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """), (user_id, player_name, team, role, notes, now))
    conn.commit()
    conn.close()
    return {"success": True}


def get_saved_players(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT * FROM saved_players
        WHERE user_id = ?
        ORDER BY created_at DESC
    """), (user_id,))
    rows = fetchall(cur)
    conn.close()
    return rows


# =========================================================
# SCOUT REPORTS
# =========================================================

def save_scout_report(user_id: int, match_id: int = None, title: str = "", report_type: str = "scout", payload: str = ""):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO scout_reports (user_id, match_id, title, report_type, payload, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, match_id, title, report_type, payload, now))
        report_id = get_last_insert_id(cur)
    else:
        cur.execute("""
            INSERT INTO scout_reports (user_id, match_id, title, report_type, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, match_id, title, report_type, payload, now))
        report_id = cur.lastrowid

    conn.commit()
    conn.close()
    return report_id


def get_scout_reports(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT * FROM scout_reports
        WHERE user_id = ?
        ORDER BY created_at DESC
    """), (user_id,))
    rows = fetchall(cur)
    conn.close()
    return rows


# =========================================================
# VIDEO REPORTS
# =========================================================

def count_video_reports(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT COUNT(*) AS total
        FROM video_reports
        WHERE user_id = ?
    """), (user_id,))
    row = fetchone(cur)
    conn.close()
    return int((row or {}).get("total") or 0)


def save_video_report(
    user_id: int,
    title: str = "",
    club_name: str = "",
    category: str = "",
    focus: str = "",
    observed_team: str = "",
    report_style: str = "",
    frames_analyzed: int = 0,
    report: str = "",
    pdf_base64: str = "",
    payload: dict = None,
):
    user = get_user_by_id(user_id)
    limits = get_plan_limits(user.get("plan", "free") if user else "free")
    archive_limit = int(limits.get("video_archive_limit", 0) or 0)

    if archive_limit <= 0:
        return {"success": False, "error": "Archivio video cloud non disponibile per questo piano", "limit": archive_limit}

    if count_video_reports(user_id) >= archive_limit:
        return {"success": False, "error": "Limite archivio video raggiunto", "limit": archive_limit}

    now = utc_now()
    payload_text = json.dumps(payload or {}, ensure_ascii=False)
    conn = get_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO video_reports (
                user_id, title, club_name, category, focus, observed_team,
                report_style, frames_analyzed, report, pdf_base64, payload, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, title, club_name, category, focus, observed_team,
            report_style, int(frames_analyzed or 0), report, pdf_base64, payload_text, now,
        ))
        report_id = get_last_insert_id(cur)
    else:
        cur.execute("""
            INSERT INTO video_reports (
                user_id, title, club_name, category, focus, observed_team,
                report_style, frames_analyzed, report, pdf_base64, payload, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, title, club_name, category, focus, observed_team,
            report_style, int(frames_analyzed or 0), report, pdf_base64, payload_text, now,
        ))
        report_id = cur.lastrowid

    conn.commit()
    conn.close()
    return {"success": True, "id": report_id}


def get_video_reports(user_id: int, limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT id, title, club_name, category, focus, observed_team, report_style,
               frames_analyzed, report, pdf_base64, created_at
        FROM video_reports
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """), (user_id, int(limit or 50)))
    rows = fetchall(cur)
    conn.close()
    return rows


def delete_video_report(user_id: int, report_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        DELETE FROM video_reports
        WHERE user_id = ? AND id = ?
    """), (user_id, report_id))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


# =========================================================
# SUBSCRIPTIONS
# =========================================================

def create_subscription(
    user_id: int,
    plan: str,
    provider: str = "manual",
    provider_customer_id: str = "",
    provider_subscription_id: str = "",
    current_period_start: str = "",
    current_period_end: str = "",
    status: str = "active",
):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    # Cancella/chiude eventuali subscription attive precedenti dello stesso provider/subscription.
    if provider_subscription_id:
        cur.execute(q("""
            UPDATE subscriptions
            SET status = 'cancelled', updated_at = ?
            WHERE provider_subscription_id = ? AND status = 'active'
        """), (now, provider_subscription_id))

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO subscriptions (
                user_id, plan, status, provider, provider_customer_id,
                provider_subscription_id, current_period_start, current_period_end,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, plan, status, provider, provider_customer_id,
            provider_subscription_id, current_period_start, current_period_end,
            now, now,
        ))
        sub_id = get_last_insert_id(cur)
    else:
        cur.execute("""
            INSERT INTO subscriptions (
                user_id, plan, status, provider, provider_customer_id,
                provider_subscription_id, current_period_start, current_period_end,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, plan, status, provider, provider_customer_id,
            provider_subscription_id, current_period_start, current_period_end,
            now, now,
        ))
        sub_id = cur.lastrowid

    conn.commit()
    conn.close()

    if status in ["active", "trialing"]:
        update_user_plan(user_id, plan)
    if provider_customer_id:
        update_user_stripe_customer(user_id, provider_customer_id)

    return sub_id


def upsert_subscription_by_provider(
    user_id: int,
    plan: str,
    provider: str,
    provider_customer_id: str,
    provider_subscription_id: str,
    status: str,
    current_period_start: str = "",
    current_period_end: str = "",
):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        SELECT id FROM subscriptions
        WHERE provider = ? AND provider_subscription_id = ?
        LIMIT 1
    """), (provider, provider_subscription_id))
    existing = fetchone(cur)

    if existing:
        cur.execute(q("""
            UPDATE subscriptions
            SET user_id = ?, plan = ?, status = ?, provider_customer_id = ?,
                current_period_start = ?, current_period_end = ?, updated_at = ?
            WHERE id = ?
        """), (
            user_id, plan, status, provider_customer_id,
            current_period_start, current_period_end, now, existing["id"],
        ))
        sub_id = existing["id"]
    else:
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO subscriptions (
                    user_id, plan, status, provider, provider_customer_id,
                    provider_subscription_id, current_period_start, current_period_end,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id, plan, status, provider, provider_customer_id,
                provider_subscription_id, current_period_start, current_period_end,
                now, now,
            ))
            sub_id = get_last_insert_id(cur)
        else:
            cur.execute("""
                INSERT INTO subscriptions (
                    user_id, plan, status, provider, provider_customer_id,
                    provider_subscription_id, current_period_start, current_period_end,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, plan, status, provider, provider_customer_id,
                provider_subscription_id, current_period_start, current_period_end,
                now, now,
            ))
            sub_id = cur.lastrowid

    conn.commit()
    conn.close()

    if provider_customer_id:
        update_user_stripe_customer(user_id, provider_customer_id)

    if status in ["active", "trialing"]:
        update_user_plan(user_id, plan)
    elif status in ["canceled", "cancelled", "unpaid", "incomplete_expired"]:
        update_user_plan(user_id, "free")

    return sub_id


def get_active_subscription(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT * FROM subscriptions
        WHERE user_id = ? AND status = 'active'
        ORDER BY created_at DESC
        LIMIT 1
    """), (user_id,))
    row = fetchone(cur)
    conn.close()
    return row


def get_subscription_by_provider_id(provider_subscription_id: str):
    if not provider_subscription_id:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        SELECT * FROM subscriptions
        WHERE provider_subscription_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """), (provider_subscription_id,))
    row = fetchone(cur)
    conn.close()
    return row


def cancel_subscription(user_id: int):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("""
        UPDATE subscriptions
        SET status = 'cancelled', updated_at = ?
        WHERE user_id = ? AND status = 'active'
    """), (now, user_id))
    conn.commit()
    conn.close()
    update_user_plan(user_id, "free")
    return True



# =========================================================
# PASSWORD RESET
# =========================================================

def create_password_reset_token(user_id: int, token_hash: str, expires_at: str):
    """
    Salva un token di reset password già hashato.
    Per sicurezza invalidiamo prima eventuali token precedenti non usati.
    """
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        UPDATE password_reset_tokens
        SET used = 1, used_at = ?
        WHERE user_id = ? AND used = 0
    """), (now, user_id))

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO password_reset_tokens (
                user_id,
                token_hash,
                expires_at,
                used,
                created_at,
                used_at
            )
            VALUES (%s, %s, %s, 0, %s, NULL)
            RETURNING id
        """, (user_id, token_hash, expires_at, now))
        token_id = get_last_insert_id(cur)
    else:
        cur.execute("""
            INSERT INTO password_reset_tokens (
                user_id,
                token_hash,
                expires_at,
                used,
                created_at,
                used_at
            )
            VALUES (?, ?, ?, 0, ?, NULL)
        """, (user_id, token_hash, expires_at, now))
        token_id = cur.lastrowid

    conn.commit()
    conn.close()
    return token_id


def get_valid_password_reset_token(token_hash: str):
    """
    Recupera un token reset non usato.
    Il controllo scadenza preciso lo facciamo lato auth.py.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        SELECT
            prt.*,
            u.email,
            u.is_active
        FROM password_reset_tokens prt
        JOIN users u ON u.id = prt.user_id
        WHERE prt.token_hash = ?
          AND prt.used = 0
        LIMIT 1
    """), (token_hash,))

    row = fetchone(cur)
    conn.close()
    return row


def mark_password_reset_token_used(token_id: int):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        UPDATE password_reset_tokens
        SET used = 1,
            used_at = ?
        WHERE id = ?
    """), (now, token_id))

    conn.commit()
    conn.close()
    return True


def update_user_password(user_id: int, password_hash: str):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        UPDATE users
        SET password_hash = ?,
            updated_at = ?
        WHERE id = ?
    """), (password_hash, now, user_id))

    conn.commit()
    conn.close()
    return True


# =========================================================
# EMAIL VERIFICATION
# =========================================================

def create_email_verification_token(user_id: int, token_hash: str, expires_at: str):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        UPDATE email_verification_tokens
        SET used = 1, used_at = ?
        WHERE user_id = ? AND used = 0
    """), (now, user_id))

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO email_verification_tokens (
                user_id, token_hash, expires_at, used, created_at, used_at
            )
            VALUES (%s, %s, %s, 0, %s, NULL)
            RETURNING id
        """, (user_id, token_hash, expires_at, now))
        token_id = get_last_insert_id(cur)
    else:
        cur.execute("""
            INSERT INTO email_verification_tokens (
                user_id, token_hash, expires_at, used, created_at, used_at
            )
            VALUES (?, ?, ?, 0, ?, NULL)
        """, (user_id, token_hash, expires_at, now))
        token_id = cur.lastrowid

    conn.commit()
    conn.close()
    return token_id


def get_valid_email_verification_token(token_hash: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        SELECT
            evt.*,
            u.email,
            u.is_active,
            u.email_verified
        FROM email_verification_tokens evt
        JOIN users u ON u.id = evt.user_id
        WHERE evt.token_hash = ?
          AND evt.used = 0
        LIMIT 1
    """), (token_hash,))

    row = fetchone(cur)
    conn.close()
    return row


def mark_email_verification_token_used(token_id: int):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        UPDATE email_verification_tokens
        SET used = 1, used_at = ?
        WHERE id = ?
    """), (now, token_id))

    conn.commit()
    conn.close()
    return True


def mark_user_email_verified(user_id: int):
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(q("""
        UPDATE users
        SET email_verified = 1,
            email_verified_at = ?,
            updated_at = ?
        WHERE id = ?
    """), (now, now, user_id))

    conn.commit()
    conn.close()
    return True
