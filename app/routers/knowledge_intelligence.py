from typing import Optional

from fastapi import APIRouter,Depends,HTTPException,Query

from app.models.knowledge_intelligence import KnowledgeEnvelope,KnowledgeNoteRequest,KnowledgeSyncRequest,KnowledgeValidationRequest,TacticalMemoryQuery
from app.services import knowledge_intelligence_service as service
from usage_guard import require_user


router=APIRouter(prefix="/api/knowledge-intelligence",tags=["knowledge-intelligence"])


def _id(user) -> int: return int(user["id"])


@router.post("/sync",response_model=KnowledgeEnvelope)
def sync(payload: KnowledgeSyncRequest,user=Depends(require_user)):
    try: data=service.sync(_id(user),payload.modules or None,payload.force)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    return KnowledgeEnvelope(data=data,errors=[{"module":name,"message":item.get("error")} for name,item in data["modules"].items() if item["status"]=="error"])


@router.post("/rebuild",response_model=KnowledgeEnvelope)
def rebuild(user=Depends(require_user)): return KnowledgeEnvelope(data=service.rebuild(_id(user)))


@router.get("/status",response_model=KnowledgeEnvelope)
def status(user=Depends(require_user)): return KnowledgeEnvelope(data=service.status(_id(user)))


@router.get("/search",response_model=KnowledgeEnvelope)
def search(text: Optional[str]=Query(default=None,max_length=200),node_type: Optional[str]=None,source_module: Optional[str]=None,team: Optional[str]=None,match_id: Optional[str]=None,player_id: Optional[str]=None,tactical_topic: Optional[str]=None,zone: Optional[str]=None,reliability_level: Optional[str]=None,validation_state: Optional[str]=None,polarity: Optional[str]=None,date_from: Optional[str]=None,date_to: Optional[str]=None,season: Optional[str]=None,tag: Optional[str]=None,relation_type: Optional[str]=None,page: int=Query(default=1,ge=1),page_size: int=Query(default=20,ge=1,le=100),user=Depends(require_user)):
    filters=locals(); filters.pop("user"); return KnowledgeEnvelope(data=service.search(_id(user),filters))


@router.get("/timeline",response_model=KnowledgeEnvelope)
def timeline(node_type: Optional[str]=None,source_module: Optional[str]=None,match_id: Optional[str]=None,tactical_topic: Optional[str]=None,zone: Optional[str]=None,reliability_level: Optional[str]=None,date_from: Optional[str]=None,date_to: Optional[str]=None,page: int=Query(default=1,ge=1),page_size: int=Query(default=20,ge=1,le=100),user=Depends(require_user)):
    filters=locals(); filters.pop("user"); return KnowledgeEnvelope(data=service.timeline(_id(user),filters))


@router.get("/nodes/{node_id}",response_model=KnowledgeEnvelope)
def detail(node_id: int,user=Depends(require_user)):
    data=service.detail(_id(user),node_id)
    if not data: raise HTTPException(status_code=404,detail="Elemento Knowledge non trovato")
    return KnowledgeEnvelope(data=data)


@router.get("/nodes/{node_id}/relations",response_model=KnowledgeEnvelope)
def relations(node_id: int,user=Depends(require_user)):
    data=service.detail(_id(user),node_id)
    if not data: raise HTTPException(status_code=404,detail="Elemento Knowledge non trovato")
    return KnowledgeEnvelope(data={"items":data["relations"]})


@router.get("/nodes/{node_id}/versions",response_model=KnowledgeEnvelope)
def versions(node_id: int,user=Depends(require_user)):
    data=service.detail(_id(user),node_id)
    if not data: raise HTTPException(status_code=404,detail="Elemento Knowledge non trovato")
    return KnowledgeEnvelope(data={"items":data["versions"]})


@router.patch("/nodes/{node_id}/validation",response_model=KnowledgeEnvelope)
def validation(node_id: int,payload: KnowledgeValidationRequest,user=Depends(require_user)):
    try: node=service.validate(_id(user),node_id,payload.state,payload.note)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    if not node: raise HTTPException(status_code=404,detail="Elemento Knowledge non trovato")
    return KnowledgeEnvelope(data={"node":node})


@router.post("/nodes/{node_id}/notes",response_model=KnowledgeEnvelope)
def note(node_id: int,payload: KnowledgeNoteRequest,user=Depends(require_user)):
    data=service.add_note(_id(user),node_id,payload.note)
    if not data: raise HTTPException(status_code=404,detail="Elemento Knowledge non trovato")
    return KnowledgeEnvelope(data=data)


@router.get("/queries/{name}",response_model=KnowledgeEnvelope)
def query(name: str,zone: Optional[str]=None,player_id: Optional[str]=None,topic: Optional[str]=None,match_id: Optional[str]=None,page: int=1,page_size: int=20,user=Depends(require_user)):
    try: data=service.preset(_id(user),name,{"zone":zone,"player_id":player_id,"topic":topic,"match_id":match_id,"page":page,"page_size":page_size})
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    return KnowledgeEnvelope(data=data)


@router.post("/memory-query",response_model=KnowledgeEnvelope)
def memory_query(payload: TacticalMemoryQuery,user=Depends(require_user)): return KnowledgeEnvelope(data=service.memory_query(_id(user),payload.model_dump()))
