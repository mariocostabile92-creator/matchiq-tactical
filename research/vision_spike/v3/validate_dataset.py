from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..utils import require_cv2_numpy
from . import CATEGORY_IDS, CLASS_NAMES, DATASET_VERSION
from .coco import bbox_iou_coco, group_annotations, load_coco, validate_bbox, validate_coco_structure
from .licenses import load_source_registry, source_index
from .manifest import FrameRecord, read_jsonl
from .paths import DatasetPaths


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    image_id: int | None = None
    annotation_id: int | None = None


def resolve_image_path(paths: DatasetPaths, image: dict[str, Any]) -> Path | None:
    file_name = str(image.get("file_name", "")).replace("\\", "/")
    if not file_name or Path(file_name).is_absolute() or ".." in Path(file_name).parts:
        return None
    candidates = [paths.root / file_name, paths.extracted / Path(file_name).name]
    split = str(image.get("split", ""))
    if split in {"train", "val", "test"}:
        candidates.append(paths.image_split(split) / Path(file_name).name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _draw_contact_sheet(
    destination: Path,
    rows: list[tuple[Path, dict[str, Any], list[dict[str, Any]]]],
    category_names: dict[int, str],
    *,
    seed: int,
) -> None:
    if not rows:
        return
    cv2, np = require_cv2_numpy()
    sampled = list(rows)
    random.Random(seed).shuffle(sampled)
    sampled = sampled[:16]
    panels = []
    for path, image, annotations in sampled:
        frame = cv2.imread(str(path))
        if frame is None:
            continue
        for annotation in annotations:
            x, y, width, height = (int(round(float(value))) for value in annotation.get("bbox", [0, 0, 0, 0]))
            name = category_names.get(int(annotation.get("category_id", -1)), "unknown")
            cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 240, 160), 2)
            cv2.putText(frame, name, (x, max(18, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 34), (4, 13, 29), -1)
        cv2.putText(frame, Path(str(image.get("file_name", ""))).name[:42], (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.47, (255, 255, 255), 1, cv2.LINE_AA)
        panels.append(cv2.resize(frame, (360, 203), interpolation=cv2.INTER_AREA))
    if not panels:
        return
    blank = np.zeros_like(panels[0])
    while len(panels) % 4:
        panels.append(blank.copy())
    sheet = np.vstack([np.hstack(panels[index : index + 4]) for index in range(0, len(panels), 4)])
    destination.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 90])


