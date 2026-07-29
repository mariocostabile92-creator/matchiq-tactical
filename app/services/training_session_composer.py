from typing import Any, Dict, Iterable, List, Optional


WEEKDAYS = {
    "lunedi": 0,
    "lunedì": 0,
    "martedi": 1,
    "martedì": 1,
    "mercoledi": 2,
    "mercoledì": 2,
    "giovedi": 3,
    "giovedì": 3,
    "venerdi": 4,
    "venerdì": 4,
    "sabato": 5,
    "domenica": 6,
}

BLOCKS = (
    ("activation", "Attivazione", 12),
    ("technique", "Tecnica", 16),
    ("situational", "Situazionale", 24),
    ("position_game", "Gioco di posizione", 18),
    ("themed_match", "Partita a tema", 22),
    ("cooldown", "Defaticamento", 8),
)

TOPIC_BLOCK = {
    "duels": "technique",
    "central_zone": "technique",
    "depth": "technique",
    "marking": "situational",
    "set_piece": "situational",
    "first_post": "situational",
    "second_post": "situational",
    "negative_transition": "situational",
    "positive_transition": "situational",
    "possession": "position_game",
    "build_up": "position_game",
    "width": "position_game",
    "team_distance": "position_game",
    "pressing": "themed_match",
    "recovery": "themed_match",
    "right_flank": "themed_match",
}


def _unique(values: Iterable[Any]) -> List[Any]:
    seen = set()
    output = []
    for value in values:
        if value is None:
            continue
        key = str(value)
        if key.strip() and key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _weekday(value: Optional[str]) -> Optional[int]:
    normalized = str(value or "").strip().lower()
    return WEEKDAYS.get(normalized)


def _days_to_match(training_day: str, match_day: Optional[str]) -> Optional[int]:
    training_index = _weekday(training_day)
    match_index = _weekday(match_day)
    if training_index is None or match_index is None:
        return None
    distance = (match_index - training_index) % 7
    return distance or 7


def _load_strategy(days_to_match: Optional[int], intensity: str) -> str:
    if days_to_match == 1:
        return "rifinitura"
    if days_to_match == 2:
        return "consolidamento"
    if days_to_match is not None and days_to_match >= 5:
        return "sviluppo"
    return "carico_%s" % (intensity or "medio")


def _decision(
    proposal: Dict[str, Any],
    days_to_match: Optional[int],
    average_intensity: str,
) -> Dict[str, Any]:
    drills = proposal.get("drills") or []
    status = "SCHEDULED"
    reason = "Priorità confermata e coerente con il contesto della prossima seduta."
    if not drills:
        status = "DEFERRED"
        reason = (
            "La libreria verificata non contiene ancora un'esercitazione compatibile "
            "con questa priorità e con i vincoli della squadra."
        )
    elif days_to_match == 1 and all(
        str(item.get("intensity") or "").lower() == "alta" for item in drills
    ):
        status = "DEFERRED"
        reason = (
            "Priorità valida, ma il carico disponibile è troppo alto per il giorno "
            "precedente alla partita."
        )
    elif str(average_intensity or "").lower() == "bassa" and all(
        str(item.get("intensity") or "").lower() == "alta" for item in drills
    ):
        status = "DEFERRED"
        reason = (
            "Priorità rinviata: le esercitazioni disponibili superano l'intensità "
            "media dichiarata nel profilo squadra."
        )
    return {
        "priority_id": str(proposal.get("priority_id") or ""),
        "topic": proposal.get("topic"),
        "title": proposal.get("title"),
        "status": status,
        "reason": reason,
        "pattern_ids": (proposal.get("references") or {}).get("pattern_ids") or [],
        "evidence_ids": (proposal.get("references") or {}).get("evidence_ids") or [],
        "canonical_match_ids": (
            proposal.get("references") or {}
        ).get("canonical_match_ids") or [],
    }


def _block_durations(total: int) -> Dict[str, int]:
    durations = {
        key: max(5, round(total * percentage / 100))
        for key, _label, percentage in BLOCKS
    }
    difference = total - sum(durations.values())
    durations["themed_match"] += difference
    return durations


