from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

from database import utc_now
from app.models.video_intelligence import EvidenceFrameRequest
from app.repositories.video_intelligence_repository import load_project, save_project


FRAME_RANKING_CONFIG = {
    "candidate_target": 7,
    "candidate_min": 5,
    "candidate_max": 9,
    "minimum_reliable_score": 0.42,
    "duplicate_timestamp_ms": 450,
    "weights": {
        "declared_quality": 0.16,
        "sharpness": 0.18,
        "exposure": 0.12,
        "contrast": 0.08,
        "visual_information": 0.08,
        "temporal_relevance": 0.18,
        "scene_stability": 0.08,
        "tactical_framing": 0.08,
        "players_context": 0.14,
    },
    "penalties": {
        "blur": 0.22,
        "black_frame": 0.72,
        "overexposure": 0.28,
        "closeup": 0.30,
        "irrelevant_scene": 0.28,
        "scene_change": 0.16,
        "excess_motion": 0.12,
        "duplicate": 0.26,
        "boundary": 0.10,
    },
}


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


def _exposure_score(meta: Dict[str, Any]) -> float:
    explicit = meta.get("exposure_score")
    if explicit is not None:
        return _number(explicit)
    brightness = meta.get("brightness", meta.get("luminance"))
    if brightness is None:
        dark_ratio = _number(meta.get("dark_ratio"))
        return max(0.0, 1.0 - dark_ratio * 1.5) if dark_ratio else 0.5
    try:
        value = float(brightness)
    except (TypeError, ValueError):
        return 0.5
    if value > 1:
        value /= 255
    return max(0.0, 1.0 - abs(max(0.0, min(1.0, value)) - 0.5) * 2)


def _visual_information(meta: Dict[str, Any]) -> float:
    explicit = meta.get("visual_information")
    if explicit is not None:
        return _number(explicit)
    edge = _number(meta.get("edge_score"))
    contrast = _number(meta.get("contrast"))
    pitch = _number(meta.get("green_ratio"))
    return max(0.0, min(1.0, edge * 0.45 + contrast * 0.30 + pitch * 0.25))


