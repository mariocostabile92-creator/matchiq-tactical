from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


ReferenceId = Union[int, str]


class MatchEvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MatchEvidenceMatchData(MatchEvidenceModel):
    result: Dict[str, Any] = Field(default_factory=dict)
    formation: Dict[str, Any] = Field(default_factory=dict)
    module: Optional[str] = Field(default=None, max_length=80)
    players: List[Dict[str, Any]] = Field(default_factory=list)
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list)
    substitutions: List[Dict[str, Any]] = Field(default_factory=list)
    cards: List[Dict[str, Any]] = Field(default_factory=list)
    goals: List[Dict[str, Any]] = Field(default_factory=list)


class MatchEvidenceCoachData(MatchEvidenceModel):
    notes: List[Any] = Field(default_factory=list)
    observations: List[Any] = Field(default_factory=list)
    ratings: List[Dict[str, Any]] = Field(default_factory=list)
    final_report: str = ""


class MatchEvidenceVoiceReferences(MatchEvidenceModel):
    observation_ids: List[ReferenceId] = Field(default_factory=list)


class MatchEvidenceVideoReferences(MatchEvidenceModel):
    video_report_ids: List[ReferenceId] = Field(default_factory=list)
    reviewed_frame_ids: List[ReferenceId] = Field(default_factory=list)


class MatchEvidenceMetadata(MatchEvidenceModel):
    coach_version: str = Field(default="", max_length=40)
    schema_version: int = Field(default=1, ge=1)
    source: str = Field(default="coach", min_length=1, max_length=80)
    flags: Dict[str, Any] = Field(default_factory=dict)


class MatchEvidenceFinalizeRequest(MatchEvidenceModel):
    schema_version: int = Field(default=1, ge=1)
    source_match_id: str = Field(min_length=1, max_length=160)
    team_id: Optional[str] = Field(default=None, max_length=160)
    season_id: Optional[str] = Field(default=None, max_length=80)
    competition: Optional[str] = Field(default=None, max_length=160)
    opponent: Optional[str] = Field(default=None, max_length=200)
    match_date: Optional[str] = Field(default=None, max_length=40)
    match: MatchEvidenceMatchData
    coach: MatchEvidenceCoachData
    voice_coach: MatchEvidenceVoiceReferences = Field(default_factory=MatchEvidenceVoiceReferences)
    video_ai: MatchEvidenceVideoReferences = Field(default_factory=MatchEvidenceVideoReferences)
    metadata: MatchEvidenceMetadata = Field(default_factory=MatchEvidenceMetadata)
    finalized_at: Optional[datetime] = None


class MatchEvidenceResponse(MatchEvidenceModel):
    canonical_match_id: str
    schema_version: int
    source_match_id: str
    user_id: int
    team_id: Optional[str] = None
    season_id: Optional[str] = None
    competition: Optional[str] = None
    opponent: Optional[str] = None
    match_date: Optional[str] = None
    created_at: datetime
    finalized_at: datetime
    updated_at: datetime
    match: MatchEvidenceMatchData
    coach: MatchEvidenceCoachData
    voice_coach: MatchEvidenceVoiceReferences
    video_ai: MatchEvidenceVideoReferences
    metadata: MatchEvidenceMetadata


class MatchEvidenceFinalizeResponse(MatchEvidenceModel):
    ok: bool = True
    created: bool
    data: MatchEvidenceResponse


class MatchEvidenceListResponse(MatchEvidenceModel):
    ok: bool = True
    data: List[MatchEvidenceResponse] = Field(default_factory=list)
