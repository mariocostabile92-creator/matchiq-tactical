import hashlib
import json
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now
from app.services.knowledge_intelligence_registry import canonical_key, validate_relation


JSON_FIELDS={"metadata_json","snapshot_json","previous_snapshot_json"}


def _dump(value: Any) -> str:
    return json.dumps(value if value is not None else {},ensure_ascii=False,sort_keys=True,default=str)


def _load(value: Any,fallback: Any=None) -> Any:
    if isinstance(value,(dict,list)): return value
    try: return json.loads(value) if value else ({} if fallback is None else fallback)
    except (TypeError,ValueError): return {} if fallback is None else fallback


def _decode(row: Optional[Dict[str,Any]]) -> Optional[Dict[str,Any]]:
    if not row: return None
    item=dict(row)
    for field in JSON_FIELDS:
        if field in item: item[field]=_load(item[field])
    for field in ("is_active","staff_confirmed"):
        if field in item: item[field]=bool(item[field])
    return item


def fingerprint(payload: Dict[str,Any]) -> str:
    return hashlib.sha256(_dump(payload).encode("utf-8")).hexdigest()


def get_node(workspace_id: int,node_id: int) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM knowledge_nodes WHERE id=? AND workspace_id=?"),(node_id,workspace_id)); row=fetchone(cur); conn.close(); return _decode(row)


def get_node_by_key(workspace_id: int,key: str) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM knowledge_nodes WHERE workspace_id=? AND canonical_key=?"),(workspace_id,key)); row=fetchone(cur); conn.close(); return _decode(row)


def upsert_node(workspace_id: int,user_id: int,node_type: str,source_module: str,source_type: str,source_id: str,payload: Dict[str,Any],changed_by: str="source_sync") -> Dict[str,Any]:
    key=canonical_key(workspace_id,node_type,source_type,str(source_id)); now=utc_now()
    meaningful={k:payload.get(k) for k in ("title","summary","occurred_at","reliability_level","validation_state","nature","polarity","tactical_topic","zone","player_id","match_id","season","team_name","metadata")}
    source_fp=fingerprint(meaningful); existing=get_node_by_key(workspace_id,key)
    fields={
      "team_profile_id":payload.get("team_profile_id"),"title":str(payload.get("title") or node_type.replace("_"," ").title())[:240],
      "summary":str(payload.get("summary") or "")[:2000],"occurred_at":payload.get("occurred_at") or payload.get("source_updated_at") or now,
      "source_updated_at":payload.get("source_updated_at"),"reliability_level":payload.get("reliability_level") or "media",
      "validation_state":payload.get("validation_state") or "da_verificare","nature":payload.get("nature") or "dato_derivato",
      "polarity":payload.get("polarity"),"tactical_topic":payload.get("tactical_topic"),"zone":payload.get("zone"),
      "player_id":str(payload["player_id"]) if payload.get("player_id") is not None else None,
      "match_id":str(payload["match_id"]) if payload.get("match_id") is not None else None,"season":payload.get("season"),
      "team_name":payload.get("team_name"),"metadata_json":_dump(payload.get("metadata") or {}),
      "search_text":" ".join(str(value or "") for value in (payload.get("title"),payload.get("summary"),payload.get("tactical_topic"),payload.get("zone"),payload.get("player_name"),payload.get("team_name"),payload.get("opponent"),payload.get("competition")," ".join(payload.get("tags") or []))).lower()[:8000],
    }
    if existing and existing["source_fingerprint"]==source_fp:
        if not existing["is_active"]:
            conn=get_connection(); cur=conn.cursor(); cur.execute(q("UPDATE knowledge_nodes SET is_active=1,indexed_at=?,updated_at=? WHERE id=?"),(now,now,existing["id"])); conn.commit(); conn.close(); return get_node(workspace_id,existing["id"])
        return existing
    conn=get_connection(); cur=conn.cursor()
    if existing:
        version=int(existing["current_version"])+1
        assignments=",".join(f"{name}=?" for name in fields)
        values=[*fields.values(),source_fp,version,now,now,existing["id"],workspace_id]
        cur.execute(q(f"UPDATE knowledge_nodes SET {assignments},source_fingerprint=?,current_version=?,is_active=1,indexed_at=?,updated_at=? WHERE id=? AND workspace_id=?"),values)
        node_id=existing["id"]
        cur.execute(q("INSERT INTO knowledge_node_versions(node_id,version_number,previous_snapshot_json,snapshot_json,change_type,changed_by,source_updated_at,created_at) VALUES(?,?,?,?,?,?,?,?)"),(node_id,version,_dump(existing),_dump({**fields,"source_fingerprint":source_fp}),"source_changed",changed_by,payload.get("source_updated_at"),now))
    else:
        returning=" RETURNING id" if USE_POSTGRES else ""
        names=list(fields)
        cur.execute(q(f"INSERT INTO knowledge_nodes(workspace_id,user_id,node_type,source_module,source_type,source_id,canonical_key,{','.join(names)},source_fingerprint,current_version,is_active,staff_confirmed,indexed_at,created_at,updated_at) VALUES({','.join('?' for _ in range(7+len(names)+7))}){returning}"),[workspace_id,user_id,node_type,source_module,source_type,str(source_id),key,*fields.values(),source_fp,1,1,0,now,now,now])
        node_id=get_last_insert_id(cur)
        cur.execute(q("INSERT INTO knowledge_node_versions(node_id,version_number,previous_snapshot_json,snapshot_json,change_type,changed_by,source_updated_at,created_at) VALUES(?,?,?,?,?,?,?,?)"),(node_id,1,None,_dump({**fields,"source_fingerprint":source_fp}),"created",changed_by,payload.get("source_updated_at"),now))
    conn.commit(); conn.close(); node=get_node(workspace_id,node_id)
    upsert_timeline(workspace_id,node,"indexed")
    set_tags(workspace_id,node_id,payload.get("tags") or [])
    return node