def score_frame(meta: Dict[str, Any], phase_type: str) -> Dict[str, Any]:
    weights = FRAME_RANKING_CONFIG["weights"]
    penalties = FRAME_RANKING_CONFIG["penalties"]
    contributions: Dict[str, float] = {}
    deductions: Dict[str, float] = {}
    reasons: List[str] = []

    quality = _number(meta.get("ai_quality", meta.get("quality", meta.get("confidence"))))
    sharpness = _number(meta.get("sharpness", meta.get("clarity")))
    blur = _number(meta.get("blur"))
    exposure = _exposure_score(meta)
    contrast = _number(meta.get("contrast"))
    information = _visual_information(meta)
    temporal = _number(meta.get("temporal_relevance"), 0.5)
    stability = _number(meta.get("scene_stability"), 0.5)

    contributions["qualita_dichiarata"] = quality * weights["declared_quality"]
    contributions["nitidezza"] = sharpness * weights["sharpness"]
    contributions["esposizione"] = exposure * weights["exposure"]
    contributions["contrasto"] = contrast * weights["contrast"]
    contributions["informazione_visiva"] = information * weights["visual_information"]
    contributions["rilevanza_temporale"] = temporal * weights["temporal_relevance"]
    contributions["stabilita_scena"] = stability * weights["scene_stability"]

    camera = " ".join(_text(meta.get(key)) for key in ("camera", "shot_type", "framing", "label"))
    tactical_framing = 0.0
    if any(token in camera for token in ("wide", "campo aperto", "grandangolo", "tactical")):
        tactical_framing = 1.0
        reasons.append("campo e reparti leggibili")
    contributions["inquadratura_tattica"] = tactical_framing * weights["tactical_framing"]

    try:
        visible_players = max(0, min(30, int(meta.get("visible_players") or 0)))
    except (TypeError, ValueError):
        visible_players = 0
    players_context = min(1.0, visible_players / 8) if visible_players else 0.0
    contributions["contesto_giocatori"] = players_context * weights["players_context"]
    if visible_players >= 6:
        reasons.append("piu giocatori e reparti visibili")

    if any(token in camera for token in ("close", "primo piano", "portrait", "zoom")):
        deductions["inquadratura_ravvicinata"] = penalties["closeup"]
        reasons.append("inquadratura ravvicinata")
    if blur:
        deductions["mosso"] = blur * penalties["blur"]
        reasons.append("possibile mosso")

    brightness = _number(meta.get("brightness", meta.get("luminance")))
    dark_ratio = _number(meta.get("dark_ratio"))
    black_ratio = _number(meta.get("black_ratio"))
    if black_ratio >= 0.82 or dark_ratio >= 0.82 or (brightness and brightness <= 0.035):
        deductions["frame_nero"] = penalties["black_frame"]
        reasons.append("frame troppo scuro")
    white_ratio = _number(meta.get("white_ratio"))
    if white_ratio >= 0.78 or (brightness >= 0.94):
        deductions["sovraesposizione"] = penalties["overexposure"]
        reasons.append("frame troppo chiaro")

    scene = " ".join(_text(meta.get(key)) for key in ("scene", "visual_context", "ai_reason", "reason", "label"))
    if any(token in scene for token in ("esult", "celebr", "intervista", "replay", "pubblico", "panchina")):
        deductions["scena_poco_tattica"] = penalties["irrelevant_scene"]
        reasons.append("scena poco utile tatticamente")
    scene_change = _number(meta.get("scene_change"))
    if scene_change:
        deductions["cambio_scena"] = scene_change * penalties["scene_change"]
        reasons.append("possibile cambio scena")
    motion = _number(meta.get("motion", meta.get("motion_score")))
    if motion >= 0.72:
        deductions["movimento_eccessivo"] = motion * penalties["excess_motion"]
        reasons.append("movimento elevato")
    duplicate = _number(meta.get("duplicate_similarity"))
    if duplicate >= 0.92:
        deductions["duplicazione"] = duplicate * penalties["duplicate"]
        reasons.append("molto simile a un altro candidato")
    boundary = _number(meta.get("boundary_penalty"))
    if boundary:
        deductions["bordo_segmento"] = boundary * penalties["boundary"]

    if sharpness >= 0.55:
        reasons.append("nitidezza adeguata")
    if exposure >= 0.55:
        reasons.append("esposizione leggibile")
    if phase_type != "unclassified" and _text(meta.get("phase")):
        reasons.append("coerente con la fase proposta")

    raw_score = 0.16 + sum(contributions.values()) - sum(deductions.values())
    score = round(max(0.0, min(0.98, raw_score)), 3)
    if score >= 0.70:
        tier = "slide_ready"
    elif score >= FRAME_RANKING_CONFIG["minimum_reliable_score"]:
        tier = "useful_hint"
    else:
        tier = "discard"
    ranked_reasons = sorted(contributions.items(), key=lambda item: (-item[1], item[0]))
    positive = [name.replace("_", " ") for name, value in ranked_reasons if value >= 0.035]
    motivation = ", ".join((positive + reasons)[:5])
    if tier == "discard":
        motivation = "Frame da verificare manualmente. " + (motivation or "Qualita visiva sotto la soglia minima.")
    return {
        "score": score,
        "tier": tier,
        "reliable": score >= FRAME_RANKING_CONFIG["minimum_reliable_score"],
        "motivation": motivation or "Fotogramma reale disponibile, da verificare nello staff.",
        "contributions": {key: round(value, 4) for key, value in contributions.items() if value},
        "penalties": {key: round(value, 4) for key, value in deductions.items() if value},
    }


