from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.tactical_identity import IdentityEnvelope, IdentityNoteRequest, IdentityRunRequest, IdentityValidationRequest
from app.services import tactical_identity_service as service
from usage_guard import require_user


router=APIRouter(prefix="/api/tactical-identity",tags=["tactical-identity"])


def _id(user): return int(user["id"])


def _filters(team_profile_id: Optional[int]=None,season: Optional[str]=None,period_start: Optional[str]=None,period_end: Optional[str]=None,competition: Optional[str]=None,formation: Optional[str]=None,source_type: Optional[str]=None,dimension_group: Optional[str]=None,confidence_level: Optional[str]=None,validation_state: Optional[str]=None):
    return {key:value for key,value in locals().items() if value is not None}


@router.post("/run",response_model=IdentityEnvelope)
def run(payload: IdentityRunRequest,user=Depends(require_user)):
    try: return IdentityEnvelope(data=service.run(_id(user),payload.model_dump(exclude_none=True)))
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except RuntimeError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc


@router.get("",response_model=IdentityEnvelope)
def current(team_profile_id: Optional[int]=None,season: Optional[str]=None,period_start: Optional[str]=None,period_end: Optional[str]=None,competition: Optional[str]=None,formation: Optional[str]=None,source_type: Optional[str]=None,dimension_group: Optional[str]=None,confidence_level: Optional[str]=None,validation_state: Optional[str]=None,user=Depends(require_user)):
    data=service.current(_id(user),_filters(team_profile_id,season,period_start,period_end,competition,formation,source_type,dimension_group,confidence_level,validation_state))
    return IdentityEnvelope(data=data or {"status":"empty","message":"Non ci sono ancora partite sufficienti per costruire l'identita tattica."})


@router.get("/status",response_model=IdentityEnvelope)
def status(team_profile_id: Optional[int]=None,user=Depends(require_user)):
    return IdentityEnvelope(data=service.status(_id(user),{"team_profile_id":team_profile_id}))


@router.get("/dimensions",response_model=IdentityEnvelope)
def dimensions(dimension_group: Optional[str]=None,confidence_level: Optional[str]=None,validation_state: Optional[str]=None,user=Depends(require_user)):
    data=service.current(_id(user),_filters(dimension_group=dimension_group,confidence_level=confidence_level,validation_state=validation_state))
    return IdentityEnvelope(data={"items":(data or {}).get("dimensions",[])})


@router.get("/dimensions/{dimension_id}",response_model=IdentityEnvelope)
def dimension(dimension_id: int,page: int=Query(default=1,ge=1),page_size: int=Query(default=20,ge=1,le=100),user=Depends(require_user)):
    data=service.dimension(_id(user),dimension_id,page,page_size)
    if not data: raise HTTPException(status_code=404,detail="Dimensione non trovata")
    return IdentityEnvelope(data=data)


@router.get("/timeline",response_model=IdentityEnvelope)
def timeline(user=Depends(require_user)):
    data=service.current(_id(user),{}) or {}
    return IdentityEnvelope(data={"items":data.get("versions",[]),"last_updated":data.get("updated_at")})


@router.patch("/dimensions/{dimension_id}/validation",response_model=IdentityEnvelope)
def validation(dimension_id: int,payload: IdentityValidationRequest,user=Depends(require_user)):
    data=service.validate(_id(user),dimension_id,payload.model_dump(exclude_none=True))
    if not data: raise HTTPException(status_code=404,detail="Dimensione non trovata")
    return IdentityEnvelope(data=data)


@router.post("/dimensions/{dimension_id}/note",response_model=IdentityEnvelope)
def note(dimension_id: int,payload: IdentityNoteRequest,user=Depends(require_user)):
    data=service.add_note(_id(user),dimension_id,payload.note.strip())
    if not data: raise HTTPException(status_code=404,detail="Dimensione non trovata")
    return IdentityEnvelope(data=data)


@router.get("/compare",response_model=IdentityEnvelope)
def compare(team_profile_id: Optional[int]=None,season: Optional[str]=None,period_start: Optional[str]=None,period_end: Optional[str]=None,user=Depends(require_user)):
    return IdentityEnvelope(data=service.compare(_id(user),_filters(team_profile_id,season,period_start,period_end)))