def validate_dataset(dataset_root: Path, *, seed: int = 42) -> dict[str, Any]:
    paths = DatasetPaths.from_root(dataset_root)
    paths.initialize()
    issues: list[ValidationIssue] = []
    try:
        coco = load_coco(paths.canonical_annotations)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        coco = {"images": [], "annotations": [], "categories": []}
        issues.append(ValidationIssue("critical", "coco_unavailable", str(exc)))
    for message in validate_coco_structure(coco):
        issues.append(ValidationIssue("critical", "coco_structure", message))

    frame_rows = read_jsonl(paths.frame_manifest)
    frame_by_name = {Path(str(item.get("file_name", ""))).name: item for item in frame_rows}
    try:
        sources = source_index(load_source_registry(paths.source_registry))
    except (ValueError, json.JSONDecodeError) as exc:
        sources = {}
        issues.append(ValidationIssue("critical", "source_registry", str(exc)))

    images = coco.get("images", [])
    annotations = coco.get("annotations", [])
    grouped = group_annotations(coco)
    category_names = {int(item["id"]): str(item["name"]) for item in coco.get("categories", []) if "id" in item and "name" in item}
    class_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    camera_counts: Counter[str] = Counter()
    lighting_counts: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    match_splits: dict[str, set[str]] = defaultdict(set)
    image_rows: list[tuple[Path, dict[str, Any], list[dict[str, Any]]]] = []
    exact_hashes: dict[str, str] = {}
    filename_seen: set[str] = set()

    for image in images:
        try:
            image_id = int(image["id"])
            width = int(image["width"])
            height = int(image["height"])
        except (KeyError, TypeError, ValueError):
            issues.append(ValidationIssue("critical", "invalid_image_metadata", "image id/width/height are required"))
            continue
        file_name = Path(str(image.get("file_name", ""))).name
        if file_name in filename_seen:
            issues.append(ValidationIssue("critical", "duplicate_file_name", f"duplicate file_name: {file_name}", image_id))
        filename_seen.add(file_name)
        image_path = resolve_image_path(paths, image)
        if image_path is None:
            issues.append(ValidationIssue("critical", "missing_image", f"image file missing or unsafe: {file_name}", image_id))
            continue
        cv2, _ = require_cv2_numpy()
        frame = cv2.imread(str(image_path))
        if frame is None:
            issues.append(ValidationIssue("critical", "unreadable_image", f"cannot decode image: {file_name}", image_id))
            continue
        actual_height, actual_width = frame.shape[:2]
        if (actual_width, actual_height) != (width, height):
            issues.append(ValidationIssue("critical", "resolution_mismatch", f"COCO size {width}x{height}, file is {actual_width}x{actual_height}", image_id))
        metadata = frame_by_name.get(file_name, image)
        required_metadata = ("video_id", "source_id", "camera_type", "quality", "lighting")
        missing = [field for field in required_metadata if not str(metadata.get(field, "")).strip()]
        if missing:
            issues.append(ValidationIssue("critical", "missing_metadata", f"missing metadata: {', '.join(missing)}", image_id))
        source_id = str(metadata.get("source_id", ""))
        source = sources.get(source_id)
        if source is None:
            issues.append(ValidationIssue("critical", "missing_source", f"source not registered: {source_id or 'empty'}", image_id))
        elif not source.approved_for_v3:
            issues.append(ValidationIssue("critical", "source_not_approved", f"source is not approved for V3 training: {source_id}", image_id))
        split = str(image.get("split", metadata.get("split", "unassigned")))
        split_counts[split] += 1
        camera_counts[str(metadata.get("camera_type", "unknown"))] += 1
        lighting_counts[str(metadata.get("lighting", "unknown"))] += 1
        quality_counts[str(metadata.get("quality", "unknown"))] += 1
        source_counts[source_id or "unknown"] += 1
        match_id = str(metadata.get("match_id") or metadata.get("video_id") or "unknown")
        match_splits[match_id].add(split)
        digest = str(metadata.get("frame_sha256", ""))
        if digest:
            if digest in exact_hashes:
                issues.append(ValidationIssue("critical", "duplicate_image", f"exact duplicate of {exact_hashes[digest]}", image_id))
            exact_hashes[digest] = file_name
        image_annotations = grouped.get(image_id, [])
        is_negative = bool(metadata.get("is_negative", image.get("is_negative", False)))
        if not image_annotations and not is_negative:
            issues.append(ValidationIssue("critical", "empty_unmarked_image", "image has no boxes and is not marked negative", image_id))
        seen_boxes: list[tuple[int, list[float], int]] = []
        for annotation in image_annotations:
            annotation_id = int(annotation.get("id", -1))
            category_id = int(annotation.get("category_id", -1))
            name = category_names.get(category_id, "unknown")
            class_counts[name] += 1
            for message in validate_bbox(annotation.get("bbox"), width, height):
                issues.append(ValidationIssue("critical", "invalid_bbox", message, image_id, annotation_id))
            bbox = annotation.get("bbox", [0, 0, 0, 0])
            if isinstance(bbox, list) and len(bbox) == 4:
                _, _, box_width, box_height = (float(value) for value in bbox)
                area = max(0.0, box_width * box_height)
                if box_width < 4 or box_height < 4 or area < 24:
                    issues.append(ValidationIssue("warning", "tiny_bbox", "box is extremely small; verify difficult object", image_id, annotation_id))
                if area > width * height * 0.9:
                    issues.append(ValidationIssue("warning", "huge_bbox", "box covers more than 90% of image", image_id, annotation_id))
                for previous_category, previous_box, previous_id in seen_boxes:
                    if previous_category == category_id and bbox_iou_coco(previous_box, bbox) >= 0.98:
                        issues.append(ValidationIssue("critical", "duplicate_annotation", f"duplicates annotation {previous_id}", image_id, annotation_id))
                seen_boxes.append((category_id, bbox, annotation_id))
        image_rows.append((image_path, image, image_annotations))

    for match_id, splits in match_splits.items():
        material_splits = splits & {"train", "val", "test"}
        if len(material_splits) > 1:
            issues.append(ValidationIssue("critical", "match_leakage", f"match {match_id} appears in {sorted(material_splits)}"))

    total_images = len(images)
    wide_count = sum(count for key, count in camera_counts.items() if key in {"tactical_wide", "wide", "broadcast_wide"})
    report = {
        "dataset_version": DATASET_VERSION,
        "status": "VALID" if not any(item.severity == "critical" for item in issues) else "INVALID",
        "dataset_root_name": paths.root.name,
        "images": total_images,
        "annotations": len(annotations),
        "matches": len(match_splits),
        "approved_sources": sum(source.approved_for_v3 for source in sources.values()),
        "class_distribution": {name: class_counts.get(name, 0) for name in CLASS_NAMES},
        "split_distribution": dict(sorted(split_counts.items())),
        "camera_distribution": dict(sorted(camera_counts.items())),
        "lighting_distribution": dict(sorted(lighting_counts.items())),
        "quality_distribution": dict(sorted(quality_counts.items())),
        "source_distribution": dict(sorted(source_counts.items())),
        "wide_tactical_percent": round(100.0 * wide_count / total_images, 2) if total_images else 0.0,
        "negative_images": sum(not grouped.get(int(item.get("id", -1)), []) for item in images),
        "critical_errors": sum(item.severity == "critical" for item in issues),
        "warnings": sum(item.severity == "warning" for item in issues),
        "issues": [asdict(item) for item in issues],
    }
    paths.reports.mkdir(parents=True, exist_ok=True)
    (paths.reports / "dataset_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with (paths.reports / "class_distribution.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("class", "annotations"))
        for name in CLASS_NAMES:
            writer.writerow((name, class_counts.get(name, 0)))
    (paths.reports / "warnings.json").write_text(
        json.dumps({"issues": [asdict(item) for item in issues]}, indent=2), encoding="utf-8"
    )
    markdown = [
        "# MatchIQ V3 Dataset Validation",
        "",
        f"- Status: **{report['status']}**",
        f"- Images: {total_images}",
        f"- Matches: {report['matches']}",
        f"- Wide tactical: {report['wide_tactical_percent']}%",
        f"- Critical errors: {report['critical_errors']}",
        f"- Warnings: {report['warnings']}",
        "",
        "## Class distribution",
        "",
    ]
    markdown.extend(f"- {name}: {class_counts.get(name, 0)}" for name in CLASS_NAMES)
    if issues:
        markdown.extend(("", "## Issues", ""))
        markdown.extend(f"- [{item.severity}] {item.code}: {item.message}" for item in issues[:200])
    (paths.reports / "dataset_report.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    _draw_contact_sheet(paths.reports / "contact_sheet.jpg", image_rows, category_names, seed=seed)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate an external MatchIQ V3 football dataset.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_dataset(args.dataset, seed=args.seed)
    print(json.dumps({key: report[key] for key in ("status", "images", "matches", "critical_errors", "warnings")}, indent=2))
    return 0 if report["status"] == "VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
