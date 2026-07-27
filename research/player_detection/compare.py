from __future__ import annotations

import argparse
import html
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from .cli import DEFAULT_RFDETR_WEIGHTS, SUPPORTED_SUFFIXES
from .reports import write_json
from .runner import PlayerDetectionConfig, PlayerDetectionRun, PlayerDetectionRunner


COMPARISON_SCHEMA_VERSION = "matchiq.ve-002.player-detection-comparison.v1"


@dataclass(frozen=True, slots=True)
class ComparisonRun:
    manifest_path: Path
    html_path: Path
    manifest: dict[str, Any]


def _collect_images(path: Path) -> list[Path]:
    if not path.is_dir():
        raise ValueError(f"input directory not found: {path}")
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _resolve_model_path(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        return explicit_path
    configured = os.getenv("MATCHIQ_RFDETR_WEIGHTS", "").strip()
    return Path(configured) if configured else DEFAULT_RFDETR_WEIGHTS


def _read_image_report(run_dir: Path, item: dict[str, Any]) -> dict[str, Any]:
    report_path = run_dir / item["json_report"]
    return json.loads(report_path.read_text(encoding="utf-8"))


def _relative_output_path(root: Path, run_dir: Path, value: str | None) -> str | None:
    if not value:
        return None
    return str((run_dir / value).relative_to(root)).replace("\\", "/")


def _render_comparison_html(manifest: dict[str, Any]) -> str:
    rows: list[str] = []
    for item in manifest["frames"]:
        hog_image = (
            f'<img src="{html.escape(item["hog"]["debug_image"])}" alt="HOG {html.escape(item["frame"])}">'
            if item["hog"].get("debug_image")
            else "<span>Nessuna immagine</span>"
        )
        rfdetr_image = (
            f'<img src="{html.escape(item["rfdetr"]["debug_image"])}" alt="RF-DETR {html.escape(item["frame"])}">'
            if item["rfdetr"].get("debug_image")
            else "<span>Nessuna immagine</span>"
        )
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(item['frame'])}</strong></td>"
            f"<td>{hog_image}<br>{item['hog']['detection_count']} candidati · "
            f"{item['hog']['average_confidence']:.3f} conf. · "
            f"{item['hog']['inference_ms']:.3f} ms</td>"
            f"<td>{rfdetr_image}<br>{item['rfdetr']['detection_count']} candidati · "
            f"{item['rfdetr']['average_confidence']:.3f} conf. · "
            f"{item['rfdetr']['inference_ms']:.3f} ms</td>"
            f"<td>{item['count_delta']:+d}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MatchIQ VE-002 HOG vs RF-DETR</title>
  <style>
    body{{font-family:Arial,sans-serif;max-width:1500px;margin:auto;padding:28px;background:#f3f6fa;color:#152033}}
    section{{background:#fff;border:1px solid #d7e0ea;padding:20px;margin:0 0 18px}}
    table{{width:100%;border-collapse:collapse}} th,td{{border:1px solid #d7e0ea;padding:10px;vertical-align:top}}
    th{{background:#edf3f8;text-align:left}} img{{width:100%;max-width:520px;height:280px;object-fit:contain;background:#101722}}
    .notice{{border-left:4px solid #d5a623;background:#fff8dc;padding:14px}}
    .scroll{{overflow-x:auto}}
  </style>
</head>
<body>
  <h1>MatchIQ Vision Engine - HOG vs RF-DETR</h1>
  <p class="notice">{html.escape(manifest["interpretation_notice"])}</p>
  <section>
    <h2>Riepilogo descrittivo</h2>
    <p>Frame identici: {manifest["aggregate"]["frames_compared"]} ·
       HOG: {manifest["aggregate"]["hog_detections_total"]} candidati ·
       RF-DETR: {manifest["aggregate"]["rfdetr_detections_total"]} candidati.</p>
  </section>
  <section><h2>Confronto visivo</h2><div class="scroll"><table>
    <thead><tr><th>Frame</th><th>HOG</th><th>RF-DETR</th><th>Delta conteggio</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div></section>
</body>
</html>
"""


class PlayerDetectionComparator:
    def __init__(
        self,
        *,
        runner_factory: Callable[[], PlayerDetectionRunner] = PlayerDetectionRunner,
    ) -> None:
        self._runner_factory = runner_factory

    def run(
        self,
        image_paths: Sequence[Path],
        *,
        output_dir: Path,
        model_path: Path,
        threshold: float = 0.30,
        device: str = "cpu",
        hog_threshold: float | None = None,
    ) -> ComparisonRun:
        paths = [Path(path) for path in image_paths]
        if not paths:
            raise ValueError("no input images found")
        output_dir = Path(output_dir)
        hog_dir = output_dir / "hog"
        rfdetr_dir = output_dir / "rfdetr"
        hog_run = self._runner_factory().run(
            paths,
            PlayerDetectionConfig(
                output_dir=hog_dir,
                backend="opencv_hog",
                confidence_threshold=threshold if hog_threshold is None else hog_threshold,
                device="cpu",
            ),
            source_mode="comparison_identical_frames",
        )
        rfdetr_run = self._runner_factory().run(
            paths,
            PlayerDetectionConfig(
                output_dir=rfdetr_dir,
                backend="rfdetr",
                confidence_threshold=threshold,
                model_path=model_path,
                device=device,
            ),
            source_mode="comparison_identical_frames",
        )
        manifest = self._build_manifest(
            paths=paths,
            output_dir=output_dir,
            hog_dir=hog_dir,
            rfdetr_dir=rfdetr_dir,
            hog_run=hog_run,
            rfdetr_run=rfdetr_run,
        )
        manifest_path = write_json(manifest, output_dir / "comparison_manifest.json")
        html_path = output_dir / "comparison_report.html"
        html_path.write_text(_render_comparison_html(manifest), encoding="utf-8")
        return ComparisonRun(
            manifest_path=manifest_path,
            html_path=html_path,
            manifest=manifest,
        )

    @staticmethod
    def _build_manifest(
        *,
        paths: list[Path],
        output_dir: Path,
        hog_dir: Path,
        rfdetr_dir: Path,
        hog_run: PlayerDetectionRun,
        rfdetr_run: PlayerDetectionRun,
    ) -> dict[str, Any]:
        hog_by_source = {item["source_path"]: item for item in hog_run.manifest["files"]}
        rfdetr_by_source = {
            item["source_path"]: item for item in rfdetr_run.manifest["files"]
        }
        frames: list[dict[str, Any]] = []
        for source_path in paths:
            source_key = str(source_path.resolve())
            hog_item = hog_by_source[source_key]
            rfdetr_item = rfdetr_by_source[source_key]
            hog_payload = _read_image_report(hog_dir, hog_item)
            rfdetr_payload = _read_image_report(rfdetr_dir, rfdetr_item)
            frames.append({
                "frame": source_path.name,
                "source_path": source_key,
                "hog": {
                    "status": hog_item["status"],
                    "detection_count": hog_item["detection_count"],
                    "average_confidence": hog_item.get("average_confidence", 0.0),
                    "inference_ms": hog_item.get("inference_ms", 0.0),
                    "boxes": [
                        detection["bbox_xyxy"]
                        for detection in hog_payload.get("detections", [])
                    ],
                    "debug_image": _relative_output_path(
                        output_dir, hog_dir, hog_item.get("debug_image")
                    ),
                    "error": hog_item.get("error"),
                },
                "rfdetr": {
                    "status": rfdetr_item["status"],
                    "detection_count": rfdetr_item["detection_count"],
                    "average_confidence": rfdetr_item.get("average_confidence", 0.0),
                    "inference_ms": rfdetr_item.get("inference_ms", 0.0),
                    "boxes": [
                        detection["bbox_xyxy"]
                        for detection in rfdetr_payload.get("detections", [])
                    ],
                    "debug_image": _relative_output_path(
                        output_dir, rfdetr_dir, rfdetr_item.get("debug_image")
                    ),
                    "error": rfdetr_item.get("error"),
                },
                "count_delta": (
                    rfdetr_item["detection_count"] - hog_item["detection_count"]
                ),
            })
        return {
            "schema_version": COMPARISON_SCHEMA_VERSION,
            "comparison": {
                "same_source_frames": True,
                "frame_order": [path.name for path in paths],
                "hog_manifest": str(
                    hog_run.manifest_path.relative_to(output_dir)
                ).replace("\\", "/"),
                "rfdetr_manifest": str(
                    rfdetr_run.manifest_path.relative_to(output_dir)
                ).replace("\\", "/"),
            },
            "backends": {
                "hog": hog_run.manifest["detector"],
                "rfdetr": rfdetr_run.manifest["detector"],
            },
            "aggregate": {
                "frames_compared": len(frames),
                "hog_detections_total": sum(
                    item["hog"]["detection_count"] for item in frames
                ),
                "rfdetr_detections_total": sum(
                    item["rfdetr"]["detection_count"] for item in frames
                ),
                "hog_average_inference_ms": hog_run.manifest["timing_ms"][
                    "average_inference_ms"
                ],
                "rfdetr_average_inference_ms": rfdetr_run.manifest["timing_ms"][
                    "average_inference_ms"
                ],
                "errors": {
                    "hog": hog_run.manifest["errors"],
                    "rfdetr": rfdetr_run.manifest["errors"],
                },
            },
            "frames": frames,
            "interpretation_notice": (
                "Confronto descrittivo e visivo senza ground truth: un numero maggiore "
                "di detection non equivale automaticamente a una qualita o accuratezza migliore."
            ),
            "accuracy_metrics": None,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MatchIQ VE-002 comparison runner for identical HOG and RF-DETR frames."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-dir", type=Path)
    source.add_argument("--ve001-frames", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--threshold", type=float, default=0.30)
    parser.add_argument("--hog-threshold", type=float)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cpu")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0.0 <= args.threshold <= 1.0:
        raise SystemExit("--threshold must be between 0 and 1")
    if args.hog_threshold is not None and not 0.0 <= args.hog_threshold <= 1.0:
        raise SystemExit("--hog-threshold must be between 0 and 1")
    source_dir = args.input_dir or args.ve001_frames
    paths = _collect_images(source_dir)
    if not paths:
        raise SystemExit("no supported images found")
    model_path = _resolve_model_path(args.model_path)
    if not model_path.is_file():
        raise SystemExit(
            f"RF-DETR local weights not found: {model_path}. "
            "No model download is performed automatically."
        )
    result = PlayerDetectionComparator().run(
        paths,
        output_dir=args.output,
        model_path=model_path,
        threshold=args.threshold,
        device=args.device,
        hog_threshold=args.hog_threshold,
    )
    print(f"Comparison JSON: {result.manifest_path}")
    print(f"Comparison HTML: {result.html_path}")
    print(
        "Compared: "
        f"{result.manifest['aggregate']['frames_compared']} | "
        f"HOG detections: {result.manifest['aggregate']['hog_detections_total']} | "
        f"RF-DETR detections: {result.manifest['aggregate']['rfdetr_detections_total']}"
    )
    errors = result.manifest["aggregate"]["errors"]
    return 0 if not errors["hog"] and not errors["rfdetr"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