def upsert_timeline(workspace_id: int,node: Dict[str,Any],event_type: str) -> None:
    now=utc_now(); returning=" RETURNING id" if USE_POSTGRES else ""; conn=get_connection(); cur=conn.cursor()
    values=(workspace_id,node["id"],node.get("match_id"),event_type,node["title"],node.get("summary"),node.get("occurred_at") or now,node["source_module"],node["source_type"],node["source_id"],node.get("tactical_topic"),node.get("zone"),node["reliability_level"],_dump({"validation_state":node["validation_state"]}),1,now)
    cur.execute(q(f"""INSERT INTO knowledge_timeline_entries(workspace_id,node_id,match_id,event_type,title,summary,occurred_at,source_module,source_type,source_id,tactical_topic,zone,reliability_level,metadata_json,is_active,created_at)
      VALUES({','.join('?' for _ in range(16))}) ON CONFLICT(workspace_id,node_id,event_type,source_type,source_id) DO UPDATE SET title=excluded.title,summary=excluded.summary,occurred_at=excluded.occurred_at,reliability_level=excluded.reliability_level,metadata_json=excluded.metadata_json,is_active=1{returning}"""),values)
    conn.commit(); conn.close()


def upsert_edge(workspace_id: int,from_node: Dict[str,Any],to_node: Dict[str,Any],relation_type: str,source_type: str,source_id: str,explanation: str="",confidence: str="media",validation: str="derived",metadata: Dict[str,Any]=None) -> Dict[str,Any]:
    validate_relation(from_node["node_type"],relation_type); now=utc_now(); conn=get_connection(); cur=conn.cursor()
    values=(workspace_id,from_node["id"],to_node["id"],relation_type,"outgoing",source_type,str(source_id),confidence,validation,explanation,_dump(metadata or {}),1,now,now)
    cur.execute(q("""INSERT INTO knowledge_edges(workspace_id,from_node_id,to_node_id,relation_type,direction,source_type,source_id,confidence_level,validation_state,explanation,metadata_json,is_active,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(workspace_id,from_node_id,to_node_id,relation_type,source_type,source_id) DO UPDATE SET confidence_level=excluded.confidence_level,validation_state=excluded.validation_state,explanation=excluded.explanation,metadata_json=excluded.metadata_json,is_active=1,updated_at=excluded.updated_at"""),values)
    conn.commit(); cur.execute(q("SELECT * FROM knowledge_edges WHERE workspace_id=? AND from_node_id=? AND to_node_id=? AND relation_type=? AND source_type=? AND source_id=?"),(workspace_id,from_node["id"],to_node["id"],relation_type,source_type,str(source_id))); row=fetchone(cur); conn.close(); return _decode(row)


def set_tags(workspace_id: int,node_id: int,tags: List[str]) -> None:
    conn=get_connection(); cur=conn.cursor(); now=utc_now()
    for raw in tags[:30]:
        name=str(raw).strip()[:60]; canonical=name.lower().replace(" ","_")
        if not canonical: continue
        cur.execute(q("INSERT INTO knowledge_tags(workspace_id,name,canonical_name,created_at) VALUES(?,?,?,?) ON CONFLICT(workspace_id,canonical_name) DO NOTHING"),(workspace_id,name,canonical,now))
        cur.execute(q("SELECT id FROM knowledge_tags WHERE workspace_id=? AND canonical_name=?"),(workspace_id,canonical)); tag=fetchone(cur)
        cur.execute(q("INSERT INTO knowledge_node_tags(node_id,tag_id,created_at) VALUES(?,?,?) ON CONFLICT(node_id,tag_id) DO NOTHING"),(node_id,tag["id"],now))
    conn.commit(); conn.close()


