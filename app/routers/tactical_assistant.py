from typing import Optional

from fastapi import APIRouter,Depends,HTTPException,Query,Request,Response

from app.models.tactical_assistant import ConversationCreate,ConversationUpdate,FeedbackCreate,MessageCreate,TacticalEnvelope
from app.services import tactical_assistant_service as service
from usage_guard import require_user
from app.security.rate_limit import enforce_rate_limit


router=APIRouter(prefix="/api/tactical-assistant",tags=["tactical-assistant"])


@router.get("/config",response_model=TacticalEnvelope)
def config(user=Depends(require_user)): return TacticalEnvelope(data=service.config(user))


@router.get("/conversations",response_model=TacticalEnvelope)
def conversations(status: Optional[str]=Query(default=None,pattern="^(active|archived)$"),user=Depends(require_user)): return TacticalEnvelope(data={"items":service.conversations(user,status)})


@router.post("/conversations",response_model=TacticalEnvelope,status_code=201)
def create(payload: ConversationCreate,user=Depends(require_user)): return TacticalEnvelope(data={"conversation":service.create(user,payload.title,payload.context_scope)})


@router.get("/conversations/{conversation_id}",response_model=TacticalEnvelope)
def detail(conversation_id: int,user=Depends(require_user)):
    data=service.detail(user,conversation_id)
    if not data: raise HTTPException(status_code=404,detail="Conversazione non trovata")
    return TacticalEnvelope(data=data)


@router.patch("/conversations/{conversation_id}",response_model=TacticalEnvelope)
def update(conversation_id: int,payload: ConversationUpdate,user=Depends(require_user)):
    data=service.update(user,conversation_id,payload.model_dump(exclude_none=True))
    if not data: raise HTTPException(status_code=404,detail="Conversazione non trovata")
    return TacticalEnvelope(data={"conversation":data})


@router.delete("/conversations/{conversation_id}",status_code=204)
def delete(conversation_id: int,user=Depends(require_user)):
    if not service.delete(user,conversation_id): raise HTTPException(status_code=404,detail="Conversazione non trovata")
    return Response(status_code=204)


@router.post("/conversations/{conversation_id}/messages",response_model=TacticalEnvelope)
def message(conversation_id: int,payload: MessageCreate,request:Request,user=Depends(require_user)):
    enforce_rate_limit(request,"tactical_assistant.message",20,60,str(user["id"]))
    data=service.ask(user,conversation_id,payload.content,payload.context)
    if not data: raise HTTPException(status_code=404,detail="Conversazione non trovata")
    return TacticalEnvelope(data=data)


@router.post("/messages/{message_id}/feedback",response_model=TacticalEnvelope)
def feedback(message_id: int,payload: FeedbackCreate,user=Depends(require_user)):
    data=service.feedback(user,message_id,payload.model_dump())
    if not data: raise HTTPException(status_code=404,detail="Messaggio non trovato")
    return TacticalEnvelope(data={"feedback":data})
