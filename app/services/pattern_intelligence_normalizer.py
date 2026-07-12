from typing import Any, Dict

from app.services.voice_coach_taxonomy import TACTICAL_TOPICS, classify_tactical_topic, normalize_text


EVENT_TOPIC_MAP = {
    "palla_persa": ("lost_ball", "Palla persa", "negative"),
    "errore_difensivo": ("marking", "Marcatura", "negative"),
    "recupero": ("recovery", "Recupero palla", "positive"),
    "pressing": ("pressing", "Pressing", "positive"),
    "ampiezza": ("width", "Ampiezza", "positive"),
    "transizione": ("negative_transition", "Transizione negativa", "negative"),
    "linea_bassa": ("team_distance", "Distanza tra reparti", "negative"),
    "squadra_lunga": ("team_distance", "Distanza tra reparti", "negative"),
    "uscita_lato": ("build_up", "Costruzione dal basso", "neutral"),
    "profondita": ("depth", "Profondita", "positive"),
    "seconda_palla": ("duels", "Duelli", "neutral"),
}


def match_phase(minute: Any) -> str:
    try:
        value = int(float(minute or 0))
    except (TypeError, ValueError):
        value = 0
    if value <= 15:
        return "first_15"
    if 40 <= value <= 50:
        return "pre_halftime"
    if value >= 70:
        return "after_70"
    return "first_half" if value <= 45 else "second_half"


def normalize_event(event: Dict[str, Any]) -> Dict[str, str]:
    event_type = normalize_text(event.get("type") or event.get("event_type"))
    note = str(event.get("note") or event.get("text") or "").strip()
    mapped = EVENT_TOPIC_MAP.get(event_type)
    tags=" ".join(str(item) for item in (event.get("tags") or []))
    classified = classify_tactical_topic(" ".join([event_type, note, tags]))
    if mapped:
        topic, label, polarity = mapped
    else:
        topic = classified["topic"]
        label = classified["topic_label"]
        polarity = str(event.get("polarity") or "neutral")
    return {
        "topic": topic,
        "label": label,
        "zone": str(event.get("zone") or classified.get("zone") or "not_specified"),
        "phase": str(event.get("phase") or match_phase(event.get("minute"))),
        "polarity": polarity,
    }


def topic_label(topic: str) -> str:
    return str((TACTICAL_TOPICS.get(topic) or {}).get("label") or topic.replace("_", " ").title())
