from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisMode(str, Enum):
    COACH = "coach"
    ANALYSIS = "analysis"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    REJECTED = "rejected"


class ConfidenceLabel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PipelineStage(str, Enum):
    VALIDATION = "validation"
    METADATA = "metadata"
    SEGMENTATION = "segmentation"
    CANDIDATES = "candidate_detection"
    CLASSIFICATION = "classification"
    FRAME_RANKING = "frame_ranking"
    CLIPS = "clip_windows"
    EVIDENCE = "evidence_generation"
    REVIEW = "human_review"
    REPORT = "report_generation"


class VideoEvidence(BaseModel):
    evidence_id: str
    project_id: str
    video_id: int
    analysis_mode: AnalysisMode
    phase_type: str = "unclassified"
    event_type: Optional[str] = None
    team_context: Optional[str] = None
    start_timestamp_ms: int
    end_timestamp_ms: int
    representative_timestamp_ms: int
    representative_frame: Dict[str, Any] = Field(default_factory=dict)
    clip_reference: Optional[Dict[str, Any]] = None
    title: str
    observation: str
    interpretation: Optional[str] = None
    motivation: str
    confidence_score: float
    confidence_label: ConfidenceLabel
    source_type: str
    linked_match_event_id: Optional[str] = None
    linked_note_id: Optional[str] = None
    link_type: Optional[str] = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[str] = None
    user_correction: Optional[str] = None
    created_at: str


class VideoProjectCreate(BaseModel):
    video_asset_id: Optional[int] = None
    analysis_mode: AnalysisMode = AnalysisMode.ANALYSIS
    title: str = ""
    observed_team: str = ""
    opponent: str = ""
    video_type: str = "full_analysis"
    period: str = "full_match"
    perspective: str = "own_team"
    notes: str = ""
    match_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class VideoPipelineRequest(BaseModel):
    idempotency_key: str = ""
    duration_seconds: float = 0
    frame_times_ms: List[int] = Field(default_factory=list)
    frame_meta: List[Dict[str, Any]] = Field(default_factory=list)
    staff_events: List[Dict[str, Any]] = Field(default_factory=list)


class ProjectStateRequest(BaseModel):
    status: str
    stage: str = ""
    progress: Optional[int] = None
    error_code: str = ""
    error_message: str = ""


class EvidenceReviewRequest(BaseModel):
    status: ReviewStatus
    title: Optional[str] = None
    observation: Optional[str] = None
    interpretation: Optional[str] = None
    phase_type: Optional[str] = None
    user_correction: Optional[str] = None


class EvidenceFrameRequest(BaseModel):
    representative_timestamp_ms: int
    frame_index: Optional[int] = None
    motivation: str = "Selezione manuale dello staff"


class EvidenceClipRequest(BaseModel):
    start_timestamp_ms: int
    end_timestamp_ms: int


class EvidenceLinkRequest(BaseModel):
    linked_match_event_id: Optional[str] = None
    linked_note_id: Optional[str] = None
    link_type: str = "manual"


class EvidenceCreateRequest(BaseModel):
    phase_type: str = "unclassified"
    event_type: Optional[str] = None
    team_context: Optional[str] = None
    start_timestamp_ms: int
    end_timestamp_ms: int
    representative_timestamp_ms: int
    representative_frame: Dict[str, Any] = Field(default_factory=dict)
    title: str
    observation: str
    interpretation: Optional[str] = None
    motivation: str
    confidence_score: float = 0
    source_type: str = "staff_manual"
