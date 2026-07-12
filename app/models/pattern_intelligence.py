from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PatternModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PatternRunRequest(PatternModel):
    period_days: int = Field(default=120, ge=14, le=730)
    team_profile_id: Optional[int] = None
    local_matches: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    force: bool = False


class PatternListQuery(PatternModel):
    category: Optional[str] = None
    polarity: Optional[str] = None
    topic: Optional[str] = None
    status: Optional[str] = None
    confidence: Optional[str] = None
    source: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=12, ge=1, le=50)


class PatternStatusRequest(PatternModel):
    status: str = Field(min_length=3, max_length=40)


class PatternNoteRequest(PatternModel):
    note: str = Field(min_length=1, max_length=1200)


class PatternEnvelope(PatternModel):
    ok: bool = True
    generated: bool = False
    changed: bool = False
    data: Optional[Dict[str, Any]] = None
