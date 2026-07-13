from typing import Any, Dict, List, Optional

from app.repositories import knowledge_intelligence_repository as knowledge


def publish_case(workspace_id: int,user_id: int,case: Dict[str,Any],options: List[Dict[str,Any]]) -> Dict[str,Any]:
    case_node=knowledge.upsert_node(workspace_id,user_id,"decision_case","decision_engine","decision_case",str(case["id"]),{
      "team_profile_id":case.get("team_profile_id"),"match_id":case.get("match_id"),"title":f"Decision Support - {case['phase'].replace('_',' ')}",
      "summary":case["situation_summary"],"occurred_at":case["created_at"],"source_updated_at":case["updated_at"],
      "reliability_level":"media" if case["evidence_state"] in {"valutabile","fortemente_supportato"} else "bassa",
      "validation_state":"generated","nature":"supporto_decisionale","tactical_topic":case["phase"],
      "metadata":{"case_id":case["id"],"evidence_state":case["evidence_state"],"limitations":case["limitations_json"]},"tags":["decision_engine",case["phase"]]
    })
    for option in options:
        node=knowledge.upsert_node(workspace_id,user_id,"decision_option","decision_engine","decision_option",str(option["id"]),{
          "team_profile_id":case.get("team_profile_id"),"match_id":case.get("match_id"),"title":option["title"],"summary":option["summary"],
          "occurred_at":option["created_at"],"source_updated_at":option["updated_at"],"reliability_level":option["confidence_level"],
          "validation_state":"generated","nature":"supporto_decisionale","tactical_topic":option["option_type"],
          "metadata":{"case_id":case["id"],"option_id":option["id"],"benefits":option["benefits_json"],"risks":option["risks_json"],"identity_alignment":option["identity_alignment"]},"tags":["decision_engine",option["option_type"]]
        })
        knowledge.upsert_edge(workspace_id,node,case_node,"belongs_to","decision_option",str(option["id"]),"Opzione appartenente al caso decisionale.",option["confidence_level"],"derived",{})
        for source in option.get("sources") or []:
            source_node=knowledge.get_node(workspace_id,int(source["knowledge_node_id"])) if source.get("knowledge_node_id") else None
            if source_node: knowledge.upsert_edge(workspace_id,node,source_node,"supported_by","decision_option_source",f"{option['id']}:{source['id']}","Fonte consultata dal Decision Engine.",source["reliability_level"],"derived",{})
    return case_node


def publish_staff(workspace_id: int,user_id: int,case_node: Dict[str,Any],decision: Dict[str,Any],option_node: Optional[Dict[str,Any]]=None) -> Dict[str,Any]:
    node=knowledge.upsert_node(workspace_id,user_id,"staff_decision","decision_engine","staff_decision",str(decision["id"]),{
      "title":"Decisione dello staff","summary":decision.get("note") or decision["action"],"occurred_at":decision["created_at"],"source_updated_at":decision["created_at"],
      "reliability_level":"alta","validation_state":"confirmed_by_staff","nature":"decisione_staff","metadata":{"case_id":decision["case_id"],"option_id":decision.get("option_id"),"action":decision["action"],"executed_manually":decision["executed_manually"]},"tags":["decision_engine","staff_decision"]
    })
    knowledge.upsert_edge(workspace_id,node,case_node,"belongs_to","staff_decision",str(decision["id"]),"Decisione collegata al caso.","alta","confirmed_by_staff",{})
    if option_node:
        relation="selected_by_staff" if decision["action"]=="selected" else "rejected_by_staff"
        knowledge.upsert_edge(workspace_id,option_node,node,relation,"staff_decision",str(decision["id"]),"Esito della valutazione dello staff.","alta","confirmed_by_staff",{})
    return node


def publish_outcome(workspace_id: int,user_id: int,decision_node: Dict[str,Any],outcome: Dict[str,Any]) -> Dict[str,Any]:
    node=knowledge.upsert_node(workspace_id,user_id,"observed_outcome","decision_engine","observed_outcome",str(outcome["id"]),{
      "title":"Esito osservato dopo la decisione","summary":outcome["summary"],"occurred_at":outcome["created_at"],"source_updated_at":outcome["created_at"],
      "reliability_level":outcome["confidence_level"],"validation_state":"derived","nature":"osservazione_successiva","metadata":{"relation_state":outcome["relation_state"],"evidence":outcome["evidence_json"]},"tags":["decision_engine","outcome"]
    })
    knowledge.upsert_edge(workspace_id,decision_node,node,"followed_by","decision_outcome",str(outcome["id"]),"Evento osservato dopo la decisione; non prova un rapporto causale.",outcome["confidence_level"],"derived",{})
    return node
