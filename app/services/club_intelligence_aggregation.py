import re
from collections import Counter
from typing import Any, Dict, List

from app.repositories import club_intelligence_repository as repository


def _tokens(value: Any) -> List[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[,;|\n]+", str(value or ""))
    return [str(item).strip() for item in raw if str(item).strip()]


def _team_context(team: Dict[str, Any]) -> Dict[str, Any]:
    workspace_id = team.get("knowledge_workspace_id")
    profile = repository.get_team_profile(int(workspace_id)) if workspace_id else None
    coach = repository.get_coach_profile(int(workspace_id)) if workspace_id else None
    identity = repository.get_latest_identity(int(workspace_id)) if workspace_id else None
    sources = []
    if profile: sources.append("profilo_squadra")
    if coach: sources.append("identita_dichiarata_allenatore")
    if identity: sources.append("identita_osservata")
    formations = _tokens((profile or {}).get("formations_used"))
    if (coach or {}).get("preferred_formation"): formations.append(coach["preferred_formation"])
    return {
        "team": team, "team_profile": profile, "coach_profile": coach,
        "observed_identity": identity, "sources": sources, "data_level": "sufficiente" if len(sources) >= 2 else "parziale" if sources else "insufficiente",
        "formations": list(dict.fromkeys(formations)), "declared_principles": _tokens((profile or {}).get("playing_principles")) + _tokens((coach or {}).get("tactical_principles")),
    }


def build(club: Dict[str, Any], teams: List[Dict[str, Any]], principles: List[Dict[str, Any]]) -> Dict[str, Any]:
    contexts = [_team_context(team) for team in teams]
    comparable = [item for item in contexts if item["data_level"] != "insufficiente"]
    formation_count = Counter(value.lower() for item in comparable for value in item["formations"])
    common_formations = [value for value, count in formation_count.items() if count >= 2]
    declared = club.get("technical_principles_json") or []
    common_principles = [item["title"] for item in principles if len(item.get("team_ids_json") or []) >= 2]
    limitations = []
    if len(comparable) < 2: limitations.append("Servono almeno due squadre con fonti collegate per un confronto attendibile.")
    if any(item["data_level"] == "insufficiente" for item in contexts): limitations.append("Una o piu squadre non dispongono ancora di dati tecnici sufficienti.")
    limitations.append("Categorie ed eta differenti non sono confrontate tramite classifiche o giudizi automatici.")
    return {
        "club": {"id": club["id"], "name": club["name"], "season": club.get("season"), "declared_philosophy": club.get("declared_philosophy"), "declared_principles": declared},
        "teams": contexts,
        "continuity": {"common_formations": common_formations, "shared_principles": common_principles, "declared_club_principles": declared},
        "differences": [{"team_id": item["team"]["id"], "team_name": item["team"]["name"], "category": item["team"].get("category"), "formations": item["formations"], "context_note": "Differenza descrittiva da verificare con lo staff, non una valutazione."} for item in contexts],
        "data_quality": {"teams_total": len(contexts), "teams_comparable": len(comparable), "levels": {item["team"]["name"]: item["data_level"] for item in contexts}},
        "limitations": limitations,
        "guardrails": ["MatchIQ non inventa: ogni sintesi conserva la fonte.", "L'allenatore decide sempre; l'AI suggerisce sempre.", "Ogni squadra mantiene il proprio contesto e i propri permessi."],
    }
