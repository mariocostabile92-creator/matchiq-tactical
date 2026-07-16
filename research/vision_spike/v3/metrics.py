from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from . import CLASS_NAMES


def iou_xyxy(first: Iterable[float], second: Iterable[float]) -> float:
    ax1, ay1, ax2, ay2 = (float(value) for value in first)
    bx1, by1, bx2, by2 = (float(value) for value in second)
    width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    height = max(0.0, min(ay2, by2) - max(ay1, by1))
    intersection = width * height
    first_area = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    second_area = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = first_area + second_area - intersection
    return intersection / union if union > 0 else 0.0


def coco_to_xyxy(box: Iterable[float]) -> tuple[float, float, float, float]:
    x, y, width, height = (float(value) for value in box)
    return x, y, x + width, y + height


@dataclass(frozen=True, slots=True)
class MatchResult:
    true_positive: int
    false_positive: int
    false_negative: int
    scores: tuple[tuple[float, int], ...]


def match_class(
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    iou_threshold: float,
) -> MatchResult:
    by_image: dict[int, list[tuple[int, tuple[float, float, float, float]]]] = defaultdict(list)
    for index, item in enumerate(ground_truth):
        box = item.get("bbox_xyxy") or coco_to_xyxy(item["bbox"])
        by_image[int(item["image_id"])].append((index, tuple(float(value) for value in box)))
    matched: set[int] = set()
    ranked = sorted(predictions, key=lambda item: float(item.get("score", 0.0)), reverse=True)
    score_labels: list[tuple[float, int]] = []
    for prediction in ranked:
        image_id = int(prediction["image_id"])
        box = prediction.get("bbox_xyxy") or coco_to_xyxy(prediction["bbox"])
        options = [
            (iou_xyxy(box, truth_box), truth_index)
            for truth_index, truth_box in by_image.get(image_id, [])
            if truth_index not in matched
        ]
        best_iou, best_index = max(options, default=(0.0, -1))
        is_match = best_iou >= iou_threshold
        if is_match:
            matched.add(best_index)
        score_labels.append((float(prediction.get("score", 0.0)), int(is_match)))
    true_positive = sum(label for _, label in score_labels)
    return MatchResult(true_positive, len(score_labels) - true_positive, len(ground_truth) - true_positive, tuple(score_labels))


def average_precision(score_labels: Iterable[tuple[float, int]], positives: int) -> float:
    if positives <= 0:
        return 0.0
    ranked = sorted(score_labels, reverse=True)
    true_positive = 0
    precisions: list[float] = []
    recalls: list[float] = []
    for index, (_, label) in enumerate(ranked, 1):
        true_positive += label
        precisions.append(true_positive / index)
        recalls.append(true_positive / positives)
    interpolated = 0.0
    for step in range(101):
        threshold = step / 100
        interpolated += max((precision for precision, recall in zip(precisions, recalls) if recall >= threshold), default=0.0)
    return interpolated / 101


def evaluate_detection_metrics(
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    class_names: Iterable[str] = CLASS_NAMES,
) -> dict[str, Any]:
    per_class: dict[str, Any] = {}
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    ap50_values: list[float] = []
    ap_values: list[float] = []
    for class_name in class_names:
        truth = [item for item in ground_truth if item["class_name"] == class_name and not item.get("ignore")]
        predicted = [item for item in predictions if item["class_name"] == class_name]
        at_50 = match_class(truth, predicted, iou_threshold=0.5)
        precision = at_50.true_positive / max(1, at_50.true_positive + at_50.false_positive)
        recall = at_50.true_positive / max(1, at_50.true_positive + at_50.false_negative)
        ap50 = average_precision(at_50.scores, len(truth))
        threshold_aps = []
        for index in range(10):
            threshold = 0.5 + 0.05 * index
            matched = match_class(truth, predicted, iou_threshold=threshold)
            threshold_aps.append(average_precision(matched.scores, len(truth)))
        ap5095 = sum(threshold_aps) / len(threshold_aps)
        per_class[class_name] = {
            "ground_truth": len(truth), "predictions": len(predicted),
            "true_positive": at_50.true_positive, "false_positive": at_50.false_positive,
            "false_negative": at_50.false_negative, "precision": round(precision, 6),
            "recall": round(recall, 6), "ap50": round(ap50, 6), "ap50_95": round(ap5095, 6),
        }
        if truth:
            ap50_values.append(ap50)
            ap_values.append(ap5095)
        confusion[class_name][class_name] += at_50.true_positive
        confusion[class_name]["missed"] += at_50.false_negative
        confusion["background"][class_name] += at_50.false_positive
    small_truth = [item for item in ground_truth if float(item.get("area", 0)) < 32**2]
    small_predictions = [item for item in predictions if float(item.get("area", 0)) < 32**2]
    small_result = match_class(small_truth, small_predictions, iou_threshold=0.5)
    return {
        "map50": round(sum(ap50_values) / len(ap50_values), 6) if ap50_values else 0.0,
        "map50_95": round(sum(ap_values) / len(ap_values), 6) if ap_values else 0.0,
        "per_class": per_class,
        "ball": per_class.get("ball", {}),
        "small_objects": {
            "ground_truth": len(small_truth), "true_positive": small_result.true_positive,
            "false_positive": small_result.false_positive, "false_negative": small_result.false_negative,
            "recall": round(small_result.true_positive / max(1, len(small_truth)), 6),
        },
        "confusion_matrix": {name: dict(values) for name, values in confusion.items()},
    }


def evaluate_by_scene(
    ground_truth: list[dict[str, Any]], predictions: list[dict[str, Any]], image_metadata: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    buckets: dict[str, set[int]] = defaultdict(set)
    for image_id, metadata in image_metadata.items():
        for field in ("camera_type", "lighting", "quality"):
            buckets[f"{field}:{metadata.get(field, 'unknown')}"] .add(image_id)
        if metadata.get("staff_public_visible"):
            buckets["staff_public_visible:true"].add(image_id)
    return {
        name: evaluate_detection_metrics(
            [item for item in ground_truth if int(item["image_id"]) in ids],
            [item for item in predictions if int(item["image_id"]) in ids],
        )
        for name, ids in sorted(buckets.items())
    }
