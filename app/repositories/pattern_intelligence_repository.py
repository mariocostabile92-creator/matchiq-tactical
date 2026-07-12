import json
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now


JSON_FIELDS = {"sources_analyzed", "limitations", "source_classes", "metadata"}


def _id_definition() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_pattern_schema() -> None:
    conn = get_connection()
    cur = conn.cursor()
    ident = _id_definition()
    cur.execute(f"""CREATE TABLE IF NOT EXISTS pattern_intelligence_runs (
        id {ident}, workspace_id INTEGER NOT NULL, user_id INTEGER NOT NULL, team_profile_id INTEGER,
        period_start TEXT NOT NULL, period_end TEXT NOT NULL, matches_analyzed INTEGER NOT NULL DEFAULT 0,
        sources_analyzed TEXT NOT NULL, source_fingerprint TEXT NOT NULL, status TEXT NOT NULL,
        started_at TEXT NOT NULL, completed_at TEXT, algorithm_version TEXT NOT NULL, error_code TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS pattern_intelligence_patterns (
        id {ident}, run_id INTEGER NOT NULL, workspace_id INTEGER NOT NULL, team_profile_id INTEGER,
        canonical_topic TEXT NOT NULL, title TEXT NOT NULL, normalized_summary TEXT NOT NULL,
        category TEXT NOT NULL, polarity TEXT NOT NULL, zone TEXT NOT NULL, phase TEXT NOT NULL, context_player_id TEXT,
        frequency_count INTEGER NOT NULL, matches_count INTEGER NOT NULL, matches_total INTEGER NOT NULL,
        occurrence_rate REAL NOT NULL, first_seen_at TEXT, last_seen_at TEXT, trend_direction TEXT NOT NULL,
        confidence_score INTEGER NOT NULL, confidence_level TEXT NOT NULL, severity TEXT NOT NULL,
        status TEXT NOT NULL, validation_state TEXT NOT NULL, explanation TEXT NOT NULL,
        limitations TEXT NOT NULL, source_classes TEXT NOT NULL, contradictory INTEGER NOT NULL DEFAULT 0,
        staff_note TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        FOREIGN KEY(run_id) REFERENCES pattern_intelligence_runs(id) ON DELETE CASCADE,
        FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE
    )""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS pattern_intelligence_evidence (
        id {ident}, pattern_id INTEGER NOT NULL, source_type TEXT NOT NULL, source_id TEXT NOT NULL,
        match_id TEXT NOT NULL, minute INTEGER, event_type TEXT, player_id TEXT, topic TEXT NOT NULL,
        zone TEXT, phase TEXT, formation TEXT, polarity TEXT, evidence_summary TEXT NOT NULL, evidence_weight REAL NOT NULL,
        objective_or_subjective TEXT NOT NULL, created_at TEXT NOT NULL,
        UNIQUE(pattern_id, source_type, source_id),
        FOREIGN KEY(pattern_id) REFERENCES pattern_intelligence_patterns(id) ON DELETE CASCADE
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pattern_runs_workspace_period ON pattern_intelligence_runs(workspace_id, period_end, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pattern_runs_fingerprint ON pattern_intelligence_runs(user_id, source_fingerprint)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_patterns_workspace_topic ON pattern_intelligence_patterns(workspace_id, canonical_topic, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_patterns_team_period ON pattern_intelligence_patterns(team_profile_id, first_seen_at, last_seen_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pattern_evidence_match ON pattern_intelligence_evidence(pattern_id, match_id, topic)")
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
        if field in data:
            data[field] = _loads(data[field], [] if field in {"sources_analyzed", "limitations"} else {})
    if "contradictory" in data:
        data["contradictory"] = bool(data["contradictory"])
    return data


def latest_run(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection(); cur = conn.cursor()
    cur.execute(q("SELECT * FROM pattern_intelligence_runs WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 1"), (user_id,))
    row = fetchone(cur); conn.close()
    return _decode(row)


def create_run(user_id: int, workspace_id: int, team_profile_id: Optional[int], period_start: str, period_end: str, matches: int, sources: list, fingerprint: str, algorithm: str) -> Dict[str, Any]:
    now = utc_now(); returning = " RETURNING id" if USE_POSTGRES else ""
    conn = get_connection(); cur = conn.cursor()
    cur.execute(q(f"""INSERT INTO pattern_intelligence_runs
        (workspace_id,user_id,team_profile_id,period_start,period_end,matches_analyzed,sources_analyzed,source_fingerprint,status,started_at,completed_at,algorithm_version,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?){returning}"""),
        (workspace_id,user_id,team_profile_id,period_start,period_end,matches,json.dumps(sources,ensure_ascii=False),fingerprint,"completed",now,now,algorithm,now,now))
    run_id = get_last_insert_id(cur); conn.commit()
    cur.execute(q("SELECT * FROM pattern_intelligence_runs WHERE id = ? AND user_id = ?"), (run_id,user_id)); row=fetchone(cur); conn.close()
    return _decode(row)


def prior_states(user_id: int) -> Dict[str, Dict[str, Any]]:
    run = latest_run(user_id)
    if not run:
        return {}
    conn=get_connection(); cur=conn.cursor()
    cur.execute(q("SELECT canonical_topic,phase,zone,context_player_id,status,validation_state,staff_note FROM pattern_intelligence_patterns WHERE run_id = ?"), (run["id"],))
    rows=fetchall(cur); conn.close()
    return {f"{row['canonical_topic']}|{row['phase']}|{row['zone']}|{row.get('context_player_id') or ''}":dict(row) for row in rows}


def save_patterns(run: Dict[str, Any], patterns: List[Dict[str, Any]], previous: Dict[str, Dict[str, Any]]) -> None:
    now=utc_now(); conn=get_connection(); cur=conn.cursor()
    for item in patterns:
        key=f"{item['canonical_topic']}|{item['phase']}|{item['zone']}|{item.get('context_player_id') or ''}"; old=previous.get(key) or {}
        status=old.get("status") if old.get("status") in {"confirmed_by_staff","dismissed_by_staff","resolved","archived","monitoring"} else item["status"]
        validation=old.get("validation_state") or "ai_candidate"
        values=(run["id"],run["workspace_id"],run.get("team_profile_id"),item["canonical_topic"],item["title"],item["normalized_summary"],item["category"],item["polarity"],item["zone"],item["phase"],item.get("context_player_id"),item["frequency_count"],item["matches_count"],item["matches_total"],item["occurrence_rate"],item.get("first_seen_at"),item.get("last_seen_at"),item["trend_direction"],item["confidence_score"],item["confidence_level"],item["severity"],status,validation,item["explanation"],json.dumps(item["limitations"],ensure_ascii=False),json.dumps(item["source_classes"],ensure_ascii=False),1 if item["contradictory"] else 0,old.get("staff_note"),now,now)
        returning=" RETURNING id" if USE_POSTGRES else ""
        cur.execute(q(f"""INSERT INTO pattern_intelligence_patterns
          (run_id,workspace_id,team_profile_id,canonical_topic,title,normalized_summary,category,polarity,zone,phase,context_player_id,frequency_count,matches_count,matches_total,occurrence_rate,first_seen_at,last_seen_at,trend_direction,confidence_score,confidence_level,severity,status,validation_state,explanation,limitations,source_classes,contradictory,staff_note,created_at,updated_at)
          VALUES ({','.join('?' for _ in range(30))}){returning}"""),values)
        pattern_id=get_last_insert_id(cur)
        for evidence in item["evidence"]:
            cur.execute(q("""INSERT INTO pattern_intelligence_evidence
              (pattern_id,source_type,source_id,match_id,minute,event_type,player_id,topic,zone,phase,formation,polarity,evidence_summary,evidence_weight,objective_or_subjective,created_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(pattern_id,source_type,source_id) DO NOTHING"""),
              (pattern_id,evidence["source_type"],evidence["source_id"],evidence["match_id"],evidence.get("minute"),evidence.get("event_type"),evidence.get("player_id"),evidence["topic"],evidence.get("zone"),evidence.get("phase"),evidence.get("formation"),evidence.get("polarity"),evidence["evidence_summary"],evidence["evidence_weight"],evidence["objective_or_subjective"],evidence.get("created_at") or now))
    conn.commit(); conn.close()


def list_patterns(user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
    run=latest_run(user_id)
    if not run:
        return {"run":None,"items":[],"total":0,"page":filters.get("page",1),"page_size":filters.get("page_size",12)}
    clauses=["p.run_id = ?", "r.user_id = ?"]; params=[run["id"],user_id]
    for field in ("category","polarity","status"):
        if filters.get(field): clauses.append(f"p.{field} = ?"); params.append(filters[field])
    if filters.get("topic"): clauses.append("p.canonical_topic = ?"); params.append(filters["topic"])
    if filters.get("confidence"): clauses.append("p.confidence_level = ?"); params.append(filters["confidence"])
    if filters.get("source"): clauses.append("p.source_classes LIKE ?"); params.append(f"%{filters['source']}%")
    where=" AND ".join(clauses); page=max(1,int(filters.get("page") or 1)); size=max(1,min(50,int(filters.get("page_size") or 12)))
    conn=get_connection(); cur=conn.cursor()
    cur.execute(q(f"SELECT COUNT(*) AS total FROM pattern_intelligence_patterns p JOIN pattern_intelligence_runs r ON r.id=p.run_id WHERE {where}"),params); total=int((fetchone(cur) or {}).get("total") or 0)
    cur.execute(q(f"SELECT p.* FROM pattern_intelligence_patterns p JOIN pattern_intelligence_runs r ON r.id=p.run_id WHERE {where} ORDER BY p.confidence_score DESC,p.matches_count DESC,p.id LIMIT ? OFFSET ?"),(*params,size,(page-1)*size))
    rows=[_decode(row) for row in fetchall(cur)]; conn.close()
    return {"run":run,"items":rows,"total":total,"page":page,"page_size":size}


def get_pattern(user_id: int, pattern_id: int, evidence_page: int=1, evidence_size: int=20) -> Optional[Dict[str, Any]]:
    conn=get_connection(); cur=conn.cursor()
    cur.execute(q("""SELECT p.* FROM pattern_intelligence_patterns p JOIN pattern_intelligence_runs r ON r.id=p.run_id
      WHERE p.id=? AND r.user_id=?"""),(pattern_id,user_id)); pattern=_decode(fetchone(cur))
    if not pattern: conn.close(); return None
    cur.execute(q("SELECT COUNT(*) AS total FROM pattern_intelligence_evidence WHERE pattern_id=?"),(pattern_id,)); total=int((fetchone(cur) or {}).get("total") or 0)
    cur.execute(q("SELECT * FROM pattern_intelligence_evidence WHERE pattern_id=? ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?"),(pattern_id,evidence_size,(evidence_page-1)*evidence_size)); evidence=[dict(row) for row in fetchall(cur)]; conn.close()
    pattern["evidence"]={"items":evidence,"total":total,"page":evidence_page,"page_size":evidence_size}
    return pattern


def update_pattern(user_id: int, pattern_id: int, status: Optional[str]=None, note: Optional[str]=None) -> Optional[Dict[str, Any]]:
    fields=[]; params=[]
    if status is not None: fields.extend(["status = ?","validation_state = ?"]); params.extend([status,"staff_reviewed"])
    if note is not None: fields.append("staff_note = ?"); params.append(note)
    fields.append("updated_at = ?"); params.append(utc_now()); params.extend([pattern_id,user_id])
    conn=get_connection(); cur=conn.cursor()
    cur.execute(q(f"""UPDATE pattern_intelligence_patterns SET {','.join(fields)} WHERE id=? AND run_id IN
      (SELECT id FROM pattern_intelligence_runs WHERE user_id=?)"""),params); conn.commit(); conn.close()
    return get_pattern(user_id,pattern_id)


def summary(user_id: int) -> Dict[str, Any]:
    data=list_patterns(user_id,{"page":1,"page_size":50}); items=data["items"]
    return {"run":data["run"],"established":sum(1 for x in items if x["status"] in {"established","confirmed_by_staff"}),"emerging":sum(1 for x in items if x["status"] in {"candidate","monitoring"}),"positive":sum(1 for x in items if x["polarity"]=="positive"),"resolved":sum(1 for x in items if x["status"]=="resolved"),"top":items[:3]}


def latest_weekly_patterns(user_id: int, limit: int=5) -> List[Dict[str, Any]]:
    data=list_patterns(user_id,{"page":1,"page_size":50})
    allowed={"established","confirmed_by_staff","monitoring"}
    return [item for item in data["items"] if item["status"] in allowed and item["confidence_score"]>=55][:limit]


def team_profile_belongs(workspace_id: int, team_profile_id: int) -> bool:
    conn=get_connection(); cur=conn.cursor()
    cur.execute(q("SELECT id FROM knowledge_team_profiles WHERE id=? AND knowledge_id=?"),(team_profile_id,workspace_id))
    found=bool(fetchone(cur)); conn.close()
    return found
