"""
player_engine.py
MatchIQ Tactical - REAL PLAYER IMPACT ENGINE
"""

from datetime import datetime
import random


# =========================================================
# HELPERS
# =========================================================

def clamp(value, minimum=0, maximum=100):
    try:
        value = float(value)
    except Exception:
        value = 0

    return max(minimum, min(maximum, value))


def safe(player, key, default=0):
    try:
        return player.get(key, default)
    except Exception:
        return default


# =========================================================
# STATUS ENGINE
# =========================================================

def get_player_status(
    rating,
    fatigue,
    danger,
    momentum,
    pressure
):

    if rating >= 8.7:
        return "WORLD CLASS"

    if momentum >= 82:
        return "ON FIRE"

    if danger >= 78:
        return "DANGEROUS"

    if fatigue >= 85:
        return "EXHAUSTED"

    if pressure >= 78:
        return "UNDER PRESSURE"

    if rating <= 5.9:
        return "STRUGGLING"

    return "STABLE"


# =========================================================
# IMPACT SCORE
# =========================================================

def calculate_impact_score(
    danger,
    aggression,
    momentum,
    rating
):

    score = (
        danger * 0.34
        + aggression * 0.12
        + momentum * 0.28
        + rating * 8
    )

    return round(clamp(score), 1)


# =========================================================
# MOMENTUM
# =========================================================

def calculate_momentum(
    shots,
    shots_on_target,
    key_passes,
    dribbles,
    assists
):

    score = (
        shots * 10
        + shots_on_target * 16
        + key_passes * 9
        + dribbles * 7
        + assists * 18
    )

    return round(clamp(score), 1)


# =========================================================
# FALLBACK
# =========================================================

def generate_fake_players(team_name, side):

    roles = [
        "Portiere",
        "Difensore",
        "Terzino",
        "Regista",
        "Mediano",
        "Mezzala",
        "Esterno",
        "Trequartista",
        "Attaccante"
    ]

    players = []

    for role in roles:

        rating = round(random.uniform(6.0, 8.5), 1)

        players.append({
            "name": f"{team_name} {role}",
            "team": team_name,
            "side": side,
            "role": role,

            "rating": rating,

            "danger": random.randint(20, 95),
            "fatigue": random.randint(20, 90),
            "aggression": random.randint(10, 85),

            "momentum": random.randint(10, 95),
            "pressure": random.randint(10, 90),

            "impact_score": random.randint(45, 98),

            "status": "STABLE"
        })

    return players


# =========================================================
# MAIN ENGINE
# =========================================================

def generate_player_ratings(match_data):

    home = match_data.get("home", "Home")
    away = match_data.get("away", "Away")

    api_players = match_data.get("players", []) or []

    real_players = []

    # =====================================================
    # REAL PLAYERS
    # =====================================================

    for p in api_players:

        try:

            name = p.get("name")

            if not name:
                continue

            team = p.get("team") or "Unknown"

            role = (
                p.get("role")
                or p.get("position")
                or "Player"
            )

            side = "home" if team == home else "away"

            shots = safe(p, "shots")
            shots_on_target = safe(p, "shots_on_target")

            key_passes = safe(p, "key_passes")

            dribbles = safe(p, "dribbles_success")

            tackles = safe(p, "tackles")
            interceptions = safe(p, "interceptions")

            assists = safe(p, "assists")

            fouls = safe(p, "fouls")

            minutes = safe(p, "minutes")

            rating_api = safe(p, "rating_api")

            # ------------------------------------------------

            danger = clamp(
                shots * 12
                + shots_on_target * 18
                + key_passes * 10
                + assists * 16
            )

            aggression = clamp(
                tackles * 9
                + interceptions * 8
            )

            fatigue = clamp(minutes * 0.95)

            pressure = clamp(
                fatigue * 0.50
                + fouls * 14
            )

            momentum = calculate_momentum(
                shots,
                shots_on_target,
                key_passes,
                dribbles,
                assists
            )

            # ------------------------------------------------
            # REALISTIC RATING
            # ------------------------------------------------

            if rating_api and rating_api > 0:

                rating = round(float(rating_api), 1)

            else:

                rating = round(
                    6.0
                    + danger * 0.018
                    + momentum * 0.012
                    + aggression * 0.005
                    - fatigue * 0.004,
                    1
                )

            rating = max(5.0, min(9.9, rating))

            # ------------------------------------------------

            impact_score = calculate_impact_score(
                danger,
                aggression,
                momentum,
                rating
            )

            status = get_player_status(
                rating,
                fatigue,
                danger,
                momentum,
                pressure
            )

            real_players.append({

                "name": name,
                "team": team,
                "side": side,
                "role": role,

                "rating": rating,

                "danger": round(danger, 1),
                "fatigue": round(fatigue, 1),
                "aggression": round(aggression, 1),

                "momentum": round(momentum, 1),
                "pressure": round(pressure, 1),

                "impact_score": round(impact_score, 1),

                "status": status
            })

        except Exception:
            continue

    # =====================================================
    # USE REAL PLAYERS
    # =====================================================

    if len(real_players) >= 6:

        players = real_players

    else:

        players = (
            generate_fake_players(home, "home")
            + generate_fake_players(away, "away")
        )

    # =====================================================
    # SORT
    # =====================================================

    players = sorted(
        players,
        key=lambda x: (
            x["impact_score"],
            x["rating"]
        ),
        reverse=True
    )

    # =====================================================
    # MVP
    # =====================================================

    mvp = players[0] if players else None

    most_dangerous = (
        max(players, key=lambda x: x["danger"])
        if players else None
    )

    most_tired = (
        max(players, key=lambda x: x["fatigue"])
        if players else None
    )

    # =====================================================
    # COMMENTARY
    # =====================================================

    commentary = []

    if mvp:
        commentary.append(
            f"{mvp['name']} è il giocatore più influente della partita."
        )

    if most_dangerous:
        commentary.append(
            f"{most_dangerous['name']} sta creando grande pericolo offensivo."
        )

    if most_tired:
        commentary.append(
            f"{most_tired['name']} mostra segni evidenti di stanchezza."
        )

    return {
        "generated_at": datetime.utcnow().isoformat(),

        "players": players,

        "mvp": mvp,

        "most_dangerous": most_dangerous,

        "most_tired": most_tired,

        "commentary": commentary
    }