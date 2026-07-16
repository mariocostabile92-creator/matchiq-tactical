from __future__ import annotations

import argparse
from pathlib import Path

from .config import VisionSpikeConfig
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matchiq-vision-spike",
        description="Run the isolated MatchIQ Vision Engine feasibility spike on a local video.",
    )
    parser.add_argument("--input", required=True, type=Path, dest="input_video")
    parser.add_argument("--output", required=True, type=Path, dest="output_dir")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--detector", choices=("opencv_hog",), default="opencv_hog")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--frame-stride", type=int, default=5)
    parser.add_argument("--start-seconds", type=float, default=0.0)
    parser.add_argument("--max-seconds", type=float, default=60.0)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--detector-width", type=int, default=960)
    parser.add_argument("--output-fps", type=float)
    parser.add_argument("--no-overlay", action="store_true")
    parser.add_argument("--no-team-clustering", action="store_true")
    parser.add_argument("--disable-pitch", action="store_true")
    parser.add_argument("--request-ball", action="store_true")
    parser.add_argument("--save-debug-frames", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = VisionSpikeConfig(
        input_video=args.input_video,
        output_dir=args.output_dir,
        detector_backend=args.detector,
        confidence_threshold=args.confidence,
        iou_threshold=args.iou,
        frame_stride=args.frame_stride,
        max_frames=args.max_frames,
        start_seconds=args.start_seconds,
        max_seconds=args.max_seconds,
        device=args.device,
        output_fps=args.output_fps,
        overlay_enabled=not args.no_overlay,
        team_clustering_enabled=not args.no_team_clustering,
        ball_detection_enabled=args.request_ball,
        pitch_detection_enabled=not args.disable_pitch,
        save_debug_frames=args.save_debug_frames,
        detector_width=args.detector_width,
    )
    try:
        result = run_pipeline(config)
    except (ValueError, RuntimeError) as exc:
        print(f"Vision Spike failed: {exc}")
        return 2
    print(f"Status: {result.status}")
    print(f"Output: {result.output_dir.resolve()}")
    print(f"Processed frames: {result.metrics.get('processed_frames', 0)}")
    print(f"Processing FPS: {result.metrics.get('processing_fps', 0)}")
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
