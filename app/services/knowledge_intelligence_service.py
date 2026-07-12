from typing import Any, Dict, Optional

from app.repositories import knowledge_intelligence_repository as repository
from app.repositories import knowledge_intelligence_search_repository as search_repository
from app.repositories.knowledge_intelligence_schema import initialize_schema
from app.repositories import knowledge_repository
from app.services import knowledge_intelligence_sync
from app.services.knowledge_memory_query_service import execute as execute_memory_query,predefined


def initialize_knowledge_intelligence() -> None:
    initialize_schema()


def workspace(user_id: int) -> Dict[str,Any]:
    return knowledge_repository.get_or_create_workspace(user_id)


def sync(user_id: int,modules=None,force: bool=False) -> Dict[str,Any]:
    item=workspace(user_id); return knowledge_intelligence_sync.sync(user_id,int(item["id"]),modules,force)


def rebuild(user_id: int) -> Dict[str,Any]:
    item=workspace(user_id); return knowledge_intelligence_sync.rebuild(user_id,int(item["id"]))


def status(user_id: int) -> Dict[str,Any]:
    item=workspace(user_id); wid=int(item["id"]); return {"workspace_id":wid,"summary":repository.summary(wid),"sources":repository.list_sync_states(wid)}


def search(user_id: int,filters: Dict[str,Any]) -> Dict[str,Any]:
    item=workspace(user_id); return search_repository.search(int(item["id"]),filters)


def timeline(user_id: int,filters: Dict[str,Any]) -> Dict[str,Any]:
    item=workspace(user_id); return search_repository.timeline(int(item["id"]),filters)


def detail(user_id: int,node_id: int) -> Optional[Dict[str,Any]]:
    item=workspace(user_id); wid=int(item["id"]); node=repository.get_node(wid,node_id)
    if not node: return None
    return {"node":node,"relations":search_repository.relations(wid,node_id),"versions":search_repository.versions(wid,node_id),"notes":search_repository.notes(wid,node_id),"limits":["La memoria collega fonti; non dimostra causalita.","Le interpretazioni AI devono essere verificate dallo staff."]}


def validate(user_id: int,node_id: int,state: str,note: Optional[str]) -> Optional[Dict[str,Any]]:
    item=workspace(user_id); return search_repository.validate(int(item["id"]),node_id,state,note,f"user:{user_id}")


def add_note(user_id: int,node_id: int,note: str) -> Optional[Dict[str,Any]]:
    item=workspace(user_id); return search_repository.add_note(int(item["id"]),user_id,node_id,note)


def preset(user_id: int,name: str,params: Dict[str,Any]) -> Dict[str,Any]:
    item=workspace(user_id); return predefined(int(item["id"]),name,params)


def memory_query(user_id: int,payload: Dict[str,Any]) -> Dict[str,Any]:
    item=workspace(user_id); return execute_memory_query(int(item["id"]),payload)
