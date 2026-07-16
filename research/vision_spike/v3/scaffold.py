from __future__ import annotations

import argparse
import json
from pathlib import Path

from .paths import DatasetPaths, assert_external_dataset_path


def create_scaffold(dataset_root: Path, repository_root: Path | None = None) -> DatasetPaths:
    paths = DatasetPaths.from_root(dataset_root)
    if repository_root is not None:
        assert_external_dataset_path(paths.root, repository_root)
    paths.initialize()
    if not paths.source_registry.exists():
        paths.source_registry.write_text(
            json.dumps({"schema_version": 1, "sources": []}, indent=2),
            encoding="utf-8",
        )
    readme = paths.root / "README_LOCAL_ONLY.txt"
    if not readme.exists():
        readme.write_text(
            "MatchIQ Vision Engine V3 local dataset. Do not commit, upload, or redistribute.\n",
            encoding="utf-8",
        )
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create an external local MatchIQ V3 dataset scaffold.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--repository-root", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = create_scaffold(args.dataset, args.repository_root)
    print(paths.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
