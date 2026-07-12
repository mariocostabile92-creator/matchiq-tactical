from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


VoiceIntent = Literal[
    "player_event",
    "substitution",
    "tactical_note",
    "player_note",
    "score_update",
    "match_control",
    "cancel",
    "unknown",
]


class VoiceCoachPlayer(BaseModel):
    id: Any = ""
    number: str = ""
    name: str = ""
    side: Literal["home", "away"] = "home"
    role: str = ""
    status: str = ""


class VoiceCoachMatchContext(BaseModel):
    match_id: Optional[Any] = None
    home_team: str = "Casa"
    away_team: str = "Trasferta"
    current_minute: int = Field(default=0, ge=0, le=130)
    period: str = "1T"
    selected_team: Literal["home", "away"] = "home"
    lineup: List[VoiceCoachPlayer] = Field(default_factory=list)


class VoiceCoachInterpretRequest(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=600)
    source: Literal["speech", "text"] = "text"
    context: VoiceCoachMatchContext = Field(default_factory=VoiceCoachMatchContext)


class VoiceCoachInterpretResponse(BaseModel):
    intent: VoiceIntent
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_confirmation: bool = True
    minute: int = Field(default=0, ge=0, le=130)
    team: Literal["home", "away"] = "home"
    entities: Dict[str, Any] = Field(default_factory=dict)
    normalized_summary: str = ""
    ambiguities: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    privacy: Dict[str, Any] = Field(default_factory=dict)
