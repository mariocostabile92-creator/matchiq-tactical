from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WeeklyBriefingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WeeklyBriefingGenerateRequest(WeeklyBriefingModel):
    local_sources: Dict[str, Any] = Field(default_factory=dict)
    timezone: str = Field(default="Europe/Rome", max_length=80)


class WeeklyBriefingRecord(WeeklyBriefingModel):
    id: int
    user_id: int
    knowledge_id: int
    week_key: str
    source_fingerprint: str
    sources: Dict[str, Any]
    content: Dict[str, Any]
    priorities: List[Dict[str, Any]]
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WeeklyBriefingEnvelope(WeeklyBriefingModel):
    ok: bool = True
    generated: bool = False
    changed: bool = False
    briefing: Optional[WeeklyBriefingRecord] = None
