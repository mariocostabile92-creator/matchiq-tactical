"""
api_scout.py
MatchIQ Tactical - Scout Mode API

Prima versione:
- genera profili scout dai match live
- usa dati reali disponibili dal live engine
- crea scout score, tag e profili giocatore
"""

from fastapi import APIRouter
from datetime import datetime
import random

from live_data import get_live_matches, get_match_live_data


router = APIRouter(prefix="/api/scout", tags=["Scout"])


SCOUT_ROLES = [
    "Portiere",
    "Difensore centrale",
    "Terzino",
    "Mediano",
    "Regista",
    "Mezzala",
    "Esterno",
    "Trequartista",
    "Attaccante"
]


def clamp(value, minimum=0, maximum=100):
    try:
        value = float(value)
    except Exception:
        value = 0

    return max(minimum, min(maximum, value))


def calculate_scout_score(momentum, danger, impact, fatigue, aggression):
    score = (
        momentum * 0.28
        + danger * 0.30
        + impact * 0.27
        + aggression * 0.08
        + (100 - fatigue) * 0.07
    )

    return round(clamp(score), 1)


def get_scout_tag(score, danger, momentum, fatigue, aggression):
    if score >= 88 and fatigue <= 45:
        return "💎 HIDDEN GEM"

    if danger >= 85:
        return "🔥 DANGER CREATOR"

    if momentum >= 82:
        return "⚡ MOMENTUM PLAYER"

    if aggression >= 80:
        return "🧱 DUEL MONSTER"

    if fatigue >= 82:
        return "⚠️ FATIGUE RISK"

    if score >= 75:
        return "📈 HIGH POTENTIAL"

    return "🧠 MONITOR PLAYER"


def get_potential_level(score):
    if score >= 88:
        return "ELITE"
    if score >= 78:
        return "HIGH"
    if score >= 68:
        return "MEDIUM"
    return "LOW"


def build_fake_profile(team_name):
    role = random.choice(SCOUT_ROLES)

    name = f"{team_name} {role}"

    momentum = random.randint(45, 95)
    danger = random.randint(35, 95)
    impact = random.randint(50, 96)
    fatigue = random.randint(20, 88)
    aggression = random.randint(20, 90)

    score = calculate_scout_score(
        momentum=momentum,
        danger=danger,
        impact=impact,
        fatigue=fatigue,
        aggression=aggression
    )

    return {
        "name": name,
        "team": team_name,
        "role": role,
        "source": "fallback-ai-profile",
        "scout_score": score,
        "potential_level": get_potential_level(score),
        "tag": get_scout_tag(score, danger, momentum, fatigue, aggression),
        "momentum": momentum,
        "danger": danger,
        "impact": impact,
        "fatigue": fatigue,
        "aggression": aggression,
        "summary": f"{name} mostra segnali interessanti per intensità, impatto e profilo tattico live."
    }


def build_profile_from_player(player):
    name = player.get("name", "Unknown Player")
    team = player.get("team", "Unknown Team")
    role = player.get("role") or player.get("position") or "Player"

    rating = clamp(player.get("rating", player.get("rating_api", 6.5)), 0, 10)
    danger = clamp(player.get("danger", 0))
    momentum = clamp(player.get("momentum", 0))
    fatigue = clamp(player.get("fatigue", 35))
    aggression = clamp(player.get("aggression", 0))
    impact = clamp(player.get("impact_score", rating * 10))

    if danger == 0 and momentum == 0:
        shots = player.get("shots", 0)
        shots_on = player.get("shots_on_target", 0)
        key_passes = player.get("key_passes", 0)
        tackles = player.get("tackles", 0)
        interceptions = player.get("interceptions", 0)
        minutes = player.get("minutes", 0)

        danger = clamp(
            shots * 12
            + shots_on * 18
            + key_passes * 10
        )

        momentum = clamp(
            shots * 10
            + shots_on * 16
            + key_passes * 9
        )

        aggression = clamp(
            tackles * 9
            + interceptions * 8
        )

        fatigue = clamp(minutes * 0.95)

        impact = clamp(
            danger * 0.35
            + momentum * 0.28
            + aggression * 0.12
            + rating * 8
        )

    score = calculate_scout_score(
        momentum=momentum,
        danger=danger,
        impact=impact,
        fatigue=fatigue,
        aggression=aggression
    )

    tag = get_scout_tag(
        score=score,
        danger=danger,
        momentum=momentum,
        fatigue=fatigue,
        aggression=aggression
    )

    return {
        "name": name,
        "team": team,
        "role": role,
        "source": "live-player-data",
        "scout_score": score,
        "potential_level": get_potential_level(score),
        "tag": tag,
        "momentum": round(momentum, 1),
        "danger": round(danger, 1),
        "impact": round(impact, 1),
        "fatigue": round(fatigue, 1),
        "aggression": round(aggression, 1),
        "summary": f"{name} profilo {tag}: score {score}, impatto {round(impact, 1)} e momentum {round(momentum, 1)}."
    }


def build_scout_profiles_for_match(match):
    match_id = match.get("match_id") or match.get("fixture_id") or match.get("id")

    home = match.get("home", "Home")
    away = match.get("away", "Away")

    profiles = []

    if not match_id:
        return profiles

    try:
        match_data = get_match_live_data(int(match_id))
        players = match_data.get("players", []) or []

        for player in players:
            profiles.append(build_profile_from_player(player))

    except Exception:
        profiles = []

    if not profiles:
        profiles = [
            build_fake_profile(home),
            build_fake_profile(away),
            build_fake_profile(home),
            build_fake_profile(away)
        ]

    profiles = sorted(
        profiles,
        key=lambda x: x.get("scout_score", 0),
        reverse=True
    )

    return profiles[:8]


@router.get("/live")
def scout_live(top_only: bool = False):
    live = get_live_matches(top_only=top_only)
    matches = live.get("matches", []) if isinstance(live, dict) else []

    scout_cards = []

    for match in matches[:10]:
        match_id = match.get("match_id") or match.get("fixture_id") or match.get("id")

        profiles = build_scout_profiles_for_match(match)

        for profile in profiles[:3]:
            profile["match_id"] = match_id
            profile["match"] = {
                "home": match.get("home"),
                "away": match.get("away"),
                "league": match.get("league"),
                "minute": match.get("minute"),
                "score": match.get("score")
            }

            scout_cards.append(profile)

    scout_cards = sorted(
        scout_cards,
        key=lambda x: x.get("scout_score", 0),
        reverse=True
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "source": "matchiq-scout-engine",
        "total_matches": len(matches),
        "total_scout_cards": len(scout_cards),
        "scout_cards": scout_cards[:30]
    }


@router.get("/match/{match_id}")
def scout_match(match_id: int):
    match_data = get_match_live_data(match_id)

    if "error" in match_data:
        return match_data

    match = {
        "match_id": match_id,
        "home": match_data.get("home"),
        "away": match_data.get("away"),
        "league": match_data.get("league"),
        "minute": match_data.get("minute"),
        "score": match_data.get("score"),
    }

    players = match_data.get("players", []) or []

    profiles = [
        build_profile_from_player(player)
        for player in players
    ]

    if not profiles:
        profiles = [
            build_fake_profile(match.get("home", "Home")),
            build_fake_profile(match.get("away", "Away")),
            build_fake_profile(match.get("home", "Home")),
            build_fake_profile(match.get("away", "Away"))
        ]

    profiles = sorted(
        profiles,
        key=lambda x: x.get("scout_score", 0),
        reverse=True
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "source": "matchiq-scout-engine",
        "match": match,
        "total_profiles": len(profiles),
        "profiles": profiles
    }