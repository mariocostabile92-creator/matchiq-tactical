from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .contracts import TrackingConfig
from .runner import TrackingRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="VE-004B: run ByteTrack on an existing VE-003 temporal sequence.",
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="VE-003 team_assignment_manifest.json, per-frame JSON, or JSON directory",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--fps",
        required=True,
        type=float,
        help="Effective FPS of the processed sequence; required when timing metadata is absent",
    )
    parser.add_argument("--high-threshold", type=float, default=0.60)
    parser.add_argument("--low-threshold", type=float, default=0.20)
    parser.add_argument("--match-threshold", type=float, default=0.10)
    parser.add_argument("--lost-buffer", type=int, default=30)
    parser.add_argument("--minimum-confirmed-frames", type=int, default=2)
    parser.add_argument("--maximum-detections", type=int, default=80)
    parser.add_argument("--minimum-box-area", type=float, default=64.0)
    parser.add_argument("--no-debug", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = TrackingConfig(
        output_dir=args.output,
        fps=args.fps,
        high_detection_threshold=args.high_threshold,
        low_detection_threshold=args.low_threshold,
        match_threshold=args.match_threshold,
        lost_buffer=args.lost_buffer,
        minimum_confirmed_frames=args.minimum_confirmed_frames,
        maximum_detections=args.maximum_detections,
        minimum_box_area=args.minimum_box_area,
        render_debug=not args.no_debug,
    )
    try:
        run = TrackingRunner().run(args.source, config)
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    print(f"VE-004B JSON: {run.manifest_path}")
    print(f"VE-004B HTML: {run.html_path}")
    print(
        "Tracking: "
        f"frames={run.manifest['aggregate']['frames_processed']} "
        f"tracks={run.manifest['aggregate']['tracks_total']} "
        f"observations={run.manifest['aggregate']['detected_observations']}"
    )
    return 0
