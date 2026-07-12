from collections import Counter
from typing import Any, Dict, List, Optional

from app.models.voice_coach_intelligence import VoiceObservationCreate
from app.repositories import knowledge_repository, voice_coach_repository
from app.services import knowledge_service
from app.services.voice_coach_schemas import VoiceCoachInterpretRequest, VoiceCoachInterpretResponse


def initialize_voice_coach_intelligence() -> None:
    voice_coach_repository.initialize_voice_coach_schema()


def knowledge_players(user_id: int) -> List[Dict[str, Any]]:
    knowledge = knowledge_service.get_knowledge(user_id)
    return [
        {
            "id": f"knowledge:{player.id}",
            "name": player.name,
            "role": player.role or "",
            "number": "",
            "side": "home",
            "status": "Rosa",
            "nickname": "",
            "aliases": [],
            "source": "knowledge",
        }
        for player in knowledge.roster
    ]


def enrich_interpretation(result: VoiceCoachInterpretResponse, request: VoiceCoachInterpretRequest) -> VoiceCoachInterpretResponse:
    entities = result.entities or {}
    result.match_phase = request.context.period or "1T"
    result.tactical_topic = str(entities.get("topic") or entities.get("event_key") or result.intent)
    result.zone = str(entities.get("zone") or "not_specified")
    result.polarity = str(entities.get("sentiment") or ("positive" if entities.get("event_key") in {"goal", "recovery"} else "neutral"))
    result.priority = str(entities.get("priority") or ("high" if result.intent in {"substitution", "score_update"} else "medium"))
    evidence = [f"Cronometro Match Day: {request.context.current_minute}'", f"Fase: {request.context.period}"]
    if entities.get("player_name"):
        evidence.append(f"Giocatore trovato nei dati partita: {entities['player_name']}")
    if entities.get("topic_label"):
        evidence.append(f"Espressione associata alla tassonomia: {entities['topic_label']}")
    result.evidence = evidence
    all_players = [*request.context.lineup, *request.context.bench]
    player_by_id = {str(player.id): player for player in all_players}
    selected_ids = [entities.get("player_id"), entities.get("player_out_id"), entities.get("player_in_id")]
    for player_id in [str(value) for value in selected_ids if value not in (None, "")]:
        player = player_by_id.get(player_id)
        if player and str(player.id) in request.context.substituted_player_ids:
            result.warnings.append(f"{player.name} risulta gia sostituito.")
    out_player = player_by_id.get(str(entities.get("player_out_id") or ""))
    in_player = player_by_id.get(str(entities.get("player_in_id") or ""))
    if result.intent == "substitution" and out_player and out_player.status == "Panchina":
        result.warnings.append(f"{out_player.name} risulta in panchina, non in campo.")
    if result.intent == "substitution" and in_player and in_player.status != "Panchina":
        result.warnings.append(f"{in_player.name} non risulta disponibile in panchina.")
    if entities.get("topic_label"):
        result.explanation = f"Ho associato l'osservazione al tema '{entities['topic_label']}' usando le parole registrate e il contesto della partita."
    elif result.intent == "substitution":
        result.explanation = "Ho riconosciuto un cambio e l'ho confrontato con formazione e panchina. Serve conferma prima di modificare la plancia."
    elif result.intent == "player_event":
        result.explanation = "Ho riconosciuto un evento partita e l'eventuale giocatore solo tra i nominativi disponibili."
    else:
        result.explanation = "Ho classificato il comando usando il cronometro e i dati disponibili della partita."
    if result.ambiguities:
        result.clarification_question = result.ambiguities[0]
        result.clarification_options = ["Giocatore", "Zona", "Reparto", "Salva senza specificare"]
    elif result.tactical_topic == "general_note" or (
        result.tactical_topic == "individual_difficulty" and not entities.get("player_id")
    ):
        result.clarification_question = "Il problema riguarda una zona, un reparto o un giocatore?"
        result.clarification_options = ["Zona", "Reparto", "Giocatore", "Salva senza specificare"]
    elif result.tactical_topic == "second_post" and "set_piece" not in request.transcript.lower():
        result.clarification_question = "Succede su calcio d'angolo, punizione laterale o azione aperta?"
        result.clarification_options = ["Calcio d'angolo", "Punizione laterale", "Azione aperta", "Salva senza specificare"]
    return result