def _candidate_pool_entry(raw: Dict[str, Any], fallback_index: int) -> Optional[Dict[str, Any]]:
    try:
        timestamp = int(raw.get("timestamp_ms", raw.get("representative_timestamp_ms")))
    except (TypeError, ValueError):
        return None
    meta = deepcopy(raw.get("frame_meta") or raw.get("meta") or {})
    return {
        "timestamp_ms": max(0, timestamp),
        "frame_index": raw.get("frame_index", fallback_index),
        "frame_meta": meta,
        "candidate_role": str(raw.get("candidate_role") or meta.get("candidate_role") or "alternative"),
    }


def build_candidate_pool(frame_times_ms: Iterable[int], frame_meta: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    metadata = list(frame_meta)
    pool: List[Dict[str, Any]] = []
    for index, raw_time in enumerate(frame_times_ms):
        entry = _candidate_pool_entry({
            "timestamp_ms": raw_time,
            "frame_index": index,
            "frame_meta": metadata[index] if index < len(metadata) and isinstance(metadata[index], dict) else {},
        }, index)
        if entry:
            pool.append(entry)
    pool.sort(key=lambda item: (item["timestamp_ms"], int(item.get("frame_index") or 0)))
    return pool


def _deduplicate_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique: List[Dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: item["timestamp_ms"]):
        visual_hash = str((candidate.get("frame_meta") or {}).get("visual_hash") or "")
        duplicate = next((item for item in unique if (
            abs(item["timestamp_ms"] - candidate["timestamp_ms"]) <= FRAME_RANKING_CONFIG["duplicate_timestamp_ms"]
            or (visual_hash and visual_hash == str((item.get("frame_meta") or {}).get("visual_hash") or ""))
        )), None)
        if duplicate:
            current_quality = _number((candidate.get("frame_meta") or {}).get("quality"))
            previous_quality = _number((duplicate.get("frame_meta") or {}).get("quality"))
            if current_quality > previous_quality:
                unique[unique.index(duplicate)] = candidate
            continue
        unique.append(candidate)
    return unique


def build_ranked_candidates(
    segment: Dict[str, Any],
    candidate_pool: List[Dict[str, Any]],
    duration_ms: int = 0,
) -> List[Dict[str, Any]]:
    start_ms = max(0, int(segment.get("start_timestamp_ms") or 0))
    end_ms = max(start_ms + 1, int(segment.get("end_timestamp_ms") or start_ms + 1))
    representative_ms = max(start_ms, min(end_ms, int(segment.get("representative_timestamp_ms") or start_ms)))
    eligible = [deepcopy(item) for item in candidate_pool if start_ms <= int(item.get("timestamp_ms") or -1) <= end_ms]
    if not any(int(item.get("timestamp_ms") or -1) == representative_ms for item in eligible):
        eligible.append({
            "timestamp_ms": representative_ms,
            "frame_index": segment.get("frame_index"),
            "frame_meta": deepcopy(segment.get("frame_meta") or {}),
            "candidate_role": "primary",
        })
    eligible = _deduplicate_candidates(eligible)
    span = max(1, end_ms - start_ms)
    ranked: List[Dict[str, Any]] = []
    for item in eligible:
        timestamp = int(item["timestamp_ms"])
        meta = deepcopy(item.get("frame_meta") or {})
        meta["temporal_relevance"] = max(0.0, 1.0 - abs(timestamp - representative_ms) / max(1, span / 2))
        edge_distance = min(timestamp - start_ms, end_ms - timestamp)
        meta["boundary_penalty"] = max(0.0, 1.0 - edge_distance / max(1000, span * 0.18))
        result = score_frame(meta, str(segment.get("phase_type") or "unclassified"))
        ranked.append({
            "frame_index": item.get("frame_index"),
            "timestamp_ms": timestamp,
            "score": result["score"],
            "tier": result["tier"],
            "reliable": result["reliable"],
            "motivation": result["motivation"],
            "contributions": result["contributions"],
            "penalties": result["penalties"],
            "candidate_role": item.get("candidate_role") or "alternative",
        })
    ranked.sort(key=lambda item: (-item["score"], abs(item["timestamp_ms"] - representative_ms), item["timestamp_ms"]))
    limit = max(FRAME_RANKING_CONFIG["candidate_min"], min(FRAME_RANKING_CONFIG["candidate_max"], FRAME_RANKING_CONFIG["candidate_target"]))
    ranked = ranked[:limit]
    for position, item in enumerate(ranked, start=1):
        item["rank"] = position
        item["selection_status"] = "suggested" if position == 1 else "alternative"
    return ranked


def rank_segments(
    segments: List[Dict[str, Any]],
    candidate_pool: Optional[List[Dict[str, Any]]] = None,
    duration_ms: int = 0,
) -> List[Dict[str, Any]]:
    pool = candidate_pool or []
    ranked = []
    for segment in segments:
        item = deepcopy(segment)
        candidates = build_ranked_candidates(item, pool, duration_ms)
        selected = candidates[0] if candidates else None
        if selected:
            item["representative_timestamp_ms"] = selected["timestamp_ms"]
            item["frame_index"] = selected.get("frame_index")
            item["frame_score"] = selected["score"]
            item["frame_tier"] = selected["tier"]
            item["frame_ranking_motivation"] = selected["motivation"]
            item["frame_candidates"] = candidates
            item["frame_review_required"] = not selected["reliable"]
        else:
            result = score_frame(item.get("frame_meta") or {}, str(item.get("phase_type") or "unclassified"))
            item["frame_score"] = result["score"]
            item["frame_tier"] = result["tier"]
            item["frame_ranking_motivation"] = result["motivation"]
            item["frame_candidates"] = []
            item["frame_review_required"] = not result["reliable"]
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
    evidences = project.get("evidences") if isinstance(project.get("evidences"), list) else []
    found = next((item for item in evidences if isinstance(item, dict) and item.get("evidence_id") == evidence_id), None)
    if not found:
        raise LookupError("Evidenza non trovata")

    candidates = found.get("frame_candidates") if isinstance(found.get("frame_candidates"), list) else []
    selected = next((item for item in candidates if int(item.get("timestamp_ms") or -1) == int(data.representative_timestamp_ms)), None)
    if not selected:
        segments = project.get("segments") if isinstance(project.get("segments"), list) else []
        for segment in segments:
            segment_candidates = segment.get("frame_candidates") if isinstance(segment.get("frame_candidates"), list) else []
            selected = next((item for item in segment_candidates if int(item.get("timestamp_ms") or -1) == int(data.representative_timestamp_ms)), None)
            if selected:
                break
            if int(segment.get("representative_timestamp_ms") or -1) == int(data.representative_timestamp_ms):
                selected = {
                    "timestamp_ms": segment.get("representative_timestamp_ms"),
                    "frame_index": segment.get("frame_index"),
                    "score": segment.get("frame_score"),
                    "tier": segment.get("frame_tier"),
                    "motivation": segment.get("frame_ranking_motivation"),
                }
                break
    if not selected:
        raise ValueError("Il fotogramma deve provenire dai timestamp reali estratti dal video")

    selected_timestamp = int(selected["timestamp_ms"])
    for candidate in candidates:
        candidate["selection_status"] = "staff_selected" if int(candidate.get("timestamp_ms") or -1) == selected_timestamp else "alternative"
    found["frame_candidates"] = candidates
    found["representative_timestamp_ms"] = selected_timestamp
    found["representative_frame"] = {
        "frame_index": data.frame_index if data.frame_index is not None else selected.get("frame_index"),
        "timestamp_ms": selected_timestamp,
        "selection_status": "staff_selected",
        "score": selected.get("score"),
        "tier": selected.get("tier"),
        "motivation": str(data.motivation or selected.get("motivation") or "Selezione manuale dello staff")[:500],
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
