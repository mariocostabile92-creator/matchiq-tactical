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


def _only(data: Dict, fields: set) -> Dict:
    return {key: data.get(key) for key in fields if key in data}


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
        team_profile=_only(team, TEAM_RESPONSE_FIELDS),
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
