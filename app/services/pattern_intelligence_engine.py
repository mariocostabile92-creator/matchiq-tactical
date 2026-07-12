from collections import Counter, defaultdict
from typing import Any, Dict, List

from app.services.pattern_intelligence_confidence import confidence, trend
from app.services.pattern_intelligence_config import CANDIDATE_MIN_EVIDENCE, CANDIDATE_MIN_MATCHES, ESTABLISHED_MIN_CONFIDENCE, ESTABLISHED_MIN_MATCHES, ESTABLISHED_MIN_RATE, MIN_TOTAL_MATCHES
from app.services.pattern_intelligence_normalizer import normalize_event, topic_label


POSITIVE_TOPICS={"recovery","pressing","build_up","width","depth","positive_transition","positive_behavior"}


def detect(bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    matches=bundle["matches"]; total=len(matches); ordered=[str(item["id"]) for item in matches]
    groups=defaultdict(list)
    for item in bundle["evidence"]:
        player=str(item.get("player_id") or "") if (item.get("zone") or "")=="individual" else ""
        groups[(item["topic"],item.get("phase") or "not_specified",item.get("zone") or "not_specified",player)].append(item)
    patterns=[]
    for (topic,phase,zone,player),items in groups.items():
        match_ids={str(item["match_id"]) for item in items}; count=len(items); match_count=len(match_ids)
        if match_count<CANDIDATE_MIN_MATCHES or count<CANDIDATE_MIN_EVIDENCE: continue
        rate=match_count/max(1,total); conf=confidence(items,match_count,total)
        established=(match_count>=ESTABLISHED_MIN_MATCHES or (total>=MIN_TOTAL_MATCHES and rate>=ESTABLISHED_MIN_RATE)) and conf["score"]>=ESTABLISHED_MIN_CONFIDENCE
        polarity_counts=Counter(item.get("polarity") or "neutral" for item in items)
        polarity=polarity_counts.most_common(1)[0][0]
        if polarity=="neutral": polarity="positive" if topic in POSITIVE_TOPICS else "negative"
        dates=sorted(str(item.get("created_at") or "") for item in items if item.get("created_at"))
        status="established" if established else "candidate"
        label=topic_label(topic); title=f"{label} - {player}" if player else label
        limitations=[]
        if total<MIN_TOTAL_MATCHES: limitations.append("Servono almeno 3 partite per definire un pattern storico affidabile.")
        if len(conf["source_classes"])==1: limitations.append("Il pattern è sostenuto da una sola tipologia di fonte.")
        if conf["contradictory"]: limitations.append("Le fonti non sono completamente concordi.")
        if phase in {"first_15","pre_halftime","after_70"} and match_count<3: limitations.append("Il campione temporale non è ancora sufficiente per conclusioni stabili.")
        formations=Counter(str(item.get("formation") or "") for item in items if item.get("formation")); formation_text=""
        if formations: formation_text=" Contesto moduli: "+", ".join(f"{name} ({value} evidenze)" for name,value in formations.most_common(3))+". Il confronto è descrittivo e non misura quale modulo funzioni meglio."
        explanation=f"Il tema {label.lower()} compare in {match_count} delle {total} partite analizzate, con {count} evidenze. Soglia {'superata' if established else 'da monitorare'}: almeno 2 partite e 3 evidenze; per un pattern consolidato servono campione e affidabilità maggiori.{formation_text}"
        summary=f"{title} emerso in {match_count} delle ultime {total} partite, con {count} evidenze nel periodo analizzato."
        patterns.append({
            "canonical_topic":topic,"title":title,"normalized_summary":summary,"context_player_id":player or None,
            "category":"temporale" if phase in {"first_15","pre_halftime","after_70"} else ("giocatore" if zone=="individual" else "tattico"),
            "polarity":polarity,"zone":zone,"phase":phase,"frequency_count":count,"matches_count":match_count,"matches_total":total,"occurrence_rate":round(rate,4),
            "first_seen_at":dates[0] if dates else None,"last_seen_at":dates[-1] if dates else None,"trend_direction":trend(items,ordered),
            "confidence_score":conf["score"],"confidence_level":conf["level"],"severity":"alta" if polarity=="negative" and conf["score"]>=72 else "media",
            "status":status,"validation_state":"ai_candidate","explanation":explanation,"limitations":limitations or ["Basata sui dati attualmente disponibili."],
            "source_classes":conf["source_classes"],"contradictory":conf["contradictory"],"evidence":items,
        })
    return sorted(patterns,key=lambda item:(item["status"]=="established",item["confidence_score"],item["matches_count"]),reverse=True)


def impact(patterns: List[Dict[str, Any]], match: Dict[str, Any]) -> Dict[str, Any]:
    topics={normalize_event(event).get("topic") for event in (match.get("events") or []) if isinstance(event,dict)}
    strengthened=[item for item in patterns if item["canonical_topic"] in topics and item["status"] not in {"dismissed_by_staff","archived"}]
    not_seen=[item for item in patterns if item["canonical_topic"] not in topics and item["status"] in {"established","confirmed_by_staff"}]
    return {"strengthened":[{"id":x["id"],"title":x["title"]} for x in strengthened[:3]],"not_confirmed":[{"id":x["id"],"title":x["title"]} for x in not_seen[:2]],"new_signal":not bool(strengthened) and bool(topics),"disclaimer":"L'assenza di un tema in una singola partita non dimostra che il pattern sia risolto."}
