from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class IdentityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IdentityScope(IdentityModel):
    team_profile_id: Optional[int] = Field(default=None, ge=1)
    coach_profile_id: Optional[int] = Field(default=None, ge=1)
    season: Optional[str] = Field(default=None, max_length=40)
    period_start: Optional[str] = Field(default=None, max_length=40)
    period_end: Optional[str] = Field(default=None, max_length=40)
    competition: Optional[str] = Field(default=None, max_length=160)
    formation: Optional[str] = Field(default=None, max_length=40)
    source_type: Optional[str] = Field(default=None, max_length=80)
    confidence_level: Optional[Literal["bassa", "media", "alta"]] = None
    validation_state: Optional[str] = Field(default=None, max_length=60)


class IdentityRunRequest(IdentityScope):
    force: bool = False
    retry: bool = False


class IdentityValidationRequest(IdentityModel):
    action: Literal["confirmed", "contested", "monitor", "not_representative", "update_declared"]
    note: Optional[str] = Field(default=None, max_length=2000)
    declared_value: Optional[str] = Field(default=None, max_length=2000)


class IdentityNoteRequest(IdentityModel):
    note: str = Field(min_length=1, max_length=2000)


class IdentityEnvelope(IdentityModel):
    ok: bool = True
    data: dict
