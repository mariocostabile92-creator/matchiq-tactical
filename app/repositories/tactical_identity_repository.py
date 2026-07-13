import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now


def _dump(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)


def _load(value: Any, fallback: Any = None) -> Any:
    if isinstance(value, (dict, list)): return value
    try: return json.loads(value) if value else (fallback if fallback is not None else {})
    except (TypeError, ValueError): return fallback if fallback is not None else {}


def _decode(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row: return None
    item = dict(row)
    for name in ("summary_json", "filters_json", "declared_source_json", "limitations_json", "distribution_json", "previous_period_json", "recent_period_json", "snapshot_json"):
        if name in item: item[name[:-5] if name.endswith("_json") else name] = _load(item.get(name), [] if name == "limitations_json" else {})
    return item


def get_profile(workspace_id: int, user_id: int, scope: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn=get_connection(); cur=conn.cursor()
    cur.execute(q("""SELECT * FROM tactical_identity_profiles WHERE workspace_id=? AND user_id=?
      AND COALESCE(team_profile_id,0)=? AND season=? AND period_start=? AND period_end=?
      AND competition=? AND formation=? AND source_type=? ORDER BY id DESC LIMIT 1"""),
      (workspace_id,user_id,int(scope.get("team_profile_id") or 0),scope.get("season") or "",scope.get("period_start") or "",scope.get("period_end") or "",scope.get("competition") or "",scope.get("formation") or "",scope.get("source_type") or ""))
    row=fetchone(cur); conn.close(); return _decode(row)


def get_profile_by_id(workspace_id: int, user_id: int, profile_id: int) -> Optional[Dict[str, Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM tactical_identity_profiles WHERE id=? AND workspace_id=? AND user_id=?"),(profile_id,workspace_id,user_id)); row=fetchone(cur); conn.close(); return _decode(row)


def latest_profile(workspace_id: int, user_id: int, filters: Dict[str,Any]=None) -> Optional[Dict[str, Any]]:
    filters=filters or {}
    conn=get_connection(); cur=conn.cursor(); sql="SELECT * FROM tactical_identity_profiles WHERE workspace_id=? AND user_id=?"; params=[workspace_id,user_id]
    if filters.get("team_profile_id"): sql+=" AND team_profile_id=?"; params.append(filters["team_profile_id"])
    for name in ("season","period_start","period_end","competition","formation","source_type"):
        if filters.get(name): sql+=f" AND {name}=?"; params.append(filters[name])
    cur.execute(q(sql+" ORDER BY updated_at DESC,id DESC LIMIT 1"),params); row=fetchone(cur); conn.close(); return _decode(row)


def _lock_is_stale(locked_at: Optional[str], minutes: int = 10) -> bool:
    if not locked_at:
        return True
    try:
        value = datetime.fromisoformat(str(locked_at).replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value < datetime.now(timezone.utc) - timedelta(minutes=minutes)
    except (TypeError, ValueError):
        return True


def acquire_lock(workspace_id: int,user_id: int,scope: Dict[str,Any],token: str) -> bool:
    existing=get_profile(workspace_id,user_id,scope)
    if existing and existing.get("status")=="processing" and existing.get("lock_token") and not _lock_is_stale(existing.get("locked_at")): return False
    if not existing:
        now=utc_now(); fields={"workspace_id":workspace_id,"user_id":user_id,"team_profile_id":scope.get("team_profile_id"),"coach_profile_id":scope.get("coach_profile_id"),"season":scope.get("season") or "","period_start":scope.get("period_start") or "","period_end":scope.get("period_end") or "","competition":scope.get("competition") or "","formation":scope.get("formation") or "","source_type":scope.get("source_type") or "","status":"processing","source_fingerprint":"","matches_analyzed":0,"sources_analyzed":0,"identity_version":0,"overall_confidence":"bassa","summary_json":"{}","filters_json":_dump(scope),"lock_token":token,"locked_at":now,"created_at":now,"updated_at":now}
        conn=get_connection(); cur=conn.cursor()
        try:
            returning=" RETURNING id" if USE_POSTGRES else ""; cur.execute(q(f"INSERT INTO tactical_identity_profiles({','.join(fields)}) VALUES({','.join('?' for _ in fields)}){returning}"),list(fields.values())); conn.commit(); return True
        except Exception:
            conn.rollback(); return False
        finally: conn.close()
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("UPDATE tactical_identity_profiles SET status='processing',lock_token=?,locked_at=?,updated_at=? WHERE id=? AND workspace_id=? AND user_id=?"),(token,utc_now(),utc_now(),existing["id"],workspace_id,user_id)); conn.commit(); conn.close(); return True


def release_unchanged(workspace_id: int,user_id: int,profile_id: int) -> None:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("UPDATE tactical_identity_profiles SET status='completed',processing_error=NULL,lock_token=NULL,locked_at=NULL,updated_at=? WHERE id=? AND workspace_id=? AND user_id=?"),(utc_now(),profile_id,workspace_id,user_id)); conn.commit(); conn.close()


def release_error(workspace_id: int,user_id: int,scope: Dict[str,Any],message: str) -> None:
    item=get_profile(workspace_id,user_id,scope)
    if not item: return
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("UPDATE tactical_identity_profiles SET status='error',processing_error=?,lock_token=NULL,locked_at=NULL,updated_at=? WHERE id=? AND workspace_id=? AND user_id=?"),(message[:1000],utc_now(),item["id"],workspace_id,user_id)); conn.commit(); conn.close()


def save_profile(workspace_id: int,user_id: int,scope: Dict[str,Any],payload: Dict[str,Any]) -> Dict[str,Any]:
    now=utc_now(); existing=get_profile(workspace_id,user_id,scope); values={
      "team_profile_id":scope.get("team_profile_id"),"coach_profile_id":scope.get("coach_profile_id"),"season":scope.get("season") or "",
      "period_start":scope.get("period_start") or "","period_end":scope.get("period_end") or "","competition":scope.get("competition") or "","formation":scope.get("formation") or "","source_type":scope.get("source_type") or "","status":"completed",
      "source_fingerprint":payload["source_fingerprint"],"matches_analyzed":payload["matches_analyzed"],"sources_analyzed":payload["sources_analyzed"],
      "identity_version":payload["identity_version"],"overall_confidence":payload["overall_confidence"],"summary_json":_dump(payload["summary"]),
      "filters_json":_dump(scope),"processing_error":None,"lock_token":None,"locked_at":None,"updated_at":now,
    }
    conn=get_connection(); cur=conn.cursor()
    if existing:
        assignments=",".join(f"{name}=?" for name in values); cur.execute(q(f"UPDATE tactical_identity_profiles SET {assignments} WHERE id=? AND workspace_id=? AND user_id=?"),[*values.values(),existing["id"],workspace_id,user_id]); profile_id=existing["id"]
    else:
        fields={"workspace_id":workspace_id,"user_id":user_id,**values,"created_at":now}; returning=" RETURNING id" if USE_POSTGRES else ""; cur.execute(q(f"INSERT INTO tactical_identity_profiles({','.join(fields)}) VALUES({','.join('?' for _ in fields)}){returning}"),list(fields.values())); profile_id=get_last_insert_id(cur)
    conn.commit(); conn.close(); return get_profile_by_id(workspace_id,user_id,int(profile_id))


def replace_dimensions(profile_id: int, dimensions: List[Dict[str,Any]]) -> None:
    now=utc_now(); conn=get_connection(); cur=conn.cursor(); keep=[]
    for item in dimensions:
        cur.execute(q("SELECT id FROM tactical_identity_dimensions WHERE identity_profile_id=? AND dimension_type=?"),(profile_id,item["dimension_type"])); existing=fetchone(cur)
        fields={"dimension_group":item["dimension_group"],"label":item["label"],"declared_value":item.get("declared_value"),"declared_source_json":_dump(item.get("declared_source") or {}),"observed_value":item.get("observed_value"),"validated_value":item.get("validated_value"),"declared_strength":item.get("declared_strength"),"observed_strength":item.get("observed_strength"),"alignment_state":item["alignment_state"],"confidence_level":item["confidence_level"],"trend_direction":item["trend_direction"],"evidence_count":item["evidence_count"],"match_count":item["match_count"],"explanation":item["explanation"],"limitations_json":_dump(item["limitations"]),"validation_state":item["validation_state"],"distribution_json":_dump(item["distribution"]),"previous_period_json":_dump(item["previous_period"]),"recent_period_json":_dump(item["recent_period"]),"updated_at":now}
        if existing:
            cur.execute(q(f"UPDATE tactical_identity_dimensions SET {','.join(f'{k}=?' for k in fields)} WHERE id=?"),[*fields.values(),existing["id"]]); dimension_id=existing["id"]
        else:
            values={"identity_profile_id":profile_id,"dimension_type":item["dimension_type"],**fields,"created_at":now}; returning=" RETURNING id" if USE_POSTGRES else ""; cur.execute(q(f"INSERT INTO tactical_identity_dimensions({','.join(values)}) VALUES({','.join('?' for _ in values)}){returning}"),list(values.values())); dimension_id=get_last_insert_id(cur)
        keep.append(int(dimension_id)); cur.execute(q("DELETE FROM tactical_identity_evidence WHERE identity_dimension_id=?"),(dimension_id,))
        for evidence in item.get("evidence") or []:
            cur.execute(q("""INSERT INTO tactical_identity_evidence(identity_dimension_id,knowledge_node_id,source_type,source_id,match_id,player_id,topic,zone,phase,evidence_summary,evidence_nature,reliability_level,evidence_weight,occurred_at,created_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(identity_dimension_id,knowledge_node_id) DO NOTHING"""),(dimension_id,evidence["knowledge_node_id"],evidence["source_type"],str(evidence["source_id"]),evidence.get("match_id"),evidence.get("player_id"),evidence.get("topic"),evidence.get("zone"),evidence.get("phase"),evidence["evidence_summary"],evidence["evidence_nature"],evidence["reliability_level"],float(evidence["evidence_weight"]),evidence.get("occurred_at"),now))
    if keep:
        marks=",".join("?" for _ in keep); cur.execute(q(f"DELETE FROM tactical_identity_dimensions WHERE identity_profile_id=? AND id NOT IN ({marks})"),[profile_id,*keep])
    conn.commit(); conn.close()


def list_dimensions(profile_id: int,filters: Dict[str,Any]=None) -> List[Dict[str,Any]]:
    filters=filters or {}; where=["identity_profile_id=?"]; params=[profile_id]
    for name,column in (("dimension_group","dimension_group"),("confidence_level","confidence_level"),("validation_state","validation_state")):
        if filters.get(name): where.append(f"{column}=?"); params.append(filters[name])
    conn=get_connection(); cur=conn.cursor(); cur.execute(q(f"SELECT * FROM tactical_identity_dimensions WHERE {' AND '.join(where)} ORDER BY dimension_group,dimension_type"),params); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows


def get_dimension(workspace_id: int,user_id: int,dimension_id: int) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("""SELECT d.* FROM tactical_identity_dimensions d JOIN tactical_identity_profiles p ON p.id=d.identity_profile_id WHERE d.id=? AND p.workspace_id=? AND p.user_id=?"""),(dimension_id,workspace_id,user_id)); row=fetchone(cur); conn.close(); return _decode(row)


def list_evidence(workspace_id: int,user_id: int,dimension_id: int,page: int=1,page_size: int=20) -> Dict[str,Any]:
    if not get_dimension(workspace_id,user_id,dimension_id): return {"items":[],"total":0,"page":page,"page_size":page_size}
    offset=(page-1)*page_size; conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT COUNT(*) AS total FROM tactical_identity_evidence WHERE identity_dimension_id=?"),(dimension_id,)); total=int(fetchone(cur)["total"]); cur.execute(q("SELECT * FROM tactical_identity_evidence WHERE identity_dimension_id=? ORDER BY occurred_at DESC,id DESC LIMIT ? OFFSET ?"),(dimension_id,page_size,offset)); items=fetchall(cur); conn.close(); return {"items":items,"total":total,"page":page,"page_size":page_size}


def add_version(profile_id: int,version: int,snapshot: Dict[str,Any],summary: str,reason: str,changed_by: str) -> None:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("INSERT INTO tactical_identity_versions(identity_profile_id,version_number,snapshot_json,change_summary,change_reason,changed_by,created_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(identity_profile_id,version_number) DO NOTHING"),(profile_id,version,_dump(snapshot),summary[:1000],reason[:200],changed_by[:120],utc_now())); conn.commit(); conn.close()


