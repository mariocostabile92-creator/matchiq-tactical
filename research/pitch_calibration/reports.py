from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


def write_json(payload: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def write_csv(rows: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "frame_id",
        "timestamp_seconds",
        "camera_segment_id",
        "status",
        "model_confidence",
        "evidence_confidence",
        "correspondence_confidence",
        "geometric_confidence",
        "temporal_confidence",
        "projection_confidence",
        "overall_confidence",
        "failure_reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_html_report(
    manifest: dict[str, Any],
    benchmark: dict[str, Any],
    path: Path,
) -> Path:
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(frame['frame_id'])}</td>"
        f"<td>{frame['timestamp_seconds']:.3f}</td>"
        f"<td>{html.escape(frame['camera_segment_id'])}</td>"
        f"<td>{html.escape(frame['status'])}</td>"
        f"<td>{_value(frame['confidence']['model'])}</td>"
        f"<td>{_value(frame['confidence']['geometric'])}</td>"
        f"<td>{_value(frame['confidence']['temporal'])}</td>"
        f"<td>{_value(frame['confidence']['overall'])}</td>"
        f"<td>{html.escape(frame.get('failure_reason') or '-')}</td>"
        "</tr>"
        for frame in manifest["frames"]
    )
    status_cards = "\n".join(
        f"<div class='metric'>{html.escape(key)}"
        f"<strong>{value}</strong>"
        f"<small>{benchmark.get('status_rates', {}).get(key, 0.0) * 100:.1f}%</small>"
        "</div>"
        for key, value in benchmark["status_distribution"].items()
    )
    timing = benchmark.get("timing_ms") or {}
    aggregate = manifest.get("aggregate") or {}
    failures = _failure_summary(manifest["frames"])
    failure_rows = "".join(
        f"<li><code>{html.escape(reason)}</code>: {count}</li>"
        for reason, count in failures.items()
    ) or "<li>No failure reason recorded.</li>"
    limitations = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in manifest.get("limitations", [])
    )
    source = manifest.get("source") or {}
    module = str(manifest.get("run", {}).get("module", "VE-005B"))
    adapter = str(manifest.get("run", {}).get("adapter", "tvcalib"))
    title = (
        "MatchIQ VE-005C Hybrid Pitch Calibrator"
        if module == "VE-005C"
        else "MatchIQ VE-005B TVCalib Baseline"
    )
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #132238; background: #f4f7fa; }}
    main {{ max-width: 1280px; margin: auto; background: white; padding: 28px; border-radius: 8px; }}
    h1, h2 {{ color: #073763; }}
    .status {{ padding: 12px; border-left: 4px solid #dc9b16; background: #fff8e8; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #ccd6e0; padding: 12px; border-radius: 6px; }}
    .metric strong {{ display: block; font-size: 1.4rem; margin-top: 6px; }}
    .metric small {{ display: block; color: #52677d; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border: 1px solid #d6dee7; padding: 7px; text-align: left; font-size: .86rem; }}
    th {{ background: #eef5fa; }}
    code {{ background: #eef2f6; padding: 2px 4px; }}
  </style>
</head>
<body><main>
  <h1>{html.escape(title)}</h1>
  <p class="status"><strong>Research status: {html.escape(benchmark['research_status'])}</strong><br>
  {html.escape(benchmark['status_reason'])}</p>
  <p>Schema <code>{html.escape(manifest['schema_version'])}</code>. Research only; not connected to production.</p>
  <p>Adapter: <code>{html.escape(adapter)}</code>.</p>
  <div class="grid">{status_cards}</div>
  <h2>Dataset and configuration</h2>
  <p>Source: <code>{html.escape(str(source.get('path', '-')))}</code><br>
  Kind: {html.escape(str(source.get('kind', '-')))}; frames: {source.get('frames', 0)}.</p>
  <pre>{html.escape(json.dumps(manifest.get('configuration', {}), indent=2))}</pre>
  <h2>Performance and projections</h2>
  <div class="grid">
    <div class="metric">Mean frame time<strong>{_value(timing.get('mean'))} ms</strong></div>
    <div class="metric">P50 frame time<strong>{_value(timing.get('p50'))} ms</strong></div>
    <div class="metric">P95 frame time<strong>{_value(timing.get('p95'))} ms</strong></div>
    <div class="metric">Valid foot points<strong>{aggregate.get('projected_observations', 0)}</strong></div>
    <div class="metric">Projection records<strong>{aggregate.get('projection_records', 0)}</strong></div>
    <div class="metric">Mean line segments<strong>{_value(benchmark.get('average_segment_count'))}</strong></div>
    <div class="metric">Mean keypoints<strong>{_value(benchmark.get('average_keypoint_count'))}</strong></div>
    <div class="metric">Accepted correspondences<strong>{benchmark.get('accepted_correspondences', 0)}</strong></div>
    <div class="metric">Rejected correspondences<strong>{benchmark.get('rejected_correspondences', 0)}</strong></div>
    <div class="metric">Mean inlier ratio<strong>{_value(benchmark.get('average_inlier_ratio'))}</strong></div>
    <div class="metric">Mean temporal confidence<strong>{_value(benchmark.get('average_temporal_confidence'))}</strong></div>
    <div class="metric">Camera segments<strong>{benchmark.get('camera_segments', 0)}</strong></div>
    <div class="metric">Visual jumps<strong>{benchmark.get('visual_jumps', 0)}</strong></div>
  </div>
  <p><strong>Accuracy:</strong> {html.escape(benchmark.get('accuracy_statement', 'Not measured.'))}</p>
  <p><strong>Technical success:</strong> {html.escape(benchmark.get('technical_success_definition', '-'))}</p>
  <p><strong>Next sprint:</strong> {html.escape(benchmark.get('next_sprint_decision', '-'))}</p>
  <h2>Best and worst candidates</h2>
  <pre>{html.escape(json.dumps({
      'best_frame': benchmark.get('best_frame'),
      'worst_frame': benchmark.get('worst_frame'),
      'assessment': benchmark.get('assessment'),
  }, indent=2))}</pre>
  <h2>Frames</h2>
  <table>
    <thead><tr><th>Frame</th><th>Time</th><th>Segment</th><th>Status</th><th>Model</th><th>Geometric</th><th>Temporal</th><th>Overall</th><th>Failure</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h2>Failure reasons</h2>
  <ul>{failure_rows}</ul>
  <h2>Known limitations</h2>
  <ul>{limitations}</ul>
  <h2>Licensing and reproducibility gate</h2>
  <pre>{html.escape(json.dumps(manifest['environment'], indent=2))}</pre>
</main></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return html.escape(str(value))


def _failure_summary(frames: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for frame in frames:
        reasons = frame.get("rejection_reasons") or ()
        if not reasons and frame.get("failure_reason"):
            reasons = (frame["failure_reason"],)
        for reason in reasons:
            key = str(reason)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
