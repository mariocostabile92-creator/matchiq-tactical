import json
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now


JSON_FIELDS = {"context_scope_json", "context_summary_json", "structured_query_json", "limitations_json", "response_json"}


def _dump(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True, default=str)


def _decode(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row: return None
    item = dict(row)
    for key in JSON_FIELDS:
        if key in item:
            try: item[key] = json.loads(item[key] or "{}")
            except (TypeError, ValueError): item[key] = {} if key.endswith("_json") else []
    if "has_sufficient_evidence" in item: item["has_sufficient_evidence"] = bool(item["has_sufficient_evidence"])
    return item


def create_conversation(workspace_id: int, user_id: int, title: str, scope: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now(); returning = " RETURNING id" if USE_POSTGRES else ""; conn = get_connection(); cur = conn.cursor()
    cur.execute(q(f"""INSERT INTO tactical_assistant_conversations
      (workspace_id,user_id,team_profile_id,title,status,context_scope_json,context_summary_json,active_match_id,active_season,started_at,last_message_at,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?){returning}"""), (workspace_id,user_id,scope.get("team_profile_id"),title,"active",_dump(scope),_dump(scope),scope.get("match_id"),scope.get("season"),now,now,now,now))
    conversation_id = get_last_insert_id(cur); conn.commit(); conn.close(); return get_conversation(workspace_id,user_id,conversation_id)


def get_conversation(workspace_id: int, user_id: int, conversation_id: int) -> Optional[Dict[str, Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM tactical_assistant_conversations WHERE id=? AND workspace_id=? AND user_id=?"),(conversation_id,workspace_id,user_id)); row=fetchone(cur); conn.close(); return _decode(row)


def list_conversations(workspace_id: int, user_id: int, status: str=None, limit: int=50) -> List[Dict[str, Any]]:
    where="workspace_id=? AND user_id=?"; params=[workspace_id,user_id]
    if status: where+=" AND status=?"; params.append(status)
    conn=get_connection(); cur=conn.cursor(); cur.execute(q(f"SELECT * FROM tactical_assistant_conversations WHERE {where} ORDER BY updated_at DESC,id DESC LIMIT ?"),[*params,min(100,max(1,limit))]); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows


def update_conversation(workspace_id: int,user_id: int,conversation_id: int,**changes) -> Optional[Dict[str, Any]]:
    allowed={key:value for key,value in changes.items() if key in {"title","status","context_summary_json","context_scope_json","active_match_id","active_season"} and value is not None}
    if not allowed: return get_conversation(workspace_id,user_id,conversation_id)
    for key in ("context_summary_json","context_scope_json"):
        if key in allowed: allowed[key]=_dump(allowed[key])
    allowed["updated_at"]=utc_now(); conn=get_connection(); cur=conn.cursor(); cur.execute(q(f"UPDATE tactical_assistant_conversations SET {','.join(f'{k}=?' for k in allowed)} WHERE id=? AND workspace_id=? AND user_id=?"),[*allowed.values(),conversation_id,workspace_id,user_id]); conn.commit(); changed=cur.rowcount; conn.close(); return get_conversation(workspace_id,user_id,conversation_id) if changed else None


def delete_conversation(workspace_id: int,user_id: int,conversation_id: int) -> bool:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT id FROM tactical_assistant_conversations WHERE id=? AND workspace_id=? AND user_id=?"),(conversation_id,workspace_id,user_id)); owned=fetchone(cur)
    if not owned: conn.close(); return False
    cur.execute(q("DELETE FROM tactical_assistant_feedback WHERE message_id IN (SELECT id FROM tactical_assistant_messages WHERE conversation_id=?)"),(conversation_id,)); cur.execute(q("DELETE FROM tactical_assistant_message_sources WHERE message_id IN (SELECT id FROM tactical_assistant_messages WHERE conversation_id=?)"),(conversation_id,)); cur.execute(q("DELETE FROM tactical_assistant_messages WHERE conversation_id=?"),(conversation_id,)); cur.execute(q("DELETE FROM tactical_assistant_conversations WHERE id=? AND workspace_id=? AND user_id=?"),(conversation_id,workspace_id,user_id)); conn.commit(); conn.close(); return True


def add_message(conversation_id: int,role: str,content: str,intent: str=None,query: Dict[str,Any]=None,answer_type: str=None,confidence: str=None,sufficient: bool=False,limitations: List[str]=None,response: Dict[str,Any]=None) -> Dict[str,Any]:
    now=utc_now(); returning=" RETURNING id" if USE_POSTGRES else ""; conn=get_connection(); cur=conn.cursor(); cur.execute(q(f"""INSERT INTO tactical_assistant_messages
      (conversation_id,role,content,intent,structured_query_json,answer_type,confidence_level,has_sufficient_evidence,limitations_json,response_json,created_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?){returning}"""),(conversation_id,role,content,intent,_dump(query or {}),answer_type,confidence,1 if sufficient else 0,_dump(limitations or []),_dump(response or {}),now)); message_id=get_last_insert_id(cur); cur.execute(q("UPDATE tactical_assistant_conversations SET last_message_at=?,updated_at=? WHERE id=?"),(now,now,conversation_id)); conn.commit(); conn.close(); return get_message(conversation_id,message_id)


def get_message(conversation_id: int,message_id: int) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM tactical_assistant_messages WHERE id=? AND conversation_id=?"),(message_id,conversation_id)); row=fetchone(cur); conn.close(); return _decode(row)


def list_messages(workspace_id: int,user_id: int,conversation_id: int,limit: int=100) -> List[Dict[str,Any]]:
    if not get_conversation(workspace_id,user_id,conversation_id): return []
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM tactical_assistant_messages WHERE conversation_id=? ORDER BY created_at,id LIMIT ?"),(conversation_id,min(200,max(1,limit)))); rows=[_decode(row) for row in fetchall(cur)]; conn.close()
    ids=[row["id"] for row in rows]; sources={}
    if ids:
        marks=",".join("?" for _ in ids); conn=get_connection(); cur=conn.cursor(); cur.execute(q(f"SELECT * FROM tactical_assistant_message_sources WHERE message_id IN ({marks}) ORDER BY reliability_level DESC,id"),ids)
        for source in fetchall(cur): sources.setdefault(source["message_id"],[]).append(dict(source))
        conn.close()
    for row in rows: row["sources"]=sources.get(row["id"],[])
    return rows


def add_sources(message_id: int,sources: List[Dict[str,Any]]) -> None:
    conn=get_connection(); cur=conn.cursor(); now=utc_now()
    for source in sources[:30]:
        cur.execute(q("""INSERT INTO tactical_assistant_message_sources(message_id,knowledge_node_id,source_type,source_id,title,evidence_summary,reliability_level,objective_or_subjective,relation_type,action_url,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(message_id,knowledge_node_id) DO NOTHING"""),(message_id,source["knowledge_node_id"],source["source_type"],source["source_id"],source["title"],source.get("evidence_summary"),source.get("reliability_level"),source.get("objective_or_subjective"),source.get("relation_type"),source.get("action_url"),now))
    conn.commit(); conn.close()


def save_feedback(workspace_id: int,user_id: int,message_id: int,rating: int,feedback_type: str,note: str=None) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT m.id FROM tactical_assistant_messages m JOIN tactical_assistant_conversations c ON c.id=m.conversation_id WHERE m.id=? AND c.workspace_id=? AND c.user_id=?"),(message_id,workspace_id,user_id)); owned=fetchone(cur)
    if not owned: conn.close(); return None
    now=utc_now(); cur.execute(q("""INSERT INTO tactical_assistant_feedback(message_id,user_id,rating,feedback_type,note,created_at) VALUES(?,?,?,?,?,?)
      ON CONFLICT(message_id,user_id) DO UPDATE SET rating=excluded.rating,feedback_type=excluded.feedback_type,note=excluded.note,created_at=excluded.created_at"""),(message_id,user_id,rating,feedback_type,note,now)); conn.commit(); cur.execute(q("SELECT * FROM tactical_assistant_feedback WHERE message_id=? AND user_id=?"),(message_id,user_id)); row=fetchone(cur); conn.close(); return dict(row)


def record_telemetry(workspace_id: int,user_id: int,conversation_id: int,intent: str,outcome: str,source_count: int,latency_ms: int,provider: str,model: str,error_code: str=None,estimated_tokens: int=0) -> None:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("INSERT INTO tactical_assistant_telemetry(workspace_id,user_id,conversation_id,intent,outcome,source_count,latency_ms,provider,model,error_code,estimated_tokens,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"),(workspace_id,user_id,conversation_id,intent,outcome,source_count,latency_ms,provider,model,error_code,estimated_tokens,utc_now())); conn.commit(); conn.close()


def recent_request_count(user_id: int,since: str) -> int:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT COUNT(*) AS total FROM tactical_assistant_telemetry WHERE user_id=? AND created_at>=?"),(user_id,since)); row=fetchone(cur); conn.close(); return int(row["total"] or 0)
