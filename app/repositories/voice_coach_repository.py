import json
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now


JSON_FIELDS = {"player_ids", "player_names", "ambiguities", "warnings", "evidence", "metadata"}
PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _id_definition() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_voice_coach_schema() -> None:
    conn = get_connection()
    cur = conn.cursor()
    id_column = _id_definition()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS voice_coach_observations (
            id {id_column},
            user_id INTEGER NOT NULL,
            knowledge_id INTEGER NOT NULL,
            client_id TEXT NOT NULL,
            match_key TEXT NOT NULL,
            match_id TEXT,
            intent TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0,
            original_text TEXT NOT NULL,
            normalized_summary TEXT,
            minute INTEGER NOT NULL DEFAULT 0,
            match_phase TEXT,
            team TEXT,
            player_ids TEXT,
            player_names TEXT,
            tactical_topic TEXT,
            topic_label TEXT,
            zone TEXT,
            polarity TEXT,
            priority TEXT,
            source TEXT,
            requires_confirmation INTEGER NOT NULL DEFAULT 0,
            ambiguities TEXT,
            warnings TEXT,
            evidence TEXT,
            explanation TEXT,
            status TEXT NOT NULL DEFAULT 'confirmed',
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, client_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(knowledge_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS voice_coach_match_themes (
            id {id_column},
            user_id INTEGER NOT NULL,
            knowledge_id INTEGER NOT NULL,
            match_key TEXT NOT NULL,
            topic TEXT NOT NULL,
            label TEXT NOT NULL,
            zone TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            first_minute INTEGER NOT NULL DEFAULT 0,
            last_minute INTEGER NOT NULL DEFAULT 0,
            involved_players TEXT,
            polarity TEXT,
            highest_priority TEXT,
            source_observation_ids TEXT,
            examples TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, match_key, topic, zone),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(knowledge_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_voice_observations_match ON voice_coach_observations(user_id, match_key, minute)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_voice_themes_match ON voice_coach_match_themes(user_id, match_key, count)")
    conn.commit()
    conn.close()


def _dump(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _load(value: Any, fallback: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def _decode(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    data = dict(row)
    for field in JSON_FIELDS:
        if field in data:
            data[field] = _load(data[field], {} if field == "metadata" else [])
    for field in ("involved_players", "source_observation_ids", "examples"):
        if field in data:
            data[field] = _load(data[field], [])
    data["requires_confirmation"] = bool(data.get("requires_confirmation"))
    return data


def upsert_observation(user_id: int, knowledge_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now()
    data = dict(payload)
    for field in JSON_FIELDS:
        data[field] = _dump(data.get(field, {} if field == "metadata" else []))
    data["requires_confirmation"] = 1 if data.get("requires_confirmation") else 0
    columns = ["user_id", "knowledge_id", *data.keys(), "created_at", "updated_at"]
    values = [user_id, knowledge_id, *data.values(), now, now]
    placeholders = ", ".join("?" for _ in columns)
    mutable = [key for key in data if key not in {"client_id", "match_key"}]
    updates = ", ".join(f"{field} = excluded.{field}" for field in [*mutable, "updated_at"])
    sql = f"INSERT INTO voice_coach_observations ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT(user_id, client_id) DO UPDATE SET {updates}"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q(sql), values)
    conn.commit()
    cur.execute(q("SELECT * FROM voice_coach_observations WHERE user_id = ? AND client_id = ?"), (user_id, payload["client_id"]))
    row = fetchone(cur)
    conn.close()
    return _decode(row)


def list_observations(user_id: int, match_key: str, include_cancelled: bool = False) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    suffix = "" if include_cancelled else " AND status <> 'cancelled'"
    cur.execute(q(f"SELECT * FROM voice_coach_observations WHERE user_id = ? AND match_key = ?{suffix} ORDER BY minute, created_at, id"), (user_id, match_key))
    rows = fetchall(cur)
    conn.close()
    return [_decode(row) for row in rows]


def set_observation_status(user_id: int, client_id: str, status: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("UPDATE voice_coach_observations SET status = ?, updated_at = ? WHERE user_id = ? AND client_id = ?"), (status, utc_now(), user_id, client_id))
    conn.commit()
    cur.execute(q("SELECT * FROM voice_coach_observations WHERE user_id = ? AND client_id = ?"), (user_id, client_id))
    row = fetchone(cur)
    conn.close()
    return _decode(row)


def rebuild_themes(user_id: int, knowledge_id: int, match_key: str) -> List[Dict[str, Any]]:
    observations = [item for item in list_observations(user_id, match_key) if item.get("status") == "confirmed"]
    grouped: Dict[str, Dict[str, Any]] = {}
    for item in observations:
        topic = item.get("tactical_topic") or "general_note"
        zone = item.get("zone") or "not_specified"
        key = f"{topic}|{zone}"
        group = grouped.setdefault(key, {
            "topic": topic, "label": item.get("topic_label") or "Nota staff", "zone": zone,
            "minutes": [], "players": [], "polarities": [], "priorities": [], "ids": [], "examples": [],
        })
        group["minutes"].append(int(item.get("minute") or 0))
        group["players"].extend(item.get("player_names") or [])
        group["polarities"].append(item.get("polarity") or "neutral")
        group["priorities"].append(item.get("priority") or "medium")
        group["ids"].append(str(item.get("client_id") or item.get("id")))
        if item.get("original_text") and item["original_text"] not in group["examples"]:
            group["examples"].append(item["original_text"])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("SELECT topic, zone, status FROM voice_coach_match_themes WHERE user_id = ? AND match_key = ?"), (user_id, match_key))
    statuses = {(row["topic"], row["zone"]): row["status"] for row in fetchall(cur)}
    cur.execute(q("DELETE FROM voice_coach_match_themes WHERE user_id = ? AND match_key = ?"), (user_id, match_key))
    now = utc_now()
    for group in grouped.values():
        priorities = group["priorities"]
        highest = max(priorities, key=lambda value: PRIORITY_ORDER.get(value, 1)) if priorities else "medium"
        polarity = max(set(group["polarities"]), key=group["polarities"].count) if group["polarities"] else "neutral"
        values = (
            user_id, knowledge_id, match_key, group["topic"], group["label"], group["zone"], len(group["ids"]),
            min(group["minutes"]), max(group["minutes"]), _dump(list(dict.fromkeys(group["players"]))), polarity,
            highest, _dump(group["ids"]), _dump(group["examples"][:6]), statuses.get((group["topic"], group["zone"]), "active"), now, now,
        )
        cur.execute(q("""INSERT INTO voice_coach_match_themes
            (user_id, knowledge_id, match_key, topic, label, zone, count, first_minute, last_minute,
             involved_players, polarity, highest_priority, source_observation_ids, examples, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""), values)
    conn.commit()
    conn.close()
    return list_themes(user_id, match_key)


def list_themes(user_id: int, match_key: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("SELECT * FROM voice_coach_match_themes WHERE user_id = ? AND match_key = ? ORDER BY count DESC, last_minute DESC"), (user_id, match_key))
    rows = fetchall(cur)
    conn.close()
    return [_decode(row) for row in rows]


def set_theme_status(user_id: int, match_key: str, theme_id: int, status: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("UPDATE voice_coach_match_themes SET status = ?, updated_at = ? WHERE id = ? AND user_id = ? AND match_key = ?"), (status, utc_now(), theme_id, user_id, match_key))
    conn.commit()
    cur.execute(q("SELECT * FROM voice_coach_match_themes WHERE id = ? AND user_id = ? AND match_key = ?"), (theme_id, user_id, match_key))
    row = fetchone(cur)
    conn.close()
    return _decode(row)


def delete_match_intelligence(user_id: int, match_key: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("SELECT client_id, knowledge_id FROM voice_coach_observations WHERE user_id = ? AND match_key = ?"), (user_id, match_key))
    links = fetchall(cur)
    cur.execute(q("DELETE FROM voice_coach_match_themes WHERE user_id = ? AND match_key = ?"), (user_id, match_key))
    cur.execute(q("DELETE FROM voice_coach_observations WHERE user_id = ? AND match_key = ?"), (user_id, match_key))
    conn.commit()
    conn.close()
    return links
