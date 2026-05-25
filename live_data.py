import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

TOP_LEAGUES = {
    39: "Premier League",
    140: "La Liga",
    78: "Bundesliga",
    61: "Ligue 1",
    135: "Serie A",
    2: "Champions League",
    3: "Europa League",
    848: "Conference League"
}

LIVE_STATUSES = {
    "1H", "2H", "HT", "ET", "BT", "P", "SUSP", "INT", "LIVE"
}

FINISHED_STATUSES = {
    "FT", "AET", "PEN", "CANC", "PST", "ABD", "AWD", "WO"
}

CACHE = {
    "live_matches_top": {"data": None, "expires_at": None},
    "live_matches_all": {"data": None, "expires_at": None},
    "match_detail": {},
    "match_stats": {},
    "match_players": {},
    "match_events": {},
}

# Memoria live per evitare sparizioni improvvise
LIVE_MATCH_MEMORY = {}

CACHE_SECONDS = 45
LIVE_MEMORY_SECONDS = 180


def cache_get(cache_name, key):
    now = datetime.now()
    cached = CACHE.get(cache_name, {}).get(key)

    if cached and cached["expires_at"] > now:
        return cached["data"]

    return None


def cache_set(cache_name, key, data, seconds=CACHE_SECONDS):
    CACHE[cache_name][key] = {
        "data": data,
        "expires_at": datetime.now() + timedelta(seconds=seconds)
    }


def api_get(endpoint: str, params: dict = None):
    if not API_KEY:
        return {
            "error": "API_FOOTBALL_KEY non configurata nel file .env",
            "response": []
        }

    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=HEADERS,
            params=params,
            timeout=10
        )

        if response.status_code == 429:
            return {
                "error": "Errore API: 429 - limite richieste raggiunto. Attendi qualche minuto.",
                "response": []
            }

        if response.status_code != 200:
            return {
                "error": f"Errore API: {response.status_code}",
                "details": response.text,
                "response": []
            }

        return response.json()

    except Exception as e:
        return {
            "error": str(e),
            "response": []
        }


def safe_int(value):
    if value is None:
        return 0

    if isinstance(value, str):
        value = value.replace("%", "").strip()

    try:
        return int(value)
    except Exception:
        return 0


def safe_float(value):
    if value is None:
        return 0.0

    try:
        return float(value)
    except Exception:
        return 0.0


def extract_stat(stats, stat_name):
    for item in stats:
        if item.get("type") == stat_name:
            return item.get("value")

    return 0


def normalize_team_stats(stats_raw):
    possession = safe_int(extract_stat(stats_raw, "Ball Possession"))
    total_shots = safe_int(extract_stat(stats_raw, "Total Shots"))
    shots_on_goal = safe_int(extract_stat(stats_raw, "Shots on Goal"))
    corners = safe_int(extract_stat(stats_raw, "Corner Kicks"))
    fouls = safe_int(extract_stat(stats_raw, "Fouls"))
    offsides = safe_int(extract_stat(stats_raw, "Offsides"))
    yellow_cards = safe_int(extract_stat(stats_raw, "Yellow Cards"))
    red_cards = safe_int(extract_stat(stats_raw, "Red Cards"))

    dangerous_attacks = (
        shots_on_goal * 5
        + total_shots * 2
        + corners * 3
    )

    estimated_xg = (
        shots_on_goal * 0.18
        + max(total_shots - shots_on_goal, 0) * 0.05
        + corners * 0.04
    )

    return {
        "possession": possession,
        "shots": total_shots,
        "shots_on_target": shots_on_goal,
        "dangerous_attacks": dangerous_attacks,
        "corners": corners,
        "xg": round(estimated_xg, 2),
        "lost_balls": fouls + offsides,
        "duels_won": 50,
        "fouls": fouls,
        "offsides": offsides,
        "yellow_cards": yellow_cards,
        "red_cards": red_cards
    }


def is_finished_status(status_short):
    if not status_short:
        return False

    return str(status_short).upper() in FINISHED_STATUSES


