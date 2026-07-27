from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_json(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_html_report(manifest: dict[str, Any]) -> str:
    aggregate = manifest["aggregate"]
    timing = manifest["timing_ms"]
    file_rows: list[str] = []
    for item in manifest["files"]:
        preview = ""
        if item.get("debug_image"):
            preview = (
                f'<a href="{html.escape(item["debug_image"])}">'
                f'<img src="{html.escape(item["debug_image"])}" alt="Debug {html.escape(item["source_name"])}"></a>'
            )
        error = item.get("error") or ""
        file_rows.append(
            "<tr>"
            f"<td>{preview}</td>"
            f"<td>{html.escape(item['source_name'])}</td>"
            f"<td>{html.escape(item['status'])}</td>"
            f"<td>{item.get('detection_count', 0)}</td>"
            f"<td>{_number(item.get('inference_ms', 0))}</td>"
            f"<td>{html.escape(error)}</td>"
            "</tr>"
        )
    error_rows = "".join(
        "<li>"
        f"<strong>{html.escape(item['source_name'])}</strong>: {html.escape(item['message'])}"
        "</li>"
        for item in manifest["errors"]
    ) or "<li>Nessun errore.</li>"
    detector = manifest["detector"]
    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MatchIQ VE-002 Player Detection</title>
  <style>
    body{{font-family:Arial,sans-serif;max-width:1180px;margin:auto;padding:28px;background:#f3f6fa;color:#152033}}
    section{{background:#fff;border:1px solid #d7e0ea;padding:20px;margin:0 0 18px}}
    .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
    .stat{{border:1px solid #d7e0ea;padding:14px}} .stat strong{{display:block;font-size:24px}}
    table{{width:100%;border-collapse:collapse}} th,td{{border:1px solid #d7e0ea;padding:9px;text-align:left;vertical-align:top}}
    th{{background:#edf3f8}} img{{width:220px;max-height:130px;object-fit:contain;background:#101722}}
    .scroll{{overflow-x:auto}} code{{font-size:12px}}
  </style>
</head>
<body>
  <h1>MatchIQ Vision Engine - VE-002 Player Detection</h1>
  <p>Run {html.escape(manifest['run']['processed_at'])} &middot; backend <code>{html.escape(str(detector.get('backend', 'unknown')))}</code></p>
  <section><h2>Riepilogo</h2><div class="stats">
    <div class="stat"><strong>{aggregate['images_processed']}</strong>Immagini processate</div>
    <div class="stat"><strong>{aggregate['images_successful']}</strong>Completate</div>
    <div class="stat"><strong>{aggregate['images_failed']}</strong>Errori</div>
    <div class="stat"><strong>{aggregate['detections_total']}</strong>Detection</div>
    <div class="stat"><strong>{_number(aggregate['detections_average'])}</strong>Media / immagine</div>
    <div class="stat"><strong>{_number(timing['total_ms'])} ms</strong>Tempo totale</div>
  </div></section>
  <section><h2>Detector</h2><pre>{html.escape(json.dumps(detector, ensure_ascii=False, indent=2))}</pre></section>
  <section><h2>Immagini</h2><div class="scroll"><table>
    <thead><tr><th>Preview</th><th>File</th><th>Stato</th><th>Player</th><th>Inferenza ms</th><th>Errore</th></tr></thead>
    <tbody>{''.join(file_rows)}</tbody>
  </table></div></section>
  <section><h2>Errori</h2><ul>{error_rows}</ul></section>
</body>
</html>
"""


def write_html_report(manifest: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html_report(manifest), encoding="utf-8")
    return path
