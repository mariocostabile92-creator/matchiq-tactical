from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_json(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return html.escape(str(value))


def write_html_report(manifest: dict[str, Any], path: Path) -> Path:
    aggregate = manifest["aggregate"]
    timing = manifest["timing_ms"]
    tracks = manifest["tracks"]
    frame_rows = "\n".join(
        "<tr>"
        f"<td>{item['sequence_index']}</td>"
        f"<td>{item['frame_index']}</td>"
        f"<td>{item['timestamp_seconds']:.3f}</td>"
        f"<td>{item['detections_input']}</td>"
        f"<td>{item['tracks_confirmed']}</td>"
        f"<td>{item['tentative_count']}</td>"
        f"<td>{html.escape(item['segment_id'])}</td>"
        "</tr>"
        for item in manifest["frames"]
    )
    track_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(track['track_id'])}</td>"
        f"<td>{track['start_timestamp_seconds']:.3f}</td>"
        f"<td>{track['end_timestamp_seconds']:.3f}</td>"
        f"<td>{track['detected_frames']}</td>"
        f"<td>{track['predicted_frames']}</td>"
        f"<td>{track['gap_count']} / {track['maximum_gap_processed_frames']}</td>"
        f"<td>{track['continuity']:.3f}</td>"
        f"<td>{_value(track['dominant_team'])}</td>"
        f"<td>{track['observed_team_changes']}</td>"
        f"<td>{track['average_detection_confidence']:.3f}</td>"
        f"<td>{track['preliminary_track_quality']:.3f}</td>"
        f"<td>{'yes' if track['id_switch_warning'] else 'no'}</td>"
        "</tr>"
        for track in tracks
    )
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MatchIQ VE-004B Tracking Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #132238; }}
    h1, h2 {{ color: #073763; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #ccd6e0; padding: 12px; border-radius: 6px; }}
    .metric strong {{ display: block; font-size: 1.35rem; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 14px 0 28px; }}
    th, td {{ border: 1px solid #d6dee7; padding: 7px; text-align: left; font-size: 0.88rem; }}
    th {{ background: #eef5fa; }}
    code {{ background: #eef2f6; padding: 2px 4px; }}
  </style>
</head>
<body>
  <h1>MatchIQ VE-004B ByteTrack Baseline</h1>
  <p>Schema <code>{html.escape(manifest['schema_version'])}</code>. Research output only.</p>
  <div class="grid">
    <div class="metric">Frames<strong>{aggregate['frames_processed']}</strong></div>
    <div class="metric">Confirmed tracks<strong>{aggregate['tracks_total']}</strong></div>
    <div class="metric">Short tracks<strong>{aggregate['short_tracks_max_2_detections']}</strong></div>
    <div class="metric">Fragmented tracks<strong>{aggregate['fragmented_tracks']}</strong></div>
    <div class="metric">Observations<strong>{aggregate['detected_observations']}</strong></div>
    <div class="metric">Predicted rows<strong>{aggregate['predicted_observations']}</strong></div>
    <div class="metric">Tentative rows<strong>{aggregate['tentative_observations']}</strong></div>
    <div class="metric">Total time (ms)<strong>{timing['total_ms']:.1f}</strong></div>
  </div>
  <h2>Tracks</h2>
  <table>
    <thead><tr><th>ID</th><th>Start</th><th>End</th><th>Detected</th><th>Predicted</th><th>Gaps / max</th><th>Continuity</th><th>Team</th><th>Team changes</th><th>Det conf.</th><th>Quality</th><th>Switch warning</th></tr></thead>
    <tbody>{track_rows}</tbody>
  </table>
  <h2>Frame processing</h2>
  <table>
    <thead><tr><th>Sequence</th><th>Source frame</th><th>Time</th><th>Input</th><th>Confirmed</th><th>Tentative</th><th>Segment</th></tr></thead>
    <tbody>{frame_rows}</tbody>
  </table>
  <h2>Method limits</h2>
  <ul>
    <li>Image-space tracking only; no field calibration or tactical interpretation.</li>
    <li>The selected ByteTrack package does not emit prediction-only rows.</li>
    <li>Team assignment is diagnostic metadata and never a hard association gate.</li>
    <li>ID-switch warnings are heuristics without ground-truth identity labels.</li>
  </ul>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path
