"""
app/services/scout_service.py

Servizio Scout MatchIQ Tactical.
Qui sposteremo progressivamente:
- normalize_player_for_scout
- extract_players_for_scout
- build_real_scout_response
"""

from datetime import datetime

from app.utils.safe import safe_float, safe_int, clamp


def scout_service_ready():
    return {
        "service": "scout_service",
        "status": "ready",
        "generated_at": datetime.utcnow().isoformat()
    }
def normalize_player_for_scout(player, match_data=None):
    """
    Normalizza qualsiasi player ricevuto da API-Football / engine interni
    nello schema che scout.html V5.5 si aspetta.
    """
    if not isinstance(player, dict):
        return None

    match_data = match_data or {}

    name = (
        player.get("name")
        or player.get("player_name")
        or player.get("nome")
        or player.get("player")
    )

    if isinstance(name, dict):
        name = name.get("name")

    if not name:
        return None

    raw_role = (
        player.get("role")
        or player.get("position")
        or player.get("pos")
        or "MID"
    )

    role_upper = str(raw_role).upper()

    if role_upper in ["G", "GK", "GOALKEEPER", "PORTIERE"]:
        role = "GK"
    elif any(x in role_upper for x in ["ATT", "FORWARD", "STRIKER", "PUNTA", "ALA", "WINGER"]):
        role = "ATT"
    elif any(x in role_upper for x in ["DEF", "BACK", "CB", "LB", "RB", "DIF", "TERZINO"]):
        role = "DEF"
    else:
        role = "MID"

    rating = safe_float(
        player.get("rating_api")
        or player.get("rating")
        or player.get("vote")
        or player.get("score"),
        6.5
    )

    goals = safe_int(player.get("goals", 0))
    assists = safe_int(player.get("assists", 0))
    shots = safe_int(player.get("shots", player.get("shots_total", 0)))
    shots_on_target = safe_int(player.get("shots_on_target", player.get("shots_on", 0)))
    key_passes = safe_int(player.get("key_passes", player.get("keyPasses", 0)))
    dribbles = safe_int(player.get("dribbles", player.get("dribbles_success", 0)))
    tackles = safe_int(player.get("tackles", 0))
    interceptions = safe_int(player.get("interceptions", 0))
    duels_won = safe_int(player.get("duels_won", 0))
    minutes = safe_int(player.get("minutes", match_data.get("minute", 0)))
    xg = safe_float(player.get("xg", player.get("expected_goals", 0.0)))
    pass_accuracy = safe_int(player.get("pass_accuracy", player.get("passes_accuracy", 0)))
    fouls = safe_int(player.get("fouls", player.get("fouls_committed", 0)))
    cards_yellow = safe_int(player.get("cards_yellow", 0))
    cards_red = safe_int(player.get("cards_red", 0))

    threat = clamp(
        shots * 12
        + shots_on_target * 10
        + key_passes * 7
        + xg * 30
        + goals * 22
        + assists * 12
    )

    creativity = clamp(
        key_passes * 14
        + assists * 18
        + dribbles * 7
        + pass_accuracy * 0.35
    )

    pressure = clamp(
        tackles * 10
        + interceptions * 8
        + duels_won * 6
        + pass_accuracy * 0.20
    )

    momentum = clamp(
        rating * 8
        + threat * 0.22
        + creativity * 0.16
        + pressure * 0.10
        + goals * 12
        + assists * 8
    )

    fatigue = clamp(
        minutes * 0.55
        + fouls * 4
        + tackles * 2
        + dribbles * 1.5
        + cards_yellow * 5
        + cards_red * 15,
        5,
        94
    )

    stamina = clamp(100 - fatigue, 1, 100)

    scout_score = clamp(
        rating * 8
        + threat * 0.20
        + creativity * 0.18
        + pressure * 0.10
        + momentum * 0.24
        + stamina * 0.08
        + goals * 8
        + assists * 5,
        1,
        99
    )

    impact_score = clamp(
        scout_score * 0.35
        + threat * 0.22
        + creativity * 0.16
        + pressure * 0.10
        + momentum * 0.17,
        1,
        99
    )

    hidden_gem = (
        scout_score >= 65
        and creativity >= 55
        and goals == 0
        and assists == 0
    )

    danger_creator = (
        threat >= 70
        or shots >= 2
        or key_passes >= 3
        or xg >= 0.35
        or goals >= 1
        or assists >= 1
    )

    if scout_score >= 86:
        level = "ELITE"
    elif scout_score >= 74:
        level = "TOP PLAYER"
    elif scout_score >= 62:
        level = "GOOD TALENT"
    else:
        level = "STANDARD"

    if impact_score >= 84:
        signal_type = "hot"
        signal = "Hot Player"
    elif danger_creator:
        signal_type = "danger"
        signal = "Danger Creator"
    elif pressure >= 75:
        signal_type = "pressure"
        signal = "Pressure Trigger"
    elif hidden_gem:
        signal_type = "gem"
        signal = "Hidden Gem"
    else:
        signal_type = "watch"
        signal = "AI Watch"

    return {
        "id": player.get("id") or player.get("player_id") or str(name).lower().replace(" ", "_"),
        "name": name,
        "photo": player.get("photo") or (player.get("player") or {}).get("photo") if isinstance(player.get("player"), dict) else player.get("photo"),
        "team": (
            player.get("team")
            if isinstance(player.get("team"), str)
            else (player.get("team") or {}).get("name") if isinstance(player.get("team"), dict) else None
        ) or player.get("team_name") or player.get("squadra") or "Unknown",
        "team_logo": player.get("team_logo"),
        "role": role,
        "position": role,
        "rating": round(rating, 1),
        "goals": goals,
        "assists": assists,
        "shots": shots,
        "shots_on_target": shots_on_target,
        "key_passes": key_passes,
        "dribbles": dribbles,
        "tackles": tackles,
        "interceptions": interceptions,
        "duels_won": duels_won,
        "minutes": minutes,
        "pass_accuracy": pass_accuracy,
        "xg": round(xg, 2),
        "momentum": int(momentum),
        "fatigue": int(fatigue),
        "stamina": int(stamina),
        "impact_score": int(impact_score),
        "impact": int(impact_score),
        "scout_score": int(scout_score),
        "scoutScore": int(scout_score),
        "threat": int(threat),
        "danger": int(threat),
        "creativity": int(creativity),
        "creative_score": int(creativity),
        "pressure": int(pressure),
        "pressure_score": int(pressure),
        "keyPasses": key_passes,
        "hidden_gem": hidden_gem,
        "danger_creator": danger_creator,
        "level": level,
        "signal_type": signal_type,
        "signalType": signal_type,
        "signal": signal,
        "ai_signal": signal,
        "real_data": bool(player.get("rating_api") or player.get("id") or player.get("player_id")),
        "is_estimated": False,
        "data_quality": "real_live_player",
        "data_source": "api_football_live",
        "source": "api_football_live",
        "ai_summary": f"{name} monitorato da MatchIQ: segnale {signal}, impact {int(impact_score)} e threat {int(threat)}.",
        "generated_at": datetime.utcnow().isoformat()
    }

def extract_players_for_scout(data, match_data=None):
    """
    Estrae e normalizza players da varie strutture API/live engine.
    """

    players = []

    if isinstance(data, list):
        raw_players = data

    elif isinstance(data, dict):

        raw_players = (
            data.get("players")
            or data.get("top_players")
            or data.get("ratings")
            or []
        )

    else:
        raw_players = []

    for player in raw_players:

        normalized = normalize_player_for_scout(
            player,
            match_data=match_data
        )

        if normalized:
            players.append(normalized)

    return players
