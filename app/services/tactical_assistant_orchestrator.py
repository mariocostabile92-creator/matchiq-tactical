import time
from typing import Any, Dict

from app.repositories import tactical_assistant_repository as repository
from app.services import tactical_assistant_context,tactical_assistant_evidence,tactical_assistant_generation,tactical_assistant_query_planner,tactical_assistant_response_builder,tactical_assistant_retrieval,tactical_assistant_sources


def answer(user: Dict[str,Any],workspace_id: int,conversation: Dict[str,Any],question: str,request_context: Dict[str,Any]) -> Dict[str,Any]:
    started=time.perf_counter(); conversation_id=int(conversation["id"]); history=repository.list_messages(workspace_id,int(user["id"]),conversation_id,30)
    context=tactical_assistant_context.recent_context(history,conversation.get("context_summary_json") or {})
    query=tactical_assistant_query_planner.plan(question,context,request_context)
    user_message=repository.add_message(conversation_id,"user",question,query["intent"],query,"question")
    retrieval={"nodes":[],"relations":[],"evidence":[],"provenance":[],"contradictions":[],"limits":[],"query_applied":{}}
    if not query["needs_clarification"]: retrieval=tactical_assistant_retrieval.retrieve(int(user["id"]),query)
    assessment=tactical_assistant_evidence.assess(retrieval); sources=tactical_assistant_sources.build(retrieval)
    base=tactical_assistant_response_builder.build(question,query,retrieval,assessment,sources); response,provider=tactical_assistant_generation.enhance(base,question,query,assessment,sources)
    limitations=list(dict.fromkeys([*assessment["limitations"],*(response.pop("limitations",[]) or [])]))[:8]
    response.update({"intent":query["intent"],"query_applied":retrieval.get("query_applied") or query,"sufficiency":assessment,"sources":sources,"limitations":limitations,"source_count":len(sources),"period":{"from":query.get("period",{}).get("from"),"to":query.get("period",{}).get("to")}})
    content=response["direct_answer"]; assistant=repository.add_message(conversation_id,"assistant",content,query["intent"],query,response["answer_type"],assessment["level"],assessment["sufficient"],limitations,response)
    repository.add_sources(assistant["id"],sources); summary=tactical_assistant_context.update(context,query,sources); repository.update_conversation(workspace_id,int(user["id"]),conversation_id,context_summary_json=summary)
    latency=int((time.perf_counter()-started)*1000); outcome="clarification" if query["needs_clarification"] else assessment["level"]
    repository.record_telemetry(workspace_id,int(user["id"]),conversation_id,query["intent"],outcome,len(sources),latency,provider["provider"],provider["model"],provider.get("error"),provider.get("estimated_tokens",0))
    assistant["response_json"]=response; assistant["sources"]=sources; return {"user_message":user_message,"assistant_message":assistant,"conversation":repository.get_conversation(workspace_id,int(user["id"]),conversation_id)}