def is_live_status(status_short):
    if not status_short:
        return False

    return str(status_short).upper() in LIVE_STATUSES


def cleanup_live_memory():
    now = datetime.now()

    expired_keys = []

    for match_id, item in LIVE_MATCH_MEMORY.items():
        last_seen = item.get("last_seen")

        if not last_seen:
            expired_keys.append(match_id)
            continue

        age = (now - last_seen).total_seconds()

        status = str(item.get("match", {}).get("status", "")).upper()

        if age > LIVE_MEMORY_SECONDS or is_finished_status(status):
            expired_keys.append(match_id)

    for key in expired_keys:
        LIVE_MATCH_MEMORY.pop(key, None)


def update_live_memory(matches):
    now = datetime.now()

    for match in matches:
        match_id = match.get("match_id") or match.get("fixture_id") or match.get("id")

        if not match_id:
            continue

        status = str(match.get("status", "")).upper()

        if is_finished_status(status):
            LIVE_MATCH_MEMORY.pop(match_id, None)
            continue

        match["memory_mode"] = False
        match["last_seen_live"] = now.isoformat()

        LIVE_MATCH_MEMORY[match_id] = {
            "last_seen": now,
            "match": match
        }


def get_memory_matches(top_only=True):
    cleanup_live_memory()

    memory_matches = []

    now = datetime.now()

    for item in LIVE_MATCH_MEMORY.values():
        match = dict(item.get("match", {}))

        if not match:
            continue

        if top_only and match.get("league_id") not in TOP_LEAGUES:
            continue

        age = int((now - item["last_seen"]).total_seconds())

        match["memory_mode"] = True
        match["memory_age_seconds"] = age
        match["live_label"] = "LIVE MEMORY"

        memory_matches.append(match)

    return memory_matches


def merge_live_and_memory(live_matches, memory_matches):
    merged = {}
    
    for match in memory_matches:
        match_id = match.get("match_id") or match.get("fixture_id") or match.get("id")
        if match_id:
            merged[match_id] = match

    for match in live_matches:
        match_id = match.get("match_id") or match.get("fixture_id") or match.get("id")
        if match_id:
            merged[match_id] = match

    return list(merged.values())


def get_cached_fixture(match_id: int):
    cached = cache_get("match_detail", match_id)
    if cached is not None:
        return cached

    data = api_get("/fixtures", {"id": match_id})
    cache_set("match_detail", match_id, data)
    return data


def get_cached_statistics(match_id: int):
    cached = cache_get("match_stats", match_id)
    if cached is not None:
        return cached

    data = api_get("/fixtures/statistics", {"fixture": match_id})
    cache_set("match_stats", match_id, data)
    return data


def get_cached_players(match_id: int):
    cached = cache_get("match_players", match_id)
    if cached is not None:
        return cached

    data = api_get("/fixtures/players", {"fixture": match_id})

    cache_set("match_players", match_id, data, seconds=120)

    return data


def get_fixture_events(match_id: int):
    cached = cache_get("match_events", match_id)
    if cached is not None:
        return cached

    data = api_get("/fixtures/events", {"fixture": match_id})

    if "error" in data:
        cache_set("match_events", match_id, [], seconds=30)
        return []

    events = []

    for event in data.get("response", []):
        team = event.get("team", {}) or {}
        player = event.get("player", {}) or {}
        assist = event.get("assist", {}) or {}
        time_data = event.get("time", {}) or {}

        events.append({
            "minute": time_data.get("elapsed", 0),
            "extra": time_data.get("extra"),
            "team": team.get("name"),
            "team_logo": team.get("logo"),
            "player": player.get("name"),
            "assist": assist.get("name"),
            "type": event.get("type"),
            "detail": event.get("detail"),
            "comments": event.get("comments")
        })

    cache_set("match_events", match_id, events, seconds=45)

    return events


