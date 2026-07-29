from typing import Dict

from app.models.knowledge import (
    CoachProfileUpdate,
    MatchIQKnowledge,
    RosterPlayerCreate,
    RosterPlayerUpdate,
    TeamProfileUpdate,
)
from app.repositories import knowledge_repository as repository


COACH_RESPONSE_FIELDS = repository.COACH_COLUMNS | {"updated_at"}
TEAM_RESPONSE_FIELDS = repository.TEAM_COLUMNS | {"updated_at"}
ROSTER_RESPONSE_FIELDS = repository.ROSTER_COLUMNS | {"id", "created_at", "updated_at"}
SOURCE_RESPONSE_FIELDS = {"id", "source_type", "source_id", "metadata", "created_at"}
TEAM_LIST_FIELDS = {
    "training_days",
    "available_materials",
    "strengths",
    "weaknesses",
    "formations_used",
    "playing_principles",
    "season_objectives",
}
TEAM_INTEGER_BOUNDS = {
    "player_count": (0, 200),
    "goalkeeper_count": (0, 30),
    "training_duration": (30, 180),
}
TEAM_FLOAT_BOUNDS = {
    "average_age": (0.0, 100.0),
    "average_availability": (0.0, 100.0),
}


def _only(data: Dict, fields: set) -> Dict:
    return {key: data.get(key) for key in fields if key in data}


def _bounded_number(value, minimum, maximum, converter):
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        normalized = converter(value)
    except (TypeError, ValueError):
        return None
    return normalized if minimum <= normalized <= maximum else None


def _normalize_team_profile(data: Dict) -> Dict:
    profile = _only(data, TEAM_RESPONSE_FIELDS)
    for field in TEAM_LIST_FIELDS:
        value = profile.get(field)
        profile[field] = [str(item) for item in value if item is not None] if isinstance(value, list) else []
    for field, bounds in TEAM_INTEGER_BOUNDS.items():
        profile[field] = _bounded_number(profile.get(field), *bounds, int)
    for field, bounds in TEAM_FLOAT_BOUNDS.items():
        profile[field] = _bounded_number(profile.get(field), *bounds, float)
    for field in repository.TEAM_COLUMNS - TEAM_LIST_FIELDS - set(TEAM_INTEGER_BOUNDS) - set(TEAM_FLOAT_BOUNDS):
        value = profile.get(field)
        profile[field] = value if value is None or isinstance(value, str) else None
    return profile


def initialize_foundation() -> None:
    repository.initialize_knowledge_schema()


def get_knowledge(user_id: int) -> MatchIQKnowledge:
    workspace = repository.get_or_create_workspace(user_id)
    knowledge_id = int(workspace["id"])
    coach = repository.get_profile(
        "knowledge_coach_profiles",
        knowledge_id,
        repository.COACH_COLUMNS,
    )
    team = repository.get_profile(
        "knowledge_team_profiles",
        knowledge_id,
        repository.TEAM_COLUMNS,
    )
    roster = repository.list_roster(knowledge_id)
    links = repository.list_source_links(knowledge_id)
    return MatchIQKnowledge(
        id=knowledge_id,
        user_id=int(workspace["user_id"]),
        coach_profile=_only(coach, COACH_RESPONSE_FIELDS),
        team_profile=_normalize_team_profile(team),
        roster=[_only(player, ROSTER_RESPONSE_FIELDS) for player in roster],
        source_links=[_only(link, SOURCE_RESPONSE_FIELDS) for link in links],
        created_at=workspace["created_at"],
        updated_at=workspace["updated_at"],
    )


def update_coach_profile(user_id: int, payload: CoachProfileUpdate) -> MatchIQKnowledge:
    workspace = repository.get_or_create_workspace(user_id)
    repository.upsert_profile(
        "knowledge_coach_profiles",
        int(workspace["id"]),
        payload.model_dump(exclude_unset=True),
        repository.COACH_COLUMNS,
    )
    return get_knowledge(user_id)


def update_team_profile(user_id: int, payload: TeamProfileUpdate) -> MatchIQKnowledge:
    workspace = repository.get_or_create_workspace(user_id)
    repository.upsert_profile(
        "knowledge_team_profiles",
        int(workspace["id"]),
        payload.model_dump(exclude_unset=True),
        repository.TEAM_COLUMNS,
    )
    return get_knowledge(user_id)


def add_roster_player(user_id: int, payload: RosterPlayerCreate):
    workspace = repository.get_or_create_workspace(user_id)
    row = repository.create_roster_player(int(workspace["id"]), payload.model_dump())
    return _only(row, ROSTER_RESPONSE_FIELDS)


def replace_roster_player(user_id: int, player_id: int, payload: RosterPlayerUpdate):
    workspace = repository.get_or_create_workspace(user_id)
    row = repository.update_roster_player(
        int(workspace["id"]),
        player_id,
        payload.model_dump(),
    )
    return _only(row, ROSTER_RESPONSE_FIELDS) if row else None


def remove_roster_player(user_id: int, player_id: int) -> bool:
    workspace = repository.get_or_create_workspace(user_id)
    return repository.delete_roster_player(int(workspace["id"]), player_id)
