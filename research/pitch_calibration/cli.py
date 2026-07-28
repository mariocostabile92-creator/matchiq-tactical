from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .adapters import MatchIQHybridAdapter, TVCalibAdapter
from .contracts import CalibrationAdapter
from .contracts import CalibrationConfig
from .reports import write_json
from .runner import PitchCalibrationRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="VE-005B/VE-005C isolated pitch-calibration research runner."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect-environment",
        help="Inspect the external TVCalib boundary without running calibration.",
    )
    _adapter_arguments(inspect_parser)

    for name in ("calibrate-image", "calibrate-video", "calibrate-sequence"):
        child = subparsers.add_parser(name)
        _run_arguments(child)

    benchmark = subparsers.add_parser(
        "benchmark",
        help="Run separate professional and amateur inputs through the same baseline.",
    )
    benchmark.add_argument("--professional", required=True, type=Path)
    benchmark.add_argument("--amateur", required=True, type=Path)
    benchmark.add_argument("--output", required=True, type=Path)
    benchmark.add_argument("--maximum-frames", type=int)
    benchmark.add_argument("--sample-interval", type=float, default=2.0)
    _quality_arguments(benchmark)
    _adapter_arguments(benchmark)
    return parser


def _adapter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--adapter",
        choices=("tvcalib", "matchiq-hybrid"),
        default="tvcalib",
    )
    parser.add_argument("--upstream-root", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--camera-profile", choices=("fixed", "smartphone"), default="fixed")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--min-hypothesis-score", type=float, default=0.34)
    parser.add_argument("--min-line-support", type=float, default=0.05)


def _run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", "--input", dest="source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-interval", type=float, default=2.0)
    parser.add_argument("--maximum-frames", type=int)
    parser.add_argument("--physical-length", type=float)
    parser.add_argument("--physical-width", type=float)
    parser.add_argument("--no-debug", action="store_true")
    parser.add_argument("--keyframe-frequency", type=int, default=1)
    _quality_arguments(parser)
    _adapter_arguments(parser)


def _quality_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--min-model-confidence", type=float, default=0.45)
    parser.add_argument("--min-geometric-confidence", type=float, default=0.45)
    parser.add_argument("--min-projection-confidence", type=float, default=0.45)
    parser.add_argument("--min-evidence-confidence", type=float, default=0.35)
    parser.add_argument("--min-correspondence-confidence", type=float, default=0.30)
    parser.add_argument("--max-condition-number", type=float, default=1.0e8)
    parser.add_argument("--max-reprojection-error", type=float, default=20.0)
    parser.add_argument("--max-temporal-jump", type=float, default=0.18)
    parser.add_argument("--min-player-inside-ratio", type=float, default=0.60)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    adapter = _build_adapter(args)
    if args.command == "inspect-environment":
        print(json.dumps(adapter.inspect_environment(), indent=2))
        return 0
    try:
        if args.command == "benchmark":
            return _benchmark(args, adapter)
        config = _config(args, args.output)
        run = PitchCalibrationRunner(adapter).run(args.source, config)
        _print_run(run)
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"VE-005 pitch-calibration error: {exc}", file=sys.stderr)
        return 2


def _benchmark(args: argparse.Namespace, adapter: CalibrationAdapter) -> int:
    output = args.output.resolve()
    runner = PitchCalibrationRunner(adapter)
    professional = runner.run(
        args.professional,
        CalibrationConfig(
            output_dir=output / "professional",
            sample_interval_seconds=args.sample_interval,
            maximum_frames=args.maximum_frames,
            camera_profile=args.camera_profile,
            random_seed=args.seed,
            **_quality_values(args),
        ),
    )
    amateur = runner.run(
        args.amateur,
        CalibrationConfig(
            output_dir=output / "amateur",
            sample_interval_seconds=args.sample_interval,
            maximum_frames=args.maximum_frames,
            camera_profile=args.camera_profile,
            random_seed=args.seed,
            **_quality_values(args),
        ),
    )
    combined = {
        "schema_version": "matchiq.ve-005b.combined-benchmark.v1",
        "professional": _run_summary(professional),
        "amateur": _run_summary(amateur),
    }
    write_json(combined, output / "combined_benchmark_summary.json")
    print(json.dumps(combined, indent=2))
    return 0


def _config(args: argparse.Namespace, output: Path) -> CalibrationConfig:
    return CalibrationConfig(
        output_dir=output,
        sample_interval_seconds=args.sample_interval,
        maximum_frames=args.maximum_frames,
        physical_pitch_length=args.physical_length,
        physical_pitch_width=args.physical_width,
        render_debug=not args.no_debug,
        camera_profile=args.camera_profile,
        random_seed=args.seed,
        keyframe_frequency=args.keyframe_frequency,
        **_quality_values(args),
    )


def _quality_values(args: argparse.Namespace) -> dict[str, float]:
    return {
        "minimum_model_confidence": args.min_model_confidence,
        "minimum_geometric_confidence": args.min_geometric_confidence,
        "minimum_projection_confidence": args.min_projection_confidence,
        "minimum_evidence_confidence": args.min_evidence_confidence,
        "minimum_correspondence_confidence": args.min_correspondence_confidence,
        "maximum_condition_number": args.max_condition_number,
        "maximum_reprojection_error_px": args.max_reprojection_error,
        "maximum_temporal_corner_jump": args.max_temporal_jump,
        "minimum_projected_player_inside_ratio": args.min_player_inside_ratio,
    }


def _build_adapter(args: argparse.Namespace) -> CalibrationAdapter:
    if args.adapter == "matchiq-hybrid":
        return MatchIQHybridAdapter(
            physical_length=getattr(args, "physical_length", None),
            physical_width=getattr(args, "physical_width", None),
            camera_profile=args.camera_profile,
            seed=args.seed,
            minimum_hypothesis_score=args.min_hypothesis_score,
            minimum_line_support=args.min_line_support,
        )
    return TVCalibAdapter(
        timeout_seconds=args.timeout,
        upstream_root=args.upstream_root,
        checkpoint=args.checkpoint,
    )


def _run_summary(run: object) -> dict[str, object]:
    manifest = run.manifest
    return {
        "manifest": str(run.manifest_path),
        "frames": manifest["aggregate"]["frames_processed"],
        "status_distribution": manifest["aggregate"]["status_distribution"],
        "projected_observations": manifest["aggregate"]["projected_observations"],
    }


def _print_run(run: object) -> None:
    print(f"Calibration manifest: {run.manifest_path}")
    print(f"Projected tracks: {run.projected_tracks_path}")
    print(f"Benchmark summary: {run.benchmark_path}")
    print(f"HTML report: {run.html_path}")
    if run.evidence_path:
        print(f"Evidence manifest: {run.evidence_path}")
    if run.correspondence_path:
        print(f"Correspondence manifest: {run.correspondence_path}")