def get_live_matches(top_only: bool = True):
    now = datetime.now()

    cache_key = "live_matches_top" if top_only else "live_matches_all"
    cached = CACHE[cache_key]

    if cached["data"] and cached["expires_at"] and cached["expires_at"] > now:
        return cached["data"]

    data = api_get("/fixtures", {"live": "all"})

    if "error" in data:
        memory_matches = get_memory_matches(top_only=top_only)

        return {
            "source": "api-football",
            "top_only": top_only,
            "error": data["error"],
            "live_memory_enabled": True,
            "memory_matches": len(memory_matches),
            "total_matches": len(memory_matches),
            "matches": memory_matches
        }

    live_matches = []

    for item in data.get("response", []):
        league = item.get("league", {}) or {}
        league_id = league.get("id")

        if top_only and league_id not in TOP_LEAGUES:
            continue

        fixture = item.get("fixture", {}) or {}
        teams = item.get("teams", {}) or {}
        goals = item.get("goals", {}) or {}
        status = fixture.get("status", {}) or {}

        status_short = status.get("short")

        if is_finished_status(status_short):
            continue

        fixture_id = fixture.get("id")

        if not fixture_id:
            continue

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        match = {
            "match_id": fixture_id,
            "fixture_id": fixture_id,
            "id": fixture_id,

            "league_id": league_id,
            "league": TOP_LEAGUES.get(league_id, league.get("name")),
            "country": league.get("country"),

            "home": teams.get("home", {}).get("name"),
            "away": teams.get("away", {}).get("name"),
            "home_logo": teams.get("home", {}).get("logo"),
            "away_logo": teams.get("away", {}).get("logo"),

            "minute": status.get("elapsed") or 0,
            "status": status_short,
            "status_long": status.get("long"),

            "home_goals": home_goals or 0,
            "away_goals": away_goals or 0,
            "score": f"{home_goals or 0}-{away_goals or 0}",

            "memory_mode": False,
            "live_label": "LIVE"
        }

        live_matches.append(match)

    update_live_memory(live_matches)

    memory_matches = get_memory_matches(top_only=top_only)

    final_matches = merge_live_and_memory(
        live_matches=live_matches,
        memory_matches=memory_matches
    )

    result = {
        "source": "api-football",
        "top_only": top_only,
        "filtered_leagues": list(TOP_LEAGUES.values()) if top_only else "all",
        "live_memory_enabled": True,
        "memory_seconds": LIVE_MEMORY_SECONDS,
        "live_api_matches": len(live_matches),
        "memory_matches": len([m for m in final_matches if m.get("memory_mode")]),
        "total_matches": len(final_matches),
        "matches": final_matches
    }

    CACHE[cache_key] = {
        "data": result,
        "expires_at": now + timedelta(seconds=45)
    }

    return result