def _priority_rank(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(value, 1)


def _summaries(observations: List[Dict], themes: List[Dict]) -> Dict[str, Dict[str, Any]]:
    confirmed = [item for item in observations if item.get("status") == "confirmed"]
    positives = [item for item in confirmed if item.get("polarity") == "positive"]
    critical = [item for item in confirmed if item.get("polarity") == "negative" or _priority_rank(item.get("priority")) >= 2]
    player_counts = Counter(name for item in confirmed for name in (item.get("player_names") or []))
    objective_events = [item for item in confirmed if item.get("intent") in {"player_event", "substitution", "score_update"}]
    staff_notes = [item for item in confirmed if item.get("intent") in {"tactical_note", "player_note"}]
    ai_readings = [
        {"topic": item.get("label"), "count": item.get("count"), "status": item.get("status")}
        for item in themes[:5]
    ]
    common = {
        "total_observations": len(confirmed),
        "top_themes": themes[:5],
        "positive_notes": positives[-5:],
        "critical_notes": sorted(critical, key=lambda item: _priority_rank(item.get("priority")), reverse=True)[:6],
        "most_mentioned_players": [{"name": name, "count": count} for name, count in player_counts.most_common(5)],
        "objective_events": objective_events[-8:],
        "staff_observations": staff_notes[-8:],
        "ai_interpretations": ai_readings,
    }
    return {"halftime": dict(common), "post_match": {**common, "timeline": confirmed[-12:]}}


def _proactive(themes: List[Dict], observations: List[Dict]) -> List[Dict[str, Any]]:
    suggestions = []
    for theme in themes:
        if theme.get("count", 0) >= 3 and theme.get("status") == "active":
            suggestions.append({
                "key": f"theme:{theme['id']}:{theme['count']}",
                "type": "recurring_theme",
                "message": f"Hai segnalato {theme['count']} volte {str(theme['label']).lower()}. Vuoi vedere il riepilogo?",
                "theme_id": theme["id"],
                "cooldown_seconds": 600,
            })
    if observations:
        latest_minute = max(int(item.get("minute") or 0) for item in observations)
        if 40 <= latest_minute <= 48:
            suggestions.append({
                "key": f"halftime:{latest_minute // 3}",
                "type": "halftime",
                "message": "L'intervallo e vicino. Vuoi preparare una sintesi delle osservazioni principali?",
                "cooldown_seconds": 600,
            })
    return suggestions[:3]


def save_observation(user_id: int, payload: VoiceObservationCreate) -> Dict[str, Any]:
    workspace = knowledge_repository.get_or_create_workspace(user_id)
    knowledge_id = int(workspace["id"])
    observation = voice_coach_repository.upsert_observation(user_id, knowledge_id, payload.model_dump())
    if observation.get("status") == "confirmed":
        knowledge_repository.upsert_source_link(
            knowledge_id,
            "voice_coach",
            payload.client_id,
            {
                "match_key": payload.match_key,
                "match_id": payload.match_id,
                "topic": payload.tactical_topic,
                "players": payload.player_ids,
                "minute": payload.minute,
                "source": payload.source,
                "validation_status": payload.status,
                "created_at": str(observation.get("created_at") or ""),
            },
        )
    themes = voice_coach_repository.rebuild_themes(user_id, knowledge_id, payload.match_key)
    return {"observation": observation, "themes": themes}


def cancel_observation(user_id: int, client_id: str) -> Optional[Dict[str, Any]]:
    observation = voice_coach_repository.set_observation_status(user_id, client_id, "cancelled")
    if not observation:
        return None
    knowledge_repository.delete_source_link(int(observation["knowledge_id"]), "voice_coach", client_id)
    voice_coach_repository.rebuild_themes(user_id, int(observation["knowledge_id"]), observation["match_key"])
    return observation


def match_intelligence(user_id: int, match_key: str) -> Dict[str, Any]:
    observations = voice_coach_repository.list_observations(user_id, match_key)
    themes = voice_coach_repository.list_themes(user_id, match_key)
    summaries = _summaries(observations, themes)
    return {
        "observations": observations,
        "themes": themes,
        "proactive_suggestions": _proactive(themes, observations),
        **summaries,
    }


def update_theme_status(user_id: int, match_key: str, theme_id: int, status: str) -> Optional[Dict[str, Any]]:
    return voice_coach_repository.set_theme_status(user_id, match_key, theme_id, status)


def delete_match_intelligence(user_id: int, match_key: str) -> int:
    links = voice_coach_repository.delete_match_intelligence(user_id, match_key)
    for link in links:
        knowledge_repository.delete_source_link(int(link["knowledge_id"]), "voice_coach", str(link["client_id"]))
    return len(links)
