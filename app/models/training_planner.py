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


class TrainingEnvelope(TrainingModel):
    ok: bool=True
    generated: bool=False
    changed: bool=False
    data: Optional[Dict[str,Any]]=None
