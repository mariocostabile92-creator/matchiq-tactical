import json
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, q


def _id_definition() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_match_evidence_schema() -> None:
    conn = get_connection()
    cur = conn.cursor()
    ident = _id_definition()
    cur.execute(
        f"""CREATE TABLE IF NOT EXISTS match_evidence (
          id {ident},
          canonical_match_id TEXT NOT NULL,
          schema_version INTEGER NOT NULL,
          source_match_id TEXT NOT NULL,
          user_id INTEGER NOT NULL,
          team_id TEXT,
          season_id TEXT,
          competition TEXT,
          opponent TEXT,
          match_date TEXT,
          match_data TEXT NOT NULL,
          coach_data TEXT NOT NULL,
          voice_references TEXT NOT NULL,
          video_references TEXT NOT NULL,
          metadata TEXT NOT NULL,
          created_at TEXT NOT NULL,
          finalized_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          UNIQUE(user_id, source_match_id),
          UNIQUE(user_id, canonical_match_id)
        )"""
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_match_evidence_user_updated "
        "ON match_evidence(user_id,updated_at)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_match_evidence_team_season "
        "ON match_evidence(user_id,team_id,season_id,match_date)"
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
    data["match"] = _loads(data.pop("match_data", None), {})
    data["coach"] = _loads(data.pop("coach_data", None), {})
    data["voice_coach"] = _loads(data.pop("voice_references", None), {"observation_ids": []})
    data["video_ai"] = _loads(
        data.pop("video_references", None),
        {"video_report_ids": [], "reviewed_frame_ids": []},
    )
    data["metadata"] = _loads(data.get("metadata"), {})
    data.pop("id", None)
    return data


def get_by_source(user_id: int, source_match_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        q("SELECT * FROM match_evidence WHERE user_id=? AND source_match_id=?"),
        (user_id, source_match_id),
    )
    row = fetchone(cur)
    conn.close()
    return _decode(row)


def get_by_canonical_id(user_id: int, canonical_match_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        q("SELECT * FROM match_evidence WHERE user_id=? AND canonical_match_id=?"),
        (user_id, canonical_match_id),
    )
    row = fetchone(cur)
    conn.close()
    return _decode(row)


def list_for_user(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        q("SELECT * FROM match_evidence WHERE user_id=? ORDER BY updated_at DESC,id DESC LIMIT ?"),
        (user_id, limit),
    )
    rows = [_decode(row) for row in fetchall(cur)]
    conn.close()
    return rows


def upsert(
    *,
    user_id: int,
    canonical_match_id: str,
    evidence: Dict[str, Any],
    created_at: str,
    finalized_at: str,
    updated_at: str,
) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        q(
            """INSERT INTO match_evidence (
              canonical_match_id,schema_version,source_match_id,user_id,team_id,season_id,
              competition,opponent,match_date,match_data,coach_data,voice_references,
              video_references,metadata,created_at,finalized_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id,source_match_id) DO UPDATE SET
              canonical_match_id=excluded.canonical_match_id,
              schema_version=excluded.schema_version,
              team_id=excluded.team_id,
              season_id=excluded.season_id,
              competition=excluded.competition,
              opponent=excluded.opponent,
              match_date=excluded.match_date,
              match_data=excluded.match_data,
              coach_data=excluded.coach_data,
              voice_references=excluded.voice_references,
              video_references=excluded.video_references,
              metadata=excluded.metadata,
              finalized_at=excluded.finalized_at,
              updated_at=excluded.updated_at"""
        ),
        (
            canonical_match_id,
            evidence["schema_version"],
            evidence["source_match_id"],
            user_id,
            evidence.get("team_id"),
            evidence.get("season_id"),
            evidence.get("competition"),
            evidence.get("opponent"),
            evidence.get("match_date"),
            json.dumps(evidence["match"], ensure_ascii=False, default=str),
            json.dumps(evidence["coach"], ensure_ascii=False, default=str),
            json.dumps(evidence["voice_coach"], ensure_ascii=False, default=str),
            json.dumps(evidence["video_ai"], ensure_ascii=False, default=str),
            json.dumps(evidence["metadata"], ensure_ascii=False, default=str),
            created_at,
            finalized_at,
            updated_at,
        ),
    )
    conn.commit()
    conn.close()
    return get_by_source(user_id, evidence["source_match_id"])
