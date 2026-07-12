import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from app.services.voice_coach_schemas import (
    VoiceCoachInterpretRequest,
    VoiceCoachInterpretResponse,
    VoiceCoachPlayer,
)


EVENT_MAP = {
    "goal": {"type": "gol", "label": "Gol", "icon": "GOL"},
    "shot": {"type": "tiro", "label": "Tiro", "icon": "TIRO"},
    "recovery": {"type": "recupero", "label": "Recupero palla", "icon": "REC"},
    "lost_ball": {"type": "palla_persa", "label": "Palla persa", "icon": "PERSA"},
    "yellow_card": {"type": "cartellino", "label": "Cartellino giallo", "icon": "GIALLO"},
}

THEME_RULES = [
    ("second_post", "Secondo palo", "area", "high", r"\b(secondo palo|palo dietro|palo libero)\b"),
    ("right_flank", "Fascia destra", "right_flank", "high", r"\b(destra|fascia destra|lato destro)\b"),
    ("left_flank", "Fascia sinistra", "left_flank", "medium", r"\b(sinistra|fascia sinistra|lato sinistro)\b"),
    ("low_press", "Pressing basso", "central", "medium", r"\b(pressiamo bassi|pressione bassa|troppo bassi|pressing basso)\b"),
    ("build_up", "Costruzione dal basso", "build_up", "medium", r"\b(usciamo dal basso|uscendo bene|costruzione|dal portiere|uscita bassa)\b"),
    ("negative_transition", "Transizione negativa", "central", "high", r"\b(transizione|ripartenza|contropiede|rest defense)\b"),
    ("duels", "Duelli e seconde palle", "duel", "medium", r"\b(duelli|seconda palla|rimbalzi|spizzata)\b"),
    ("tiredness", "Stanchezza", "individual", "medium", r"\b(stanco|stanchezza|non ne ha|fatica)\b"),
    ("team_long", "Distanza tra reparti", "central", "high", r"\b(squadra lunga|reparti|distanze|troppo lunghi)\b"),
]


