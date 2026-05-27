"""
database.py
MatchIQ Tactical - Database Layer V8.1 Stripe Ready

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
        "scout_daily": 10,
        "full_analysis_daily": 15,
        "live_matches_daily": 50,
        "pdf_export_daily": 0,
        "saved_players": 10,
        "saved_matches": 10,
        "advanced_timeline": False,
        "advanced_scout": False,
        "pdf_export": False,
    },
    "pro": {
        "scout_daily": 250,
        "full_analysis_daily": 250,
        "live_matches_daily": 500,
        "pdf_export_daily": 30,
        "saved_players": 250,
        "saved_matches": 250,
        "advanced_timeline": True,
        "advanced_scout": True,
        "pdf_export": True,
    },
    "scout": {
        "scout_daily": 1000,
        "full_analysis_daily": 1000,
        "live_matches_daily": 2000,
        "pdf_export_daily": 100,
        "saved_players": 1000,
        "saved_matches": 1000,
        "advanced_timeline": True,
        "advanced_scout": True,
        "pdf_export": True,
    },
    "owner": {
        "scout_daily": 999999,
        "full_analysis_daily": 999999,
        "live_matches_daily": 999999,
        "pdf_export_daily": 999999,
        "saved_players": 999999,
        "saved_matches": 999999,
        "advanced_timeline": True,
        "advanced_scout": True,
        "pdf_export": True,
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
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT
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
