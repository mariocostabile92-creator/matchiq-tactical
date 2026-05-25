def generate_ai_report(match_data: dict, tactical: dict, players: dict):
    home = match_data["home"]
    away = match_data["away"]
    minute = match_data["minute"]

    best_player = players.get("best_player")
    worst_player = players.get("worst_player")

    insights = tactical.get("tactical_insights", [])

    report_lines = []

    report_lines.append(f"Analisi live al minuto {minute} di {home} vs {away}.")
    report_lines.append(f"La squadra attualmente dominante è: {tactical['dominant_team']}.")

    if insights:
        report_lines.append("Punti tattici principali:")
        for insight in insights:
            report_lines.append(f"- {insight}")

    if best_player:
        report_lines.append(
            f"Migliore in campo provvisorio: {best_player['name']} "
            f"con rating {best_player['rating']}."
        )

    if worst_player:
        report_lines.append(
            f"Giocatore più in difficoltà: {worst_player['name']} "
            f"con rating {worst_player['rating']}."
        )

    report_lines.append(
        "Suggerimento AI: monitorare le zone laterali e la qualità delle transizioni, "
        "soprattutto nelle fasi successive alla perdita del possesso."
    )

    return {
        "match": f"{home} vs {away}",
        "minute": minute,
        "ai_report": "\n".join(report_lines)
    }