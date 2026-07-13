from typing import Dict, Tuple


DIMENSIONS: Dict[str, dict] = {
    "structure.primary_formation": {"group": "structure", "label": "Modulo principale", "topics": ("formation", "module")},
    "structure.alternative_formation": {"group": "structure", "label": "Modulo alternativo", "topics": ("formation_change", "module")},
    "structure.variations": {"group": "structure", "label": "Variazioni di struttura", "topics": ("shape_change", "formation_change", "tactical_change")},
    "structure.formation_stability": {"group": "structure", "label": "Stabilita del modulo", "topics": ("formation", "shape")},
    "buildup.short": {"group": "buildup", "label": "Costruzione dal basso", "topics": ("build_up", "short_build_up", "goalkeeper_build_up")},
    "buildup.direct": {"group": "buildup", "label": "Gioco diretto", "topics": ("direct_play", "verticality")},
    "buildup.goalkeeper": {"group": "buildup", "label": "Utilizzo portiere", "topics": ("goalkeeper_build_up", "goalkeeper")},
    "buildup.central": {"group": "buildup", "label": "Sviluppo centrale", "topics": ("central_build_up", "third_man")},
    "buildup.wide": {"group": "buildup", "label": "Sviluppo laterale", "topics": ("wide_build_up", "width")},
    "buildup.third_man": {"group": "buildup", "label": "Terzo uomo", "topics": ("third_man",)},
    "buildup.verticality": {"group": "buildup", "label": "Verticalita", "topics": ("verticality", "direct_play")},
    "attack.possession": {"group": "attack", "label": "Possesso", "topics": ("possession",)},
    "attack.width": {"group": "attack", "label": "Ampiezza", "topics": ("width",)},
    "attack.depth": {"group": "attack", "label": "Profondita", "topics": ("depth",)},
    "attack.finishing": {"group": "attack", "label": "Rifinitura", "topics": ("finishing", "chance")},
    "attack.cross": {"group": "attack", "label": "Cross", "topics": ("cross",)},
    "attack.box": {"group": "attack", "label": "Attacco area", "topics": ("box_attack", "finishing")},
    "attack.positive_transition": {"group": "attack", "label": "Transizione positiva", "topics": ("positive_transition", "counterattack")},
    "attack.between_lines": {"group": "attack", "label": "Gioco tra le linee", "topics": ("between_lines", "third_man")},
    "defence.high_press": {"group": "defence", "label": "Pressione alta", "topics": ("pressing", "high_press")},
    "defence.mid_block": {"group": "defence", "label": "Blocco medio", "topics": ("mid_block", "compactness")},
    "defence.low_block": {"group": "defence", "label": "Blocco basso", "topics": ("low_block", "line_low")},
    "defence.marking": {"group": "defence", "label": "Marcatura", "topics": ("marking", "coverage")},
    "defence.box_protection": {"group": "defence", "label": "Protezione area", "topics": ("box_protection", "coverage")},
    "defence.second_post": {"group": "defence", "label": "Difesa secondo palo", "topics": ("second_post",)},
    "defence.unit_distances": {"group": "defence", "label": "Distanze tra reparti", "topics": ("compactness", "unit_distance", "team_long")},
    "defence.duels": {"group": "defence", "label": "Duelli", "topics": ("duel", "second_ball")},
    "transition.counterpress": {"group": "transitions", "label": "Riaggressione", "topics": ("pressing", "counterpress", "ball_loss")},
    "transition.recovery": {"group": "transitions", "label": "Recupero posizione", "topics": ("recovery", "negative_transition")},
    "transition.fast_attack": {"group": "transitions", "label": "Attacco rapido", "topics": ("positive_transition", "counterattack")},
    "transition.consolidation": {"group": "transitions", "label": "Consolidamento dopo recupero", "topics": ("recovery", "possession")},
    "set_piece.corner_attack": {"group": "set_pieces", "label": "Corner offensivi", "topics": ("corner_offensive", "set_piece_offensive")},
    "set_piece.corner_defence": {"group": "set_pieces", "label": "Corner difensivi", "topics": ("corner_defensive", "set_piece_defensive")},
    "set_piece.free_kick_attack": {"group": "set_pieces", "label": "Punizioni offensive", "topics": ("free_kick_offensive", "set_piece_offensive")},
    "set_piece.free_kick_defence": {"group": "set_pieces", "label": "Punizioni difensive", "topics": ("free_kick_defensive", "set_piece_defensive")},
    "set_piece.marking": {"group": "set_pieces", "label": "Marcatura sui piazzati", "topics": ("set_piece_marking", "marking")},
    "game.start": {"group": "game_management", "label": "Approccio iniziale", "topics": ("first_15", "match_start")},
    "game.leading": {"group": "game_management", "label": "Dopo il vantaggio", "topics": ("after_lead",)},
    "game.trailing": {"group": "game_management", "label": "Dopo lo svantaggio", "topics": ("after_trailing",)},
    "game.final": {"group": "game_management", "label": "Gestione finale", "topics": ("after_70", "match_end")},
    "game.change_reaction": {"group": "game_management", "label": "Reazione dopo cambio", "topics": ("substitution", "formation_change")},
    "squad.usage": {"group": "squad", "label": "Utilizzo giocatori", "topics": ("player_usage",)},
    "squad.roles": {"group": "squad", "label": "Ruoli ricorrenti", "topics": ("player_role",)},
    "squad.characteristics": {"group": "squad", "label": "Caratteristiche emergenti", "topics": ("player_characteristic", "squad_characteristic")},
    "squad.adaptability": {"group": "squad", "label": "Adattabilita", "topics": ("adaptability", "formation_change")},
    "squad.leadership": {"group": "squad", "label": "Leadership", "topics": ("leadership", "communication")},
    "squad.dependencies": {"group": "squad", "label": "Dipendenze tattiche", "topics": ("player_dependency",)},
}

GROUPS: Tuple[str, ...] = ("structure", "buildup", "attack", "defence", "transitions", "set_pieces", "game_management", "squad")


def dimension_for_topic(topic: str):
    value = (topic or "").strip().lower()
    return [key for key, item in DIMENSIONS.items() if value and value in item["topics"]]