def deactivate_missing(workspace_id: int,source_type: str,seen_ids: List[str]) -> int:
    conn=get_connection(); cur=conn.cursor(); now=utc_now()
    cur.execute(q("SELECT id,source_id FROM knowledge_nodes WHERE workspace_id=? AND source_type=? AND is_active=1"),(workspace_id,source_type)); rows=fetchall(cur); missing=[row["id"] for row in rows if str(row["source_id"]) not in set(map(str,seen_ids))]
    for node_id in missing:
        cur.execute(q("UPDATE knowledge_nodes SET is_active=0,validation_state='source_removed',updated_at=? WHERE id=? AND workspace_id=?"),(now,node_id,workspace_id)); cur.execute(q("UPDATE knowledge_edges SET is_active=0,updated_at=? WHERE workspace_id=? AND (from_node_id=? OR to_node_id=?)"),(now,workspace_id,node_id,node_id)); cur.execute(q("UPDATE knowledge_timeline_entries SET is_active=0 WHERE workspace_id=? AND node_id=?"),(workspace_id,node_id))
        cur.execute(q("SELECT * FROM knowledge_nodes WHERE id=?"),(node_id,)); snapshot=fetchone(cur); version=int(snapshot["current_version"])+1; cur.execute(q("UPDATE knowledge_nodes SET current_version=? WHERE id=?"),(version,node_id)); cur.execute(q("INSERT INTO knowledge_node_versions(node_id,version_number,previous_snapshot_json,snapshot_json,change_type,changed_by,created_at) VALUES(?,?,?,?,?,?,?)"),(node_id,version,_dump(dict(snapshot)),_dump({**dict(snapshot),"is_active":False,"validation_state":"source_removed"}),"source_removed","source_sync",now))
    conn.commit(); conn.close(); return len(missing)


def get_sync_state(workspace_id: int,module: str) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM knowledge_sync_state WHERE workspace_id=? AND module=?"),(workspace_id,module)); row=fetchone(cur); conn.close(); return _decode(row)


def set_sync_state(workspace_id: int,user_id: int,module: str,status: str,source_fp: str=None,error: str=None,metadata: Dict[str,Any]=None,lock_token: str=None) -> Dict[str,Any]:
    now=utc_now(); current=get_sync_state(workspace_id,module); retry=(int(current.get("retry_count") or 0)+1) if error and current else (1 if error else 0)
    values=(workspace_id,user_id,module,status,source_fp,now if status=="completed" else None,now if status=="completed" else None,str(error or "")[:500] or None,retry,lock_token,now if lock_token else None,_dump(metadata or {}),now,now)
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("""INSERT INTO knowledge_sync_state(workspace_id,user_id,module,status,source_fingerprint,last_source_updated_at,last_synced_at,last_error,retry_count,lock_token,locked_at,metadata_json,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(workspace_id,module) DO UPDATE SET status=excluded.status,source_fingerprint=COALESCE(excluded.source_fingerprint,knowledge_sync_state.source_fingerprint),last_source_updated_at=COALESCE(excluded.last_source_updated_at,knowledge_sync_state.last_source_updated_at),last_synced_at=COALESCE(excluded.last_synced_at,knowledge_sync_state.last_synced_at),last_error=excluded.last_error,retry_count=excluded.retry_count,lock_token=excluded.lock_token,locked_at=excluded.locked_at,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at"""),values); conn.commit(); conn.close(); return get_sync_state(workspace_id,module)


def summary(workspace_id: int) -> Dict[str,Any]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT node_type,COUNT(*) AS total,MAX(updated_at) AS latest FROM knowledge_nodes WHERE workspace_id=? AND is_active=1 GROUP BY node_type"),(workspace_id,)); groups=fetchall(cur); cur.execute(q("SELECT COUNT(*) AS total FROM knowledge_edges WHERE workspace_id=? AND is_active=1"),(workspace_id,)); edges=fetchone(cur); cur.execute(q("SELECT MAX(last_synced_at) AS latest FROM knowledge_sync_state WHERE workspace_id=?"),(workspace_id,)); sync=fetchone(cur); conn.close(); return {"nodes":sum(int(x["total"]) for x in groups),"edges":int(edges["total"] or 0),"by_type":{x["node_type"]:int(x["total"]) for x in groups},"last_updated":max((x["latest"] for x in groups if x.get("latest")),default=None),"last_synced_at":sync.get("latest") if sync else None}


def list_nodes(workspace_id: int,active_only: bool=True) -> List[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); suffix=" AND is_active=1" if active_only else ""; cur.execute(q(f"SELECT * FROM knowledge_nodes WHERE workspace_id=?{suffix} ORDER BY id"),(workspace_id,)); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows


def list_sync_states(workspace_id: int) -> List[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM knowledge_sync_state WHERE workspace_id=? ORDER BY module"),(workspace_id,)); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows
