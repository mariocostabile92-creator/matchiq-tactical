import json
from typing import Any, Dict, List, Optional

from database import fetchall, fetchone, get_connection, q, utc_now
from app.repositories.knowledge_intelligence_repository import _decode, _dump, get_node


FILTER_COLUMNS={
  "node_id":"n.id","source_id":"n.source_id",
  "node_type":"n.node_type","source_module":"n.source_module","team":"n.team_name","match_id":"n.match_id",
  "player_id":"n.player_id","tactical_topic":"n.tactical_topic","zone":"n.zone","reliability_level":"n.reliability_level",
  "validation_state":"n.validation_state","polarity":"n.polarity","season":"n.season",
}


def search(workspace_id: int,filters: Dict[str,Any]) -> Dict[str,Any]:
    where=["n.workspace_id=?","n.is_active=1"]; params=[workspace_id]
    text=str(filters.get("text") or "").strip().lower()
    if text: where.append("LOWER(n.search_text) LIKE ?"); params.append(f"%{text}%")
    for name,column in FILTER_COLUMNS.items():
        value=filters.get(name)
        if value: where.append(f"{column}=?"); params.append(value)
    if filters.get("date_from"): where.append("n.occurred_at>=?"); params.append(filters["date_from"])
    if filters.get("date_to"): where.append("n.occurred_at<=?"); params.append(filters["date_to"])
    if filters.get("tag"):
        where.append("EXISTS(SELECT 1 FROM knowledge_node_tags nt JOIN knowledge_tags t ON t.id=nt.tag_id WHERE nt.node_id=n.id AND t.canonical_name=?)"); params.append(str(filters["tag"]).lower().replace(" ","_"))
    if filters.get("relation_type"):
        where.append("EXISTS(SELECT 1 FROM knowledge_edges e WHERE e.workspace_id=n.workspace_id AND e.is_active=1 AND (e.from_node_id=n.id OR e.to_node_id=n.id) AND e.relation_type=?)"); params.append(filters["relation_type"])
    page=max(1,int(filters.get("page") or 1)); size=min(100,max(1,int(filters.get("page_size") or 20))); offset=(page-1)*size
    clause=" AND ".join(where); conn=get_connection(); cur=conn.cursor()
    cur.execute(q(f"SELECT COUNT(*) AS total FROM knowledge_nodes n WHERE {clause}"),params); total=int(fetchone(cur)["total"] or 0)
    cur.execute(q(f"SELECT n.* FROM knowledge_nodes n WHERE {clause} ORDER BY n.occurred_at DESC,n.id DESC LIMIT ? OFFSET ?"),[*params,size,offset]); rows=[_decode(row) for row in fetchall(cur)]
    node_ids=[row["id"] for row in rows]; relations={}
    if node_ids:
        marks=",".join("?" for _ in node_ids); cur.execute(q(f"SELECT e.*,a.title AS from_title,b.title AS to_title FROM knowledge_edges e JOIN knowledge_nodes a ON a.id=e.from_node_id JOIN knowledge_nodes b ON b.id=e.to_node_id WHERE e.workspace_id=? AND e.is_active=1 AND (e.from_node_id IN ({marks}) OR e.to_node_id IN ({marks})) ORDER BY e.updated_at DESC"),[workspace_id,*node_ids,*node_ids])
        for edge in fetchall(cur):
            for node_id in (edge["from_node_id"],edge["to_node_id"]):
                if node_id in node_ids: relations.setdefault(node_id,[]).append(dict(edge))
    conn.close()
    for row in rows: row["relations"]=(relations.get(row["id"]) or [])[:5]
    return {"items":rows,"total":total,"page":page,"page_size":size,"pages":max(1,(total+size-1)//size),"filters":filters}


def timeline(workspace_id: int,filters: Dict[str,Any]) -> Dict[str,Any]:
    where=["t.workspace_id=?","t.is_active=1","n.is_active=1"]; params=[workspace_id]
    for name,column in (("match_id","t.match_id"),("tactical_topic","t.tactical_topic"),("zone","t.zone"),("reliability_level","t.reliability_level"),("node_type","n.node_type"),("source_module","t.source_module")):
        if filters.get(name): where.append(f"{column}=?"); params.append(filters[name])
    if filters.get("date_from"): where.append("t.occurred_at>=?"); params.append(filters["date_from"])
    if filters.get("date_to"): where.append("t.occurred_at<=?"); params.append(filters["date_to"])
    page=max(1,int(filters.get("page") or 1)); size=min(100,max(1,int(filters.get("page_size") or 20))); offset=(page-1)*size; clause=" AND ".join(where)
    conn=get_connection(); cur=conn.cursor(); cur.execute(q(f"SELECT COUNT(*) AS total FROM knowledge_timeline_entries t JOIN knowledge_nodes n ON n.id=t.node_id WHERE {clause}"),params); total=int(fetchone(cur)["total"] or 0)
    cur.execute(q(f"SELECT t.*,n.node_type,n.validation_state,n.team_name,n.player_id FROM knowledge_timeline_entries t JOIN knowledge_nodes n ON n.id=t.node_id WHERE {clause} ORDER BY t.occurred_at DESC,t.id DESC LIMIT ? OFFSET ?"),[*params,size,offset]); items=[_decode(row) for row in fetchall(cur)]; conn.close(); return {"items":items,"total":total,"page":page,"page_size":size,"pages":max(1,(total+size-1)//size)}


def relations(workspace_id: int,node_id: int) -> List[Dict[str,Any]]:
    if not get_node(workspace_id,node_id): return []
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("""SELECT e.*,a.node_type AS from_type,a.title AS from_title,b.node_type AS to_type,b.title AS to_title
      FROM knowledge_edges e JOIN knowledge_nodes a ON a.id=e.from_node_id JOIN knowledge_nodes b ON b.id=e.to_node_id
      WHERE e.workspace_id=? AND e.is_active=1 AND (e.from_node_id=? OR e.to_node_id=?) ORDER BY e.updated_at DESC,e.id DESC"""),(workspace_id,node_id,node_id)); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows


def versions(workspace_id: int,node_id: int) -> List[Dict[str,Any]]:
    if not get_node(workspace_id,node_id): return []
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT v.* FROM knowledge_node_versions v JOIN knowledge_nodes n ON n.id=v.node_id WHERE v.node_id=? AND n.workspace_id=? ORDER BY v.version_number DESC"),(node_id,workspace_id)); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows


def notes(workspace_id: int,node_id: int) -> List[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT id,node_id,note,created_at FROM knowledge_staff_notes WHERE workspace_id=? AND node_id=? ORDER BY created_at DESC,id DESC"),(workspace_id,node_id)); rows=[dict(row) for row in fetchall(cur)]; conn.close(); return rows


def add_note(workspace_id: int,user_id: int,node_id: int,note: str) -> Optional[Dict[str,Any]]:
    node=get_node(workspace_id,node_id)
    if not node: return None
    now=utc_now(); conn=get_connection(); cur=conn.cursor(); cur.execute(q("INSERT INTO knowledge_staff_notes(workspace_id,node_id,user_id,note,created_at) VALUES(?,?,?,?,?)"),(workspace_id,node_id,user_id,note,now)); conn.commit(); conn.close(); return {"node":node,"notes":notes(workspace_id,node_id)}


def validate(workspace_id: int,node_id: int,state: str,note: Optional[str],changed_by: str) -> Optional[Dict[str,Any]]:
    allowed={"confirmed_by_staff","contested_by_staff","archived","to_verify","dismissed_by_staff"}
    if state not in allowed: raise ValueError("Stato di validazione non valido")
    node=get_node(workspace_id,node_id)
    if not node: return None
    if node["validation_state"]==state and not note: return node
    now=utc_now(); version=int(node["current_version"])+1; active=0 if state=="archived" else 1; confirmed=1 if state=="confirmed_by_staff" else 0
    snapshot={**node,"validation_state":state,"is_active":bool(active),"staff_confirmed":bool(confirmed)}; conn=get_connection(); cur=conn.cursor(); cur.execute(q("UPDATE knowledge_nodes SET validation_state=?,is_active=?,staff_confirmed=?,current_version=?,last_verified_at=?,updated_at=? WHERE id=? AND workspace_id=?"),(state,active,confirmed,version,now,now,node_id,workspace_id)); cur.execute(q("INSERT INTO knowledge_node_versions(node_id,version_number,previous_snapshot_json,snapshot_json,change_type,changed_by,created_at) VALUES(?,?,?,?,?,?,?)"),(node_id,version,_dump(node),_dump(snapshot),"staff_validation",changed_by,now)); conn.commit(); conn.close()
    if note: add_note(workspace_id,int(node["user_id"]),node_id,note)
    return get_node(workspace_id,node_id)
