from __future__ import annotations

import argparse
import csv
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import VisionSpikeConfig
from .pipeline import run_pipeline
from .utils import write_json


@dataclass(frozen=True, slots=True)
class ClipSpec:
    name: str
    path: Path
    frame_stride: int


@dataclass(frozen=True, slots=True)
class VariantSpec:
    name: str
    input_resolution: int
    inference_mode: str
    tile_size: int = 960
    tile_overlap: float = 0.2


DEFAULT_VARIANTS = (
    VariantSpec("rfdetr_small_standard", 512, "standard"),
    VariantSpec("rfdetr_small_highres", 960, "highres"),
    VariantSpec("rfdetr_small_tiled", 512, "tiled"),
)


def default_clips(root: Path) -> tuple[ClipSpec, ...]:
    return (
        ClipSpec("minute_1", root / "bayern-60-90.mp4", 15),
        ClipSpec("minute_20", root / "bayern-1200-1230.mp4", 30),
        ClipSpec("minute_80", root / "bayern-4800-4830.mp4", 30),
    )


def run_variant(
    variant: VariantSpec,
    clips: tuple[ClipSpec, ...],
    output_root: Path,
    *,
    device: str = "auto",
    confidence: float = 0.25,
    half_precision: bool = True,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for clip in clips:
        if not clip.path.is_file():
            raise ValueError(f"benchmark clip not found: {clip.path}")
        output = output_root / variant.name / clip.name
        config = VisionSpikeConfig(
            input_video=clip.path,
            output_dir=output,
            detector_backend="rfdetr",
            confidence_threshold=confidence,
            iou_threshold=0.45,
            frame_stride=clip.frame_stride,
            max_seconds=30.0,
            device=device,
            overlay_enabled=True,
            team_clustering_enabled=True,
            pitch_detection_enabled=True,
            model_size="small",
            input_resolution=variant.input_resolution,
            inference_mode=variant.inference_mode,
            tile_size=variant.tile_size,
            tile_overlap=variant.tile_overlap,
            half_precision=half_precision,
            max_detections=100,
        )
        result = run_pipeline(config)
        rows.append({"variant": variant.name, "clip": clip.name, "output": str(output), **result.metrics})
    write_json(output_root / variant.name / "aggregate.json", aggregate_rows(rows))
    return rows


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_frames = sum(int(row.get("processed_frames", 0)) for row in rows)
    total_elapsed = sum(float(row.get("elapsed_seconds", 0.0)) for row in rows)

    def weighted(key: str) -> float:
        if not total_frames:
            return 0.0
        return round(
            sum(float(row.get(key, 0.0)) * int(row.get("processed_frames", 0)) for row in rows) / total_frames,
            4,
        )

    return {
        "clips": len(rows),
        "processed_frames": total_frames,
        "elapsed_seconds": round(total_elapsed, 4),
        "processing_fps": round(total_frames / total_elapsed, 4) if total_elapsed else 0.0,
        "average_people_detected": weighted("average_people_detected"),
        "frames_with_detections_percent": weighted("frames_with_detections_percent"),
        "frames_with_active_tracks_percent": weighted("frames_with_active_tracks_percent"),
        "average_latency_ms": weighted("average_latency_ms"),
        "detections_outside_pitch_percent": weighted("detections_outside_pitch_percent"),
        "tracks_total": sum(int(row.get("tracks_total", 0)) for row in rows),
        "tracks_lost": sum(int(row.get("tracks_lost", 0)) for row in rows),
        "peak_rss_mb": max((float(row.get("peak_rss_mb", 0.0)) for row in rows), default=0.0),
        "peak_vram_mb": max((float(row.get("peak_vram_mb", 0.0)) for row in rows), default=0.0),
        "model_load_seconds": max((float(row.get("model_load_seconds", 0.0)) for row in rows), default=0.0),
        "model_size_bytes": next((row.get("model_size_bytes") for row in rows if row.get("model_size_bytes")), None),
        "duplicate_detections_removed": sum(int(row.get("duplicate_detections_removed", 0)) for row in rows),
        "accuracy_note": "No precision/recall: manual exploratory coverage is reported separately.",
    }


def import_v0_baseline(source_dirs: tuple[Path, ...], output_root: Path) -> list[dict[str, Any]]:
    destination = output_root / "baseline_opencv"
    rows: list[dict[str, Any]] = []
    for name, source in zip(("minute_1", "minute_20", "minute_80"), source_dirs):
        target = destination / name
        target.mkdir(parents=True, exist_ok=True)
        for filename in (
            "overlay.mp4",
            "detections.json",
            "tracks.json",
            "frames.json",
            "metrics.json",
            "run_manifest.json",
            "evaluation.md",
        ):
            source_file = source / filename
            if source_file.is_file():
                shutil.copy2(source_file, target / filename)
        metrics_path = target / "metrics.json"
        if metrics_path.is_file():
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            frames_path = target / "frames.json"
            if frames_path.is_file():
                frames = json.loads(frames_path.read_text(encoding="utf-8"))
                detected = sum(bool(frame.get("detections")) for frame in frames)
                if frames:
                    metrics["frames_with_detections_percent"] = round(100.0 * detected / len(frames), 2)
            rows.append({"variant": "baseline_opencv", "clip": name, "output": str(target), **metrics})
        for source_name, target_name in (("detections.json", "detections.jsonl"), ("tracks.json", "tracks.jsonl")):
            source_path = target / source_name
            target_path = target / target_name
            if source_path.is_file() and not target_path.exists():
                payload = json.loads(source_path.read_text(encoding="utf-8"))
                with target_path.open("w", encoding="utf-8") as handle:
                    for item in payload:
                        handle.write(json.dumps(item, ensure_ascii=True, sort_keys=True) + "\n")
    write_json(destination / "aggregate.json", aggregate_rows(rows))
    return rows


def write_comparison(output_root: Path, rows: list[dict[str, Any]]) -> None:
    comparison = output_root / "comparison"
    comparison.mkdir(parents=True, exist_ok=True)
    variants = sorted({str(row["variant"]) for row in rows})
    aggregates = {name: aggregate_rows([row for row in rows if row["variant"] == name]) for name in variants}
    write_json(comparison / "detector_comparison.json", {"variants": aggregates, "runs": rows})
    fields = [
        "variant",
        "processed_frames",
        "average_people_detected",
        "frames_with_detections_percent",
        "frames_with_active_tracks_percent",
        "processing_fps",
        "average_latency_ms",
        "peak_rss_mb",
        "peak_vram_mb",
        "detections_outside_pitch_percent",
    ]
    with (comparison / "detector_comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for variant in variants:
            row = {"variant": variant, **aggregates[variant]}
            writer.writerow({field: row.get(field) for field in fields})
    lines = ["# Detector comparison", "", "No precision or recall is claimed; see manual exploratory coverage.", ""]
    lines.extend(
        f"- {name}: {data['average_people_detected']} people/frame, "
        f"{data['frames_with_active_tracks_percent']}% frames with active tracks, {data['processing_fps']} FPS"
        for name, data in aggregates.items()
    )
    (comparison / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Controlled MatchIQ V0 versus RF-DETR V2 detector benchmark.")
    parser.add_argument("--clip-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--variant", choices=tuple(item.name for item in DEFAULT_VARIANTS), action="append")
    parser.add_argument("--confidence", type=float, default=0.25)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    selected = set(args.variant or [item.name for item in DEFAULT_VARIANTS])
    clips = default_clips(args.clip_root)
    rows: list[dict[str, Any]] = []
    for variant in DEFAULT_VARIANTS:
        if variant.name in selected:
            rows.extend(run_variant(variant, clips, args.output_root, device=args.device, confidence=args.confidence))
    write_comparison(args.output_root, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
