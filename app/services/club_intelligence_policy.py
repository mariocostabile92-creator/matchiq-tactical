from typing import Any, Dict, Iterable


ROLES = {"club_owner", "technical_director", "academy_director", "head_coach", "assistant_coach", "analyst", "viewer"}
MANAGERS = {"club_owner", "technical_director"}
TECHNICAL_VIEWERS = MANAGERS | {"academy_director"}


def validate_role(role: str) -> str:
    value = str(role or "viewer").strip().lower()
    if value not in ROLES:
        raise ValueError("Ruolo club non valido")
    return value


def can_manage(membership: Dict[str, Any]) -> bool:
    return bool(membership and membership.get("status") == "active" and (membership.get("role") in MANAGERS or (membership.get("permissions_json") or {}).get("manage_club")))


def can_compare(membership: Dict[str, Any]) -> bool:
    return bool(membership and membership.get("status") == "active" and (membership.get("role") in TECHNICAL_VIEWERS or (membership.get("permissions_json") or {}).get("compare_teams")))


def can_share(membership: Dict[str, Any]) -> bool:
    return bool(membership and membership.get("status") == "active" and (membership.get("role") in MANAGERS or (membership.get("permissions_json") or {}).get("share_resources")))


def can_view_team(membership: Dict[str, Any], team: Dict[str, Any]) -> bool:
    if not membership or membership.get("status") != "active":
        return False
    if membership.get("role") in TECHNICAL_VIEWERS:
        return True
    allowed = {int(value) for value in (membership.get("team_ids_json") or []) if str(value).isdigit()}
    return int(team["id"]) in allowed or team.get("sharing_scope") == "club_technical" and membership.get("role") in {"head_coach", "assistant_coach", "analyst"}


def visible_teams(membership: Dict[str, Any], teams: Iterable[Dict[str, Any]]) -> list:
    return [team for team in teams if can_view_team(membership, team)]


def can_view_resource(membership: Dict[str, Any], resource: Dict[str, Any]) -> bool:
    if membership.get("role") in TECHNICAL_VIEWERS:
        return True
    if resource.get("target_scope") == "club_technical":
        return membership.get("role") in {"head_coach", "assistant_coach", "analyst"}
    allowed = {int(value) for value in resource.get("allowed_team_ids_json") or [] if str(value).isdigit()}
    own = {int(value) for value in membership.get("team_ids_json") or [] if str(value).isdigit()}
    return bool(allowed & own)
