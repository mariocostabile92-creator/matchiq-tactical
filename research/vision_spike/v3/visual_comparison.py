from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..utils import require_cv2_numpy


CLASS_STYLE = {
    "player": ((0, 220, 80), "PLAYER"),
    "goalkeeper": ((0, 190, 255), "GOALKEEPER"),
    "referee": ((220, 100, 255), "REFEREE"),
    "ball": ((40, 40, 255), "BALL"),
    "person": ((255, 170, 30), "COCO PERSON"),
}


def draw_detections(frame: Any, detections: list[dict[str, Any]], *, timestamp: str = "") -> Any:
    cv2, _ = require_cv2_numpy()
    output = frame.copy()
    for item in detections:
        name = str(item.get("class_name", "unknown"))
        color, label = CLASS_STYLE.get(name, ((200, 200, 200), name.upper()))
        x1, y1, x2, y2 = (int(round(float(value))) for value in item["bbox_xyxy"])
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        suffix = f" {float(item.get('confidence', item.get('score', 0))):.2f}"
        track = item.get("track_id")
        if track is not None:
            suffix += f" ID {track}"
        cv2.putText(output, label + suffix, (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2, cv2.LINE_AA)
    cv2.rectangle(output, (0, 0), (output.shape[1], 30), (4, 13, 29), -1)
    legend = " | ".join(value[1] for value in CLASS_STYLE.values())
    cv2.putText(output, f"{timestamp}  {legend}", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    return output


def comparison_sheet(original: Any, coco: Any, football: Any, destination: Path) -> None:
    cv2, np = require_cv2_numpy()
    height = min(original.shape[0], coco.shape[0], football.shape[0])
    panels = []
    for label, frame in (("ORIGINALE", original), ("COCO", coco), ("FOOTBALL V3", football)):
        resized = cv2.resize(frame, (int(frame.shape[1] * height / frame.shape[0]), height))
        cv2.rectangle(resized, (0, 0), (resized.shape[1], 44), (4, 13, 29), -1)
        cv2.putText(resized, label, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)
        panels.append(resized)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination), np.hstack(panels), [int(cv2.IMWRITE_JPEG_QUALITY), 92])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an ORIGINALE | COCO | FOOTBALL V3 comparison sheet.")
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--coco", required=True, type=Path)
    parser.add_argument("--football", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cv2, _ = require_cv2_numpy()
    frames = [cv2.imread(str(path)) for path in (args.original, args.coco, args.football)]
    if any(frame is None for frame in frames):
        raise ValueError("all comparison images must be readable")
    comparison_sheet(*frames, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
