from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


KnowledgeSourceType = Literal[
    "coach",
    "video_ai",
    "voice_coach",
    "pattern",
    "report",
    "training",
]


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CoachProfileUpdate(KnowledgeModel):
    coach_name: Optional[str] = Field(default=None, max_length=160)
    playing_philosophy: Optional[str] = Field(default=None, max_length=4000)
    preferred_formation: Optional[str] = Field(default=None, max_length=40)
    alternative_formation: Optional[str] = Field(default=None, max_length=40)
    pressing: Optional[str] = Field(default=None, max_length=2000)
    buildup: Optional[str] = Field(default=None, max_length=2000)
    offensive_style: Optional[str] = Field(default=None, max_length=2000)
    defensive_style: Optional[str] = Field(default=None, max_length=2000)
    tactical_principles: List[str] = Field(default_factory=list, max_length=50)
    transition_management: Optional[str] = Field(default=None, max_length=2000)
    set_piece_preferences: List[str] = Field(default_factory=list, max_length=50)
    personal_notes: Optional[str] = Field(default=None, max_length=8000)


class CoachProfile(CoachProfileUpdate):
    updated_at: Optional[datetime] = None


class TeamProfileUpdate(KnowledgeModel):
    category: Optional[str] = Field(default=None, max_length=120)
    average_age: Optional[float] = Field(default=None, ge=0, le=100)
    player_count: Optional[int] = Field(default=None, ge=0, le=200)
    goalkeeper_count: Optional[int] = Field(default=None, ge=0, le=30)
    strengths: List[str] = Field(default_factory=list, max_length=50)
    weaknesses: List[str] = Field(default_factory=list, max_length=50)
    formations_used: List[str] = Field(default_factory=list, max_length=30)
    playing_principles: List[str] = Field(default_factory=list, max_length=50)
    average_availability: Optional[float] = Field(default=None, ge=0, le=100)
    physical_level: Optional[str] = Field(default=None, max_length=1000)
    technical_level: Optional[str] = Field(default=None, max_length=1000)
    season_objectives: List[str] = Field(default_factory=list, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=8000)


class TeamProfile(TeamProfileUpdate):
    updated_at: Optional[datetime] = None


class RosterPlayerBase(KnowledgeModel):
    external_player_id: Optional[str] = Field(default=None, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    role: Optional[str] = Field(default=None, max_length=80)
    preferred_foot: Optional[str] = Field(default=None, max_length=30)
    characteristics: List[str] = Field(default_factory=list, max_length=50)
    speed: Optional[int] = Field(default=None, ge=0, le=100)
    strength: Optional[int] = Field(default=None, ge=0, le=100)
    technique: Optional[int] = Field(default=None, ge=0, le=100)
    personality: Optional[str] = Field(default=None, max_length=1000)
    leadership: Optional[int] = Field(default=None, ge=0, le=100)
    adaptability: Optional[int] = Field(default=None, ge=0, le=100)
    secondary_roles: List[str] = Field(default_factory=list, max_length=20)
    coach_notes: Optional[str] = Field(default=None, max_length=4000)


class RosterPlayerCreate(RosterPlayerBase):
    pass


class RosterPlayerUpdate(RosterPlayerBase):
    pass


class RosterPlayer(RosterPlayerBase):
    id: int
    created_at: datetime
    updated_at: datetime


class KnowledgeSourceLink(KnowledgeModel):
    id: int
    source_type: KnowledgeSourceType
    source_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class MatchIQKnowledge(KnowledgeModel):
    id: int
    user_id: int
    coach_profile: CoachProfile
    team_profile: TeamProfile
    roster: List[RosterPlayer] = Field(default_factory=list)
    source_links: List[KnowledgeSourceLink] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class KnowledgeEnvelope(KnowledgeModel):
    ok: bool = True
    knowledge: MatchIQKnowledge


class DeleteKnowledgeItemResponse(KnowledgeModel):
    ok: bool = True
    deleted: bool = True
    player_id: int
