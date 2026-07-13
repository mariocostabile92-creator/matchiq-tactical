from typing import Any, Dict, List

from app.services.tactical_identity_declared import extract as declared_extract
from app.services.tactical_identity_observed import evidence_payload, extract as observed_extract
from app.services.tactical_identity_registry import DIMENSIONS
from app.services.tactical_identity_scoring import alignment, confidence, trend


def _summary(dimensions: List[Dict[str,Any]],matches: int) -> Dict[str,Any]:
    ranked=[item for item in dimensions if item["observed_value"] and item["confidence_level"] in {"media","alta"}]
    ranked.sort(key=lambda item:(item["confidence_level"]=="alta",item["evidence_count"],item["match_count"]),reverse=True)
    traits=[item["label"] for item in ranked[:3]]; evolving=[item["label"] for item in dimensions if item["trend_direction"] in {"in_aumento","in_diminuzione","in_trasformazione"}][:2]; unknown=[item["label"] for item in dimensions if item["alignment_state"]=="insufficient_data"][:2]
    if not traits: text="I dati disponibili non sono ancora sufficienti per descrivere un'identita tattica affidabile."
    else: text=f"Nel periodo analizzato emergono {', '.join(traits)}. L'identita resta prudente e verificabile sul campione di {matches} partite."
    return {"text":text,"main_traits":traits,"evolving":evolving,"undetermined":unknown}


def build(nodes: list,existing: Dict[str,Dict[str,Any]]=None) -> Dict[str,Any]:
    existing=existing or {}; declared=declared_extract(nodes); observed=observed_extract(nodes); dimensions=[]
    for key,definition in DIMENSIONS.items():
        declared_item=declared.get(key); observed_item=observed.get(key); old=existing.get(key) or {}; validation=old.get("validation_state") or "not_validated"; validated=old.get("validated_value")
        trend_data=trend((observed_item or {}).get("items") or []); conf=confidence(observed_item,validation=="confirmed_by_staff"); align=alignment(key,declared_item,observed,validated)
        if trend_data["direction"] in {"in_aumento","in_diminuzione"} and align=="aligned": align="evolving"
        limitations=[]
        if not observed_item: limitations.append("Nessuna evidenza osservata sufficiente nel periodo selezionato.")
        elif observed_item.get("matches",0)<3: limitations.append("Campione ridotto: servono almeno 3 partite per una lettura piu stabile.")
        if observed_item and observed_item.get("contradictions"): limitations.append("Le fonti non sono completamente concordi.")
        explanation=(f"Dichiarato: {declared_item['value']}. " if declared_item else "Nessuna preferenza dichiarata disponibile. ")+(f"Osservato su {observed_item['matches']} partite e {len(observed_item['items'])} evidenze." if observed_item else "Comportamento non ancora determinabile dai dati disponibili.")
        dimensions.append({"dimension_type":key,"dimension_group":definition["group"],"label":definition["label"],"declared_value":declared_item["value"] if declared_item else None,"declared_source":declared_item["source"] if declared_item else {},"observed_value":observed_item["value"] if observed_item else None,"validated_value":validated,"declared_strength":declared_item["strength"] if declared_item else None,"observed_strength":"ricorrente" if observed_item and observed_item["matches"]>=3 else ("segnale" if observed_item else None),"alignment_state":align,"confidence_level":conf,"trend_direction":trend_data["direction"],"evidence_count":len((observed_item or {}).get("items") or []),"match_count":int((observed_item or {}).get("matches") or 0),"explanation":explanation,"limitations":limitations or ["Basata sulle fonti disponibili nel periodo selezionato."],"validation_state":validation,"distribution":(observed_item or {}).get("distribution") or {},"previous_period":trend_data["previous"],"recent_period":trend_data["recent"],"evidence":[evidence_payload(node) for node in (observed_item or {}).get("items") or []]})
    match_ids={str(node.get("match_id") or node.get("source_id")) for node in nodes if node.get("node_type")=="match" or node.get("match_id")}
    levels=[item["confidence_level"] for item in dimensions if item["observed_value"]]; overall="alta" if levels.count("alta")>=3 and len(match_ids)>=5 else ("media" if levels.count("alta")+levels.count("media")>=3 and len(match_ids)>=3 else "bassa")
    return {"dimensions":dimensions,"summary":_summary(dimensions,len(match_ids)),"matches_analyzed":len(match_ids),"sources_analyzed":len(nodes),"overall_confidence":overall}
