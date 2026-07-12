import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.pattern_intelligence import PatternEnvelope, PatternListQuery, PatternNoteRequest, PatternRunRequest, PatternStatusRequest
from app.services import pattern_intelligence_service
from usage_guard import require_user


router=APIRouter(prefix="/api/pattern-intelligence",tags=["pattern-intelligence"])


@router.post("/run",response_model=PatternEnvelope)
def run_patterns(payload: PatternRunRequest,user=Depends(require_user)):
    if len(json.dumps(payload.local_matches,ensure_ascii=False,default=str))>1_200_000:
        raise HTTPException(status_code=413,detail="Storico Coach troppo grande")
    try:
        result=pattern_intelligence_service.run(int(user["id"]),payload)
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc
    return PatternEnvelope(**result)


@router.get("",response_model=PatternEnvelope)
def list_patterns(category: str=None,polarity: str=None,topic: str=None,status: str=None,confidence: str=None,source: str=None,page: int=Query(1,ge=1),page_size: int=Query(12,ge=1,le=50),user=Depends(require_user)):
    query=PatternListQuery(category=category,polarity=polarity,topic=topic,status=status,confidence=confidence,source=source,page=page,page_size=page_size)
    return PatternEnvelope(data=pattern_intelligence_service.list_for_user(int(user["id"]),query))


@router.get("/status",response_model=PatternEnvelope)
def pattern_status(user=Depends(require_user)):
    return PatternEnvelope(data=pattern_intelligence_service.summary(int(user["id"])))


@router.post("/impact",response_model=PatternEnvelope)
def pattern_impact(payload: dict,user=Depends(require_user)):
    return PatternEnvelope(data=pattern_intelligence_service.post_match_impact(int(user["id"]),payload))


@router.get("/{pattern_id}",response_model=PatternEnvelope)
def pattern_detail(pattern_id: int,evidence_page: int=Query(1,ge=1),evidence_size: int=Query(20,ge=1,le=50),user=Depends(require_user)):
    item=pattern_intelligence_service.detail(int(user["id"]),pattern_id,evidence_page,evidence_size)
    if not item: raise HTTPException(status_code=404,detail="Pattern non trovato")
    return PatternEnvelope(data=item)


@router.patch("/{pattern_id}/status",response_model=PatternEnvelope)
def update_status(pattern_id: int,payload: PatternStatusRequest,user=Depends(require_user)):
    try: item=pattern_intelligence_service.set_status(int(user["id"]),pattern_id,payload.status)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    if not item: raise HTTPException(status_code=404,detail="Pattern non trovato")
    return PatternEnvelope(data=item)


@router.post("/{pattern_id}/note",response_model=PatternEnvelope)
def add_note(pattern_id: int,payload: PatternNoteRequest,user=Depends(require_user)):
    item=pattern_intelligence_service.add_note(int(user["id"]),pattern_id,payload.note)
    if not item: raise HTTPException(status_code=404,detail="Pattern non trovato")
    return PatternEnvelope(data=item)
