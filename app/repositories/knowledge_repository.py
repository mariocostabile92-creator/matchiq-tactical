import json
from typing import Any, Dict, Iterable, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now


COACH_COLUMNS = {
    "coach_name",
    "playing_philosophy",
    "preferred_formation",
    "alternative_formation",
    "pressing",
    "buildup",
    "offensive_style",
    "defensive_style",
    "tactical_principles",
    "transition_management",
    "set_piece_preferences",
    "personal_notes",
}

TEAM_COLUMNS = {
    "category",
    "average_age",
    "player_count",
    "goalkeeper_count",
    "strengths",
    "weaknesses",
    "formations_used",
    "playing_principles",
    "average_availability",
    "physical_level",
    "technical_level",
    "season_objectives",
    "notes",
}

ROSTER_COLUMNS = {
    "external_player_id",
    "name",
    "role",
    "preferred_foot",
    "characteristics",
    "speed",
    "strength",
    "technique",
    "personality",
    "leadership",
    "adaptability",
    "secondary_roles",
    "coach_notes",
}

JSON_COLUMNS = {
    "tactical_principles",
    "set_piece_preferences",
    "strengths",
    "weaknesses",
    "formations_used",
    "playing_principles",
    "season_objectives",
    "characteristics",
    "secondary_roles",
    "metadata",
}


