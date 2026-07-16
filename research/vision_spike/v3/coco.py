from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .annotation_schema import empty_coco_dataset, validate_category_schema


def load_coco(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"COCO annotations not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("COCO annotation root must be an object")
    for key in ("images", "annotations", "categories"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"COCO annotations require a '{key}' list")
    return payload


def write_coco(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def ensure_canonical_coco(path: Path) -> dict[str, Any]:
    if path.is_file():
        return load_coco(path)
    payload = empty_coco_dataset()
    write_coco(path, payload)
    return payload


def group_annotations(payload: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for annotation in payload.get("annotations", []):
        try:
            result[int(annotation["image_id"])].append(annotation)
        except (KeyError, TypeError, ValueError):
            continue
    return dict(result)


def bbox_iou_coco(first: Iterable[float], second: Iterable[float]) -> float:
    ax, ay, aw, ah = (float(value) for value in first)
    bx, by, bw, bh = (float(value) for value in second)
    ax2, ay2, bx2, by2 = ax + aw, ay + ah, bx + bw, by + bh
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    intersection = iw * ih
    union = max(0.0, aw * ah) + max(0.0, bw * bh) - intersection
    return intersection / union if union > 0 else 0.0


def validate_bbox(bbox: Any, width: int, height: int) -> list[str]:
    if not isinstance(bbox, list) or len(bbox) != 4:
        return ["bbox must be [x, y, width, height]"]
    try:
        x, y, box_width, box_height = (float(value) for value in bbox)
    except (TypeError, ValueError):
        return ["bbox values must be numeric"]
    if not all(math.isfinite(value) for value in (x, y, box_width, box_height)):
        return ["bbox values must be finite"]
    errors: list[str] = []
    if x < 0 or y < 0:
        errors.append("bbox origin cannot be negative")
    if box_width <= 0 or box_height <= 0:
        errors.append("bbox width and height must be positive")
    if x + box_width > width + 0.5 or y + box_height > height + 0.5:
        errors.append("bbox exceeds image bounds")
    return errors


def validate_coco_structure(payload: dict[str, Any]) -> list[str]:
    errors = validate_category_schema(payload.get("categories", []))
    image_ids: set[int] = set()
    annotation_ids: set[int] = set()
    for image in payload.get("images", []):
        try:
            image_id = int(image["id"])
        except (KeyError, TypeError, ValueError):
            errors.append("every image requires a unique integer id")
            continue
        if image_id in image_ids:
            errors.append(f"duplicate image id: {image_id}")
        image_ids.add(image_id)
    category_ids = {int(item["id"]) for item in payload.get("categories", []) if "id" in item}
    for annotation in payload.get("annotations", []):
        try:
            annotation_id = int(annotation["id"])
            image_id = int(annotation["image_id"])
            category_id = int(annotation["category_id"])
        except (KeyError, TypeError, ValueError):
            errors.append("every annotation requires integer id, image_id, and category_id")
            continue
        if annotation_id in annotation_ids:
            errors.append(f"duplicate annotation id: {annotation_id}")
        annotation_ids.add(annotation_id)
        if image_id not in image_ids:
            errors.append(f"orphan annotation {annotation_id}: missing image {image_id}")
        if category_id not in category_ids:
            errors.append(f"annotation {annotation_id}: unknown category {category_id}")
    return errors