def normalize_player_from_api(player_block, team_name, team_logo):
    player_info = player_block.get("player", {}) or {}
    statistics = player_block.get("statistics", []) or []

    if not statistics:
        return None

    s = statistics[0] or {}

    games = s.get("games", {}) or {}
    shots = s.get("shots", {}) or {}
    passes = s.get("passes", {}) or {}
    duels = s.get("duels", {}) or {}
    dribbles = s.get("dribbles", {}) or {}
    tackles = s.get("tackles", {}) or {}
    cards = s.get("cards", {}) or {}
    fouls = s.get("fouls", {}) or {}
    goals = s.get("goals", {}) or {}

    player_name = player_info.get("name")

    if not player_name:
        return None

    shots_total = safe_int(shots.get("total"))
    shots_on = safe_int(shots.get("on"))
    key_passes = safe_int(passes.get("key"))
    assists = safe_int(goals.get("assists"))

    dribbles_attempts = safe_int(dribbles.get("attempts"))
    dribbles_success = safe_int(dribbles.get("success"))

    tackles_total = safe_int(tackles.get("total"))
    interceptions = safe_int(tackles.get("interceptions"))

    fouls_committed = safe_int(fouls.get("committed"))
    fouls_drawn = safe_int(fouls.get("drawn"))

    yellow_cards = safe_int(cards.get("yellow"))
    red_cards = safe_int(cards.get("red"))

    minutes = safe_int(games.get("minutes"))
    rating_api = safe_float(games.get("rating"))

    xg = round(
        shots_on * 0.18
        + max(shots_total - shots_on, 0) * 0.04,
        2
    )

    return {
        "id": player_info.get("id"),
        "name": player_name,
        "photo": player_info.get("photo"),

        "team": team_name,
        "team_logo": team_logo,

        "role": games.get("position"),
        "position": games.get("position"),
        "captain": bool(games.get("captain")),

        "minutes": minutes,
        "rating_api": rating_api,

        "shots": shots_total,
        "shots_on_target": shots_on,

        "key_passes": key_passes,
        "assists": assists,

        "total_passes": safe_int(passes.get("total")),
        "pass_accuracy": safe_int(passes.get("accuracy")),

        "duels_total": safe_int(duels.get("total")),
        "duels_won": safe_int(duels.get("won")),

        "dribbles_attempts": dribbles_attempts,
        "dribbles_success": dribbles_success,
        "dribbles": dribbles_success,

        "lost_balls": safe_int(dribbles.get("past")),

        "tackles": tackles_total,
        "interceptions": interceptions,

        "fouls": fouls_committed,
        "fouls_committed": fouls_committed,
        "fouls_drawn": fouls_drawn,

        "cards_yellow": yellow_cards,
        "cards_red": red_cards,

        "xg": xg
    }


def extract_players(players_data):
    players = []

    if "error" in players_data:
        return players

    for team_block in players_data.get("response", []):
        team = team_block.get("team", {}) or {}
        team_name = team.get("name")
        team_logo = team.get("logo")

        for player_block in team_block.get("players", []):
            player = normalize_player_from_api(
                player_block=player_block,
                team_name=team_name,
                team_logo=team_logo
            )

            if player:
                players.append(player)

    return players


def get_match_live_data(match_id: int):
    fixture_data = get_cached_fixture(match_id)
    stats_data = get_cached_statistics(match_id)
    players_data = get_cached_players(match_id)
    events = get_fixture_events(match_id)

    if "error" in fixture_data:
        return {
            "error": fixture_data["error"],
            "match_id": match_id
        }

    if not fixture_data.get("response"):
        return {
            "error": "Partita non trovata",
            "match_id": match_id
        }

    fixture_item = fixture_data["response"][0]

    fixture = fixture_item.get("fixture", {}) or {}
    league = fixture_item.get("league", {}) or {}
    teams = fixture_item.get("teams", {}) or {}
    goals = fixture_item.get("goals", {}) or {}
    status = fixture.get("status", {}) or {}

    home_team = teams.get("home", {}).get("name")
    away_team = teams.get("away", {}).get("name")

    home_logo = teams.get("home", {}).get("logo")
    away_logo = teams.get("away", {}).get("logo")

    stats_response = stats_data.get("response", [])

    if len(stats_response) >= 2:
        home_stats_raw = stats_response[0].get("statistics", [])
        away_stats_raw = stats_response[1].get("statistics", [])
    else:
        home_stats_raw = []
        away_stats_raw = []

    home_stats = normalize_team_stats(home_stats_raw)
    away_stats = normalize_team_stats(away_stats_raw)

    players = extract_players(players_data)

    return {
        "source": "api-football",
        "match_id": match_id,

        "league": league.get("name"),
        "league_id": league.get("id"),
        "country": league.get("country"),

        "home": home_team,
        "away": away_team,
        "home_logo": home_logo,
        "away_logo": away_logo,

        "minute": status.get("elapsed") or 0,
        "status": status.get("short"),
        "status_long": status.get("long"),

        "score": {
            "home": goals.get("home") or 0,
            "away": goals.get("away") or 0
        },

        "events": events,

        "team_stats": {
            "home": home_stats,
            "away": away_stats
        },

        "players": players,
        "players_count": len(players),
        "players_source": "api-football" if players else "empty"
    }