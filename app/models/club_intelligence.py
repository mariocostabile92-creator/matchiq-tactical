from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ClubCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    season: Optional[str] = Field(default=None, max_length=30)
    declared_philosophy: Optional[str] = Field(default=None, max_length=4000)
    technical_principles: List[str] = Field(default_factory=list, max_length=40)
    transition_principles: List[str] = Field(default_factory=list, max_length=30)
    set_piece_principles: List[str] = Field(default_factory=list, max_length=30)


class ClubUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    season: Optional[str] = Field(default=None, max_length=30)
    declared_philosophy: Optional[str] = Field(default=None, max_length=4000)
    technical_principles: Optional[List[str]] = None
    transition_principles: Optional[List[str]] = None
    set_piece_principles: Optional[List[str]] = None
    status: Optional[str] = None


class ClubMemberCreate(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = Field(default=None, max_length=240)
    role: str = "viewer"
    team_ids: List[int] = Field(default_factory=list)
    permissions: Dict[str, Any] = Field(default_factory=dict)


class ClubMemberUpdate(BaseModel):
    role: Optional[str] = None
    team_ids: Optional[List[int]] = None
    permissions: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class ClubTeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    category: Optional[str] = Field(default=None, max_length=100)
    age_group: Optional[str] = Field(default=None, max_length=80)
    season: Optional[str] = Field(default=None, max_length=30)
    team_type: str = "other"
    level_order: int = Field(default=100, ge=0, le=1000)
    knowledge_workspace_id: Optional[int] = None
    sharing_scope: str = "private"


class ClubTeamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    category: Optional[str] = Field(default=None, max_length=100)
    age_group: Optional[str] = Field(default=None, max_length=80)
    season: Optional[str] = Field(default=None, max_length=30)
    team_type: Optional[str] = None
    level_order: Optional[int] = Field(default=None, ge=0, le=1000)
    sharing_scope: Optional[str] = None
    status: Optional[str] = None


class ClubPrincipleCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    principle_area: str = Field(default="general", max_length=80)
    description: str = Field(min_length=2, max_length=4000)
    source_kind: str = "declared_by_club"
    validation_state: str = "declared"
    team_ids: List[int] = Field(default_factory=list)


class ClubResourceCreate(BaseModel):
    source_workspace_id: int
    source_node_id: int
    resource_type: str = Field(default="knowledge_node", max_length=80)
    title: str = Field(min_length=2, max_length=200)
    target_scope: str = "selected_teams"
    allowed_team_ids: List[int] = Field(default_factory=list)
    purpose: str = Field(default="technical_continuity", max_length=500)


class ClubSnapshotRequest(BaseModel):
    team_ids: List[int] = Field(default_factory=list)
    period_label: Optional[str] = Field(default=None, max_length=80)


class ClubEnvelope(BaseModel):
    ok: bool = True
    data: Any
