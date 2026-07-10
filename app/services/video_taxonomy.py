from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class TacticalSituation:
    id: str
    label: str
    group: str
    keywords: Tuple[str, ...]
    strict: bool = False
    min_quality: int = 65


SITUATIONS: Tuple[TacticalSituation, ...] = (
    TacticalSituation("corner_defensive", "Calcio d'angolo difensivo", "corner", ("calcio d'angolo difensivo", "corner difensivo"), True, 82),
    TacticalSituation("corner_offensive", "Calcio d'angolo offensivo", "corner", ("calcio d'angolo offensivo", "corner offensivo"), True, 82),
    TacticalSituation("wide_free_kick_defensive", "Punizione laterale difensiva", "free_kick", ("punizione laterale difensiva",), True, 78),
    TacticalSituation("wide_free_kick_offensive", "Punizione laterale offensiva", "free_kick", ("punizione laterale offensiva",), True, 78),
    TacticalSituation("central_free_kick_defensive", "Punizione centrale difensiva", "free_kick", ("punizione centrale difensiva",), True, 78),
    TacticalSituation("central_free_kick_offensive", "Punizione centrale offensiva", "free_kick", ("punizione centrale offensiva",), True, 78),
    TacticalSituation("throw_in_defensive", "Rimessa laterale difensiva", "throw_in", ("rimessa laterale difensiva",), True, 78),
    TacticalSituation("throw_in_offensive", "Rimessa laterale offensiva", "throw_in", ("rimessa laterale offensiva",), True, 78),
    TacticalSituation("goal_kick", "Rimessa dal fondo", "goal_kick", ("rimessa dal fondo", "rinvio dal fondo"), True, 74),
    TacticalSituation("build_from_back", "Costruzione dal basso", "build_up", ("costruzione dal basso", "portiere", "prima costruzione"), True, 72),
    TacticalSituation("defensive_line", "Linea difensiva", "line", ("linea difensiva", "difensiva"), False, 64),
    TacticalSituation("midfield_line", "Linea centrocampo", "line", ("centrocampo", "linea centrocampo"), False, 62),
    TacticalSituation("offensive_line", "Linea offensiva", "line", ("linea offensiva", "offensiva"), False, 62),
    TacticalSituation("pressing", "Pressing e transizioni", "pressing", ("pressing", "transizione", "transizioni"), False, 64),
    TacticalSituation("width", "Ampiezza", "spacing", ("ampiezza",), False, 62),
    TacticalSituation("between_lines", "Spazio tra reparti", "spacing", ("spazio tra reparti", "reparti"), False, 62),
    TacticalSituation("rest_defense", "Rest defense", "rest_defense", ("rest defense", "rest difensiva"), False, 62),
    TacticalSituation("set_piece_defensive", "Palla inattiva difensiva", "set_piece_defensive", ("palla inattiva difensiva", "palle inattive difensive"), True, 78),
    TacticalSituation("set_piece_offensive", "Palla inattiva offensiva", "set_piece_offensive", ("palla inattiva offensiva", "palle inattive offensive"), True, 78),
    TacticalSituation("set_piece_generic", "Palla inattiva", "set_piece", ("palla inattiva", "palle inattive"), True, 76),
    TacticalSituation("general", "Analisi tattica generale", "general", ("analisi tattica", "generale"), False, 55),
)


BAD_FRAME_KEYWORDS = (
    "non tattico",
    "scart",
    "esultanza",
    "primo piano",
    "giocatore isolato",
    "panchina",
    "arbitro isolato",
    "replay",
)


def _text(*values: Any) -> str:
    return " ".join(str(value or "") for value in values).lower()


def _quality(value: Any) -> int:
    try:
        return max(0, min(100, int(float(value or 0))))
    except Exception:
        return 0


def resolve_situation(value: str) -> TacticalSituation:
    text = _text(value)
    exact_matches = [item for item in SITUATIONS if any(keyword in text for keyword in item.keywords)]
    if exact_matches:
        return sorted(exact_matches, key=lambda item: len(item.label), reverse=True)[0]
    return SITUATIONS[-1]


def detected_situation(note: Dict[str, Any]) -> TacticalSituation:
    return resolve_situation(_text(note.get("set_piece_type"), note.get("phase"), note.get("label"), note.get("reason")))


def _compatible(requested: TacticalSituation, detected: TacticalSituation) -> bool:
    if requested.id == "general":
        return True
    if requested.id == detected.id:
        return True
    if requested.id == "set_piece_generic":
        return detected.group in {"corner", "free_kick", "throw_in", "goal_kick", "set_piece"}
    if requested.id == "set_piece_defensive":
        return detected.id.endswith("defensive") or detected.group == "goal_kick"
    if requested.id == "set_piece_offensive":
        return detected.id.endswith("offensive")
    if requested.group == "free_kick" and detected.group == "free_kick":
        return requested.id.split("_")[-1] == detected.id.split("_")[-1]
    if requested.group in {"line", "spacing"} and detected.group in {"line", "spacing", "pressing", "general"}:
        return True
    return False


