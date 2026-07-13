import json
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now


JSON_FIELDS = {"technical_principles_json", "transition_principles_json", "set_piece_principles_json", "sharing_policy_json", "team_ids_json", "permissions_json", "allowed_team_ids_json", "summary_json", "sources_json", "limitations_json", "metadata_json"}


def _dump(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


def _load(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def _decode(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    item = dict(row)
    for field in JSON_FIELDS:
        if field in item:
            item[field] = _load(item[field], [] if field.endswith("ids_json") or field in {"technical_principles_json", "transition_principles_json", "set_piece_principles_json", "sources_json", "limitations_json"} else {})
    return item


def _insert(table: str, values: Dict[str, Any]) -> int:
    conn = get_connection(); cur = conn.cursor(); names = list(values)
    returning = " RETURNING id" if USE_POSTGRES else ""
    cur.execute(q(f"INSERT INTO {table}({','.join(names)}) VALUES({','.join('?' for _ in names)}){returning}"), [values[name] for name in names])
    item_id = int(get_last_insert_id(cur)); conn.commit(); conn.close(); return item_id


def _one(sql: str, params: tuple) -> Optional[Dict[str, Any]]:
    conn = get_connection(); cur = conn.cursor(); cur.execute(q(sql), params); row = fetchone(cur); conn.close(); return _decode(row)


def _many(sql: str, params: tuple) -> List[Dict[str, Any]]:
    conn = get_connection(); cur = conn.cursor(); cur.execute(q(sql), params); rows = [_decode(row) for row in fetchall(cur)]; conn.close(); return rows


def create_club(owner_user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now()
    club_id = _insert("club_intelligence_clubs", {
        "owner_user_id": owner_user_id, "name": payload["name"], "season": payload.get("season"),
        "declared_philosophy": payload.get("declared_philosophy"), "technical_principles_json": _dump(payload.get("technical_principles") or []),
        "transition_principles_json": _dump(payload.get("transition_principles") or []), "set_piece_principles_json": _dump(payload.get("set_piece_principles") or []),
        "sharing_policy_json": _dump({"default": "private", "comparison": "technical_roles"}), "status": "active", "created_at": now, "updated_at": now,
    })
    upsert_membership(club_id, owner_user_id, "club_owner", [], {"manage_club": True, "compare_teams": True, "share_resources": True}, owner_user_id)
    audit(club_id, owner_user_id, "club_created", "club", club_id, {"name": payload["name"]})
    return get_club(club_id)


def get_club(club_id: int) -> Optional[Dict[str, Any]]:
    return _one("SELECT * FROM club_intelligence_clubs WHERE id=?", (club_id,))


def update_club(club_id: int, values: Dict[str, Any]) -> Dict[str, Any]:
    mapping = {"technical_principles": "technical_principles_json", "transition_principles": "transition_principles_json", "set_piece_principles": "set_piece_principles_json"}
    fields = {}
    for key, value in values.items():
        field = mapping.get(key, key)
        fields[field] = _dump(value) if field.endswith("_json") else value
    fields["updated_at"] = utc_now()
    conn = get_connection(); cur = conn.cursor(); cur.execute(q(f"UPDATE club_intelligence_clubs SET {','.join(f'{k}=?' for k in fields)} WHERE id=?"), [*fields.values(), club_id]); conn.commit(); conn.close(); return get_club(club_id)


def list_user_clubs(user_id: int) -> List[Dict[str, Any]]:
    return _many("""SELECT c.*,m.role AS membership_role,m.team_ids_json,m.permissions_json
        FROM club_intelligence_clubs c JOIN club_intelligence_memberships m ON m.club_id=c.id
        WHERE m.user_id=? AND m.status='active' AND c.status='active' ORDER BY c.name""", (user_id,))


def get_membership(club_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    return _one("SELECT * FROM club_intelligence_memberships WHERE club_id=? AND user_id=?", (club_id, user_id))


def get_membership_by_id(club_id: int, membership_id: int) -> Optional[Dict[str, Any]]:
    return _one("SELECT * FROM club_intelligence_memberships WHERE club_id=? AND id=?", (club_id, membership_id))


def upsert_membership(club_id: int, user_id: int, role: str, team_ids: List[int], permissions: Dict[str, Any], invited_by: int) -> Dict[str, Any]:
    now = utc_now(); conn = get_connection(); cur = conn.cursor()
    cur.execute(q("""INSERT INTO club_intelligence_memberships(club_id,user_id,role,team_ids_json,permissions_json,status,invited_by,created_at,updated_at)
        VALUES(?,?,?,?,?,'active',?,?,?) ON CONFLICT(club_id,user_id) DO UPDATE SET role=excluded.role,team_ids_json=excluded.team_ids_json,permissions_json=excluded.permissions_json,status='active',updated_at=excluded.updated_at"""),
        (club_id, user_id, role, _dump(team_ids), _dump(permissions), invited_by, now, now))
    conn.commit(); conn.close(); return get_membership(club_id, user_id)


def update_membership(club_id: int, membership_id: int, values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    mapping = {"team_ids": "team_ids_json", "permissions": "permissions_json"}; fields = {}
    for key, value in values.items(): fields[mapping.get(key, key)] = _dump(value) if key in mapping else value
    fields["updated_at"] = utc_now(); conn = get_connection(); cur = conn.cursor()
    cur.execute(q(f"UPDATE club_intelligence_memberships SET {','.join(f'{k}=?' for k in fields)} WHERE id=? AND club_id=?"), [*fields.values(), membership_id, club_id]); conn.commit(); conn.close()
    return _one("SELECT * FROM club_intelligence_memberships WHERE id=? AND club_id=?", (membership_id, club_id))


def list_members(club_id: int) -> List[Dict[str, Any]]:
    return _many("""SELECT m.*,u.email FROM club_intelligence_memberships m LEFT JOIN users u ON u.id=m.user_id
        WHERE m.club_id=? ORDER BY CASE m.role WHEN 'club_owner' THEN 0 WHEN 'technical_director' THEN 1 WHEN 'academy_director' THEN 2 ELSE 3 END,m.id""", (club_id,))


def create_team(club_id: int, payload: Dict[str, Any], workspace_owner_user_id: Optional[int]) -> Dict[str, Any]:
    now = utc_now(); team_id = _insert("club_intelligence_teams", {"club_id": club_id, "knowledge_workspace_id": payload.get("knowledge_workspace_id"), "workspace_owner_user_id": workspace_owner_user_id,
        "name": payload["name"], "category": payload.get("category"), "age_group": payload.get("age_group"), "season": payload.get("season"), "team_type": payload.get("team_type") or "other",
        "level_order": payload.get("level_order", 100), "sharing_scope": payload.get("sharing_scope") or "private", "status": "active", "created_at": now, "updated_at": now})
    return get_team(club_id, team_id)


def get_team(club_id: int, team_id: int) -> Optional[Dict[str, Any]]:
    return _one("SELECT * FROM club_intelligence_teams WHERE id=? AND club_id=?", (team_id, club_id))


def list_teams(club_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
    suffix = " AND status='active'" if active_only else ""
    return _many(f"SELECT * FROM club_intelligence_teams WHERE club_id=?{suffix} ORDER BY level_order,name", (club_id,))


def update_team(club_id: int, team_id: int, values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    fields = {**values, "updated_at": utc_now()}; conn = get_connection(); cur = conn.cursor()
    cur.execute(q(f"UPDATE club_intelligence_teams SET {','.join(f'{k}=?' for k in fields)} WHERE id=? AND club_id=?"), [*fields.values(), team_id, club_id]); conn.commit(); conn.close(); return get_team(club_id, team_id)


def get_workspace(workspace_id: int) -> Optional[Dict[str, Any]]:
    return _one("SELECT * FROM knowledge_workspaces WHERE id=?", (workspace_id,))


def get_team_profile(workspace_id: int) -> Optional[Dict[str, Any]]:
    return _one("SELECT * FROM knowledge_team_profiles WHERE knowledge_id=?", (workspace_id,))


def get_coach_profile(workspace_id: int) -> Optional[Dict[str, Any]]:
    return _one("SELECT * FROM knowledge_coach_profiles WHERE knowledge_id=?", (workspace_id,))


def get_latest_identity(workspace_id: int) -> Optional[Dict[str, Any]]:
    return _one("SELECT * FROM tactical_identity_profiles WHERE workspace_id=? ORDER BY created_at DESC,id DESC LIMIT 1", (workspace_id,))


def create_principle(club_id: int, owner_user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now(); item_id = _insert("club_intelligence_principles", {"club_id": club_id, "title": payload["title"], "principle_area": payload["principle_area"], "description": payload["description"],
        "source_kind": payload["source_kind"], "validation_state": payload["validation_state"], "team_ids_json": _dump(payload.get("team_ids") or []), "owner_user_id": owner_user_id, "created_at": now, "updated_at": now})
    return _one("SELECT * FROM club_intelligence_principles WHERE id=?", (item_id,))


def list_principles(club_id: int) -> List[Dict[str, Any]]:
    return _many("SELECT * FROM club_intelligence_principles WHERE club_id=? ORDER BY principle_area,title", (club_id,))


def create_resource(club_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now(); conn = get_connection(); cur = conn.cursor()
    cur.execute(q("""INSERT INTO club_intelligence_resources(club_id,source_workspace_id,source_node_id,shared_by,resource_type,title,target_scope,allowed_team_ids_json,purpose,status,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,'active',?,?) ON CONFLICT(club_id,source_workspace_id,source_node_id) DO UPDATE SET title=excluded.title,target_scope=excluded.target_scope,allowed_team_ids_json=excluded.allowed_team_ids_json,purpose=excluded.purpose,status='active',updated_at=excluded.updated_at"""),
        (club_id, payload["source_workspace_id"], payload["source_node_id"], user_id, payload["resource_type"], payload["title"], payload["target_scope"], _dump(payload.get("allowed_team_ids") or []), payload.get("purpose"), now, now))
    conn.commit(); conn.close(); return _one("SELECT * FROM club_intelligence_resources WHERE club_id=? AND source_workspace_id=? AND source_node_id=?", (club_id, payload["source_workspace_id"], payload["source_node_id"]))


def list_resources(club_id: int) -> List[Dict[str, Any]]:
    return _many("SELECT * FROM club_intelligence_resources WHERE club_id=? AND status='active' ORDER BY updated_at DESC", (club_id,))


def create_snapshot(club_id: int, user_id: int, period_label: Optional[str], team_ids: List[int], summary: Dict[str, Any], sources: List[Any], limitations: List[str]) -> Dict[str, Any]:
    item_id = _insert("club_intelligence_snapshots", {"club_id": club_id, "requested_by": user_id, "period_label": period_label, "team_ids_json": _dump(team_ids), "summary_json": _dump(summary), "sources_json": _dump(sources), "limitations_json": _dump(limitations), "status": "ready", "created_at": utc_now()})
    return _one("SELECT * FROM club_intelligence_snapshots WHERE id=?", (item_id,))


def list_snapshots(club_id: int, limit: int = 12) -> List[Dict[str, Any]]:
    return _many("SELECT * FROM club_intelligence_snapshots WHERE club_id=? ORDER BY created_at DESC,id DESC LIMIT ?", (club_id, limit))


def audit(club_id: int, actor_user_id: int, action: str, entity_type: str, entity_id: Any, metadata: Dict[str, Any]) -> None:
    _insert("club_intelligence_audit", {"club_id": club_id, "actor_user_id": actor_user_id, "action": action, "entity_type": entity_type, "entity_id": str(entity_id), "metadata_json": _dump(metadata), "created_at": utc_now()})
