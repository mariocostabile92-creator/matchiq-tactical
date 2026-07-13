from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeIntelligenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeSearchQuery(KnowledgeIntelligenceModel):
    text: Optional[str] = Field(default=None, max_length=200)
    node_type: Optional[str] = Field(default=None, max_length=50)
    source_module: Optional[str] = Field(default=None, max_length=50)
    team: Optional[str] = Field(default=None, max_length=120)
    match_id: Optional[str] = Field(default=None, max_length=100)
    player_id: Optional[str] = Field(default=None, max_length=100)
    tactical_topic: Optional[str] = Field(default=None, max_length=100)
    zone: Optional[str] = Field(default=None, max_length=80)
    reliability_level: Optional[str] = Field(default=None, max_length=20)
    validation_state: Optional[str] = Field(default=None, max_length=40)
    source_id: Optional[str] = Field(default=None, max_length=120)
    node_id: Optional[int] = Field(default=None, ge=1)
    polarity: Optional[str] = Field(default=None, max_length=20)
    date_from: Optional[str] = Field(default=None, max_length=40)
    date_to: Optional[str] = Field(default=None, max_length=40)
    season: Optional[str] = Field(default=None, max_length=40)
    tag: Optional[str] = Field(default=None, max_length=60)
    relation_type: Optional[str] = Field(default=None, max_length=50)
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=20, ge=1, le=100)


class KnowledgeValidationRequest(KnowledgeIntelligenceModel):
    state: str = Field(min_length=3, max_length=40)
    note: Optional[str] = Field(default=None, max_length=1200)


class KnowledgeNoteRequest(KnowledgeIntelligenceModel):
    note: str = Field(min_length=1, max_length=2000)


class KnowledgeSyncRequest(KnowledgeIntelligenceModel):
    modules: List[str] = Field(default_factory=list, max_length=20)
    force: bool = False


class TacticalMemoryQuery(KnowledgeIntelligenceModel):
    team: Optional[str] = Field(default=None, max_length=120)
    question: Dict[str, Any] = Field(default_factory=dict)
    period: Dict[str, Optional[str]] = Field(default_factory=dict)
    themes: List[str] = Field(default_factory=list, max_length=20)
    players: List[str] = Field(default_factory=list, max_length=30)
    zones: List[str] = Field(default_factory=list, max_length=20)
    source_types: List[str] = Field(default_factory=list, max_length=30)
    node_types: List[str] = Field(default_factory=list, max_length=30)
    match_id: Optional[str] = Field(default=None, max_length=100)
    season: Optional[str] = Field(default=None, max_length=40)
    validation_state: Optional[str] = Field(default=None, max_length=40)
    source_id: Optional[str] = Field(default=None, max_length=120)
    node_id: Optional[int] = Field(default=None, ge=1)
    minimum_reliability: str = Field(default="bassa", max_length=20)
    limit: int = Field(default=20, ge=1, le=100)


class KnowledgeEnvelope(KnowledgeIntelligenceModel):
    ok: bool = True
    data: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)
