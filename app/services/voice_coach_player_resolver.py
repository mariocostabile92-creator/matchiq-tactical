from difflib import SequenceMatcher
from typing import Dict, Iterable, List

from app.services.voice_coach_taxonomy import normalize_text


def _aliases(player: Dict) -> List[str]:
    values = [player.get("name", ""), player.get("nickname", "")]
    values.extend(player.get("aliases") or [])
    name = normalize_text(player.get("name", ""))
    values.extend(part for part in name.split() if len(part) >= 3)
    return list(dict.fromkeys(normalize_text(value) for value in values if normalize_text(value)))


def resolve_players(text: str, players: Iterable[Dict]) -> Dict:
    clean = normalize_text(text)
    scored = []
    for player in players:
        best = 0.0
        for alias in _aliases(player):
            if alias in clean:
                best = max(best, 1.0 if " " in alias else 0.82)
            else:
                best = max(best, SequenceMatcher(None, clean, alias).ratio() * 0.58)
        number = str(player.get("number") or "").strip()
        if number and f"numero {number}" in clean:
            best = max(best, 0.78)
        if best >= 0.55:
            scored.append((best, player))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return {"player": None, "confidence": 0.0, "candidates": [], "warning": ""}
    top = scored[0][0]
    candidates = [player for score, player in scored if score >= top - 0.07][:4]
    warning = ""
    if len(candidates) > 1:
        warning = "Intendevi " + " o ".join(str(player.get("name") or "") for player in candidates) + "?"
    return {"player": scored[0][1], "confidence": top, "candidates": candidates, "warning": warning}