def _block_objective(
    block: str,
    included: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> str:
    titles = _unique(item.get("title") for item in included if item.get("title"))
    focus = ", ".join(titles[:2]) or "carico e disponibilità della squadra"
    if block == "activation":
        return "Preparare la squadra al carico della seduta."
    if block == "cooldown":
        return "Ridurre progressivamente il carico e raccogliere il feedback."
    if block == "technique":
        return f"Curare i prerequisiti tecnici collegati a {focus}."
    if block == "situational":
        return f"Allenare in situazione le priorità: {focus}."
    if block == "position_game":
        principles = profile.get("playing_principles") or []
        principle = principles[0] if principles else "i principi di gioco dichiarati"
        return f"Collegare {focus} a {principle}."
    return f"Verificare {focus} in un contesto competitivo controllato."


def compose_session(
    proposals: List[Dict[str, Any]],
    settings: Dict[str, Any],
    team_profile: Dict[str, Any],
    training_days: List[str],
) -> Dict[str, Any]:
    selected_days = [str(value).strip() for value in training_days if str(value).strip()]
    training_day = selected_days[0] if selected_days else "Da programmare"
    match_day = team_profile.get("match_day")
    days_to_match = _days_to_match(training_day, match_day)
    decisions = [
        _decision(
            proposal,
            days_to_match,
            team_profile.get("average_intensity") or settings.get("intensity") or "media",
        )
        for proposal in proposals
    ]
    included_ids = {
        item["priority_id"] for item in decisions if item["status"] == "SCHEDULED"
    }
    included = [
        item for item in proposals if str(item.get("priority_id") or "") in included_ids
    ]
    deferred = [item for item in decisions if item["status"] == "DEFERRED"]

    drills = []
    for proposal in included:
        for source in proposal.get("drills") or []:
            drill = dict(source)
            drill["composer_block"] = TOPIC_BLOCK.get(
                str(drill.get("tactical_theme") or proposal.get("topic") or ""),
                "situational",
            )
            drill["priority_id"] = str(proposal.get("priority_id") or "")
            drills.append(drill)

    durations = _block_durations(int(settings["session_duration"]))
    blocks = []
    for key, label, _percentage in BLOCKS:
        block_drills = [item["id"] for item in drills if item["composer_block"] == key]
        blocks.append(
            {
                "block_id": key,
                "label": label,
                "duration": durations[key],
                "objective": _block_objective(key, included, team_profile),
                "drill_ids": block_drills,
                "status": "library_drills" if block_drills else "staff_protocol",
                "note": (
                    ""
                    if block_drills
                    else "Completa con il protocollo abituale dello staff."
                ),
            }
        )

    references = {
        "canonical_match_ids": _unique(
            value
            for item in included
            for value in (item.get("references") or {}).get(
                "canonical_match_ids", []
            )
        ),
        "pattern_ids": _unique(
            value
            for item in included
            for value in (item.get("references") or {}).get("pattern_ids", [])
        ),
        "evidence_ids": _unique(
            value
            for item in included
            for value in (item.get("references") or {}).get("evidence_ids", [])
        ),
    }
    objective_titles = _unique(
        item.get("title") for item in included if item.get("title")
    )
    objective = (
        " + ".join(objective_titles[:2])
        if objective_titles
        else "Seduta da completare con lo staff"
    )
    reason = (
        "Composizione basata su profilo squadra, calendario e priorità confermate."
    )
    if deferred:
        reason += f" {len(deferred)} priorità rinviate per coerenza del carico."

    session = {
        "session_id": "session_composer_%s" % training_day.lower().replace(" ", "_"),
        "title": f"Seduta: {objective}",
        "day": training_day,
        "objective": objective,
        "why": reason,
        "theme": ", ".join(_unique(item.get("topic") for item in included)) or "staff",
        "duration": int(settings["session_duration"]),
        "players": int(settings["players"]),
        "goalkeepers": int(settings["goalkeepers"]),
        "intensity": settings["intensity"],
        "drills": drills,
        "blocks": blocks,
        "decision_summary": (
            f"{len(included)} priorità inserite, {len(deferred)} rinviate."
        ),
        "notes": "",
        "status": "proposta_ai",
        "priority_ids": [str(item.get("priority_id") or "") for item in included],
        "references": references,
    }
    calendar_context = {
        "training_day": training_day,
        "training_days": selected_days,
        "match_day": match_day,
        "days_to_match": days_to_match,
        "load_strategy": _load_strategy(days_to_match, settings["intensity"]),
    }
    explainability = {
        "chain": ["Pattern", "Priorità", "Decisione", "Seduta"],
        **references,
        "decision_priority_ids": [item["priority_id"] for item in decisions],
    }
    return {
        "contract": "weekly-priority-session-composer-v2",
        "title": "Seduta MatchIQ",
        "sessions": [session],
        "priorities": proposals,
        "team_profile": {
            key: team_profile.get(key)
            for key in (
                "category",
                "level",
                "average_age",
                "player_count",
                "goalkeeper_count",
                "training_days",
                "training_duration",
                "match_day",
                "pitch_type",
                "pitch_dimensions",
                "available_materials",
                "playing_principles",
                "preferred_formation",
                "average_intensity",
                "season_objectives",
            )
        },
        "calendar_context": calendar_context,
        "decisions": decisions,
        "explainability": explainability,
        "disclaimer": (
            "La seduta è una bozza deterministica basata sui dati disponibili. "
            "Lo staff modifica e conferma sempre contenuti e carichi definitivi."
        ),
    }
