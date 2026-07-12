import json
from typing import Any, Dict, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now


def _id_definition() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_weekly_briefing_schema() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS weekly_ai_briefings (
            id {_id_definition()},
            user_id INTEGER NOT NULL,
            knowledge_id INTEGER NOT NULL,
            week_key TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            sources TEXT NOT NULL,
            content TEXT NOT NULL,
            priorities TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            read_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, week_key),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(knowledge_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_weekly_briefing_user_updated ON weekly_ai_briefings(user_id, updated_at)")
    conn.commit()
    conn.close()


def _decode(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    data = dict(row)
    for field, fallback in (("sources", {}), ("content", {}), ("priorities", [])):
        try:
            data[field] = json.loads(data.get(field) or "")
        except (TypeError, ValueError):
            data[field] = fallback
    data["is_read"] = bool(data.get("is_read"))
    return data


def get_week(user_id: int, week_key: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("SELECT * FROM weekly_ai_briefings WHERE user_id = ? AND week_key = ?"), (user_id, week_key))
    row = fetchone(cur)
    conn.close()
    return _decode(row)


def get_latest(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("SELECT * FROM weekly_ai_briefings WHERE user_id = ? ORDER BY week_key DESC, updated_at DESC LIMIT 1"), (user_id,))
    row = fetchone(cur)
    conn.close()
    return _decode(row)


def save_week(user_id: int, knowledge_id: int, week_key: str, fingerprint: str, sources: Dict, content: Dict, priorities: list) -> Dict[str, Any]:
    now = utc_now()
    existing = get_week(user_id, week_key)
    encoded = (json.dumps(sources, ensure_ascii=False, sort_keys=True), json.dumps(content, ensure_ascii=False), json.dumps(priorities, ensure_ascii=False))
    conn = get_connection()
    cur = conn.cursor()
    if existing:
        cur.execute(q("""UPDATE weekly_ai_briefings
            SET source_fingerprint = ?, sources = ?, content = ?, priorities = ?, is_read = 0, read_at = NULL, updated_at = ?
            WHERE id = ? AND user_id = ?"""), (fingerprint, *encoded, now, existing["id"], user_id))
        briefing_id = existing["id"]
    else:
        returning = " RETURNING id" if USE_POSTGRES else ""
        cur.execute(q(f"""INSERT INTO weekly_ai_briefings
            (user_id, knowledge_id, week_key, source_fingerprint, sources, content, priorities, is_read, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?){returning}"""), (user_id, knowledge_id, week_key, fingerprint, *encoded, now, now))
        briefing_id = get_last_insert_id(cur)
    conn.commit()
    conn.close()
    return get_week(user_id, week_key)


def mark_read(user_id: int, briefing_id: int) -> Optional[Dict[str, Any]]:
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("UPDATE weekly_ai_briefings SET is_read = 1, read_at = ?, updated_at = ? WHERE id = ? AND user_id = ?"), (now, now, briefing_id, user_id))
    conn.commit()
    cur.execute(q("SELECT * FROM weekly_ai_briefings WHERE id = ? AND user_id = ?"), (briefing_id, user_id))
    row = fetchone(cur)
    conn.close()
    return _decode(row)


def collect_cloud_sources(user_id: int, week_start: str) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("SELECT client_id, match_key, minute, intent, tactical_topic, topic_label, zone, polarity, priority, player_names, original_text, created_at FROM voice_coach_observations WHERE user_id = ? AND status = 'confirmed' AND created_at >= ? ORDER BY created_at DESC LIMIT 100"), (user_id, week_start))
    voice = fetchall(cur)
    for item in voice:
        try: item["player_names"] = json.loads(item.get("player_names") or "[]")
        except (TypeError, ValueError): item["player_names"] = []
    cur.execute(q("SELECT id, title, club_name, focus, frames_analyzed, created_at FROM video_reports WHERE user_id = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 30"), (user_id, week_start))
    reports = fetchall(cur)
    cur.execute(q("SELECT id, title, status, created_at, updated_at FROM video_assets WHERE user_id = ? AND updated_at >= ? ORDER BY updated_at DESC LIMIT 30"), (user_id, week_start))
    sessions = fetchall(cur)
    cur.execute(q("SELECT id, home, away, league, created_at FROM saved_matches WHERE user_id = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 30"), (user_id, week_start))
    matches = fetchall(cur)
    cur.execute(q("SELECT COUNT(*) AS total FROM video_frame_feedback WHERE user_id = ? AND created_at >= ?"), (user_id, week_start))
    frames = int((fetchone(cur) or {}).get("total") or 0)
    conn.close()
    return {"voice_observations": voice, "video_reports": reports, "video_sessions": sessions, "saved_matches": matches, "reviewed_frames": frames, "week_start": week_start}
