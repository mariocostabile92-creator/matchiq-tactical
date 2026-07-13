from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.decision_engine import DecisionEnvelope, DecisionEvaluateRequest, DecisionNoteRequest, DecisionOutcomeRequest, StaffDecisionRequest
from app.services import decision_engine_service as service
from usage_guard import require_user


router=APIRouter(prefix="/api/decision-engine",tags=["decision-engine"])
def _id(user): return int(user["id"])


@router.post("/evaluate",response_model=DecisionEnvelope)
def evaluate(payload: DecisionEvaluateRequest,user=Depends(require_user)):
    try: return DecisionEnvelope(data=service.evaluate(_id(user),payload.model_dump(exclude_none=True)))
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc


@router.get("/cases",response_model=DecisionEnvelope)
def cases(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),phase:Optional[str]=None,user=Depends(require_user)): return DecisionEnvelope(data=service.cases(_id(user),page,page_size,phase))


@router.get("/cases/{case_id}",response_model=DecisionEnvelope)
def case(case_id:int,user=Depends(require_user)):
    data=service.full_case(_id(user),case_id)
    if not data: raise HTTPException(status_code=404,detail="Caso decisionale non trovato")
    return DecisionEnvelope(data=data)


@router.get("/cases/{case_id}/options",response_model=DecisionEnvelope)
def options(case_id:int,user=Depends(require_user)):
    data=service.full_case(_id(user),case_id)
    if not data: raise HTTPException(status_code=404,detail="Caso decisionale non trovato")
    return DecisionEnvelope(data={"items":data["options"]})


@router.post("/cases/{case_id}/decision",response_model=DecisionEnvelope)
def decision(case_id:int,payload:StaffDecisionRequest,user=Depends(require_user)):
    try: data=service.staff_decision(_id(user),case_id,payload.model_dump(exclude_none=True))
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not data: raise HTTPException(status_code=404,detail="Caso o opzione non trovati")
    return DecisionEnvelope(data=data)


@router.post("/cases/{case_id}/note",response_model=DecisionEnvelope)
def note(case_id:int,payload:DecisionNoteRequest,user=Depends(require_user)):
    data=service.note(_id(user),case_id,payload.note.strip())
    if not data: raise HTTPException(status_code=404,detail="Caso non trovato")
    return DecisionEnvelope(data=data)


@router.post("/cases/{case_id}/outcomes/{decision_id}",response_model=DecisionEnvelope)
def add_outcome(case_id:int,decision_id:int,payload:DecisionOutcomeRequest,user=Depends(require_user)):
    data=service.add_outcome(_id(user),case_id,decision_id,payload.model_dump())
    if not data: raise HTTPException(status_code=404,detail="Decisione non trovata")
    return DecisionEnvelope(data=data)


@router.get("/cases/{case_id}/outcome",response_model=DecisionEnvelope)
def outcome(case_id:int,user=Depends(require_user)):
    data=service.full_case(_id(user),case_id)
    if not data: raise HTTPException(status_code=404,detail="Caso non trovato")
    return DecisionEnvelope(data={"items":data["outcomes"]})


@router.get("/similar",response_model=DecisionEnvelope)
def similar(phase:Optional[str]=None,user=Depends(require_user)): return DecisionEnvelope(data=service.cases(_id(user),1,10,phase))


@router.get("/status",response_model=DecisionEnvelope)
def status(user=Depends(require_user)): return DecisionEnvelope(data=service.status(_id(user)))
