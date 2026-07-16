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
    parser.add_argument("--detector", choices=("opencv_hog", "rfdetr"), default="opencv_hog")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--frame-stride", type=int, default=5)
    parser.add_argument("--start-seconds", type=float, default=0.0)
    parser.add_argument("--max-seconds", type=float, default=60.0)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--detector-width", type=int, default=960)
    parser.add_argument("--model-size", choices=("small", "medium"), default="small")
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--input-resolution", type=int, default=512)
    parser.add_argument("--inference-mode", choices=("standard", "highres", "tiled"), default="standard")
    parser.add_argument("--tile-size", type=int, default=960)
    parser.add_argument("--tile-overlap", type=float, default=0.2)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--half-precision", action="store_true")
    parser.add_argument("--max-detections", type=int, default=100)
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
        model_size=args.model_size,
        model_path=args.model_path,
        input_resolution=args.input_resolution,
        inference_mode=args.inference_mode,
        tile_size=args.tile_size,
        tile_overlap=args.tile_overlap,
        batch_size=args.batch_size,
        half_precision=args.half_precision,
        max_detections=args.max_detections,
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
