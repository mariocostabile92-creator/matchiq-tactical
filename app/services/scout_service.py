"""
import time
from datetime import datetime

from app.utils.safe import safe_float, safe_int, clamp
from app.utils.cache import cache_valid
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

def build_real_scout_response(
    match_id=None,
    *,
    scout_players_cache,
    scout_players_cache_seconds,
    get_match_live_data_func,
    get_cached_full_analysis_func,
    build_live_scout_func,
    scout_engine_available=False
):
    """
    Risposta Scout V6 compatibile con scout.html V5.5.
    Versione service: riceve cache e funzioni esterne da main.py.
    """
    cache_key = f"scout_{match_id}"
    cached = scout_players_cache.get(cache_key)

    if cache_valid(cached, scout_players_cache_seconds):
        data = cached["data"].copy()
        cached_players = data.get("players", [])

        if isinstance(cached_players, list) and len(cached_players) > 0:
            data["cache"] = True
            data["cache_seconds"] = scout_players_cache_seconds
            return data

    match_data = {}
    players = []
    source_mode = "real_players_unavailable"
    error_message = None

    if match_id:
        try:
            match_data = get_match_live_data_func(match_id)

            if isinstance(match_data, dict) and "error" not in match_data:
                real_players = (
                    match_data.get("players")
                    or match_data.get("lineups")
                    or match_data.get("player_statistics")
                    or []
                )

                players = extract_players_for_scout(
                    real_players,
                    match_data=match_data
                )

                source_mode = "live_real_players" if players else "live_no_players"
            else:
                error_message = match_data.get("error") if isinstance(match_data, dict) else "match_data non valido"

        except Exception as e:
            error_message = str(e)
            match_data = {
                "error": str(e),
                "match_id": match_id
            }
            players = []

    if not players and match_id:
        try:
            full = get_cached_full_analysis_func(match_id)

            if isinstance(full, dict) and "error" not in full:
                match_data = full.get("match", match_data) or match_data

                players = extract_players_for_scout(
                    full.get("match", {}).get("players", []),
                    match_data=match_data
                )

                if not players:
                    players = extract_players_for_scout(
                        full.get("players_analysis", {}),
                        match_data=match_data
                    )

                if players:
                    source_mode = "live_full_analysis"

        except Exception as e:
            error_message = str(e)

    if not isinstance(match_data, dict):
        match_data = {}

    home = (
        match_data.get("home")
        or match_data.get("home_team")
        or "Home"
    )

    away = (
        match_data.get("away")
        or match_data.get("away_team")
        or "Away"
    )

    league = match_data.get("league") or "Live"
    minute = safe_int(match_data.get("minute", match_data.get("elapsed", 0)), 0)
    status = match_data.get("status") or "LIVE"

    score_raw = match_data.get("score", {})

    if isinstance(score_raw, str):
        parts = score_raw.replace(" ", "").split("-")
        score = {
            "home": safe_int(parts[0], 0) if len(parts) > 0 else 0,
            "away": safe_int(parts[1], 0) if len(parts) > 1 else 0
        }
    elif isinstance(score_raw, dict):
        score = score_raw
    else:
        score = {
            "home": safe_int(match_data.get("home_goals", 0), 0),
            "away": safe_int(match_data.get("away_goals", 0), 0)
        }

    home_goals = safe_int(score.get("home", match_data.get("home_goals", 0)), 0)
    away_goals = safe_int(score.get("away", match_data.get("away_goals", 0)), 0)

    def make_virtual_player(team, role_code, role_label, index, side):
        is_home = side == "home"
        team_goals = home_goals if is_home else away_goals
        opp_goals = away_goals if is_home else home_goals

        role_bonus = {
            "ATT": 16,
            "MID": 12,
            "DEF": 8,
            "GK": 5
        }.get(role_code, 8)

        match_bonus = clamp((team_goals - opp_goals) * 8, -12, 18)
        minute_bonus = clamp(minute * 0.35, 0, 35)

        scout_score = clamp(58 + role_bonus + match_bonus + minute_bonus - (index * 2), 45, 94)
        threat = clamp((team_goals * 18) + (role_bonus * 2) + (minute * 0.25) - (index * 3), 5, 88)
        creativity = clamp(role_bonus * 3 + minute * 0.18 + team_goals * 10 - index, 8, 86)
        pressure = clamp(30 + minute * 0.22 + abs(team_goals - opp_goals) * 8 + (6 - index), 10, 90)
        momentum = clamp(scout_score * 0.65 + threat * 0.2 + creativity * 0.15, 0, 99)
        fatigue = clamp(minute * 0.55 + index * 3, 10, 88)
        stamina = clamp(100 - fatigue, 0, 100)
        impact_score = clamp(momentum * 0.55 + threat * 0.25 + creativity * 0.20, 1, 99)

        if impact_score >= 82:
            signal_type = "hot"
            signal = "Hot Player"
            level = "ELITE"
        elif threat >= 65:
            signal_type = "danger"
            signal = "Danger Creator"
            level = "TOP PLAYER"
        elif creativity >= 62:
            signal_type = "gem"
            signal = "Hidden Gem"
            level = "GOOD TALENT"
        else:
            signal_type = "watch"
            signal = "AI Watch"
            level = "STANDARD"

        return {
            "id": f"virtual_{side}_{index}_{role_code.lower()}",
            "name": f"{team} {role_label}",
            "photo": None,
            "team": team,
            "team_logo": match_data.get("home_logo") if is_home else match_data.get("away_logo"),
            "role": role_code,
            "position": role_code,
            "rating": round(6.3 + scout_score / 40, 1),
            "goals": 0,
            "assists": 0,
            "shots": 0,
            "shots_on_target": 0,
            "key_passes": 0,
            "dribbles": 0,
            "tackles": 0,
            "interceptions": 0,
            "duels_won": 0,
            "minutes": minute,
            "pass_accuracy": 0,
            "xg": 0.0,
            "momentum": int(momentum),
            "fatigue": int(fatigue),
            "stamina": int(stamina),
            "scout_score": int(scout_score),
            "scoutScore": int(scout_score),
            "impact_score": int(impact_score),
            "impact": int(impact_score),
            "threat": int(threat),
            "danger": int(threat),
            "creativity": int(creativity),
            "creative_score": int(creativity),
            "pressure": int(pressure),
            "pressure_score": int(pressure),
            "keyPasses": 0,
            "hidden_gem": signal_type == "gem",
            "danger_creator": signal_type == "danger",
            "level": level,
            "signal_type": signal_type,
            "signalType": signal_type,
            "signal": signal,
            "ai_signal": signal,
            "real_data": False,
            "is_estimated": True,
            "data_quality": "fallback_role_profile",
            "data_source": "matchiq_virtual_scout",
            "source": "matchiq_virtual_scout",
            "ai_summary": f"Profilo ruolo stimato per {team}: {role_label}. Utile quando API-Football non fornisce player reali per campionati minori.",
            "generated_at": datetime.utcnow().isoformat()
        }

    if not players:
        role_plan = [
            ("ATT", "Attaccante"),
            ("MID", "Regista"),
            ("MID", "Mezzala"),
            ("DEF", "Difensore"),
            ("GK", "Portiere"),
        ]

        generated_players = []

        for i, (role_code, role_label) in enumerate(role_plan):
            generated_players.append(
                make_virtual_player(home, role_code, role_label, i, "home")
            )

        for i, (role_code, role_label) in enumerate(role_plan):
            generated_players.append(
                make_virtual_player(away, role_code, role_label, i, "away")
            )

        players = sorted(
            generated_players,
            key=lambda x: x.get("scout_score", 0),
            reverse=True
        )

        source_mode = "fallback_virtual_roles"

    players = sorted(
        players,
        key=lambda x: x.get("scout_score", 0),
        reverse=True
    )[:16]

    try:
        scout = build_live_scout_func(
            players=players,
            match_data=match_data
        )
    except Exception as e:
        scout = {
            "available": False,
            "source": "scout_engine_exception",
            "error": str(e),
            "players": players
        }

    if not isinstance(scout, dict):
        scout = {
            "available": False,
            "source": "scout_engine_invalid",
            "players": players
        }

    scout["available"] = True
    scout["source"] = "scout_engine" if scout_engine_available else "fallback"
    scout["match_id"] = match_id
    scout["mode"] = "live" if match_id else "demo"
    scout["data_mode"] = source_mode
    scout["real_players"] = source_mode in ["live_real_players", "live_full_analysis"]
    scout["fallback_players"] = source_mode == "fallback_virtual_roles"
    scout["premium_feature"] = True
    scout["required_plan"] = "scout"
    scout["cache"] = False
    scout["cache_seconds"] = scout_players_cache_seconds
    scout["api_safe"] = True
    scout["players"] = players
    scout["total_players"] = len(players)
    scout["events"] = scout.get("events", [])
    scout["error"] = error_message
    scout["version"] = "6.0-scout-fallback"

    scout["match"] = {
        "id": match_id,
        "match_id": match_id,
        "fixture_id": match_id,
        "home": home,
        "away": away,
        "home_logo": match_data.get("home_logo"),
        "away_logo": match_data.get("away_logo"),
        "score": {
            "home": home_goals,
            "away": away_goals
        },
        "home_goals": home_goals,
        "away_goals": away_goals,
        "minute": minute,
        "elapsed": minute,
        "status": status,
        "league": league,
    }

    scout["summary"] = {
        "mode": source_mode,
        "message": (
            "Giocatori reali disponibili"
            if scout["real_players"]
            else "Profili ruolo generati da MatchIQ per match senza dati player reali"
        ),
        "total_players": len(players),
        "top_player": players[0].get("name") if players else None,
        "avg_scout_score": round(sum(p.get("scout_score", 0) for p in players) / len(players), 1) if players else 0,
        "avg_threat": round(sum(p.get("threat", 0) for p in players) / len(players), 1) if players else 0,
        "avg_creativity": round(sum(p.get("creativity", 0) for p in players) / len(players), 1) if players else 0,
        "avg_pressure": round(sum(p.get("pressure", 0) for p in players) / len(players), 1) if players else 0,
        "avg_momentum": round(sum(p.get("momentum", 0) for p in players) / len(players), 1) if players else 0,
        "avg_stamina": round(sum(p.get("stamina", 0) for p in players) / len(players), 1) if players else 0,
    }

    if match_id and players:
        scout_players_cache[cache_key] = {
            "timestamp": time.time(),
            "data": scout
        }

    return scout
