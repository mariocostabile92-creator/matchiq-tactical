from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_json_report(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _value(value: Any) -> str:
    if value is None or value == "":
        return "n/d"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _rows(items: list[tuple[str, Any]]) -> str:
    return "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(_value(value))}</td></tr>"
        for label, value in items
    )


def render_html_report(report: dict[str, Any]) -> str:
    video = report["video"]
    statistics = report["pipeline_statistics"]
    performance = report["performance"]
    category_rows = "".join(
        f"<tr><td>{html.escape(category)}</td><td>{count}</td></tr>"
        for category, count in report["category_distribution"].items()
    ) or '<tr><td colspan="2">Nessuna categoria</td></tr>'
    candidate_rows = []
    for candidate in report["candidates"]:
        confidence = candidate["confidence"]
        candidate_rows.append(
            "<tr>"
            f"<td>{candidate['index'] + 1}</td>"
            f"<td>{html.escape(candidate['timestamp_label'])}</td>"
            f"<td><a href=\"{html.escape(candidate['frame_file'])}\">JPEG</a></td>"
            f"<td>{'si' if candidate['frame_selected'] else 'no'}</td>"
            f"<td>{html.escape(candidate['category'])}</td>"
            f"<td>{html.escape(candidate['selection_status'])}</td>"
            f"<td>{html.escape(_value(confidence['displayed']))}</td>"
            f"<td>{html.escape(confidence['type'])}</td>"
            f"<td>{html.escape(confidence['origin'])}</td>"
            f"<td>{html.escape(candidate['description'])}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MatchIQ VE-001 Baseline - {html.escape(video['file_name'])}</title>
  <style>
    body{{font-family:Arial,sans-serif;max-width:1180px;margin:0 auto;padding:28px;color:#172033;background:#f4f7fb}}
    h1,h2{{margin:0 0 14px}} section{{background:#fff;border:1px solid #dce3ed;margin:0 0 18px;padding:20px}}
    table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{border:1px solid #dce3ed;padding:9px;text-align:left;vertical-align:top}}
    th{{background:#edf3f8}} .note{{padding:12px;background:#fff8df;border:1px solid #eed998}}
    .scroll{{overflow-x:auto}} code{{font-size:12px}}
  </style>
</head>
<body>
  <h1>MatchIQ Vision Engine - VE-001 Baseline</h1>
  <p>Esecuzione {html.escape(report['run']['processed_at'])} &middot; pipeline <code>{html.escape(report['run']['pipeline_version'])}</code></p>
  <section><h2>Video</h2><table>{_rows([
      ("File", video["file_name"]),
      ("Durata (s)", video["duration_seconds"]),
      ("FPS", video["fps"]),
      ("Risoluzione", video["resolution"]),
      ("Frame sorgente", video["frame_count"]),
  ])}</table></section>
  <section><h2>Statistiche pipeline</h2><table>{_rows([
      ("Frame analizzati", statistics["frames_analyzed"]),
      ("Candidate trovate", statistics["candidates_found"]),
      ("Candidate inviate a OpenAI", statistics["candidates_sent_to_openai"]),
      ("Descrizioni generate", statistics["descriptions_generated"]),
      ("Tempo medio/candidate (s)", statistics["average_seconds_per_candidate"]),
  ])}</table></section>
  <section><h2>Performance</h2><table>{_rows([
      ("Estrazione frame (s)", performance["frame_extraction_seconds"]),
      ("Chiamate AI (s)", performance["ai_calls_seconds"]),
      ("Validazione locale (s)", performance["local_validation_seconds"]),
      ("Totale pipeline (s)", performance["total_processing_seconds"]),
  ])}</table></section>
  <section><h2>Distribuzione categorie</h2><table><thead><tr><th>Categoria</th><th>Conteggio</th></tr></thead><tbody>{category_rows}</tbody></table></section>
  <section><h2>Candidate</h2><div class="scroll"><table>
    <thead><tr><th>#</th><th>Timestamp</th><th>Frame</th><th>Selezionato</th><th>Categoria</th><th>Stato</th><th>Confidence</th><th>Tipo</th><th>Origine</th><th>Descrizione</th></tr></thead>
    <tbody>{''.join(candidate_rows)}</tbody>
  </table></div></section>
  <p class="note">{html.escape(report['limitations']['confidence_note'])}</p>
</body>
</html>
"""


def write_html_report(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html_report(report), encoding="utf-8")
    return path
