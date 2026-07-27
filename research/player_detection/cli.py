from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Sequence

from .runner import PlayerDetectionConfig, PlayerDetectionRunner


SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DEFAULT_RFDETR_WEIGHTS = Path(
    "research/vision_spike/checkpoints/rfdetr-small-coco/checkpoint_best_regular.pth"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MatchIQ VE-002 isolated player detection runner."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path, help="Single source image.")
    source.add_argument("--input-dir", type=Path, help="Directory containing source images.")
    source.add_argument(
        "--ve001-frames",
        type=Path,
        help="VE-001 frames directory (equivalent to --input-dir).",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output report directory.")
    parser.add_argument(
        "--backend",
        choices=("hog", "opencv_hog", "rfdetr"),
        default="opencv_hog",
        help="Detector backend. RF-DETR requires local dependencies and weights.",
    )
    parser.add_argument("--confidence", "--threshold", dest="confidence", type=float, default=0.35)
    parser.add_argument("--nms-threshold", type=float, default=0.45)
    parser.add_argument("--detector-width", type=int, default=960)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def resolve_model_path(explicit_path: Path | None) -> Path | None:
    if explicit_path is not None:
        return explicit_path
    configured = os.getenv("MATCHIQ_RFDETR_WEIGHTS", "").strip()
    if configured:
        return Path(configured)
    return DEFAULT_RFDETR_WEIGHTS


def _collect_images(path: Path) -> list[Path]:
    if not path.is_dir():
        raise ValueError(f"input directory not found: {path}")
    return sorted(
        item for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0.0 <= args.confidence <= 1.0:
        raise SystemExit("--confidence must be between 0 and 1")
    if not 0.0 <= args.nms_threshold <= 1.0:
        raise SystemExit("--nms-threshold must be between 0 and 1")
    if args.detector_width < 320:
        raise SystemExit("--detector-width must be at least 320")
    backend = "opencv_hog" if args.backend == "hog" else args.backend
    model_path = resolve_model_path(args.model_path) if backend == "rfdetr" else args.model_path
    if args.image:
        if not args.image.is_file():
            raise SystemExit(f"input image not found: {args.image}")
        paths = [args.image]
        source_mode = "single_image"
    else:
        directory = args.input_dir or args.ve001_frames
        paths = _collect_images(directory)
        source_mode = "ve001_frames" if args.ve001_frames else "image_directory"
    if not paths:
        raise SystemExit("no supported images found")

    result = PlayerDetectionRunner().run(
        paths,
        PlayerDetectionConfig(
            output_dir=args.output,
            backend=backend,
            confidence_threshold=args.confidence,
            nms_threshold=args.nms_threshold,
            detector_width=args.detector_width,
            model_path=model_path,
            device=args.device,
        ),
        source_mode=source_mode,
    )
    print(f"JSON manifest: {result.manifest_path}")
    print(f"HTML report: {result.html_path}")
    print(
        "Processed: "
        f"{result.manifest['aggregate']['images_processed']} | "
        f"Failed: {result.manifest['aggregate']['images_failed']} | "
        f"Detections: {result.manifest['aggregate']['detections_total']}"
    )
    return 0 if result.manifest["aggregate"]["images_failed"] == 0 else 2
