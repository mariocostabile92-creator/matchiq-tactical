from typing import Any, Dict, List


def alignment(candidate: Dict[str, Any], sources: List[Dict[str, Any]]) -> str:
    identity=[item for item in sources if item.get("node_type") in {"tactical_identity_profile","tactical_identity_dimension"}]
    if not identity: return "non_valutabile"
    text=(candidate.get("summary") or "").lower()
    supporting=sum(1 for item in identity if any(token in (item.get("summary") or "").lower() for token in text.split() if len(token)>6))
    return "allineata" if supporting else "da_verificare"
