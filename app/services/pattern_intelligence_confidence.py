from collections import Counter
from typing import Any, Dict, List

from app.services.pattern_intelligence_config import SOURCE_WEIGHTS, TREND_CHANGE_THRESHOLD, TREND_MIN_MATCHES


def confidence(evidence: List[Dict[str, Any]], matches_count: int, matches_total: int) -> Dict[str, Any]:
    source_classes = Counter(item.get("objective_or_subjective") or "derived" for item in evidence)
    weighted = sum(SOURCE_WEIGHTS.get(kind, 0.4) for kind in source_classes.elements())
    polarity = Counter(item.get("polarity") or "neutral" for item in evidence)
    contradiction = polarity.get("positive", 0) > 0 and polarity.get("negative", 0) > 0
    sample_score = min(32, matches_count * 8)
    evidence_score = min(28, weighted * 5)
    diversity_score = min(18, len(source_classes) * 6)
    coverage_score = min(17, (matches_count / max(1, matches_total)) * 17)
    score = round(max(0, min(95, sample_score + evidence_score + diversity_score + coverage_score - (15 if contradiction else 0))))
    level = "alta" if score >= 72 else ("media" if score >= 48 else "bassa")
    return {
        "score": score,
        "level": level,
        "contradictory": contradiction,
        "source_classes": dict(source_classes),
        "reason": f"{matches_count} partite, {len(evidence)} evidenze e {len(source_classes)} tipologie di fonte.",
    }


def trend(evidence: List[Dict[str, Any]], ordered_match_ids: List[str]) -> str:
    if len(ordered_match_ids) < TREND_MIN_MATCHES:
        return "non determinabile"
    midpoint = len(ordered_match_ids) // 2
    older, newer = set(ordered_match_ids[:midpoint]), set(ordered_match_ids[midpoint:])
    if len(older) < 2 or len(newer) < 2:
        return "non determinabile"
    old_rate = len({str(item.get("match_id")) for item in evidence if str(item.get("match_id")) in older}) / len(older)
    new_rate = len({str(item.get("match_id")) for item in evidence if str(item.get("match_id")) in newer}) / len(newer)
    delta = new_rate - old_rate
    if abs(delta) < TREND_CHANGE_THRESHOLD:
        return "stabile"
    return "in aumento" if delta > 0 else "in diminuzione"
