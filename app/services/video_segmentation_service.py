from __future__ import annotations

from typing import Any, Dict, List


SUPPORTED_PHASES = {
    "costruzione dal basso": "build_up",
    "sviluppo": "development",
    "rifinitura": "final_third",
    "finalizzazione": "finishing",
    "transizione positiva": "positive_transition",
    "transizione negativa": "negative_transition",
    "pressione": "pressure",
    "pressing": "pressure",
    "pressing alto": "high_press",
    "recupero palla": "ball_recovery",
    "perdita palla": "ball_loss",
    "palla inattiva offensiva": "attacking_set_piece",
    "palla inattiva difensiva": "defending_set_piece",
    "calcio d'angolo offensivo": "attacking_corner",
    "calcio d'angolo difensivo": "defending_corner",
    "punizione laterale offensiva": "attacking_free_kick",
    "punizione laterale difensiva": "defending_free_kick",
    "punizione centrale offensiva": "attacking_free_kick",
    "punizione centrale difensiva": "defending_free_kick",
    "rimessa laterale offensiva": "attacking_throw_in",
    "rimessa laterale difensiva": "defending_throw_in",
    "rimessa dal fondo": "goal_kick",
    "fase di non possesso": "out_of_possession",
    "linea difensiva": "defensive_line",
    "ampiezza": "width",
    "spazio tra reparti": "between_lines",
    "rest defense": "rest_defense",
}


def _clean(value: Any, limit: int = 220) -> str:
    return str(value or "").strip()[:limit]


def _normalized_phase(meta: Dict[str, Any]) -> str:
    candidates = (
        meta.get("corrected_phase"),
        meta.get("phase"),
        meta.get("label"),
        meta.get("detected_phase"),
        meta.get("set_piece_type"),
    )
    for candidate in candidates:
        text = _clean(candidate, 120).lower()
        if not text:
            continue
        for label, phase in SUPPORTED_PHASES.items():
            if label in text:
                return phase
    return "unclassified"


def _confidence(meta: Dict[str, Any], phase: str) -> float:
    raw = meta.get("ai_quality", meta.get("quality", meta.get("confidence", 0)))
    try:
        value = float(raw or 0)
    except (TypeError, ValueError):
        value = 0
    if value > 1:
        value /= 100
    value = max(0.0, min(0.90, value))
    if phase == "unclassified":
        value = min(value, 0.35)
    return round(value, 3)


def _signals(meta: Dict[str, Any]) -> List[str]:
    values = meta.get("visual_signals") if isinstance(meta.get("visual_signals"), list) else []
    clean = [_clean(item, 100) for item in values if _clean(item, 100)]
    for key in ("ball_state", "field_zone", "camera", "restart_type"):
        value = _clean(meta.get(key), 100)
        if value and value not in clean:
            clean.append(value)
    return clean[:8]


def segment_frames(frame_times_ms: List[int], frame_meta: List[Dict[str, Any]], duration_ms: int) -> List[Dict[str, Any]]:
    candidates = []
    for index, raw_time in enumerate(frame_times_ms):
        try:
            timestamp = max(0, int(raw_time))
        except (TypeError, ValueError):
            continue
        meta = frame_meta[index] if index < len(frame_meta) and isinstance(frame_meta[index], dict) else {}
        candidates.append((timestamp, index, meta))
    candidates.sort(key=lambda item: item[0])

    unique = []
    for item in candidates:
        if unique and item[0] - unique[-1][0] < 1200:
            previous_quality = _confidence(unique[-1][2], _normalized_phase(unique[-1][2]))
            current_quality = _confidence(item[2], _normalized_phase(item[2]))
            if current_quality > previous_quality:
                unique[-1] = item
            continue
        unique.append(item)
    if not unique:
        return []

    safe_duration = max(duration_ms, unique[-1][0] + 5000)
    segments = []
    for position, (timestamp, frame_index, meta) in enumerate(unique):
        previous_time = unique[position - 1][0] if position else 0
        next_time = unique[position + 1][0] if position + 1 < len(unique) else safe_duration
        start_ms = max(0, timestamp - min(5000, max(1500, (timestamp - previous_time) // 2)))
        end_ms = min(safe_duration, timestamp + min(7000, max(2000, (next_time - timestamp) // 2)))
        if segments and start_ms < segments[-1]["end_timestamp_ms"]:
            boundary = (segments[-1]["representative_timestamp_ms"] + timestamp) // 2
            segments[-1]["end_timestamp_ms"] = boundary
            start_ms = boundary
        phase = _normalized_phase(meta)
        signals = _signals(meta)
        confidence = _confidence(meta, phase)
        segments.append({
            "segment_id": f"seg_{position + 1}",
            "start_timestamp_ms": start_ms,
            "end_timestamp_ms": max(start_ms + 1000, end_ms),
            "representative_timestamp_ms": timestamp,
            "frame_index": frame_index,
            "phase_type": phase,
            "confidence_score": confidence,
            "signals": signals,
            "motivation": _clean(meta.get("ai_reason") or meta.get("reason") or meta.get("evidence"), 500)
                or "Segmento candidato derivato da un fotogramma reale selezionato nel video.",
            "source_type": "ai_visual_assessment" if any(meta.get(key) for key in ("ai_reason", "evidence", "detected_phase")) else "frame_metadata",
            "frame_meta": meta,
        })
    return segments


def phase_title(phase: str) -> str:
    labels = {
        "build_up": "Possibile costruzione dal basso",
        "development": "Possibile fase di sviluppo",
        "final_third": "Possibile rifinitura",
        "finishing": "Possibile finalizzazione",
        "positive_transition": "Possibile transizione positiva",
        "negative_transition": "Possibile transizione negativa",
        "pressure": "Possibile pressione",
        "high_press": "Possibile pressing alto",
        "ball_recovery": "Possibile recupero palla",
        "ball_loss": "Possibile perdita palla",
        "attacking_set_piece": "Possibile palla inattiva offensiva",
        "defending_set_piece": "Possibile palla inattiva difensiva",
        "attacking_corner": "Possibile calcio d'angolo offensivo",
        "defending_corner": "Possibile calcio d'angolo difensivo",
        "attacking_free_kick": "Possibile punizione offensiva",
        "defending_free_kick": "Possibile punizione difensiva",
        "attacking_throw_in": "Possibile rimessa laterale offensiva",
        "defending_throw_in": "Possibile rimessa laterale difensiva",
        "goal_kick": "Possibile rimessa dal fondo",
        "out_of_possession": "Possibile fase di non possesso",
        "defensive_line": "Possibile lettura della linea difensiva",
        "width": "Possibile lettura dell'ampiezza",
        "between_lines": "Possibile lettura dello spazio tra reparti",
        "rest_defense": "Possibile rest defense",
    }
    return labels.get(phase, "Momento video da classificare")

