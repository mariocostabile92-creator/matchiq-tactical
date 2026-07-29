from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TrainingModel(BaseModel):
    model_config=ConfigDict(extra="forbid")


class TrainingPlanGenerateRequest(TrainingModel):
    training_days: List[str]=Field(min_length=1,max_length=7)
    players: int=Field(default=18,ge=6,le=40)
    goalkeepers: int=Field(default=2,ge=0,le=6)
    session_duration: int=Field(default=90,ge=30,le=180)
    intensity: str=Field(default="media",max_length=30)
    category: str=Field(default="Dilettanti",max_length=80)
    local_context: Dict[str,Any]=Field(default_factory=dict)
    force: bool=False


class TrainingPlanUpdateRequest(TrainingModel):
    current_plan: Dict[str,Any]
    note: Optional[str]=Field(default=None,max_length=1200)


class TrainingPlanActionRequest(TrainingModel):
    action: str=Field(min_length=3,max_length=30)
    note: Optional[str]=Field(default=None,max_length=1200)


class TrainingDraftReferences(TrainingModel):
    canonical_match_ids: List[str]=Field(default_factory=list)
    pattern_ids: List[int]=Field(default_factory=list)
    evidence_ids: List[int]=Field(default_factory=list)


class TrainingDraftSession(TrainingModel):
    session_id: str
    title: str
    day: str
    objective: str
    why: str
    theme: str
    duration: int
    players: int
    goalkeepers: int
    intensity: str
    drills: List[Dict[str,Any]]=Field(default_factory=list)
    notes: str=""
    status: str="proposta_ai"
    priority_ids: List[str]=Field(default_factory=list)
    references: TrainingDraftReferences


class TrainingDraftPayload(TrainingModel):
    contract: str="weekly-priority-training-draft-v1"
    title: str
    sessions: List[TrainingDraftSession]=Field(default_factory=list)
    priorities: List[Dict[str,Any]]=Field(default_factory=list)
    disclaimer: str


class TrainingEnvelope(TrainingModel):
    ok: bool=True
    generated: bool=False
    changed: bool=False
    data: Optional[Dict[str,Any]]=None