def _local_reasons(meta: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    try:
        green_ratio = float(meta.get("green_ratio") or 0)
    except Exception:
        green_ratio = 0
    if green_ratio and green_ratio < 0.14:
        reasons.append("poco campo visibile")
    try:
        white_ratio = float(meta.get("white_ratio") or 0)
    except Exception:
        white_ratio = 0
    if white_ratio and white_ratio < 0.004:
        reasons.append("pochi riferimenti di campo o giocatori")
    return reasons


def validate_frame_note(
    note: Dict[str, Any],
    requested: TacticalSituation,
    local_meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    local_meta = local_meta or {}
    detected = detected_situation(note)
    quality = _quality(note.get("quality") or note.get("ai_quality"))
    text = _text(note.get("phase"), note.get("set_piece_type"), note.get("grade"), note.get("reason"), note.get("grade_reason"))

    reasons: List[str] = []
    reject_reasons: List[str] = []

    if any(keyword in text for keyword in BAD_FRAME_KEYWORDS):
        reject_reasons.append("inquadratura non collettiva")

    local_flags = _local_reasons(local_meta)
    if local_flags:
        reasons.extend(local_flags)
        if requested.strict:
            reject_reasons.extend(local_flags)

    if not _compatible(requested, detected):
        reject_reasons.append(f"richiesto {requested.label}, rilevato {detected.label}")

    if requested.strict and requested.group == "corner" and detected.group != "corner":
        reject_reasons.append("corner non riconosciuto con certezza")
    if requested.strict and requested.group == "throw_in" and detected.group != "throw_in":
        reject_reasons.append("rimessa laterale non riconosciuta con certezza")
    if requested.strict and requested.group == "free_kick" and detected.group != "free_kick":
        reject_reasons.append("punizione non riconosciuta con certezza")

    threshold = requested.min_quality
    if reject_reasons:
        status = "rejected"
    elif quality >= threshold:
        status = "verified"
    elif quality >= max(45, threshold - 18):
        status = "candidate"
        reasons.append("da controllare prima del report")
    else:
        status = "rejected"
        reject_reasons.append("confidenza insufficiente")

    return {
        **note,
        "label": note.get("label") or note.get("phase") or detected.label,
        "set_piece_type": note.get("set_piece_type") or (detected.label if detected.group in {"corner", "free_kick", "throw_in", "goal_kick"} else ""),
        "ai_quality": quality,
        "confidence": quality,
        "requested_situation_id": requested.id,
        "requested_label": requested.label,
        "detected_situation_id": detected.id,
        "detected_label": detected.label,
        "validation_status": status,
        "validation_reasons": reasons,
        "rejection_reasons": reject_reasons,
        "feedback_status": "none",
    }


def _dedupe_by_time(indexes: Iterable[int], frame_times: List[float], min_gap_seconds: int = 7) -> List[int]:
    selected: List[int] = []
    for index in indexes:
        if index < 0:
            continue
        try:
            current = float(frame_times[index])
        except Exception:
            current = float(index * min_gap_seconds)
        too_close = False
        for chosen in selected:
            try:
                chosen_time = float(frame_times[chosen])
            except Exception:
                chosen_time = float(chosen * min_gap_seconds)
            if abs(current - chosen_time) < min_gap_seconds:
                too_close = True
                break
        if not too_close:
            selected.append(index)
    return selected


def validate_selection_result(result: Dict[str, Any], data: Any, frame_count: int, max_count: int) -> Dict[str, Any]:
    requested = resolve_situation(getattr(data, "focus", "") or "")
    frame_meta = list(getattr(data, "frame_meta", []) or [])
    frame_times = list(getattr(data, "frame_times", []) or [])
    raw_notes = result.get("frame_notes") or []

    notes_by_index: Dict[str, Dict[str, Any]] = {}
    for raw_note in raw_notes:
        try:
            index = int(raw_note.get("index"))
        except Exception:
            continue
        if index < 0 or index >= frame_count:
            continue
        local_meta = frame_meta[index] if index < len(frame_meta) and isinstance(frame_meta[index], dict) else {}
        notes_by_index[str(index)] = validate_frame_note(raw_note, requested, local_meta)

    selected_order: List[int] = []
    for value in result.get("selected_indexes") or []:
        try:
            index = int(value)
        except Exception:
            continue
        if 0 <= index < frame_count and index not in selected_order:
            selected_order.append(index)

    all_note_indexes = []
    for key in notes_by_index:
        try:
            all_note_indexes.append(int(key))
        except Exception:
            pass
    ordered = selected_order + [idx for idx in all_note_indexes if idx not in selected_order]

    verified = [idx for idx in ordered if notes_by_index.get(str(idx), {}).get("validation_status") == "verified"]
    candidates = [idx for idx in ordered if notes_by_index.get(str(idx), {}).get("validation_status") == "candidate"]
    rejected = [idx for idx in ordered if notes_by_index.get(str(idx), {}).get("validation_status") == "rejected"]

    verified = _dedupe_by_time(verified, frame_times)[:max_count]
    candidates = [idx for idx in _dedupe_by_time(candidates, frame_times) if idx not in verified][:max_count]

    return {
        "ok": True,
        "selected_indexes": verified,
        "verified_indexes": verified,
        "candidate_indexes": candidates,
        "rejected_indexes": rejected,
        "frame_notes": notes_by_index,
        "team_guess": result.get("team_guess") or {},
        "validation_summary": {
            "requested": requested.label,
            "verified": len(verified),
            "candidates": len(candidates),
            "rejected": len(rejected),
        },
    }
