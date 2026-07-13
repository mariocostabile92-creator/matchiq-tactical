from typing import Any, Dict


def _text(value: Any) -> str:
    if isinstance(value,list): return ", ".join(str(item) for item in value if item)
    return str(value or "").strip()


def _source(node: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "knowledge_node_id": node.get("id"),
        "source_type": node.get("source_type"),
        "source_id": node.get("source_id"),
        "author": "staff tecnico",
        "declared_at": node.get("occurred_at"),
        "updated_at": node.get("source_updated_at") or node.get("updated_at"),
        "confirmation_state": node.get("validation_state") or "staff_source",
        "reliability": "alta come dichiarazione, non come comportamento osservato",
    }


def extract(nodes: list) -> Dict[str, Dict[str, Any]]:
    declared={}
    for node in nodes:
        metadata=node.get("metadata_json") or {}
        if node.get("node_type")=="coach_profile":
            mapping={
              "structure.primary_formation":"preferred_formation","structure.alternative_formation":"alternative_formation",
              "buildup.short":"buildup","defence.high_press":"pressing","attack.possession":"offensive_style",
              "defence.mid_block":"defensive_style","transition.counterpress":"transition_management","set_piece.marking":"set_piece_preferences",
            }
            for dimension,field in mapping.items():
                value=_text(metadata.get(field))
                if value: declared[dimension]={"value":value,"source":_source(node),"strength":"dichiarata"}
            philosophy=_text(metadata.get("playing_philosophy"))
            if philosophy: declared.setdefault("attack.possession",{"value":philosophy,"source":_source(node),"strength":"dichiarata"})
        elif node.get("node_type")=="team_profile":
            formations=metadata.get("formations") or []
            if formations and "structure.primary_formation" not in declared:
                declared["structure.primary_formation"]={"value":_text(formations[0]),"source":_source(node),"strength":"profilo_squadra"}
    return declared
