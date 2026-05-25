import random


def get_team_name(match_data, side):
    if side == "home":
        return match_data.get("home") or match_data.get("home_team") or "Home"

    return match_data.get("away") or match_data.get("away_team") or "Away"


def safe_team_name(ev):
    team = ev.get("team")

    if isinstance(team, dict):
        return team.get("name", "Unknown")

    if isinstance(team, str):
        return team

    return "Unknown"


def safe_minute(ev):
    time_data = ev.get("time")

    if isinstance(time_data, dict):
        return time_data.get("elapsed", 0) or 0

    return ev.get("minute", 0) or 0


def build_live_events(match_data):
    events = match_data.get("events", []) or []
    live_events = []

    for ev in events:
        event_type = ev.get("type", "")
        detail = ev.get("detail", "")
        minute = safe_minute(ev)
        team_name = safe_team_name(ev)

        icon = "⚽"

        if event_type == "Card":
            icon = "🟨"
        elif event_type == "subst":
            icon = "🔄"
        elif event_type == "Goal":
            icon = "⚽"
        elif event_type == "Var":
            icon = "📺"

        live_events.append({
            "minute": minute,
            "team": team_name,
            "type": event_type,
            "detail": detail,
            "icon": icon
        })

    if not live_events:
        home = get_team_name(match_data, "home")
        away = get_team_name(match_data, "away")

        fallback_texts = [
            "High pressing",
            "Dangerous transition",
            "Ball possession control",
            "Counter attack chance",
            "Wide attacking play",
            "Defensive compactness"
        ]

        for _ in range(3):
            live_events.append({
                "minute": random.randint(5, 85),
                "team": random.choice([home, away]),
                "type": "AI Tactical",
                "detail": random.choice(fallback_texts),
                "icon": "🧠"
            })

    return sorted(live_events, key=lambda x: x.get("minute", 0))