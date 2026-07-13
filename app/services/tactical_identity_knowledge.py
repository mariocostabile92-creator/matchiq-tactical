from typing import Any, Dict, List
from app.repositories import knowledge_intelligence_repository as repository


def publish(workspace_id: int,user_id: int,profile: Dict[str,Any],dimensions: List[Dict[str,Any]]) -> None:
    profile_node=repository.upsert_node(workspace_id,user_id,"tactical_identity_profile","tactical_identity","tactical_identity_profile",str(profile["id"]),{
      "team_profile_id":profile.get("team_profile_id"),"title":"AI Tactical Identity","summary":(profile.get("summary") or {}).get("text") or "Identita tattica nel periodo analizzato.",
      "occurred_at":profile.get("updated_at"),"source_updated_at":profile.get("updated_at"),"reliability_level":profile.get("overall_confidence") or "bassa",
      "validation_state":"generated","nature":"dato_derivato","season":profile.get("season"),"metadata":{"identity_version":profile.get("identity_version"),"matches_analyzed":profile.get("matches_analyzed"),"period_start":profile.get("period_start"),"period_end":profile.get("period_end")},"tags":["identita_tattica",profile.get("season") or ""]
    })
    for item in dimensions:
        node=repository.upsert_node(workspace_id,user_id,"tactical_identity_dimension","tactical_identity","tactical_identity_dimension",str(item["id"]),{
          "team_profile_id":profile.get("team_profile_id"),"title":item["label"],"summary":item["explanation"],"occurred_at":item.get("updated_at"),"source_updated_at":item.get("updated_at"),
          "reliability_level":item["confidence_level"],"validation_state":item["validation_state"],"nature":"validazione_staff" if item["validation_state"]=="confirmed_by_staff" else "dato_derivato",
          "tactical_topic":item["dimension_type"],"season":profile.get("season"),"metadata":{"alignment_state":item["alignment_state"],"trend_direction":item["trend_direction"],"declared_value":item.get("declared_value"),"observed_value":item.get("observed_value"),"validated_value":item.get("validated_value"),"evidence_count":item["evidence_count"],"match_count":item["match_count"]},"tags":["identita_tattica",item["dimension_group"],item["dimension_type"]]
        })
        repository.upsert_edge(workspace_id,node,profile_node,"belongs_to","tactical_identity_dimension",str(item["id"]),"Dimensione appartenente al profilo Tactical Identity.",item["confidence_level"],item["validation_state"],{})
        for evidence in item.get("evidence") or []:
            source=repository.get_node(workspace_id,int(evidence["knowledge_node_id"]))
            if source:
                relation="contradicts" if item["alignment_state"]=="contradictory" else "supported_by"
                repository.upsert_edge(workspace_id,node,source,relation,"tactical_identity_evidence",str(evidence["knowledge_node_id"]),"Fonte verificabile usata per la dimensione.",evidence["reliability_level"],"derived",{})
