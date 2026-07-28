from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


PriorityStatus = Literal["PROPOSED", "CONFIRMED", "DISMISSED", "MODIFIED"]
PriorityLevel = Literal["HIGH", "MEDIUM", "LOW"]


class WeeklyPriorityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WeeklyPriorityReason(WeeklyPriorityModel):
    code: str
    summary: str
    factors: Dict[str, Any] = Field(default_factory=dict)


class WeeklyPriorityReferences(WeeklyPriorityModel):
    matches: List[str] = Field(default_factory=list)
    patterns: List[int] = Field(default_factory=list)
    evidence: List[int] = Field(default_factory=list)
    voice_coach: List[str] = Field(default_factory=list)
    video_ai: List[str] = Field(default_factory=list)
    coach_notes: List[str] = Field(default_factory=list)


class WeeklyPriorityRecord(WeeklyPriorityModel):
    priority_id: str
    canonical_match_ids: List[str]
    pattern_ids: List[int]
    evidence_ids: List[int]
    topic: str
    phase: str
    priority_level: PriorityLevel
    confidence: float
    ranking_score: float
    reason: WeeklyPriorityReason
    references: WeeklyPriorityReferences
    status: PriorityStatus
    staff_status: Optional[PriorityStatus] = None
    staff_reason: Optional[str] = None
    staff_updated_at: Optional[datetime] = None
    staff_updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class WeeklyPriorityListResponse(WeeklyPriorityModel):
    ok: bool = True
    data: List[WeeklyPriorityRecord] = Field(default_factory=list)


class WeeklyPriorityDetailResponse(WeeklyPriorityModel):
    ok: bool = True
    data: WeeklyPriorityRecord


class WeeklyPriorityStaffRequest(WeeklyPriorityModel):
    status: PriorityStatus
    staff_reason: Optional[str] = Field(default=None, max_length=1200)
    topic: Optional[str] = Field(default=None, min_length=2, max_length=160)
    phase: Optional[str] = Field(default=None, min_length=2, max_length=80)
    priority_level: Optional[PriorityLevel] = None
