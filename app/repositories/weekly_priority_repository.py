import json
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, q, utc_now


JSON_FIELDS = {
    "canonical_match_ids",
    "pattern_ids",
    "evidence_ids",
    "reason",
    "evidence_references",
}


def _id_definition() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_weekly_priority_schema() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""CREATE TABLE IF NOT EXISTS weekly_priorities (
          id {_id_definition()},
          priority_id TEXT NOT NULL,
          user_id INTEGER NOT NULL,
          workspace_id INTEGER NOT NULL,
          week_key TEXT NOT NULL,
          source_key TEXT NOT NULL,
          source_fingerprint TEXT NOT NULL,
          canonical_match_ids TEXT NOT NULL,
          pattern_ids TEXT NOT NULL,
          evidence_ids TEXT NOT NULL,
          topic TEXT NOT NULL,
          phase TEXT NOT NULL,
          priority_level TEXT NOT NULL,
          confidence REAL NOT NULL,
          ranking_score REAL NOT NULL,
          reason TEXT NOT NULL,
          evidence_references TEXT NOT NULL,
          status TEXT NOT NULL,
          staff_status TEXT,
          staff_reason TEXT,
          staff_updated_at TEXT,
          staff_updated_by INTEGER,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(user_id, priority_id),
          UNIQUE(user_id, week_key, source_key),
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE
        )"""
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_weekly_priorities_user_week "
        "ON weekly_priorities(user_id,week_key,ranking_score)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_weekly_priorities_status "
        "ON weekly_priorities(user_id,status,updated_at)"
    )
    conn.commit()
    conn.close()


def _loads(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
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
        fallback = {} if field in {"reason", "evidence_references"} else []
        data[field] = _loads(data.get(field), fallback)
    data["references"] = data.pop("evidence_references", {})
    data.pop("id", None)
    data.pop("source_key", None)
    data.pop("source_fingerprint", None)
    data.pop("user_id", None)
    data.pop("workspace_id", None)
    data.pop("week_key", None)
    return data


def get_by_priority_id(user_id: int, priority_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        q("SELECT * FROM weekly_priorities WHERE user_id=? AND priority_id=?"),
        (user_id, priority_id),
    )
    row = fetchone(cur)
    conn.close()
    return _decode(row)


def list_for_week(
    user_id: int,
    week_key: str,
    *,
    include_dismissed: bool = False,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    clauses = ["user_id=?", "week_key=?"]
    params: List[Any] = [user_id, week_key]
    if not include_dismissed:
        clauses.append("status<>'DISMISSED'")
    params.append(max(1, min(100, int(limit))))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        q(
            f"SELECT * FROM weekly_priorities WHERE {' AND '.join(clauses)} "
            "ORDER BY ranking_score DESC,confidence DESC,priority_id LIMIT ?"
        ),
        params,
    )
    rows = [_decode(row) for row in fetchall(cur)]
    conn.close()
    return rows


def list_latest(
    user_id: int,
    *,
    include_dismissed: bool = False,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        q("SELECT MAX(week_key) AS week_key FROM weekly_priorities WHERE user_id=?"),
        (user_id,),
    )
    week_key = (fetchone(cur) or {}).get("week_key")
    conn.close()
    if not week_key:
        return []
    return list_for_week(
        user_id,
        str(week_key),
        include_dismissed=include_dismissed,
        limit=limit,
    )


def upsert_generated(
    *,
    user_id: int,
    workspace_id: int,
    week_key: str,
    item: Dict[str, Any],
) -> Dict[str, Any]:
    now = utc_now()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        q(
            "SELECT * FROM weekly_priorities "
            "WHERE user_id=? AND week_key=? AND source_key=?"
        ),
        (user_id, week_key, item["source_key"]),
    )
    existing = fetchone(cur)
    existing_data = dict(existing) if existing else None

    status = str((existing_data or {}).get("status") or "PROPOSED")
    topic = item["topic"]
    phase = item["phase"]
    priority_level = item["priority_level"]
    reason = item["reason"]
    if status == "MODIFIED" and existing_data:
        topic = existing_data["topic"]
        phase = existing_data["phase"]
        priority_level = existing_data["priority_level"]
        reason = _loads(existing_data.get("reason"), item["reason"])

    encoded = {
        field: json.dumps(item[field], ensure_ascii=False, sort_keys=True)
        for field in (
            "canonical_match_ids",
            "pattern_ids",
            "evidence_ids",
            "references",
        )
    }
    encoded_reason = json.dumps(reason, ensure_ascii=False, sort_keys=True)

    if existing_data:
        cur.execute(
            q(
                """UPDATE weekly_priorities SET
                  source_fingerprint=?,canonical_match_ids=?,pattern_ids=?,
                  evidence_ids=?,topic=?,phase=?,priority_level=?,confidence=?,
                  ranking_score=?,reason=?,evidence_references=?,updated_at=?
                WHERE id=? AND user_id=?"""
            ),
            (
                item["source_fingerprint"],
                encoded["canonical_match_ids"],
                encoded["pattern_ids"],
                encoded["evidence_ids"],
                topic,
                phase,
                priority_level,
                item["confidence"],
                item["ranking_score"],
                encoded_reason,
                encoded["references"],
                now,
                existing_data["id"],
                user_id,
            ),
        )
    else:
        cur.execute(
            q(
                """INSERT INTO weekly_priorities (
                  priority_id,user_id,workspace_id,week_key,source_key,
                  source_fingerprint,canonical_match_ids,pattern_ids,evidence_ids,
                  topic,phase,priority_level,confidence,ranking_score,reason,
                  evidence_references,status,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            ),
            (
                item["priority_id"],
                user_id,
                workspace_id,
                week_key,
                item["source_key"],
                item["source_fingerprint"],
                encoded["canonical_match_ids"],
                encoded["pattern_ids"],
                encoded["evidence_ids"],
                topic,
                phase,
                priority_level,
                item["confidence"],
                item["ranking_score"],
                encoded_reason,
                encoded["references"],
                "PROPOSED",
                now,
                now,
            ),
        )
    conn.commit()
    conn.close()
    return get_by_priority_id(user_id, item["priority_id"])


def update_staff_status(
    user_id: int,
    priority_id: str,
    *,
    status: str,
    staff_reason: Optional[str],
    topic: Optional[str],
    phase: Optional[str],
    priority_level: Optional[str],
    staff_user_id: int,
) -> Optional[Dict[str, Any]]:
    fields = [
        "status=?",
        "staff_status=?",
        "staff_reason=?",
        "staff_updated_at=?",
        "staff_updated_by=?",
        "updated_at=?",
    ]
    now = utc_now()
    params: List[Any] = [
        status,
        status,
        staff_reason,
        now,
        staff_user_id,
        now,
    ]
    if status == "MODIFIED":
        if topic is not None:
            fields.append("topic=?")
            params.append(topic)
        if phase is not None:
            fields.append("phase=?")
            params.append(phase)
        if priority_level is not None:
            fields.append("priority_level=?")
            params.append(priority_level)
    params.extend([user_id, priority_id])
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        q(
            f"UPDATE weekly_priorities SET {','.join(fields)} "
            "WHERE user_id=? AND priority_id=?"
        ),
        params,
    )
    conn.commit()
    changed = bool(cur.rowcount)
    conn.close()
    return get_by_priority_id(user_id, priority_id) if changed else None