def _id_definition() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_knowledge_schema() -> None:
    conn = get_connection()
    cur = conn.cursor()
    id_column = _id_definition()

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS knowledge_workspaces (
            id {id_column},
            user_id INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS knowledge_coach_profiles (
            id {id_column},
            knowledge_id INTEGER NOT NULL UNIQUE,
            coach_name TEXT,
            playing_philosophy TEXT,
            preferred_formation TEXT,
            alternative_formation TEXT,
            pressing TEXT,
            buildup TEXT,
            offensive_style TEXT,
            defensive_style TEXT,
            tactical_principles TEXT,
            transition_management TEXT,
            set_piece_preferences TEXT,
            personal_notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(knowledge_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS knowledge_team_profiles (
            id {id_column},
            knowledge_id INTEGER NOT NULL UNIQUE,
            category TEXT,
            average_age REAL,
            player_count INTEGER,
            goalkeeper_count INTEGER,
            strengths TEXT,
            weaknesses TEXT,
            formations_used TEXT,
            playing_principles TEXT,
            average_availability REAL,
            physical_level TEXT,
            technical_level TEXT,
            season_objectives TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(knowledge_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS knowledge_roster_players (
            id {id_column},
            knowledge_id INTEGER NOT NULL,
            external_player_id TEXT,
            name TEXT NOT NULL,
            role TEXT,
            preferred_foot TEXT,
            characteristics TEXT,
            speed INTEGER,
            strength INTEGER,
            technique INTEGER,
            personality TEXT,
            leadership INTEGER,
            adaptability INTEGER,
            secondary_roles TEXT,
            coach_notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(knowledge_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS knowledge_source_links (
            id {id_column},
            knowledge_id INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(knowledge_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_roster_workspace ON knowledge_roster_players(knowledge_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_source_workspace ON knowledge_source_links(knowledge_id, source_type)")
    conn.commit()
    conn.close()


def _json_dump(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _json_load(value: Any, fallback: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _serialize_fields(data: Dict[str, Any], allowed: Iterable[str]) -> Dict[str, Any]:
    result = {key: value for key, value in data.items() if key in allowed}
    for key in JSON_COLUMNS.intersection(result):
        result[key] = _json_dump(result[key])
    return result


def _deserialize_row(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    result = dict(row or {})
    for key in JSON_COLUMNS.intersection(result):
        result[key] = _json_load(result.get(key), {} if key == "metadata" else [])
    return result


def get_or_create_workspace(user_id: int) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("SELECT * FROM knowledge_workspaces WHERE user_id = ?"), (user_id,))
    row = fetchone(cur)
    if row:
        conn.close()
        return row

    now = utc_now()
    if USE_POSTGRES:
        cur.execute(
            "INSERT INTO knowledge_workspaces (user_id, created_at, updated_at) VALUES (%s, %s, %s) ON CONFLICT(user_id) DO NOTHING",
            (user_id, now, now),
        )
    else:
        cur.execute(
            "INSERT OR IGNORE INTO knowledge_workspaces (user_id, created_at, updated_at) VALUES (?, ?, ?)",
            (user_id, now, now),
        )
    conn.commit()
    cur.execute(q("SELECT * FROM knowledge_workspaces WHERE user_id = ?"), (user_id,))
    row = fetchone(cur)
    conn.close()
    return row


def _empty_profile(table: str, knowledge_id: int, columns: Iterable[str]) -> Dict[str, Any]:
    profile = {column: [] if column in JSON_COLUMNS else None for column in columns}
    profile.update({"knowledge_id": knowledge_id, "updated_at": None})
    return profile


def get_profile(table: str, knowledge_id: int, columns: Iterable[str]) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q(f"SELECT * FROM {table} WHERE knowledge_id = ?"), (knowledge_id,))
    row = fetchone(cur)
    conn.close()
    return _deserialize_row(row) if row else _empty_profile(table, knowledge_id, columns)


def upsert_profile(table: str, knowledge_id: int, data: Dict[str, Any], allowed: Iterable[str]) -> Dict[str, Any]:
    payload = _serialize_fields(data, allowed)
    now = utc_now()
    columns = ["knowledge_id", *payload.keys(), "updated_at"]
    values = [knowledge_id, *payload.values(), now]
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{column} = excluded.{column}" for column in [*payload.keys(), "updated_at"])
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT(knowledge_id) DO UPDATE SET {updates}"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q(sql), values)
    cur.execute(q("UPDATE knowledge_workspaces SET updated_at = ? WHERE id = ?"), (now, knowledge_id))
    conn.commit()
    conn.close()
    return get_profile(table, knowledge_id, allowed)


def list_roster(knowledge_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("SELECT * FROM knowledge_roster_players WHERE knowledge_id = ? ORDER BY name, id"), (knowledge_id,))
    rows = fetchall(cur)
    conn.close()
    return [_deserialize_row(row) for row in rows]


def create_roster_player(knowledge_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    payload = _serialize_fields(data, ROSTER_COLUMNS)
    now = utc_now()
    columns = ["knowledge_id", *payload.keys(), "created_at", "updated_at"]
    values = [knowledge_id, *payload.values(), now, now]
    placeholders = ", ".join("?" for _ in columns)
    returning = " RETURNING id" if USE_POSTGRES else ""

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q(f"INSERT INTO knowledge_roster_players ({', '.join(columns)}) VALUES ({placeholders}){returning}"), values)
    player_id = get_last_insert_id(cur)
    cur.execute(q("UPDATE knowledge_workspaces SET updated_at = ? WHERE id = ?"), (now, knowledge_id))
    conn.commit()
    cur.execute(q("SELECT * FROM knowledge_roster_players WHERE id = ? AND knowledge_id = ?"), (player_id, knowledge_id))
    row = fetchone(cur)
    conn.close()
    return _deserialize_row(row)


def update_roster_player(knowledge_id: int, player_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    payload = _serialize_fields(data, ROSTER_COLUMNS)
    now = utc_now()
    assignments = ", ".join(f"{column} = ?" for column in payload)
    values = [*payload.values(), now, player_id, knowledge_id]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q(f"UPDATE knowledge_roster_players SET {assignments}, updated_at = ? WHERE id = ? AND knowledge_id = ?"), values)
    changed = cur.rowcount
    if changed:
        cur.execute(q("UPDATE knowledge_workspaces SET updated_at = ? WHERE id = ?"), (now, knowledge_id))
    conn.commit()
    cur.execute(q("SELECT * FROM knowledge_roster_players WHERE id = ? AND knowledge_id = ?"), (player_id, knowledge_id))
    row = fetchone(cur)
    conn.close()
    return _deserialize_row(row) if row else None


def delete_roster_player(knowledge_id: int, player_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("DELETE FROM knowledge_roster_players WHERE id = ? AND knowledge_id = ?"), (player_id, knowledge_id))
    deleted = cur.rowcount > 0
    if deleted:
        cur.execute(q("UPDATE knowledge_workspaces SET updated_at = ? WHERE id = ?"), (utc_now(), knowledge_id))
    conn.commit()
    conn.close()
    return deleted


def list_source_links(knowledge_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(q("SELECT * FROM knowledge_source_links WHERE knowledge_id = ? ORDER BY created_at, id"), (knowledge_id,))
    rows = fetchall(cur)
    conn.close()
    return [_deserialize_row(row) for row in rows]
