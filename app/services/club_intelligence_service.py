from typing import Any, Dict, List, Optional

import database
from app.repositories import club_intelligence_repository as repository
from app.repositories.club_intelligence_schema import initialize_schema
from app.repositories import knowledge_intelligence_repository
from app.services import club_intelligence_aggregation as aggregation
from app.services import club_intelligence_knowledge as knowledge
from app.services import club_intelligence_policy as policy


CLUB_STATUSES = {"active", "archived"}
MEMBERSHIP_STATUSES = {"active", "inactive"}
TEAM_STATUSES = {"active", "inactive", "archived"}
TEAM_TYPES = {"first_team", "youth", "women", "other"}
SHARING_SCOPES = {"private", "club_technical", "selected"}
RESOURCE_SCOPES = {"club_technical", "selected_teams"}
PRINCIPLE_STATES = {"draft", "declared", "validated"}


def initialize_club_intelligence() -> None:
    initialize_schema()


def _membership(club_id: int, user_id: int) -> Dict[str, Any]:
    item = repository.get_membership(club_id, user_id)
    if not item or item.get("status") != "active":
        raise PermissionError("Accesso Club Intelligence non autorizzato")
    return item


def _validate_team_ids(club_id: int, team_ids: List[int]) -> List[int]:
    normalized = list(dict.fromkeys(int(team_id) for team_id in team_ids))
    allowed = {int(team["id"]) for team in repository.list_teams(club_id)}
    if any(team_id not in allowed for team_id in normalized):
        raise ValueError("Una o piu squadre non appartengono al club")
    return normalized


