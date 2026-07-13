import json
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now


JSON_FIELDS = {
    "source_context_json", "limitations_json", "tactical_changes_json", "player_changes_json",
    "formation_changes_json", "benefits_json", "risks_json", "prerequisites_json", "evidence_json", "metadata_json",
}


def _dump(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True, default=str)


def _load(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)): return value
    try: return json.loads(value) if value else fallback
    except (TypeError, ValueError): return fallback


def _decode(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row: return None
    item = dict(row)
    for field in JSON_FIELDS:
        if field in item: item[field] = _load(item[field], [] if field.endswith("s_json") or field in {"limitations_json", "benefits_json", "risks_json", "prerequisites_json"} else {})
    if "executed_manually" in item: item["executed_manually"] = bool(item["executed_manually"])
    return item


def get_case(workspace_id: int, user_id: int, case_id: int) -> Optional[Dict[str, Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM decision_engine_cases WHERE id=? AND workspace_id=? AND user_id=?"),(case_id,workspace_id,user_id)); row=fetchone(cur); conn.close(); return _decode(row)


def get_case_by_fingerprint(workspace_id: int,user_id: int,fingerprint: str) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM decision_engine_cases WHERE workspace_id=? AND user_id=? AND source_fingerprint=?"),(workspace_id,user_id,fingerprint)); row=fetchone(cur); conn.close(); return _decode(row)


def create_case(workspace_id: int,user_id: int,payload: Dict[str,Any]) -> Dict[str,Any]:
    now=utc_now(); returning=" RETURNING id" if USE_POSTGRES else ""; conn=get_connection(); cur=conn.cursor()
    values=(workspace_id,user_id,payload.get("team_profile_id"),payload.get("match_id"),payload["phase"],payload.get("minute"),payload.get("score_state"),payload.get("prompt"),payload["situation_summary"],payload["status"],payload["evidence_state"],payload["source_fingerprint"],_dump(payload.get("source_context") or {}),_dump(payload.get("limitations") or []),now,now)
    cur.execute(q(f"""INSERT INTO decision_engine_cases(workspace_id,user_id,team_profile_id,match_id,phase,minute,score_state,prompt,situation_summary,status,evidence_state,source_fingerprint,source_context_json,limitations_json,created_at,updated_at) VALUES({','.join('?' for _ in range(16))}){returning}"""),values)
    case_id=get_last_insert_id(cur); conn.commit(); conn.close(); return get_case(workspace_id,user_id,case_id)


def replace_options(case_id: int,options: List[Dict[str,Any]],sources: List[Dict[str,Any]]) -> None:
    now=utc_now(); conn=get_connection(); cur=conn.cursor(); cur.execute(q("DELETE FROM decision_engine_options WHERE case_id=?"),(case_id,))
    for rank,item in enumerate(options,1):
        returning=" RETURNING id" if USE_POSTGRES else ""; values=(case_id,item["option_type"],item["title"],item["summary"],_dump(item.get("tactical_changes") or []),_dump(item.get("player_changes") or []),_dump(item.get("formation_changes") or []),_dump(item.get("benefits") or []),_dump(item.get("risks") or []),_dump(item.get("prerequisites") or []),item["confidence_level"],item["suitability_score"],item["identity_alignment"],item["evidence_summary"],_dump(item.get("limitations") or []),rank,item.get("status") or "proposed",now,now)
        cur.execute(q(f"""INSERT INTO decision_engine_options(case_id,option_type,title,summary,tactical_changes_json,player_changes_json,formation_changes_json,benefits_json,risks_json,prerequisites_json,confidence_level,suitability_score,identity_alignment,evidence_summary,limitations_json,rank_order,status,created_at,updated_at) VALUES({','.join('?' for _ in range(19))}){returning}"""),values)
        option_id=get_last_insert_id(cur)
        for source in sources[:12]:
            cur.execute(q("""INSERT INTO decision_engine_option_sources(option_id,knowledge_node_id,source_type,source_id,title,summary,reliability_level,relation_type,action_url,created_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(option_id,source_type,source_id) DO NOTHING"""),(option_id,source.get("id"),source["node_type"],str(source.get("source_id") or source.get("id")),source.get("title") or "Fonte MatchIQ",source.get("summary") or "",source.get("reliability_level") or "bassa","supported_by",source.get("action_url"),now))
    conn.commit(); conn.close()


def list_options(workspace_id: int,user_id: int,case_id: int) -> List[Dict[str,Any]]:
    if not get_case(workspace_id,user_id,case_id): return []
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM decision_engine_options WHERE case_id=? ORDER BY rank_order,id"),(case_id,)); items=[_decode(row) for row in fetchall(cur)]
    for item in items:
        cur.execute(q("SELECT * FROM decision_engine_option_sources WHERE option_id=? ORDER BY reliability_level DESC,id"),(item["id"],)); item["sources"]=[_decode(row) for row in fetchall(cur)]
    conn.close(); return items


def list_cases(workspace_id: int,user_id: int,page: int,page_size: int,phase: Optional[str]=None) -> Dict[str,Any]:
    where=["workspace_id=?","user_id=?"]; params=[workspace_id,user_id]
    if phase: where.append("phase=?"); params.append(phase)
    clause=" AND ".join(where); offset=(page-1)*page_size; conn=get_connection(); cur=conn.cursor(); cur.execute(q(f"SELECT COUNT(*) AS total FROM decision_engine_cases WHERE {clause}"),params); total=int(fetchone(cur)["total"] or 0); cur.execute(q(f"SELECT * FROM decision_engine_cases WHERE {clause} ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?"),[*params,page_size,offset]); items=[_decode(row) for row in fetchall(cur)]; conn.close(); return {"items":items,"total":total,"page":page,"page_size":page_size,"pages":max(1,(total+page_size-1)//page_size)}


def option_belongs(workspace_id: int,user_id: int,case_id: int,option_id: int) -> bool:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT o.id FROM decision_engine_options o JOIN decision_engine_cases c ON c.id=o.case_id WHERE o.id=? AND c.id=? AND c.workspace_id=? AND c.user_id=?"),(option_id,case_id,workspace_id,user_id)); row=fetchone(cur); conn.close(); return bool(row)


def add_staff_decision(workspace_id: int,user_id: int,case_id: int,payload: Dict[str,Any]) -> Optional[Dict[str,Any]]:
    if not get_case(workspace_id,user_id,case_id): return None
    if payload.get("option_id") and not option_belongs(workspace_id,user_id,case_id,int(payload["option_id"])): return None
    now=utc_now(); returning=" RETURNING id" if USE_POSTGRES else ""; conn=get_connection(); cur=conn.cursor(); cur.execute(q(f"INSERT INTO decision_engine_staff_decisions(case_id,option_id,user_id,action,note,executed_manually,execution_reference,created_at) VALUES(?,?,?,?,?,?,?,?){returning}"),(case_id,payload.get("option_id"),user_id,payload["action"],payload.get("note"),1 if payload.get("executed_manually") else 0,payload.get("execution_reference"),now)); item_id=get_last_insert_id(cur); cur.execute(q("UPDATE decision_engine_cases SET status=?,updated_at=? WHERE id=?"),("staff_reviewed",now,case_id)); conn.commit(); cur.execute(q("SELECT * FROM decision_engine_staff_decisions WHERE id=? AND user_id=?"),(item_id,user_id)); row=fetchone(cur); conn.close(); return _decode(row)


def list_staff_decisions(workspace_id: int,user_id: int,case_id: int) -> List[Dict[str,Any]]:
    if not get_case(workspace_id,user_id,case_id): return []
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM decision_engine_staff_decisions WHERE case_id=? AND user_id=? ORDER BY created_at DESC,id DESC"),(case_id,user_id)); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows


def add_outcome(workspace_id: int,user_id: int,case_id: int,decision_id: int,payload: Dict[str,Any]) -> Optional[Dict[str,Any]]:
    if not get_case(workspace_id,user_id,case_id): return None
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT id FROM decision_engine_staff_decisions WHERE id=? AND case_id=? AND user_id=?"),(decision_id,case_id,user_id)); owned=fetchone(cur)
    if not owned: conn.close(); return None
    now=utc_now(); returning=" RETURNING id" if USE_POSTGRES else ""; cur.execute(q(f"INSERT INTO decision_engine_outcomes(staff_decision_id,summary,evidence_json,relation_state,confidence_level,created_at) VALUES(?,?,?,?,?,?){returning}"),(decision_id,payload["summary"],_dump(payload.get("evidence") or {}),"observed_after_decision",payload.get("confidence") or "bassa",now)); item_id=get_last_insert_id(cur); conn.commit(); cur.execute(q("SELECT * FROM decision_engine_outcomes WHERE id=?"),(item_id,)); row=fetchone(cur); conn.close(); return _decode(row)


def outcomes(workspace_id: int,user_id: int,case_id: int) -> List[Dict[str,Any]]:
    if not get_case(workspace_id,user_id,case_id): return []
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("""SELECT o.* FROM decision_engine_outcomes o JOIN decision_engine_staff_decisions d ON d.id=o.staff_decision_id WHERE d.case_id=? AND d.user_id=? ORDER BY o.created_at DESC,o.id DESC"""),(case_id,user_id)); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows


def telemetry(workspace_id: int,user_id: int,case_id: Optional[int],event_type: str,duration_ms: int=0,source_count: int=0,option_count: int=0,metadata: Optional[Dict[str,Any]]=None) -> None:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("INSERT INTO decision_engine_telemetry(workspace_id,user_id,case_id,event_type,duration_ms,source_count,option_count,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)"),(workspace_id,user_id,case_id,event_type,duration_ms,source_count,option_count,_dump(metadata or {}),utc_now())); conn.commit(); conn.close()
