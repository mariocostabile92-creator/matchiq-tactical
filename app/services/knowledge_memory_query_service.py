from typing import Any, Dict

from app.repositories import knowledge_intelligence_search_repository as search_repository


RELIABILITY_ORDER={"bassa":0,"media":1,"alta":2}


def execute(workspace_id: int,query: Dict[str,Any]) -> Dict[str,Any]:
    filters={
      "text":str((query.get("question") or {}).get("text") or "")[:200] or None,
      "team":query.get("team"),"date_from":(query.get("period") or {}).get("from"),"date_to":(query.get("period") or {}).get("to"),
      "tactical_topic":(query.get("themes") or [None])[0],"player_id":(query.get("players") or [None])[0],"zone":(query.get("zones") or [None])[0],
      "source_module":(query.get("source_types") or [None])[0],"page":1,"page_size":min(100,int(query.get("limit") or 20)),
      "node_type":(query.get("node_types") or [None])[0],"match_id":query.get("match_id"),"season":query.get("season"),
      "validation_state":query.get("validation_state"),
      "source_id":query.get("source_id"),"node_id":query.get("node_id"),
    }
    result=search_repository.search(workspace_id,filters); minimum=RELIABILITY_ORDER.get(query.get("minimum_reliability"),0)
    items=[item for item in result["items"] if RELIABILITY_ORDER.get(item.get("reliability_level"),0)>=minimum]
    contradictions=[item for item in items if item.get("polarity")=="contradictory" or item.get("validation_state") in {"contested_by_staff","dismissed_by_staff"}]
    return {"query_applied":filters,"results":items,"nodes":items,"relations":[edge for item in items for edge in item.get("relations",[])],"evidence":[item for item in items if item.get("node_type")=="evidence"],"provenance":[{"node_id":item["id"],"module":item["source_module"],"source_type":item["source_type"],"source_id":item["source_id"]} for item in items],"reliability":{"minimum":query.get("minimum_reliability"),"levels":sorted({item.get("reliability_level") for item in items if item.get("reliability_level")})},"contradictions":contradictions,"limits":["Ricerca strutturata, non conversazionale.","Nessuna relazione causale viene dedotta.","Sono restituite soltanto fonti indicizzate e autorizzate."]}


def predefined(workspace_id: int,name: str,params: Dict[str,Any]) -> Dict[str,Any]:
    presets={
      "confirmed_patterns":{"node_type":"historical_pattern","validation_state":"confirmed_by_staff"},
      "recurring_topics":{"node_type":"historical_pattern"},
      "zone_patterns":{"node_type":"historical_pattern","zone":params.get("zone")},
      "player_observations":{"node_type":"voice_observation","player_id":params.get("player_id")},
      "training_for_pattern":{"node_type":"training_plan","tactical_topic":params.get("topic")},
      "briefings_from_match":{"node_type":"weekly_briefing","match_id":params.get("match_id")},
      "topic_evolution":{"tactical_topic":params.get("topic")},
      "contradictory_sources":{"validation_state":"contested_by_staff"},
      "staff_decisions":{"validation_state":"confirmed_by_staff"},
      "to_validate":{"validation_state":"to_verify"},
    }
    if name not in presets: raise ValueError("Query memoria non supportata")
    filters={**presets[name],"page":max(1,int(params.get("page") or 1)),"page_size":min(100,max(1,int(params.get("page_size") or 20)))}
    return {"name":name,"limits":["I risultati dipendono dalle fonti persistenti sincronizzate."],**search_repository.search(workspace_id,filters)}
