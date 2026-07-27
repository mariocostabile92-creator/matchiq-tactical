from __future__ import annotations

import argparse
from pathlib import Path

from .runner import BaselineRunConfig, BaselineRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matchiq-ve-001",
        description="Measure the current MatchIQ static-frame Video AI pipeline.",
    )
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/vision-baseline"))
    parser.add_argument("--focus", default="Analisi tattica generale")
    parser.add_argument("--desired-count", type=int, default=6)
    parser.add_argument("--observed-team", default="")
    parser.add_argument("--home-team", default="")
    parser.add_argument("--away-team", default="")
    parser.add_argument("--home-formation", default="")
    parser.add_argument("--away-formation", default="")
    parser.add_argument("--lineup-notes", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.desired_count < 2:
        print("VE-001 failed: --desired-count deve essere almeno 2")
        return 2
    context = {
        "observed_team": args.observed_team,
        "home_team": args.home_team,
        "away_team": args.away_team,
        "home_formation": args.home_formation,
        "away_formation": args.away_formation,
        "lineup_notes": args.lineup_notes,
    }
    try:
        result = BaselineRunner().run(
            BaselineRunConfig(
                video_path=args.video,
                output_dir=args.output,
                focus=args.focus,
                desired_count=args.desired_count,
                context=context,
            )
        )
    except (ValueError, RuntimeError) as exc:
        print(f"VE-001 failed: {exc}")
        return 2
    print(f"JSON: {result.json_path.resolve()}")
    print(f"HTML: {result.html_path.resolve()}")
    print(f"Candidate: {result.report['pipeline_statistics']['candidates_found']}")
    print(f"Tempo totale: {result.report['performance']['total_processing_seconds']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
