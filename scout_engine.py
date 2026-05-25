"""
scout_engine.py
MatchIQ Scout Engine V5.6 PRO

Backend-only upgrade:
- schema stabile V5.5 mantenuto
- metriche mai a 0 se il player è valido
- threat / creativity / pressure / stamina / impact_score realistici
- data_source chiaro: real_api / ai_estimation / hybrid
- timeline eventi più credibile
"""

from datetime import datetime


# =========================================================
# HELPERS
# =========================================================

def clamp(value, min_value=0, max_value=100):
    try:
        value = float(value)
    except Exception:
        value = min_value
    return max(min_value, min(max_value, value))


def safe_number(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    return int(round(safe_number(value, default)))


def safe_text(value, default="Unknown"):
    if value is None or value == "":
        return default
    return str(value)


def utc_now():
    return datetime.utcnow().isoformat()


def get_nested(data, *keys, default=None):
    cur = data
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def role_base(role, att=0, mid=0, defn=0, gk=0, default=0):
    return {
        "ATT": att,
        "MID": mid,
        "DEF": defn,
        "GK": gk,
    }.get(role, default)


def normalize_role(value):
    role = safe_text(value, "MID").upper().strip()

    if role in ["ATT", "FW", "F", "ST", "CF", "LW", "RW", "LF", "RF"] or "FORWARD" in role or "STRIKER" in role:
        return "ATT"

    if role in ["MID", "M", "CM", "CAM", "CDM", "LM", "RM"] or "MID" in role:
        return "MID"

    if role in ["DEF", "D", "CB", "LB", "RB", "LWB", "RWB"] or "DEF" in role or "BACK" in role:
        return "DEF"

    if role in ["GK", "G"] or "KEEP" in role:
        return "GK"

    return "MID"


def get_match_minute(match_data=None):
    if not isinstance(match_data, dict):
        return 60

    minute = (
        match_data.get("minute")
        or match_data.get("elapsed")
        or get_nested(match_data, "fixture", "status", "elapsed")
        or get_nested(match_data, "status", "elapsed")
        or 60
    )

    return clamp(safe_number(minute, 60), 1, 130)


def get_statistics(player):
    stats = player.get("statistics")

    if isinstance(stats, list) and stats:
        return stats[0] or {}

    if isinstance(stats, dict):
        return stats

    return {}


def extract_player_identity(player, index=0):
    player_obj = player.get("player") if isinstance(player.get("player"), dict) else {}

    name = (
        player.get("name")
        or player.get("player_name")
        or player_obj.get("name")
        or f"Player {index + 1}"
    )

    player_id = (
        player.get("id")
        or player.get("player_id")
        or player_obj.get("id")
        or f"{name}_{index}"
    )

    photo = player.get("photo") or player_obj.get("photo") or ""

    return str(player_id), safe_text(name), safe_text(photo, "")


def extract_team_name(player):
    team = player.get("team")

    if isinstance(team, str):
        return team

    if isinstance(team, dict):
        return team.get("name") or "Unknown"

    return player.get("team_name") or player.get("club") or "Unknown"


# =========================================================
# RAW STATS
# =========================================================

def extract_raw_stats(player):
    stats = get_statistics(player)

    games = stats.get("games", {}) if isinstance(stats.get("games"), dict) else {}
    goals = stats.get("goals", {}) if isinstance(stats.get("goals"), dict) else {}
    shots = stats.get("shots", {}) if isinstance(stats.get("shots"), dict) else {}
    passes = stats.get("passes", {}) if isinstance(stats.get("passes"), dict) else {}
    dribbles = stats.get("dribbles", {}) if isinstance(stats.get("dribbles"), dict) else {}
    tackles = stats.get("tackles", {}) if isinstance(stats.get("tackles"), dict) else {}
    duels = stats.get("duels", {}) if isinstance(stats.get("duels"), dict) else {}
    fouls = stats.get("fouls", {}) if isinstance(stats.get("fouls"), dict) else {}

    role = normalize_role(
        player.get("role")
        or player.get("position")
        or player.get("pos")
        or games.get("position")
        or "MID"
    )

    rating = safe_number(
        player.get("rating")
        or player.get("rating_api")
        or player.get("statistics_rating")
        or games.get("rating")
        or 6.5,
        6.5
    )

    if rating > 10:
        rating = rating / 10

    raw = {
        "role": role,
        "rating": clamp(rating, 4.5, 10),

        "goals": safe_number(player.get("goals") or goals.get("total"), 0),
        "assists": safe_number(player.get("assists") or goals.get("assists"), 0),

        "shots": safe_number(player.get("shots") or player.get("shots_total") or shots.get("total"), 0),
        "shots_on_target": safe_number(player.get("shots_on_target") or player.get("shots_on") or shots.get("on"), 0),

        "key_passes": safe_number(player.get("key_passes") or player.get("keyPasses") or passes.get("key"), 0),

        "dribbles": safe_number(player.get("dribbles") or player.get("dribbles_success") or dribbles.get("success"), 0),

        "tackles": safe_number(player.get("tackles") or tackles.get("total"), 0),
        "interceptions": safe_number(player.get("interceptions") or tackles.get("interceptions"), 0),
        "fouls": safe_number(player.get("fouls") or fouls.get("committed"), 0),
        "duels_won": safe_number(player.get("duels_won") or duels.get("won"), 0),

        "minutes": safe_number(player.get("minutes") or games.get("minutes"), 0),

        # optional advanced API fields
        "xg": safe_number(player.get("xg") or player.get("expected_goals"), 0),
        "xa": safe_number(player.get("xa") or player.get("expected_assists"), 0),
        "touches_box": safe_number(player.get("touches_box") or player.get("touches_in_box"), 0),
        "recoveries": safe_number(player.get("recoveries"), 0),
        "progressive_runs": safe_number(player.get("progressive_runs"), 0),
        "progressive_passes": safe_number(player.get("progressive_passes"), 0),
        "pass_accuracy": safe_number(player.get("pass_accuracy") or passes.get("accuracy"), 0),
    }

    return raw


# =========================================================
# DATA QUALITY + ESTIMATION
# =========================================================

def count_real_fields(raw):
    fields = [
        "goals", "assists", "shots", "shots_on_target", "key_passes",
        "dribbles", "tackles", "interceptions", "duels_won",
        "xg", "xa", "touches_box", "recoveries",
        "progressive_runs", "progressive_passes"
    ]
    return sum(1 for f in fields if safe_number(raw.get(f), 0) > 0)


def calculate_data_quality(raw):
    real_fields = count_real_fields(raw)

    if real_fields >= 6:
        return "high", "real_api", False

    if real_fields >= 3:
        return "medium", "hybrid", True

    return "low", "ai_estimation", True


def enrich_low_data(raw, match_minute):
    """
    Se API non dà stats live dettagliate, genera stima coerente da ruolo/rating/minuto.
    Non è fake player: è AI estimation dichiarata.
    """
    role = raw["role"]
    rating = raw["rating"]

    rating_factor = max(0, rating - 6.0)

    if raw["minutes"] <= 0:
        raw["minutes"] = match_minute

    if raw["shots"] <= 0:
        raw["shots"] = role_base(role, att=2, mid=1, defn=0, gk=0, default=1) + (1 if rating >= 7.3 and role in ["ATT", "MID"] else 0)

    if raw["shots_on_target"] <= 0:
        raw["shots_on_target"] = 1 if role == "ATT" and rating >= 7.0 else 0

    if raw["key_passes"] <= 0:
        raw["key_passes"] = role_base(role, att=1, mid=2, defn=1, gk=0, default=1) + (1 if rating >= 7.5 and role == "MID" else 0)

    if raw["dribbles"] <= 0:
        raw["dribbles"] = role_base(role, att=2, mid=1, defn=0, gk=0, default=1)

    if raw["tackles"] <= 0:
        raw["tackles"] = role_base(role, att=0, mid=1, defn=2, gk=0, default=1)

    if raw["interceptions"] <= 0:
        raw["interceptions"] = role_base(role, att=0, mid=1, defn=2, gk=0, default=1)

    if raw["duels_won"] <= 0:
        raw["duels_won"] = role_base(role, att=2, mid=2, defn=3, gk=0, default=2)

    if raw["progressive_runs"] <= 0:
        raw["progressive_runs"] = role_base(role, att=2, mid=1, defn=0, gk=0, default=1)

    if raw["progressive_passes"] <= 0:
        raw["progressive_passes"] = role_base(role, att=1, mid=3, defn=2, gk=0, default=1)

    if raw["xg"] <= 0:
        raw["xg"] = round(role_base(role, att=0.18, mid=0.08, defn=0.03, gk=0, default=0.06) + rating_factor * 0.04, 2)

    if raw["xa"] <= 0:
        raw["xa"] = round(role_base(role, att=0.10, mid=0.16, defn=0.04, gk=0, default=0.06) + rating_factor * 0.03, 2)

    if raw["pass_accuracy"] <= 0:
        raw["pass_accuracy"] = role_base(role, att=76, mid=84, defn=82, gk=68, default=78)

    return raw


# =========================================================
# METRIC ENGINES V5.6
# =========================================================

def calculate_threat(raw):
    role = raw["role"]

    score = (
        role_base(role, att=32, mid=24, defn=10, gk=2, default=18)
        + raw["shots"] * 7
        + raw["shots_on_target"] * 13
        + raw["goals"] * 24
        + raw["xg"] * 38
        + raw["touches_box"] * 5
        + raw["progressive_runs"] * 4
        + raw["key_passes"] * 3
        + raw["dribbles"] * 3
    )

    return round(clamp(score, 1, 99))


def calculate_creativity(raw):
    role = raw["role"]

    score = (
        role_base(role, att=22, mid=36, defn=16, gk=4, default=20)
        + raw["key_passes"] * 11
        + raw["assists"] * 26
        + raw["xa"] * 42
        + raw["progressive_passes"] * 5
        + raw["dribbles"] * 5
        + raw["pass_accuracy"] * 0.08
    )

    return round(clamp(score, 1, 99))


def calculate_pressure(raw):
    role = raw["role"]

    score = (
        role_base(role, att=20, mid=34, defn=42, gk=6, default=28)
        + raw["tackles"] * 9
        + raw["interceptions"] * 9
        + raw["duels_won"] * 5
        + raw["recoveries"] * 5
        + raw["fouls"] * 2
    )

    return round(clamp(score, 1, 99))


def calculate_momentum(raw, threat, creativity, pressure):
    score = (
        raw["rating"] * 7.0
        + threat * 0.24
        + creativity * 0.18
        + pressure * 0.12
        + raw["goals"] * 13
        + raw["assists"] * 9
        + raw["shots_on_target"] * 3
    )

    return round(clamp(score, 1, 99))


def calculate_fatigue(raw, match_minute, pressure):
    role = raw["role"]

    workload = (
        raw["minutes"] if raw["minutes"] > 0 else match_minute
    )

    score = (
        workload * 0.44
        + role_base(role, att=9, mid=13, defn=11, gk=3, default=9)
        + raw["tackles"] * 1.8
        + raw["duels_won"] * 1.3
        + raw["dribbles"] * 1.4
        + pressure * 0.10
    )

    return round(clamp(score, 8, 94))


def calculate_scout_score(raw, threat, creativity, pressure, momentum, stamina):
    score = (
        raw["rating"] * 8.2
        + threat * 0.20
        + creativity * 0.18
        + pressure * 0.11
        + momentum * 0.26
        + stamina * 0.08
        + raw["goals"] * 8
        + raw["assists"] * 5
    )

    return round(clamp(score, 1, 99))


def calculate_impact_score(scout_score, threat, creativity, pressure, momentum, stamina, raw):
    score = (
        scout_score * 0.28
        + threat * 0.22
        + creativity * 0.16
        + pressure * 0.11
        + momentum * 0.16
        + stamina * 0.07
        + raw["goals"] * 8
        + raw["assists"] * 6
    )

    return round(clamp(score, 1, 99))


# =========================================================
# SIGNALS
# =========================================================

def build_signal(raw, scout_score, threat, creativity, pressure, stamina, impact_score):
    if raw["goals"] >= 1 or scout_score >= 86 or impact_score >= 86:
        return "hot", "Hot Player"

    if threat >= 78:
        return "danger", "High Threat Zone"

    if creativity >= 76:
        return "gem", "Creative Hidden Gem"

    if pressure >= 78:
        return "pressure", "Pressure Trigger"

    if stamina <= 34:
        return "pressure", "Fatigue Alert"

    if scout_score >= 72 and raw["goals"] == 0 and raw["assists"] <= 1:
        return "gem", "Hidden Gem Watch"

    return "watch", "AI Watch"


def build_level(score):
    if score >= 88:
        return "WORLD CLASS"
    if score >= 78:
        return "ELITE"
    if score >= 68:
        return "GOOD TALENT"
    if score >= 55:
        return "DEVELOPING"
    return "LOW IMPACT"


def build_ai_summary(player):
    name = player["name"]

    if player["impact_score"] >= 85:
        return f"{name} sta generando un impatto elite: profilo prioritario da monitorare."

    if player["threat"] >= 78:
        return f"{name} è molto pericoloso negli ultimi metri: possibile azione decisiva."

    if player["creativity"] >= 76:
        return f"{name} sta creando valore tra le linee: profilo interessante per assist e chance creation."

    if player["pressure"] >= 78:
        return f"{name} è un trigger di pressione: utile per leggere intensità e recupero palla."

    if player["stamina"] <= 35:
        return f"{name} mostra segnali di fatica: possibile calo nei prossimi minuti."

    return f"{name} è in monitoraggio live: profilo stabile con margine di crescita."


# =========================================================
# MAIN PLAYER SCOUT
# =========================================================

def generate_player_scout(player, match_data=None, index=0):
    if not isinstance(player, dict):
        player = {}

    player_id, name, photo = extract_player_identity(player, index)
    team = extract_team_name(player)

    raw = extract_raw_stats(player)
    match_minute = get_match_minute(match_data)

    data_quality, data_source, is_estimated = calculate_data_quality(raw)

    if data_quality in ["low", "medium"]:
        raw = enrich_low_data(raw, match_minute)

    threat = calculate_threat(raw)
    creativity = calculate_creativity(raw)
    pressure = calculate_pressure(raw)
    momentum = calculate_momentum(raw, threat, creativity, pressure)
    fatigue = calculate_fatigue(raw, match_minute, pressure)
    stamina = round(clamp(100 - fatigue, 1, 100))

    scout_score = calculate_scout_score(raw, threat, creativity, pressure, momentum, stamina)
    impact_score = calculate_impact_score(scout_score, threat, creativity, pressure, momentum, stamina, raw)

    signal_type, signal = build_signal(
        raw=raw,
        scout_score=scout_score,
        threat=threat,
        creativity=creativity,
        pressure=pressure,
        stamina=stamina,
        impact_score=impact_score
    )

    danger_creator = threat >= 74 or raw["shots"] >= 3 or raw["key_passes"] >= 3 or raw["goals"] >= 1
    hidden_gem = scout_score >= 70 and raw["goals"] == 0 and raw["assists"] <= 1 and stamina >= 40

    result = {
        "id": str(player_id),
        "name": name,
        "photo": photo,
        "team": team,
        "role": raw["role"],
        "position": raw["role"],

        "rating": round(raw["rating"], 1),

        "goals": safe_int(raw["goals"]),
        "assists": safe_int(raw["assists"]),
        "shots": safe_int(raw["shots"]),
        "shots_on_target": safe_int(raw["shots_on_target"]),
        "key_passes": safe_int(raw["key_passes"]),
        "dribbles": safe_int(raw["dribbles"]),
        "tackles": safe_int(raw["tackles"]),
        "interceptions": safe_int(raw["interceptions"]),
        "fouls": safe_int(raw["fouls"]),
        "duels_won": safe_int(raw["duels_won"]),
        "minutes": safe_int(raw["minutes"] or match_minute),

        "xg": round(raw["xg"], 2),
        "xa": round(raw["xa"], 2),
        "touches_box": safe_int(raw["touches_box"]),
        "recoveries": safe_int(raw["recoveries"]),
        "progressive_runs": safe_int(raw["progressive_runs"]),
        "progressive_passes": safe_int(raw["progressive_passes"]),
        "pass_accuracy": safe_int(raw["pass_accuracy"]),

        "threat": threat,
        "creativity": creativity,
        "pressure": pressure,
        "momentum": momentum,
        "fatigue": fatigue,
        "stamina": stamina,
        "scout_score": scout_score,
        "impact_score": impact_score,

        "signal_type": signal_type,
        "signal": signal,
        "level": build_level(scout_score),

        "danger_creator": danger_creator,
        "hidden_gem": hidden_gem,

        "data_quality": data_quality,
        "data_source": data_source,
        "is_estimated": is_estimated,
        "real_data": not is_estimated,

        # compatibility aliases
        "scoutScore": scout_score,
        "impact": impact_score,
        "xThreat": threat,
        "danger": threat,
        "creative_score": creativity,
        "pressure_score": pressure,
        "momentum_score": momentum,
        "fatigue_score": fatigue,
        "signalType": signal_type,
        "ai_signal": signal,
        "keyPasses": safe_int(raw["key_passes"]),

        "ai_summary": "",
        "generated_at": utc_now()
    }

    result["ai_summary"] = build_ai_summary(result)

    return result


# =========================================================
# SUMMARY + EVENTS
# =========================================================

def avg(players, field):
    if not players:
        return 0
    return round(sum(safe_number(p.get(field), 0) for p in players) / len(players), 1)


def build_match_scout_summary(players):
    return {
        "total_players": len(players),
        "avg_scout_score": avg(players, "scout_score"),
        "avg_threat": avg(players, "threat"),
        "avg_creativity": avg(players, "creativity"),
        "avg_pressure": avg(players, "pressure"),
        "avg_momentum": avg(players, "momentum"),
        "avg_stamina": avg(players, "stamina"),
        "hot_players": len([p for p in players if p.get("signal_type") == "hot"]),
        "danger_creators": len([p for p in players if p.get("danger_creator")]),
        "hidden_gems": len([p for p in players if p.get("hidden_gem")]),
        "estimated_players": len([p for p in players if p.get("is_estimated")]),
        "real_players": len([p for p in players if not p.get("is_estimated")]),
    }


def build_live_events_from_players(players, match_data=None):
    minute = int(get_match_minute(match_data))
    events = []

    for p in players[:10]:
        if p.get("signal_type") == "hot":
            events.append({
                "id": f"hot_{p['id']}",
                "minute": minute,
                "type": "momentum",
                "label": "HOT",
                "className": "momentum",
                "playerId": p["id"],
                "playerName": p["name"],
                "title": f"{p['name']} è in forte crescita",
                "desc": p.get("ai_summary", "Hot player rilevato dal motore Scout.")
            })

        elif p.get("threat", 0) >= 78:
            events.append({
                "id": f"threat_{p['id']}",
                "minute": minute,
                "type": "alert",
                "label": "THREAT",
                "className": "alert",
                "playerId": p["id"],
                "playerName": p["name"],
                "title": f"{p['name']} in zona pericolosa",
                "desc": "Threat offensivo sopra soglia."
            })

        elif p.get("creativity", 0) >= 76:
            events.append({
                "id": f"creative_{p['id']}",
                "minute": minute,
                "type": "chance",
                "label": "CREATIVE",
                "className": "alert",
                "playerId": p["id"],
                "playerName": p["name"],
                "title": f"{p['name']} crea valore tra le linee",
                "desc": "Creativity score sopra soglia."
            })

        elif p.get("pressure", 0) >= 78:
            events.append({
                "id": f"pressure_{p['id']}",
                "minute": minute,
                "type": "pressure",
                "label": "PRESS",
                "className": "momentum",
                "playerId": p["id"],
                "playerName": p["name"],
                "title": f"{p['name']} attiva pressione alta",
                "desc": "Pressure engine sopra soglia."
            })

    return events[:12]


# =========================================================
# PUBLIC BUILDER
# =========================================================

def build_live_scout(players, match_data=None):
    if players is None:
        players = []

    scout_players = []

    for index, player in enumerate(players):
        try:
            scout_players.append(
                generate_player_scout(
                    player=player,
                    match_data=match_data,
                    index=index
                )
            )
        except Exception as error:
            scout_players.append({
                "id": f"error_player_{index}",
                "name": f"Player {index + 1}",
                "team": "Unknown",
                "role": "MID",
                "rating": 6.0,
                "goals": 0,
                "assists": 0,
                "shots": 1,
                "shots_on_target": 0,
                "key_passes": 1,
                "dribbles": 1,
                "tackles": 1,
                "threat": 30,
                "creativity": 35,
                "pressure": 35,
                "momentum": 45,
                "fatigue": 45,
                "stamina": 55,
                "scout_score": 50,
                "impact_score": 45,
                "signal_type": "watch",
                "signal": "AI Watch",
                "level": "DEVELOPING",
                "data_quality": "error",
                "data_source": "fallback",
                "is_estimated": True,
                "real_data": False,
                "ai_summary": "Fallback generato per errore nel calcolo player.",
                "error": str(error),
                "generated_at": utc_now()
            })

    scout_players.sort(
        key=lambda item: item.get("scout_score", 0),
        reverse=True
    )

    top_performer = scout_players[0] if scout_players else None

    hidden_gems = [p for p in scout_players if p.get("hidden_gem")]
    danger_creators = [p for p in scout_players if p.get("danger_creator")]
    pressure_triggers = [p for p in scout_players if p.get("signal_type") == "pressure"]
    hot_players = [p for p in scout_players if p.get("signal_type") == "hot"]

    events = build_live_events_from_players(scout_players, match_data)

    return {
        "available": True,
        "source": "matchiq_scout_engine_v5_6_pro",
        "version": "5.6",
        "generated_at": utc_now(),

        "match": match_data or {},

        "players": scout_players,
        "events": events,

        "top_performer": top_performer,
        "hidden_gems": hidden_gems[:5],
        "danger_creators": danger_creators[:5],
        "pressure_triggers": pressure_triggers[:5],
        "hot_players": hot_players[:5],

        "summary": build_match_scout_summary(scout_players),

        "schema": {
            "player_required_fields": [
                "id",
                "name",
                "team",
                "role",
                "rating",
                "threat",
                "creativity",
                "pressure",
                "momentum",
                "fatigue",
                "stamina",
                "scout_score",
                "impact_score",
                "signal_type",
                "signal",
                "data_quality",
                "data_source",
                "is_estimated"
            ]
        },

        "total_players": len(scout_players)
    }