from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

import os


def generate_match_pdf(match_data):
    """
    Genera report PDF tattico MatchIQ Tactical
    """

    match = match_data.get("match", {})
    tactical = match_data.get("tactical_analysis", {})
    pressure = match_data.get("pressure_engine", {})
    ai_core = match_data.get("ai_core", {})
    xg = match_data.get("xg_analysis", {})
    future = match_data.get("future_prediction", {})
    players = match_data.get("players_analysis", {}).get("players", [])

    home = match.get("home", "Home")
    away = match.get("away", "Away")

    score_home = match.get("score", {}).get("home", 0)
    score_away = match.get("score", {}).get("away", 0)

    filename = f"report_{home}_{away}.pdf"
    filename = filename.replace(" ", "_")

    os.makedirs("reports", exist_ok=True)

    pdf_path = os.path.join("reports", filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()

    elements = []

    title = Paragraph(
        f"<font size=24><b>MatchIQ Tactical Report</b></font>",
        styles["Title"]
    )

    elements.append(title)
    elements.append(Spacer(1, 20))

    match_title = Paragraph(
        f"<font size=18><b>{home} {score_home} - {score_away} {away}</b></font>",
        styles["Heading1"]
    )

    elements.append(match_title)
    elements.append(Spacer(1, 20))

    # xG TABLE
    xg_table = Table([
        ["Metric", home, away],
        ["xG", xg.get("home_xg", 0), xg.get("away_xg", 0)],
        ["Big Chances", xg.get("home_big_chances", 0), xg.get("away_big_chances", 0)],
        ["Shot Quality", xg.get("home_shot_quality", 0), xg.get("away_shot_quality", 0)],
        ["xThreat", xg.get("home_xthreat", 0), xg.get("away_xthreat", 0)],
    ])

    xg_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#e8f0ff")),

        ("GRID", (0, 0), (-1, -1), 1, colors.black),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
    ]))

    elements.append(Paragraph("<b>xG Analysis</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    elements.append(xg_table)
    elements.append(Spacer(1, 20))

    # TACTICAL ANALYSIS
    tactical_text = f"""
    <b>Dominant Team:</b> {pressure.get("dominant_team", "N/A")}<br/>
    <b>Match Tempo:</b> {tactical.get("match_tempo", "N/A")}<br/>
    <b>Home Pressure:</b> {tactical.get("home_pressure", 0)}<br/>
    <b>Away Pressure:</b> {tactical.get("away_pressure", 0)}<br/>
    <b>Home Danger:</b> {tactical.get("home_danger", 0)}<br/>
    <b>Away Danger:</b> {tactical.get("away_danger", 0)}<br/>
    """

    elements.append(Paragraph("<b>Tactical Analysis</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(tactical_text, styles["BodyText"]))
    elements.append(Spacer(1, 20))

    # FUTURE PREDICTION
    fp = future.get("prediction_engine", {})

    future_text = f"""
    <b>Prediction:</b> {fp.get("prediction", "N/A")}<br/>
    <b>Confidence:</b> {fp.get("confidence", 0)}%<br/>
    <b>Counter Attack Risk:</b> {fp.get("counter_attack_risk", "N/A")}<br/>
    <b>Collapse Risk:</b> {fp.get("collapse_risk", "N/A")}<br/>
    """

    elements.append(Paragraph("<b>Future Prediction AI</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(future_text, styles["BodyText"]))
    elements.append(Spacer(1, 20))

    # PLAYER RATINGS
    player_table_data = [["Player", "Rating", "Danger", "Fatigue"]]

    for p in players[:10]:
        player_table_data.append([
            p.get("name", "Player"),
            p.get("rating", 0),
            p.get("danger", 0),
            p.get("fatigue", 0),
        ])

    player_table = Table(player_table_data)

    player_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("GRID", (0, 0), (-1, -1), 1, colors.black),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    elements.append(Paragraph("<b>Player Ratings</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    elements.append(player_table)
    elements.append(Spacer(1, 20))

    # AI COMMENTARY
    commentary = ai_core.get("commentary", [])

    commentary_text = "<br/>".join([
        f"• {c}" for c in commentary
    ])

    elements.append(Paragraph("<b>AI Commentary</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(commentary_text, styles["BodyText"]))
    elements.append(Spacer(1, 20))

    # FINAL REPORT
    report = ai_core.get("report", "No AI Report")

    elements.append(Paragraph("<b>Final AI Match Report</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(report, styles["BodyText"]))

    doc.build(elements)

    return {
        "success": True,
        "pdf_path": pdf_path
    }