def list_versions(profile_id: int,limit: int=50) -> List[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM tactical_identity_versions WHERE identity_profile_id=? ORDER BY version_number DESC LIMIT ?"),(profile_id,limit)); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows


def save_feedback(workspace_id: int,user_id: int,dimension_id: int,action: str,note: str=None,declared_value: str=None) -> Optional[Dict[str,Any]]:
    dimension=get_dimension(workspace_id,user_id,dimension_id)
    if not dimension: return None
    now=utc_now(); conn=get_connection(); cur=conn.cursor(); cur.execute(q("INSERT INTO tactical_identity_staff_feedback(identity_dimension_id,user_id,action,note,declared_value,created_at) VALUES(?,?,?,?,?,?)"),(dimension_id,user_id,action,note,declared_value,now))
    state={"confirmed":"confirmed_by_staff","contested":"contested_by_staff","monitor":"monitor","not_representative":"not_representative","update_declared":"declared_updated"}[action]
    validated=dimension.get("observed_value") if action=="confirmed" else dimension.get("validated_value")
    if action=="update_declared" and declared_value: validated=declared_value
    cur.execute(q("UPDATE tactical_identity_dimensions SET validation_state=?,validated_value=?,updated_at=? WHERE id=?"),(state,validated,now,dimension_id)); conn.commit(); conn.close(); return get_dimension(workspace_id,user_id,dimension_id)


def feedback_for_dimension(dimension_id: int) -> List[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT id,action,note,declared_value,created_at FROM tactical_identity_staff_feedback WHERE identity_dimension_id=? ORDER BY created_at DESC,id DESC"),(dimension_id,)); rows=fetchall(cur); conn.close(); return rows


def full_profile(workspace_id: int,user_id: int,profile: Dict[str,Any],filters: Dict[str,Any]=None) -> Dict[str,Any]:
    result=dict(profile); result["dimensions"]=list_dimensions(profile["id"],filters); result["versions"]=list_versions(profile["id"],20); return result