def _clean(text: str) -> str:
    value = unicodedata.normalize("NFD", str(text or "").lower())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = re.sub(r"[.,;:!?]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _player_label(player: VoiceCoachPlayer) -> str:
    return f"#{player.number} {player.name}".strip() if player.number else player.name


def _minute(text: str, current: int) -> Tuple[int, str]:
    clean = _clean(text)
    match = re.search(r"\b(?:minuto|min|al minuto|all)\s*(\d{1,3})\b", clean)
    if not match:
        match = re.search(r"\b(\d{1,3})\s*(?:minuto|min|')\b", clean)
    if not match:
        return max(0, min(130, current)), ""
    value = max(0, min(130, int(match.group(1))))
    if current and abs(value - current) >= 12:
        return value, f"Minuto indicato ({value}') distante dal cronometro ({current}')."
    return value, ""


def _team(text: str, selected: str) -> Tuple[str, bool]:
    clean = _clean(text)
    if re.search(r"\b(loro|avversari|avversario|ospiti|trasferta|subiamo|ci pressano|ci attaccano|gol loro)\b", clean):
        return "away", False
    if re.search(r"\b(noi|nostra|nostro|casa|recuperiamo|pressiamo|gol nostro|segnamo|segnato noi)\b", clean):
        return "home", False
    return selected if selected in ("home", "away") else "home", True


def _resolve_player(text: str, lineup: List[VoiceCoachPlayer]) -> Tuple[Optional[VoiceCoachPlayer], float, List[VoiceCoachPlayer]]:
    clean = _clean(text)
    scored = []
    for player in lineup:
        name = _clean(player.name)
        if not name:
            continue
        score = 0.0
        if name in clean:
            score = 1.0
        else:
            parts = [part for part in name.split(" ") if len(part) >= 3]
            if any(part in clean for part in parts):
                score = 0.76
            elif player.number and re.search(rf"\b(?:numero\s*)?{re.escape(str(player.number))}\b", clean):
                score = 0.72
            else:
                score = SequenceMatcher(None, clean, name).ratio() * 0.55
        if score >= 0.55:
            scored.append((score, player))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return None, 0.0, []
    top = scored[0][0]
    alternatives = [player for score, player in scored if score >= top - 0.08][:4]
    return scored[0][1], top, alternatives


def _event_key(text: str) -> Optional[Tuple[str, float]]:
    clean = _clean(text)
    if re.search(r"\b(gol|rete|segnato)\b", clean):
        return "goal", 0.91
    if re.search(r"\b(tiro|conclusione|calcia)\b", clean):
        return "shot", 0.82
    if re.search(r"\b(recupero|recupera|riconquista|ruba palla|grande recupero)\b", clean):
        return "recovery", 0.86
    if re.search(r"\b(palla persa|perde palla|perso palla)\b", clean):
        return "lost_ball", 0.86
    if re.search(r"\b(giallo|cartellino)\b", clean):
        return "yellow_card", 0.82
    return None


def _theme(text: str) -> Dict[str, str]:
    clean = _clean(text)
    for key, label, zone, priority, pattern in THEME_RULES:
        if re.search(pattern, clean):
            return {"topic": key, "topic_label": label, "zone": zone, "priority": priority}
    return {"topic": "general_note", "topic_label": "Nota staff", "zone": "not_specified", "priority": "medium"}


def _sentiment(text: str) -> str:
    clean = _clean(text)
    if re.search(r"\b(bene|grande|ottimo|riusciamo|recupero|positivo|funziona|uscendo bene)\b", clean):
        return "positive"
    if re.search(r"\b(soffrendo|male|errore|persa|libero|troppo|problema|fatica|subiamo)\b", clean):
        return "negative"
    return "neutral"


def _substitution(text: str, lineup: List[VoiceCoachPlayer]) -> Optional[Dict[str, object]]:
    clean = _clean(text)
    if not re.search(r"\b(cambio|sostituzione|esce|entra|al posto di|per)\b", clean):
        return None
    out_player = None
    in_player = None
    out_first = re.search(r"\b(?:cambio|esce)\s+([a-z0-9 ]{2,40})\s+(?:per|entra|con)\s+([a-z0-9 ]{2,40})\b", clean)
    in_first = re.search(r"\b(?:entra|metti)\s+([a-z0-9 ]{2,40})\s+(?:per|al posto di)\s+([a-z0-9 ]{2,40})\b", clean)
    if out_first or in_first:
        out_text = out_first.group(1) if out_first else in_first.group(2)
        in_text = out_first.group(2) if out_first else in_first.group(1)
        out_player = _resolve_player(out_text, lineup)[0]
        in_player = _resolve_player(in_text, lineup)[0]
    if not out_player or not in_player:
        matches = []
        for player in lineup:
            score = _resolve_player(player.name, lineup)[1] if player.name else 0
            if player.name and _clean(player.name) in clean:
                matches.append(player)
        if not out_player and matches:
            out_player = matches[0]
        if not in_player and len(matches) > 1:
            in_player = matches[1]
    return {"out": out_player, "in": in_player, "confidence": 0.88 if out_player and in_player else 0.48}


def interpret_voice_coach_command(payload: VoiceCoachInterpretRequest) -> VoiceCoachInterpretResponse:
    text = payload.transcript.strip()
    clean = _clean(text)
    context = payload.context
    minute, minute_warning = _minute(text, context.current_minute)
    team, team_ambiguous = _team(text, context.selected_team)
    warnings = [minute_warning] if minute_warning else []
    ambiguities: List[str] = []

    if re.search(r"\b(annulla|lascia perdere|non salvare)\b", clean):
        return VoiceCoachInterpretResponse(
            intent="cancel",
            confidence=0.96,
            requires_confirmation=False,
            minute=minute,
            team=team,
            normalized_summary="Comando annullato.",
            privacy={"audio_stored": False, "transcript_source": payload.source},
        )

    substitution = _substitution(text, context.lineup)
    if substitution:
        out_player = substitution.get("out")
        in_player = substitution.get("in")
        if not out_player:
            ambiguities.append("Giocatore in uscita non riconosciuto.")
        if not in_player:
            ambiguities.append("Giocatore in entrata non riconosciuto.")
        return VoiceCoachInterpretResponse(
            intent="substitution",
            confidence=float(substitution["confidence"]),
            requires_confirmation=True,
            minute=minute,
            team=team,
            entities={
                "player_out_id": getattr(out_player, "id", "") if out_player else "",
                "player_out_name": _player_label(out_player) if out_player else "",
                "player_in_id": getattr(in_player, "id", "") if in_player else "",
                "player_in_name": _player_label(in_player) if in_player else "",
            },
            normalized_summary=(
                f"Cambio: {_player_label(out_player)} esce, {_player_label(in_player)} entra al {minute}'."
                if out_player and in_player
                else "Cambio da completare: non ho riconosciuto tutti i giocatori."
            ),
            ambiguities=ambiguities,
            warnings=warnings,
            privacy={"audio_stored": False, "transcript_source": payload.source},
        )

    player, player_confidence, alternatives = _resolve_player(text, context.lineup)
    event = _event_key(text)
    if event:
        key, confidence = event
        mapped = EVENT_MAP[key]
        if len(alternatives) > 1:
            ambiguities.append("Giocatore ambiguo: " + " / ".join(_player_label(p) for p in alternatives))
        if not player and key != "goal":
            ambiguities.append("Giocatore non riconosciuto nella formazione o in panchina.")
        return VoiceCoachInterpretResponse(
            intent="player_event",
            confidence=0.58 if not player and key != "goal" else confidence,
            requires_confirmation=(key == "goal" and team_ambiguous) or len(alternatives) > 1 or (not player and key != "goal"),
            minute=minute,
            team=team,
            entities={
                "event_key": key,
                "event_type": mapped["type"],
                "event_label": mapped["label"],
                "event_icon": mapped["icon"],
                "player_id": player.id if player else "",
                "player_name": _player_label(player) if player else "",
            },
            normalized_summary=f"{mapped['label']}{' di ' + _player_label(player) if player else ''} al {minute}'.",
            ambiguities=ambiguities,
            warnings=warnings,
            privacy={"audio_stored": False, "transcript_source": payload.source},
        )

    if re.search(r"\b(inizia|intervallo|riprendi|termina|fine partita|secondo tempo)\b", clean):
        return VoiceCoachInterpretResponse(
            intent="match_control",
            confidence=0.78,
            requires_confirmation=True,
            minute=minute,
            team=team,
            entities={"command": clean},
            normalized_summary="Comando partita da confermare.",
            warnings=warnings,
            privacy={"audio_stored": False, "transcript_source": payload.source},
        )

    theme = _theme(text)
    if len(alternatives) > 1:
        ambiguities.append("Giocatore ambiguo: " + " / ".join(_player_label(p) for p in alternatives))
    individual = bool(player and re.search(r"\b(stanco|duelli|giocando bene|male|perdendo|fatica)\b", clean))
    return VoiceCoachInterpretResponse(
        intent="player_note" if individual else "tactical_note",
        confidence=0.62 if theme["topic"] == "general_note" else 0.84,
        requires_confirmation=len(alternatives) > 1 or theme["topic"] == "general_note",
        minute=minute,
        team=team,
        entities={
            **theme,
            "sentiment": _sentiment(text),
            "player_id": player.id if player else "",
            "player_name": _player_label(player) if player else "",
            "note_original": text,
            "note_normalized": text,
        },
        normalized_summary=f"{theme['topic_label']}: {text}",
        ambiguities=ambiguities,
        warnings=warnings,
        privacy={"audio_stored": False, "transcript_source": payload.source},
    )
