from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from database import utc_now
from app.models.video_intelligence import EvidenceFrameRequest
from app.repositories.video_intelligence_repository import load_project, save_project


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number > 1:
        number /= 100
    return max(0.0, min(1.0, number))


def _text(value: Any) -> str:
    return str(value or "").strip().lower()


def score_frame(meta: Dict[str, Any], phase_type: str) -> Dict[str, Any]:
    score = 0.35
    reasons: List[str] = []
    quality = _number(meta.get("ai_quality", meta.get("quality", meta.get("confidence"))))
    if quality:
        score += quality * 0.28
        reasons.append(f"qualita dichiarata {round(quality * 100)}%")

    camera = " ".join(_text(meta.get(key)) for key in ("camera", "shot_type", "framing"))
    if any(token in camera for token in ("wide", "campo aperto", "grandangolo", "tactical")):
        score += 0.18
        reasons.append("campo e reparti leggibili")
    if any(token in camera for token in ("close", "primo piano", "portrait", "zoom")):
        score -= 0.32
        reasons.append("inquadratura ravvicinata")

    sharpness = _number(meta.get("sharpness", meta.get("clarity")))
    blur = _number(meta.get("blur"))
    if sharpness:
        score += sharpness * 0.12
        reasons.append("nitidezza disponibile")
    if blur:
        score -= blur * 0.18
        reasons.append("possibile mosso")

    try:
        visible_players = max(0, min(30, int(meta.get("visible_players") or 0)))
    except (TypeError, ValueError):
        visible_players = 0
    if visible_players >= 6:
        score += 0.12
        reasons.append("piu giocatori visibili")
    elif visible_players and visible_players <= 2:
        score -= 0.12
        reasons.append("pochi giocatori visibili")

    scene = " ".join(_text(meta.get(key)) for key in ("scene", "visual_context", "ai_reason", "reason"))
    if any(token in scene for token in ("esult", "celebr", "intervista", "replay", "pubblico", "panchina")):
        score -= 0.28
        reasons.append("scena poco utile tatticamente")
    if phase_type != "unclassified" and _text(meta.get("phase")):
        score += 0.08
        reasons.append("coerente con la fase proposta")

    score = round(max(0.0, min(0.98, score)), 3)
    if score >= 0.75:
        tier = "slide_ready"
    elif score >= 0.45:
        tier = "useful_hint"
    else:
        tier = "discard"
    return {
        "score": score,
        "tier": tier,
        "motivation": ", ".join(reasons[:5]) or "Fotogramma reale disponibile, da verificare nello staff.",
    }


def rank_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = []
    for segment in segments:
        item = deepcopy(segment)
        result = score_frame(item.get("frame_meta") or {}, str(item.get("phase_type") or "unclassified"))
        item["frame_score"] = result["score"]
        item["frame_tier"] = result["tier"]
        item["frame_ranking_motivation"] = result["motivation"]
        ranked.append(item)
    ranked_order = sorted(
        range(len(ranked)),
        key=lambda index: (-ranked[index]["frame_score"], ranked[index]["representative_timestamp_ms"]),
    )
    for position, index in enumerate(ranked_order, start=1):
        ranked[index]["frame_rank"] = position
    return ranked


def replace_evidence_frame(
    user_id: int,
    asset_id: int,
    evidence_id: str,
    data: EvidenceFrameRequest,
) -> Dict[str, Any]:
    project = load_project(user_id, asset_id)
    if not project:
        raise LookupError("Progetto Video Intelligence non trovato")
    candidates = project.get("segments") if isinstance(project.get("segments"), list) else []
    selected = None
    for candidate in candidates:
        if int(candidate.get("representative_timestamp_ms") or -1) == int(data.representative_timestamp_ms):
            selected = candidate
            break
    if not selected:
        raise ValueError("Il fotogramma deve provenire dai timestamp reali estratti dal video")

    evidences = project.get("evidences") if isinstance(project.get("evidences"), list) else []
    found = None
    for evidence in evidences:
        if isinstance(evidence, dict) and evidence.get("evidence_id") == evidence_id:
            found = evidence
            break
    if not found:
        raise LookupError("Evidenza non trovata")

    frame_index = data.frame_index if data.frame_index is not None else selected.get("frame_index")
    found["representative_timestamp_ms"] = int(selected["representative_timestamp_ms"])
    found["representative_frame"] = {
        "frame_index": frame_index,
        "timestamp_ms": int(selected["representative_timestamp_ms"]),
        "selection_status": "staff_selected",
        "score": selected.get("frame_score"),
        "tier": selected.get("frame_tier"),
        "motivation": str(data.motivation or "Selezione manuale dello staff")[:500],
        "updated_at": utc_now(),
    }
    found["review_status"] = "corrected"
    found["reviewed_by"] = int(user_id)
    found["reviewed_at"] = utc_now()
    found["user_correction"] = str(data.motivation or "Fotogramma rappresentativo sostituito dallo staff")[:1200]
    project["evidences"] = evidences
    saved = save_project(user_id, asset_id, project, status="review_ready", stage="human_review", progress=90)
    if not saved:
        raise RuntimeError("Impossibile salvare il nuovo fotogramma")
    return deepcopy(found)
