from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_json(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return path


def _number(value: object, digits: int = 3) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}f}"
    return html.escape(str(value))


def write_html_report(manifest: dict[str, Any], path: Path) -> Path:
    aggregate = manifest["aggregate"]
    file_rows: list[str] = []
    for item in manifest["files"]:
        file_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item['source_name']))}</td>"
            f"<td>{item.get('player_count', 0)}</td>"
            f"<td>{item.get('team_a', 0)}</td>"
            f"<td>{item.get('team_b', 0)}</td>"
            f"<td>{item.get('unknown', 0)}</td>"
            f"<td>{_number(item.get('average_team_confidence', 0.0))}</td>"
            f"<td><a href=\"{html.escape(str(item.get('debug_image', '')))}\">debug</a></td>"
            "</tr>"
        )

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MatchIQ VE-003 Team Assignment</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f3f6fa; color: #102033; }}
    main {{ max-width: 1120px; margin: 32px auto; padding: 0 20px 40px; }}
    header {{ background: #071426; color: #fff; padding: 24px; border-radius: 8px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 18px 0; }}
    .metric {{ background: #fff; border: 1px solid #d8e0ea; border-radius: 6px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 5px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ padding: 10px; border: 1px solid #d8e0ea; text-align: left; }}
    th {{ background: #eaf1f8; }}
    .note {{ background: #fff8df; border: 1px solid #e2c86c; padding: 12px; margin-top: 18px; }}
  </style>
</head>
<body>
<main>
  <header>
    <small>MatchIQ Vision Engine</small>
    <h1>VE-003 Team Assignment</h1>
    <p>Deterministic jersey-color clustering over existing VE-002 detections.</p>
  </header>
  <section class="metrics">
    <div class="metric">Players<strong>{aggregate['players_total']}</strong></div>
    <div class="metric">TEAM_A<strong>{aggregate['team_a']}</strong></div>
    <div class="metric">TEAM_B<strong>{aggregate['team_b']}</strong></div>
    <div class="metric">UNKNOWN<strong>{aggregate['unknown']}</strong></div>
    <div class="metric">ROI excluded<strong>{aggregate['roi_excluded']}</strong></div>
    <div class="metric">Mean confidence<strong>{_number(aggregate['average_team_confidence'])}</strong></div>
    <div class="metric">Mean time/player<strong>{_number(aggregate['average_ms_per_player'])} ms</strong></div>
  </section>
  <table>
    <thead>
      <tr><th>Frame</th><th>Players</th><th>A</th><th>B</th><th>Unknown</th><th>Mean confidence</th><th>Image</th></tr>
    </thead>
    <tbody>{''.join(file_rows)}</tbody>
  </table>
  <div class="note">
    TEAM_A and TEAM_B are anonymous color clusters. They do not identify club names, goalkeepers,
    referees, player identity, roles, tracking, or tactical behavior.
  </div>
</main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path

