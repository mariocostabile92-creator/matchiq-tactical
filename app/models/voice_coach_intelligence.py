from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class VoiceIntelligenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VoiceObservationCreate(VoiceIntelligenceModel):
    client_id: str = Field(min_length=3, max_length=120)
    match_key: str = Field(min_length=1, max_length=160)
    match_id: Optional[str] = Field(default=None, max_length=160)
    intent: str = Field(max_length=60)
    confidence: float = Field(default=0.0, ge=0, le=1)
    original_text: str = Field(max_length=2000)
    normalized_summary: str = Field(default="", max_length=3000)
    minute: int = Field(default=0, ge=0, le=130)
    match_phase: str = Field(default="1T", max_length=30)
    team: str = Field(default="home", max_length=40)
    player_ids: List[str] = Field(default_factory=list, max_length=20)
    player_names: List[str] = Field(default_factory=list, max_length=20)
    tactical_topic: str = Field(default="general_note", max_length=80)
    topic_label: str = Field(default="Nota staff", max_length=160)
    zone: str = Field(default="not_specified", max_length=80)
    polarity: Literal["positive", "negative", "neutral"] = "neutral"
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    source: Literal["speech", "text"] = "text"
    requires_confirmation: bool = False
    ambiguities: List[str] = Field(default_factory=list, max_length=20)
    warnings: List[str] = Field(default_factory=list, max_length=20)
    evidence: List[str] = Field(default_factory=list, max_length=20)
    explanation: str = Field(default="", max_length=2000)
    status: Literal["pending", "confirmed", "cancelled"] = "confirmed"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceObservation(VoiceObservationCreate):
    id: int
    knowledge_id: int
    created_at: datetime
    updated_at: datetime


class VoiceTheme(VoiceIntelligenceModel):
    id: int
    topic: str
    label: str
    zone: str
    count: int
    first_minute: int
    last_minute: int
    involved_players: List[str] = Field(default_factory=list)
    polarity: str
    highest_priority: str
    source_observation_ids: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    status: Literal["active", "confirmed", "ignored", "resolved"] = "active"
    updated_at: datetime


class VoiceMatchIntelligence(VoiceIntelligenceModel):
    observations: List[VoiceObservation] = Field(default_factory=list)
    themes: List[VoiceTheme] = Field(default_factory=list)
    proactive_suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    halftime: Dict[str, Any] = Field(default_factory=dict)
    post_match: Dict[str, Any] = Field(default_factory=dict)


class VoiceThemeStatusUpdate(VoiceIntelligenceModel):
    status: Literal["active", "confirmed", "ignored", "resolved"]
