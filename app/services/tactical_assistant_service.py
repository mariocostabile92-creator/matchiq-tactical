from typing import Any, Dict, Optional

from app.repositories import knowledge_repository,tactical_assistant_repository as repository
from app.repositories.tactical_assistant_schema import initialize_schema
from app.services import knowledge_intelligence_service,tactical_assistant_orchestrator
from app.services.tactical_assistant_intents import supported_intents
from app.services.tactical_assistant_policy import enforce_rate,validate_question
from usage_guard import build_frontend_limits


def initialize_tactical_assistant() -> None: initialize_schema()


def _workspace(user_id: int) -> Dict[str,Any]: return knowledge_repository.get_or_create_workspace(user_id)


def create(user: Dict[str,Any],title: str=None,scope: Dict[str,Any]=None) -> Dict[str,Any]:
    workspace=_workspace(int(user["id"])); return repository.create_conversation(int(workspace["id"]),int(user["id"]),title or "Nuova analisi",scope or {})


def conversations(user: Dict[str,Any],status: str=None):
    workspace=_workspace(int(user["id"])); return repository.list_conversations(int(workspace["id"]),int(user["id"]),status)


def detail(user: Dict[str,Any],conversation_id: int) -> Optional[Dict[str,Any]]:
    workspace=_workspace(int(user["id"])); wid=int(workspace["id"]); conversation=repository.get_conversation(wid,int(user["id"]),conversation_id)
    if not conversation:return None
    return {"conversation":conversation,"messages":repository.list_messages(wid,int(user["id"]),conversation_id)}


def update(user: Dict[str,Any],conversation_id: int,changes: Dict[str,Any]):
    workspace=_workspace(int(user["id"])); return repository.update_conversation(int(workspace["id"]),int(user["id"]),conversation_id,**changes)


def delete(user: Dict[str,Any],conversation_id: int) -> bool:
    workspace=_workspace(int(user["id"])); return repository.delete_conversation(int(workspace["id"]),int(user["id"]),conversation_id)


def ask(user: Dict[str,Any],conversation_id: int,content: str,context: Dict[str,Any]) -> Optional[Dict[str,Any]]:
    enforce_rate(user); question=validate_question(content); workspace=_workspace(int(user["id"])); wid=int(workspace["id"]); conversation=repository.get_conversation(wid,int(user["id"]),conversation_id)
    if not conversation:return None
    if conversation["status"]=="archived": repository.update_conversation(wid,int(user["id"]),conversation_id,status="active"); conversation=repository.get_conversation(wid,int(user["id"]),conversation_id)
    if conversation["title"]=="Nuova analisi": repository.update_conversation(wid,int(user["id"]),conversation_id,title=" ".join(question.split()[:7])[:120]); conversation=repository.get_conversation(wid,int(user["id"]),conversation_id)
    return tactical_assistant_orchestrator.answer(user,wid,conversation,question,context)


def feedback(user: Dict[str,Any],message_id: int,payload: Dict[str,Any]):
    workspace=_workspace(int(user["id"])); return repository.save_feedback(int(workspace["id"]),int(user["id"]),message_id,payload.get("rating"),payload["feedback_type"],payload.get("note"))


def config(user: Dict[str,Any]) -> Dict[str,Any]:
    summary=knowledge_intelligence_service.status(int(user["id"]))["summary"]; types=summary.get("by_type") or {}; suggestions=[]
    if types.get("historical_pattern"): suggestions.append("Quali pattern non risultano ancora risolti?")
    if types.get("training_plan"): suggestions.append("Quale piano allenamento e stato proposto e perche?")
    if types.get("voice_observation"): suggestions.append("Quali osservazioni dello staff ricorrono piu spesso?")
    if types.get("video_report"): suggestions.append("Quali report Video AI sono disponibili?")
    if not suggestions: suggestions=["Cosa contiene la memoria tecnica?","Quali dati devo raccogliere per ottenere una risposta affidabile?"]
    return {"plan":build_frontend_limits(user),"knowledge_summary":summary,"suggestions":suggestions[:5],"intents":supported_intents(),"limits":{"question_max":1200,"context_sources_max":20,"hourly_technical_guard":30},"provider":{"name":"OpenAI","model_configured":bool(__import__('os').getenv('OPENAI_API_KEY'))}}
