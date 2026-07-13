from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DecisionPhase = Literal["pre_match", "live_match", "halftime", "post_match", "weekly"]


class DecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DecisionEvaluateRequest(DecisionModel):
    phase: DecisionPhase
    team_profile_id: Optional[int] = Field(default=None, ge=1)
    match_id: Optional[str] = Field(default=None, max_length=120)
    minute: Optional[int] = Field(default=None, ge=0, le=180)
    score_state: Optional[str] = Field(default=None, max_length=40)
    prompt: Optional[str] = Field(default=None, max_length=600)
    source_context: Dict[str, Any] = Field(default_factory=dict)
    force: bool = False


class StaffDecisionRequest(DecisionModel):
    action: Literal["selected", "rejected_all", "save_later", "deepen", "different"]
    option_id: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = Field(default=None, max_length=2000)
    executed_manually: bool = False
    execution_reference: Optional[str] = Field(default=None, max_length=240)


class DecisionNoteRequest(DecisionModel):
    note: str = Field(min_length=1, max_length=2000)


class DecisionOutcomeRequest(DecisionModel):
    summary: str = Field(min_length=1, max_length=2000)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    confidence: Literal["bassa", "media", "alta"] = "bassa"


class DecisionEnvelope(DecisionModel):
    ok: bool = True
    data: dict
