from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .contracts import TeamAssignmentConfig
from .runner import TeamAssignmentRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="VE-003: assign existing VE-002 player detections to anonymous color teams.",
    )
    parser.add_argument("--manifest", required=True, type=Path, help="VE-002 player_detection_manifest.json")
    parser.add_argument("--output", required=True, type=Path, help="Output directory for VE-003 reports")
    parser.add_argument(
        "--minimum-confidence",
        type=float,
        default=0.20,
        help="Minimum team assignment confidence before returning UNKNOWN",
    )
    parser.add_argument(
        "--minimum-separation",
        type=float,
        default=0.18,
        help="Minimum distance between the two color cluster centers",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0.0 <= args.minimum_confidence <= 1.0:
        raise SystemExit("--minimum-confidence must be between 0 and 1")
    if args.minimum_separation < 0.0:
        raise SystemExit("--minimum-separation must be non-negative")

    run = TeamAssignmentRunner().run_manifest(
        args.manifest,
        TeamAssignmentConfig(
            output_dir=args.output,
            minimum_team_confidence=args.minimum_confidence,
            minimum_cluster_separation=args.minimum_separation,
        ),
    )
    print(f"VE-003 JSON: {run.manifest_path}")
    print(f"VE-003 HTML: {run.html_path}")
    print(
        "Assignments: "
        f"A={run.manifest['aggregate']['team_a']} "
        f"B={run.manifest['aggregate']['team_b']} "
        f"UNKNOWN={run.manifest['aggregate']['unknown']}"
    )
    return 0
