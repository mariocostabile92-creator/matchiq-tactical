import json

from fastapi import APIRouter,Depends,HTTPException

from app.models.training_planner import TrainingEnvelope,TrainingPlanActionRequest,TrainingPlanGenerateRequest,TrainingPlanUpdateRequest
from app.repositories import training_planner_repository
from app.services import training_planner_service
from usage_guard import require_user


router=APIRouter(prefix="/api/training-planner",tags=["training-planner"])


@router.get("/library",response_model=TrainingEnvelope)
def library(theme: str=None,user=Depends(require_user)):
    return TrainingEnvelope(data={"items":training_planner_repository.list_exercises(theme,50)})


@router.post("/generate",response_model=TrainingEnvelope)
def generate(payload: TrainingPlanGenerateRequest,user=Depends(require_user)):
    if len(json.dumps(payload.local_context,ensure_ascii=False,default=str))>1_200_000: raise HTTPException(status_code=413,detail="Contesto Coach troppo grande")
    return TrainingEnvelope(**training_planner_service.generate(int(user["id"]),payload))


@router.get("/current",response_model=TrainingEnvelope)
def current(user=Depends(require_user)):
    return TrainingEnvelope(data=training_planner_service.current(int(user["id"])))


@router.get("/{plan_id}",response_model=TrainingEnvelope)
def detail(plan_id: int,user=Depends(require_user)):
    data=training_planner_service.get(int(user["id"]),plan_id)
    if not data: raise HTTPException(status_code=404,detail="Piano non trovato")
    return TrainingEnvelope(data=data)


@router.patch("/{plan_id}",response_model=TrainingEnvelope)
def modify(plan_id: int,payload: TrainingPlanUpdateRequest,user=Depends(require_user)):
    item=training_planner_service.modify(int(user["id"]),plan_id,payload.current_plan,payload.note)
    if not item: raise HTTPException(status_code=404,detail="Piano non trovato")
    return TrainingEnvelope(data={"plan":item})


@router.post("/{plan_id}/action",response_model=TrainingEnvelope)
def action(plan_id: int,payload: TrainingPlanActionRequest,user=Depends(require_user)):
    try: item=training_planner_service.action(int(user["id"]),plan_id,payload.action,payload.note)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    if not item: raise HTTPException(status_code=404,detail="Piano non trovato")
    return TrainingEnvelope(data={"plan":item})


@router.post("/{plan_id}/view",response_model=TrainingEnvelope)
def viewed(plan_id: int,user=Depends(require_user)):
    item=training_planner_service.mark_viewed(int(user["id"]),plan_id)
    if not item: raise HTTPException(status_code=404,detail="Piano non trovato")
    return TrainingEnvelope(data={"plan":item})
