from collections import Counter
from typing import Any, Dict


WEIGHTS={"bassa":1,"media":2,"alta":3}


def assess(retrieval: Dict[str,Any]) -> Dict[str,Any]:
    nodes=retrieval.get("nodes") or []; contradictions=retrieval.get("contradictions") or []
    modules={node.get("source_module") for node in nodes if node.get("source_module")}; matches={node.get("match_id") for node in nodes if node.get("match_id")}
    score=sum(WEIGHTS.get(node.get("reliability_level"),1) for node in nodes)+min(3,len(modules))+min(3,len(matches))-min(3,len(contradictions))
    if not nodes: level="insufficiente"
    elif score<5: level="parziale"
    elif score<11: level="sufficiente"
    else: level="forte"
    limits=list(retrieval.get("limits") or [])
    if len(matches)<2: limits.append("Il campione comprende meno di due partite collegate.")
    if contradictions: limits.append("Le fonti disponibili contengono indicazioni non concordi.")
    return {"level":level,"sufficient":level in {"sufficiente","forte"},"score":score,"source_count":len(nodes),"match_count":len(matches),"module_count":len(modules),"contradiction_count":len(contradictions),"reliability_distribution":dict(Counter(node.get("reliability_level") or "non indicata" for node in nodes)),"limitations":list(dict.fromkeys(limits))[:6]}