def _visible_principles(membership: Dict[str, Any], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if policy.can_compare(membership):
        return items
    assigned = {int(value) for value in membership.get("team_ids_json") or [] if str(value).isdigit()}
    return [
        item for item in items
        if not item.get("team_ids_json") or assigned.intersection(int(value) for value in item["team_ids_json"] if str(value).isdigit())
    ]


def create(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return repository.create_club(user_id, payload)


def list_for_user(user_id: int) -> List[Dict[str, Any]]:
    return repository.list_user_clubs(user_id)


def detail(club_id: int, user_id: int) -> Dict[str, Any]:
    membership = _membership(club_id, user_id); club = repository.get_club(club_id)
    teams = policy.visible_teams(membership, repository.list_teams(club_id))
    principles = _visible_principles(membership, repository.list_principles(club_id))
    snapshots = repository.list_snapshots(club_id, 5) if policy.can_compare(membership) else []
    return {"club": club, "membership": membership, "teams": teams, "principles": principles, "snapshots": snapshots}


def update_club(club_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    membership = _membership(club_id, user_id)
    if not policy.can_manage(membership): raise PermissionError("Solo la direzione tecnica puo modificare il club")
    data = {key: value for key, value in payload.items() if value is not None}
    if data.get("status") and data["status"] not in CLUB_STATUSES: raise ValueError("Stato club non valido")
    club = repository.update_club(club_id, data); repository.audit(club_id, user_id, "club_updated", "club", club_id, {"fields": list(data)})
    _publish_base(club_id, user_id)
    return club


def add_member(club_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    membership = _membership(club_id, user_id)
    if not policy.can_manage(membership): raise PermissionError("Solo la direzione tecnica puo gestire lo staff")
    target = database.get_user_by_id(payload.get("user_id")) if payload.get("user_id") else database.get_user_by_email(payload.get("email") or "")
    if not target: raise ValueError("Utente MatchIQ non trovato")
    role = policy.validate_role(payload.get("role"))
    team_ids = _validate_team_ids(club_id, payload.get("team_ids") or [])
    item = repository.upsert_membership(club_id, int(target["id"]), role, team_ids, payload.get("permissions") or {}, user_id)
    repository.audit(club_id, user_id, "membership_saved", "membership", item["id"], {"role": role, "target_user_id": target["id"]})
    return item


def change_member(club_id: int, membership_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    membership = _membership(club_id, user_id)
    if not policy.can_manage(membership): raise PermissionError("Solo la direzione tecnica puo gestire lo staff")
    data = {key: value for key, value in payload.items() if value is not None}
    if "role" in data: data["role"] = policy.validate_role(data["role"])
    if "team_ids" in data: data["team_ids"] = _validate_team_ids(club_id, data["team_ids"])
    if data.get("status") and data["status"] not in MEMBERSHIP_STATUSES: raise ValueError("Stato membership non valido")
    target = repository.get_membership_by_id(club_id, membership_id)
    if not target: raise ValueError("Membership non trovata")
    club = repository.get_club(club_id)
    if int(target["user_id"]) == int(club["owner_user_id"]) and (data.get("role", "club_owner") != "club_owner" or data.get("status") == "inactive"):
        raise ValueError("Il proprietario del club non puo essere disattivato o declassato")
    item = repository.update_membership(club_id, membership_id, data)
    if not item: raise ValueError("Membership non trovata")
    repository.audit(club_id, user_id, "membership_updated", "membership", membership_id, {"fields": list(data)})
    return item


def members(club_id: int, user_id: int) -> List[Dict[str, Any]]:
    membership = _membership(club_id, user_id)
    if not policy.can_manage(membership): return [{key: value for key, value in item.items() if key not in {"email", "permissions_json"}} for item in repository.list_members(club_id) if item["id"] == membership["id"]]
    return repository.list_members(club_id)


def add_team(club_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    membership = _membership(club_id, user_id)
    if not policy.can_manage(membership): raise PermissionError("Solo la direzione tecnica puo aggiungere squadre")
    payload["team_type"] = payload.get("team_type") or "other"
    payload["sharing_scope"] = payload.get("sharing_scope") or "private"
    if payload["team_type"] not in TEAM_TYPES: raise ValueError("Tipo squadra non valido")
    workspace_owner = None
    if payload.get("knowledge_workspace_id"):
        workspace = repository.get_workspace(int(payload["knowledge_workspace_id"]))
        if not workspace: raise ValueError("Workspace Knowledge non trovato")
        workspace_owner = int(workspace["user_id"])
        if not repository.get_membership(club_id, workspace_owner): raise ValueError("Il proprietario del workspace deve appartenere al club")
    if payload["sharing_scope"] not in SHARING_SCOPES: raise ValueError("Ambito condivisione squadra non valido")
    item = repository.create_team(club_id, payload, workspace_owner); repository.audit(club_id, user_id, "team_created", "team", item["id"], {"name": item["name"]})
    _publish_base(club_id, user_id)
    return item


def change_team(club_id: int, team_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    membership = _membership(club_id, user_id)
    if not policy.can_manage(membership): raise PermissionError("Solo la direzione tecnica puo modificare le squadre")
    data = {key: value for key, value in payload.items() if value is not None}
    if data.get("sharing_scope") and data["sharing_scope"] not in SHARING_SCOPES: raise ValueError("Ambito condivisione squadra non valido")
    if data.get("team_type") and data["team_type"] not in TEAM_TYPES: raise ValueError("Tipo squadra non valido")
    if data.get("status") and data["status"] not in TEAM_STATUSES: raise ValueError("Stato squadra non valido")
    item = repository.update_team(club_id, team_id, data)
    if not item: raise ValueError("Squadra club non trovata")
    repository.audit(club_id, user_id, "team_updated", "team", team_id, {"fields": list(data)})
    return item


def teams(club_id: int, user_id: int) -> List[Dict[str, Any]]:
    membership = _membership(club_id, user_id)
    return policy.visible_teams(membership, repository.list_teams(club_id))


def add_principle(club_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    membership = _membership(club_id, user_id)
    if not policy.can_manage(membership): raise PermissionError("Solo la direzione tecnica puo definire principi club")
    if payload.get("source_kind") not in {"declared_by_club", "staff_validated"}: raise ValueError("Fonte principio non valida")
    if payload.get("validation_state") not in PRINCIPLE_STATES: raise ValueError("Stato validazione principio non valido")
    payload["team_ids"] = _validate_team_ids(club_id, payload.get("team_ids") or [])
    item = repository.create_principle(club_id, user_id, payload); repository.audit(club_id, user_id, "principle_created", "principle", item["id"], {"area": item["principle_area"]})
    _publish_base(club_id, user_id)
    return item


def principles(club_id: int, user_id: int) -> List[Dict[str, Any]]:
    membership = _membership(club_id, user_id)
    return _visible_principles(membership, repository.list_principles(club_id))


def share_resource(club_id: int, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    membership = _membership(club_id, user_id)
    if not policy.can_share(membership): raise PermissionError("Condivisione non autorizzata")
    source_workspace = repository.get_workspace(int(payload["source_workspace_id"]))
    if not source_workspace: raise ValueError("Workspace sorgente non trovato")
    source_owner = int(source_workspace["user_id"])
    if source_owner != user_id and not policy.can_manage(membership): raise PermissionError("Non puoi condividere fonti di un altro staff")
    node = knowledge_intelligence_repository.get_node(int(payload["source_workspace_id"]), int(payload["source_node_id"]))
    if not node: raise ValueError("Fonte Knowledge non trovata")
    if payload.get("target_scope") not in RESOURCE_SCOPES: raise ValueError("Ambito condivisione risorsa non valido")
    payload["allowed_team_ids"] = _validate_team_ids(club_id, payload.get("allowed_team_ids") or [])
    if payload["target_scope"] == "selected_teams" and not payload["allowed_team_ids"]: raise ValueError("Seleziona almeno una squadra destinataria")
    item = repository.create_resource(club_id, user_id, payload); repository.audit(club_id, user_id, "resource_shared", "resource", item["id"], {"target_scope": item["target_scope"]})
    return item


def resources(club_id: int, user_id: int) -> List[Dict[str, Any]]:
    membership = _membership(club_id, user_id)
    return [item for item in repository.list_resources(club_id) if policy.can_view_resource(membership, item)]


def overview(club_id: int, user_id: int, team_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    membership = _membership(club_id, user_id); all_visible = policy.visible_teams(membership, repository.list_teams(club_id))
    visible_ids = {int(team["id"]) for team in all_visible}
    if team_ids and any(int(team_id) not in visible_ids for team_id in team_ids): raise PermissionError("Confronto richiesto su una squadra non autorizzata")
    selected = [team for team in all_visible if not team_ids or team["id"] in team_ids]
    principles = _visible_principles(membership, repository.list_principles(club_id))
    result = aggregation.build(repository.get_club(club_id), selected, principles)
    result["access"] = {"role": membership["role"], "can_manage": policy.can_manage(membership), "can_compare": policy.can_compare(membership), "can_share": policy.can_share(membership)}
    if not policy.can_compare(membership):
        result["continuity"] = {"notice": "Il confronto tra squadre e riservato ai ruoli tecnici autorizzati."}; result["differences"] = []
    result["resources"] = resources(club_id, user_id)
    return result


def snapshot(club_id: int, user_id: int, team_ids: List[int], period_label: Optional[str]) -> Dict[str, Any]:
    membership = _membership(club_id, user_id)
    if not policy.can_compare(membership): raise PermissionError("Snapshot multi-squadra non autorizzato")
    result = overview(club_id, user_id, team_ids)
    item = repository.create_snapshot(club_id, user_id, period_label, [team["team"]["id"] for team in result["teams"]], result, [source for team in result["teams"] for source in team["sources"]], result["limitations"])
    repository.audit(club_id, user_id, "snapshot_created", "snapshot", item["id"], {"teams": item["team_ids_json"]}); _publish_base(club_id, user_id, item)
    return item


def _publish_base(club_id: int, user_id: int, snapshot_item: Dict[str, Any] = None) -> None:
    membership = repository.get_membership(club_id, user_id); club = repository.get_club(club_id)
    if not membership or not club: return
    workspaces = [team.get("knowledge_workspace_id") for team in repository.list_teams(club_id) if team.get("knowledge_workspace_id") and policy.can_view_team(membership, team)]
    for workspace_id in workspaces:
        linked_team = next((team for team in repository.list_teams(club_id) if team.get("knowledge_workspace_id") == workspace_id), None)
        node_owner_id = int((linked_team or {}).get("workspace_owner_user_id") or user_id)
        club_node = knowledge.publish_club(int(workspace_id), node_owner_id, club)
        for team in repository.list_teams(club_id):
            if team.get("knowledge_workspace_id") == workspace_id: knowledge.publish_team(int(workspace_id), node_owner_id, club_node, team)
        for principle in repository.list_principles(club_id): knowledge.publish_principle(int(workspace_id), node_owner_id, club_node, principle)
        if snapshot_item: knowledge.publish_snapshot(int(workspace_id), node_owner_id, club_node, snapshot_item)
