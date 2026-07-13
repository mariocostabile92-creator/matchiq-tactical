from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TacticalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationCreate(TacticalModel):
    title: Optional[str] = Field(default=None, max_length=120)
    context_scope: Dict[str, Any] = Field(default_factory=dict)


class ConversationUpdate(TacticalModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    status: Optional[str] = Field(default=None, pattern="^(active|archived)$")


class MessageCreate(TacticalModel):
    content: str = Field(min_length=2, max_length=1200)
    context: Dict[str, Any] = Field(default_factory=dict)


class FeedbackCreate(TacticalModel):
    rating: Optional[int] = Field(default=None, ge=-1, le=1)
    feedback_type: str = Field(default="utile", pattern="^(utile|non_utile|fonte_mancante|interpretazione_errata|troppo_generico)$")
    note: Optional[str] = Field(default=None, max_length=1000)


class TacticalEnvelope(TacticalModel):
    ok: bool = True
    data: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)
