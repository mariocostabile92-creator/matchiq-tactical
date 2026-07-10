from __future__ import annotations

import re
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
    required_signals: Tuple[str, ...] = ()


SITUATIONS: Tuple[TacticalSituation, ...] = (
    TacticalSituation("corner_defensive", "Calcio d'angolo difensivo", "corner", ("calcio d'angolo difensivo", "corner difensivo"), True, 84, ("corner", "calcio d'angolo", "bandierina", "area", "palla ferma", "punto di battuta")),
    TacticalSituation("corner_offensive", "Calcio d'angolo offensivo", "corner", ("calcio d'angolo offensivo", "corner offensivo"), True, 84, ("corner", "calcio d'angolo", "bandierina", "area", "palla ferma", "punto di battuta")),
    TacticalSituation("wide_free_kick_defensive", "Punizione laterale difensiva", "free_kick", ("punizione laterale difensiva",), True, 80, ("punizione", "palla ferma", "barriera", "punto di battuta", "linea difensiva", "fallo")),
    TacticalSituation("wide_free_kick_offensive", "Punizione laterale offensiva", "free_kick", ("punizione laterale offensiva",), True, 80, ("punizione", "palla ferma", "barriera", "punto di battuta", "linea difensiva", "fallo")),
    TacticalSituation("central_free_kick_defensive", "Punizione centrale difensiva", "free_kick", ("punizione centrale difensiva",), True, 80, ("punizione", "palla ferma", "barriera", "punto di battuta", "linea difensiva", "fallo")),
    TacticalSituation("central_free_kick_offensive", "Punizione centrale offensiva", "free_kick", ("punizione centrale offensiva",), True, 80, ("punizione", "palla ferma", "barriera", "punto di battuta", "linea difensiva", "fallo")),
    TacticalSituation("throw_in_defensive", "Rimessa laterale difensiva", "throw_in", ("rimessa laterale difensiva",), True, 80, ("rimessa", "laterale", "linea laterale", "mani", "fuori", "battuta")),
    TacticalSituation("throw_in_offensive", "Rimessa laterale offensiva", "throw_in", ("rimessa laterale offensiva",), True, 80, ("rimessa", "laterale", "linea laterale", "mani", "fuori", "battuta")),
    TacticalSituation("goal_kick", "Rimessa dal fondo", "goal_kick", ("rimessa dal fondo", "rinvio dal fondo"), True, 76, ("rimessa dal fondo", "rinvio", "portiere", "area piccola", "difensori", "palla ferma")),
    TacticalSituation("build_from_back", "Costruzione dal basso", "build_up", ("costruzione dal basso", "portiere", "prima costruzione"), True, 74, ("portiere", "difensori", "prima costruzione", "pressione", "linee di passaggio", "palla bassa")),
    TacticalSituation("defensive_line", "Linea difensiva", "line", ("linea difensiva", "difensiva"), False, 64),
    TacticalSituation("midfield_line", "Linea centrocampo", "line", ("centrocampo", "linea centrocampo"), False, 62),
    TacticalSituation("offensive_line", "Linea offensiva", "line", ("linea offensiva", "offensiva"), False, 62),
    TacticalSituation("pressing", "Pressing e transizioni", "pressing", ("pressing", "transizione", "transizioni"), False, 64),
    TacticalSituation("width", "Ampiezza", "spacing", ("ampiezza",), False, 62),
    TacticalSituation("between_lines", "Spazio tra reparti", "spacing", ("spazio tra reparti", "reparti"), False, 62),
    TacticalSituation("rest_defense", "Rest defense", "rest_defense", ("rest defense", "rest difensiva"), False, 62),
    TacticalSituation("set_piece_defensive", "Palla inattiva difensiva", "set_piece_defensive", ("palla inattiva difensiva", "palle inattive difensive"), True, 78, ("calcio d'angolo", "corner", "punizione", "rimessa", "laterale", "palla ferma", "punto di battuta", "bandierina", "barriera", "area", "marcature")),
    TacticalSituation("set_piece_offensive", "Palla inattiva offensiva", "set_piece_offensive", ("palla inattiva offensiva", "palle inattive offensive"), True, 78, ("calcio d'angolo", "corner", "punizione", "rimessa", "laterale", "palla ferma", "punto di battuta", "bandierina", "barriera", "area", "marcature")),
    TacticalSituation("set_piece_generic", "Palla inattiva", "set_piece", ("palla inattiva", "palle inattive"), True, 76, ("calcio d'angolo", "corner", "punizione", "rimessa", "laterale", "palla ferma", "punto di battuta", "bandierina", "barriera", "area", "marcature")),
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
    return resolve_situation(_signals_text(note))


def _signals_text(note: Dict[str, Any]) -> str:
    values: List[Any] = [
        note.get("set_piece_type"),
        note.get("phase"),
        note.get("label"),
        note.get("reason"),
        note.get("grade_reason"),
        note.get("camera"),
        note.get("ai_reason"),
        note.get("restart_type"),
        note.get("restart_side"),
        note.get("field_zone"),
        note.get("ball_state"),
        note.get("evidence"),
    ]
    for key in ("visual_signals", "missing_signals"):
        signals = note.get(key)
        if isinstance(signals, list):
            values.extend(signals)
        else:
            values.append(signals)
    return _text(*values)


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


def _signal_hits(text: str, signals: Tuple[str, ...]) -> List[str]:
    hits: List[str] = []
    for signal in signals:
        if not signal or signal not in text:
            continue
        negated = re.search(rf"(senza|manca|mancano|non si vede|non visibile|assente)\s+.{0,24}{re.escape(signal)}", text)
        if not negated:
            hits.append(signal)
    return hits


def _set_piece_evidence(requested: TacticalSituation, detected: TacticalSituation, text: str) -> Tuple[List[str], List[str]]:
    reasons: List[str] = []
    reject_reasons: List[str] = []

    if requested.group == "corner" or detected.group == "corner":
        hits = _signal_hits(text, ("corner", "calcio d'angolo", "bandierina", "area", "palla ferma", "punto di battuta", "traiettoria da corner"))
        if "azione a campo aperto" in text or "open_play" in text:
            reject_reasons.append("azione aperta, non calcio d'angolo")
        if not any(hit in hits for hit in ("corner", "calcio d'angolo")) or not any(hit in hits for hit in ("bandierina", "area", "palla ferma", "punto di battuta", "traiettoria da corner")):
            reject_reasons.append("mancano prove visive da calcio d'angolo")

    if requested.group == "free_kick" or detected.group == "free_kick":
        hits = _signal_hits(text, ("punizione", "palla ferma", "barriera", "punto di battuta", "fallo", "linea difensiva"))
        if "azione a campo aperto" in text or "open_play" in text:
            reject_reasons.append("azione aperta, non punizione")
        if "punizione" not in hits or len(hits) < 2:
            reject_reasons.append("mancano prove visive da punizione")

    if requested.group == "throw_in" or detected.group == "throw_in":
        hits = _signal_hits(text, ("rimessa", "laterale", "linea laterale", "mani", "fuori", "battuta"))
        if "azione a campo aperto" in text or "open_play" in text:
            reject_reasons.append("azione aperta, non rimessa laterale")
        if "rimessa" not in hits or len(hits) < 2:
            reject_reasons.append("mancano prove visive da rimessa laterale")

    if requested.group == "goal_kick" or detected.group == "goal_kick":
        hits = _signal_hits(text, ("rimessa dal fondo", "rinvio", "portiere", "area piccola", "palla ferma", "difensori"))
        if not any(hit in hits for hit in ("rimessa dal fondo", "rinvio", "portiere")) or len(hits) < 2:
            reject_reasons.append("mancano prove visive da rimessa dal fondo")

    if requested.group == "build_up" or detected.group == "build_up":
        has_first_line = any(signal in text for signal in ("portiere", "difensori", "centrali", "area"))
        has_build_signal = any(signal in text for signal in ("prima costruzione", "costruzione dal basso", "pressione", "linee di passaggio", "palla bassa"))
        if not (has_first_line and has_build_signal):
            reject_reasons.append("mancano portiere/difensori e segnali di prima costruzione")

    if requested.group in {"set_piece", "set_piece_defensive", "set_piece_offensive"}:
        if detected.group == "set_piece" or detected.id.startswith("set_piece"):
            reasons.append("palla inattiva generica: classificare il tipo prima del PDF")
        hits = _signal_hits(text, requested.required_signals)
        if len(hits) < 2:
            reject_reasons.append("palla inattiva non dimostrata da segnali visivi sufficienti")

    return reasons, reject_reasons


def validate_frame_note(
    note: Dict[str, Any],
    requested: TacticalSituation,
    local_meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    local_meta = local_meta or {}
    detected = detected_situation(note)
    quality = _quality(note.get("quality") or note.get("ai_quality"))
    text = _signals_text(note)

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
    if requested.strict and requested.group == "goal_kick" and detected.group != "goal_kick":
        reject_reasons.append("rimessa dal fondo non riconosciuta con certezza")
    if requested.strict and requested.group == "build_up" and detected.group != "build_up":
        reject_reasons.append("costruzione dal basso non riconosciuta con certezza")

    evidence_reasons, evidence_rejects = _set_piece_evidence(requested, detected, text)
    reasons.extend(evidence_reasons)
    reject_reasons.extend(evidence_rejects)

    if detected.group == "set_piece" and requested.group in {"set_piece", "set_piece_defensive", "set_piece_offensive"}:
        quality = min(quality, 58)
    if reject_reasons:
        quality = min(quality, 44)

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
