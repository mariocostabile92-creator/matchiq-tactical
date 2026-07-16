from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .annotation_schema import coco_categories
from .coco import load_coco, write_coco
from .manifest import read_jsonl, write_jsonl
from .paths import DatasetPaths


SPLIT_NAMES = ("train", "val", "test")


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def assign_matches(
    match_sizes: dict[str, int],
    *,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, str]:
    if not match_sizes:
        return {}
    if train_ratio <= 0 or val_ratio < 0 or train_ratio + val_ratio >= 1:
        raise ValueError("ratios must leave a positive test split")
    matches = sorted(match_sizes)
    random.Random(seed).shuffle(matches)
    targets = {
        "train": sum(match_sizes.values()) * train_ratio,
        "val": sum(match_sizes.values()) * val_ratio,
        "test": sum(match_sizes.values()) * (1.0 - train_ratio - val_ratio),
    }
    result: dict[str, str] = {}
    assigned = Counter()
    for match_id in sorted(matches, key=lambda item: (-match_sizes[item], matches.index(item))):
        split = max(SPLIT_NAMES, key=lambda name: targets[name] - assigned[name])
        result[match_id] = split
        assigned[split] += match_sizes[match_id]
    if len(matches) >= 3:
        missing = [name for name in SPLIT_NAMES if name not in result.values()]
        donors = sorted(SPLIT_NAMES, key=lambda name: sum(value == name for value in result.values()), reverse=True)
        for split in missing:
            donor = next(name for name in donors if sum(value == name for value in result.values()) > 1)
            candidate = min((item for item, value in result.items() if value == donor), key=lambda item: match_sizes[item])
            result[candidate] = split
    return result


def _resolve_source(paths: DatasetPaths, file_name: str) -> Path:
    normalized = Path(file_name.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError(f"unsafe image path: {file_name}")
    for candidate in (paths.root / normalized, paths.extracted / normalized.name):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"image not found: {file_name}")


def _link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def split_dataset(
    dataset_root: Path,
    *,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42,
    materialize: bool = True,
) -> dict[str, Any]:
    paths = DatasetPaths.from_root(dataset_root)
    frames = read_jsonl(paths.frame_manifest)
    coco = load_coco(paths.canonical_annotations)
    frame_by_name = {Path(str(row.get("file_name", ""))).name: row for row in frames}
    image_match: dict[int, str] = {}
    match_sizes: Counter[str] = Counter()
    for image in coco["images"]:
        name = Path(str(image.get("file_name", ""))).name
        metadata = image.get("metadata") if isinstance(image.get("metadata"), dict) else {}
        frame = frame_by_name.get(name, {})
        match_id = str(metadata.get("match_id") or frame.get("match_id") or metadata.get("video_id") or frame.get("video_id") or "")
        if not match_id:
            raise ValueError(f"missing match_id/video_id for image {name}")
        image_id = int(image["id"])
        image_match[image_id] = match_id
        match_sizes[match_id] += 1
    assignments = assign_matches(dict(match_sizes), train_ratio=train_ratio, val_ratio=val_ratio, seed=seed)
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    image_split: dict[int, str] = {}
    for image in coco["images"]:
        image_id = int(image["id"])
        split = assignments[image_match[image_id]]
        image["split"] = split
        metadata = image.setdefault("metadata", {})
        metadata["split"] = split
        by_split[split].append(image)
        image_split[image_id] = split
    for row in frames:
        match_id = str(row.get("match_id") or row.get("video_id") or "")
        if match_id in assignments:
            row["split"] = assignments[match_id]
    write_jsonl(paths.frame_manifest, frames)
    write_coco(paths.canonical_annotations, coco)

    split_payloads: dict[str, dict[str, Any]] = {}
    for split in SPLIT_NAMES:
        images = by_split.get(split, [])
        ids = {int(item["id"]) for item in images}
        split_payloads[split] = {
            "info": dict(coco.get("info", {}), split=split),
            "licenses": coco.get("licenses", []),
            "categories": coco_categories(),
            "images": images,
            "annotations": [item for item in coco["annotations"] if int(item.get("image_id", -1)) in ids],
        }

    export_root = paths.cache / "rfdetr_dataset"
    if materialize:
        directory_names = {"train": "train", "val": "valid", "test": "test"}
        for split, payload in split_payloads.items():
            destination = export_root / directory_names[split]
            destination.mkdir(parents=True, exist_ok=True)
            for image in payload["images"]:
                source = _resolve_source(paths, str(image["file_name"]))
                target = destination / source.name
                _link_or_copy(source, target)
                image["file_name"] = source.name
            write_coco(destination / "_annotations.coco.json", payload)

    frozen_test = {
        "seed": seed,
        "match_ids": sorted(match_id for match_id, split in assignments.items() if split == "test"),
        "image_ids": sorted(image_id for image_id, split in image_split.items() if split == "test"),
    }
    frozen_test["sha256"] = _stable_hash(frozen_test)
    manifest = {
        "seed": seed,
        "ratios": {"train": train_ratio, "val": val_ratio, "test": 1.0 - train_ratio - val_ratio},
        "assignments": dict(sorted(assignments.items())),
        "image_counts": {split: len(split_payloads[split]["images"]) for split in SPLIT_NAMES},
        "annotation_counts": {split: len(split_payloads[split]["annotations"]) for split in SPLIT_NAMES},
        "frozen_test": frozen_test,
        "rfdetr_export": str(export_root.name) if materialize else None,
    }
    paths.split_manifest.parent.mkdir(parents=True, exist_ok=True)
    paths.split_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Split MatchIQ V3 data by complete match and prepare RF-DETR COCO folders.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-materialize", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = split_dataset(
        args.dataset,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
        materialize=not args.no_materialize,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
