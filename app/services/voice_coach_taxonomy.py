import re
import unicodedata
from typing import Dict, List


TACTICAL_TOPICS = {
    "pressing": {"label": "Pressing", "zone": "central", "priority": "medium", "patterns": [r"press(?:ing|iamo|ione)", r"riaggress"]},
    "build_up": {"label": "Costruzione dal basso", "zone": "build_up", "priority": "medium", "patterns": [r"dal basso", r"dal portiere", r"costruzione", r"uscita bassa"]},
    "positive_transition": {"label": "Transizione positiva", "zone": "central", "priority": "medium", "patterns": [r"transizione positiva", r"ripartiamo bene", r"attacchiamo subito"]},
    "negative_transition": {"label": "Transizione negativa", "zone": "central", "priority": "high", "patterns": [r"transizione negativa", r"ripartenza", r"contropiede", r"rest defense", r"rientro"]},
    "right_flank": {"label": "Fascia destra", "zone": "right_flank", "priority": "high", "patterns": [r"destra", r"lato destro"]},
    "left_flank": {"label": "Fascia sinistra", "zone": "left_flank", "priority": "medium", "patterns": [r"sinistra", r"lato sinistro"]},
    "central_zone": {"label": "Zona centrale", "zone": "central", "priority": "medium", "patterns": [r"centro", r"zona centrale", r"centralmente"]},
    "width": {"label": "Ampiezza", "zone": "wide", "priority": "medium", "patterns": [r"ampiezza", r"troppo stretti", r"allargh"]},
    "depth": {"label": "Profondita", "zone": "deep", "priority": "medium", "patterns": [r"profondita", r"attacco spazio", r"alle spalle"]},
    "second_post": {"label": "Secondo palo", "zone": "area", "priority": "high", "patterns": [r"secondo palo", r"palo dietro", r"palo libero"]},
    "first_post": {"label": "Primo palo", "zone": "area", "priority": "medium", "patterns": [r"primo palo"]},
    "set_piece": {"label": "Palla inattiva", "zone": "set_piece", "priority": "medium", "patterns": [r"palla inattiva", r"calcio d.angolo", r"corner", r"punizione", r"rimessa"]},
    "duels": {"label": "Duelli", "zone": "duel", "priority": "medium", "patterns": [r"duell", r"seconda palla", r"rimbalzi", r"spizzata"]},
    "lost_ball": {"label": "Palla persa", "zone": "not_specified", "priority": "high", "patterns": [r"palla persa", r"perde palla", r"perso palla"]},
    "recovery": {"label": "Recupero palla", "zone": "not_specified", "priority": "medium", "patterns": [r"recuper", r"riconquist", r"ruba palla"]},
    "marking": {"label": "Marcatura", "zone": "defensive", "priority": "high", "patterns": [r"marcatura", r"marcato", r"uomo libero", r"copertura"]},
    "team_distance": {"label": "Distanza tra reparti", "zone": "central", "priority": "high", "patterns": [r"squadra lunga", r"distanza.*repart", r"troppo lunghi"]},
    "tiredness": {"label": "Stanchezza", "zone": "individual", "priority": "medium", "patterns": [r"stanco", r"stanchezza", r"fatica", r"non ne ha"]},
    "individual_difficulty": {"label": "Difficolta individuale", "zone": "individual", "priority": "high", "patterns": [r"in difficolta", r"sta giocando male", r"soffre"]},
    "positive_behavior": {"label": "Comportamento positivo", "zone": "not_specified", "priority": "low", "patterns": [r"giocando bene", r"molto bene", r"ottimo", r"bravo"]},
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[.,;:!?]+", " ", text)).strip()


def classify_tactical_topic(text: str) -> Dict[str, str]:
    clean = normalize_text(text)
    matches: List[tuple] = []
    for key, item in TACTICAL_TOPICS.items():
        score = sum(1 for pattern in item["patterns"] if re.search(pattern, clean))
        if score:
            matches.append((score, key, item))
    if not matches:
        return {"topic": "general_note", "topic_label": "Nota staff", "zone": "not_specified", "priority": "medium"}
    _, key, item = sorted(matches, key=lambda row: row[0], reverse=True)[0]
    return {"topic": key, "topic_label": item["label"], "zone": item["zone"], "priority": item["priority"]}


def tactical_topic_options() -> List[Dict[str, str]]:
    return [{"key": key, **{field: item[field] for field in ("label", "zone", "priority")}} for key, item in TACTICAL_TOPICS.items()]
