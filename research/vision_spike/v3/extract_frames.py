from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from ..pitch_detector import PitchDetector
from ..utils import require_cv2_numpy, sha256_file
from .image_quality import (
    blur_score,
    difference_hash,
    infer_lighting,
    infer_quality,
    is_near_duplicate,
    mean_luma,
)
from .manifest import FrameRecord, append_unique_records
from .paths import DatasetPaths


def anonymous_video_id(source_sha256: str) -> str:
    return f"video-{source_sha256[:16]}"


def safe_origin(value: str) -> str:
    normalized = value.strip() or "unverified"
    if ":\\" in normalized or normalized.startswith(("/", "\\")):
        raise ValueError("authorization origin must be a reference, not a personal file path")
    return normalized


def extract_frames(
    *,
    input_video: Path,
    output_dir: Path,
    source_id: str,
    every_seconds: float = 3.0,
    max_frames: int = 150,
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
    min_blur: float = 35.0,
    min_luma: float = 12.0,
    max_luma: float = 245.0,
    duplicate_hamming: int = 4,
    duplicate_window: int = 12,
    wide_only: bool = False,
    min_tactical_score: float = 0.3,
    camera_type: str = "unknown",
    lighting: str = "auto",
    quality: str = "auto",
    authorization_origin: str = "unverified",
    split: str = "unassigned",
    match_id: str = "",
) -> dict:
    if not input_video.is_file():
        raise ValueError(f"input video not found: {input_video}")
    if every_seconds <= 0:
        raise ValueError("every_seconds must be positive")
    if max_frames < 1:
        raise ValueError("max_frames must be positive")
    if split not in {"unassigned", "train", "val", "test"}:
        raise ValueError(f"unsupported split: {split}")
    authorization_origin = safe_origin(authorization_origin)
    output_dir.mkdir(parents=True, exist_ok=True)
    cv2, _ = require_cv2_numpy()
    source_hash = sha256_file(input_video)
    video_id = anonymous_video_id(source_hash)
    capture = cv2.VideoCapture(str(input_video))
    if not capture.isOpened():
        raise ValueError(f"cannot open local video: {input_video.name}")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / source_fps if source_fps > 0 else 0.0
    stop_at = min(duration, end_seconds) if end_seconds is not None and duration else end_seconds or duration
    pitch_detector = PitchDetector()
    accepted: list[FrameRecord] = []
    recent_hashes: list[int] = []
    counters = {
        "sampled": 0,
        "accepted": 0,
        "black_or_overexposed": 0,
        "blurred": 0,
        "near_duplicate": 0,
        "not_wide": 0,
        "read_failed": 0,
    }
    timestamp = max(0.0, start_seconds)
    try:
        while len(accepted) < max_frames and (not stop_at or timestamp <= stop_at):
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
            ok, frame = capture.read()
            if not ok or frame is None:
                counters["read_failed"] += 1
                break
            counters["sampled"] += 1
            frame_index = int(round(timestamp * source_fps)) if source_fps > 0 else counters["sampled"] - 1
            luma = mean_luma(frame)
            if luma < min_luma or luma > max_luma:
                counters["black_or_overexposed"] += 1
                timestamp += every_seconds
                continue
            sharpness = blur_score(frame)
            if sharpness < min_blur:
                counters["blurred"] += 1
                timestamp += every_seconds
                continue
            frame_hash = difference_hash(frame)
            if is_near_duplicate(frame_hash, recent_hashes, duplicate_hamming):
                counters["near_duplicate"] += 1
                timestamp += every_seconds
                continue
            pitch = pitch_detector.analyze(frame, include_mask=False)
            if wide_only and pitch.tactical_view_score < min_tactical_score:
                counters["not_wide"] += 1
                timestamp += every_seconds
                continue
            digest = hashlib.sha256(
                f"{source_hash}:{frame_index}:{timestamp:.3f}".encode("ascii")
            ).hexdigest()
            frame_id = f"frame-{digest[:20]}"
            filename = f"{frame_id}.jpg"
            destination = output_dir / filename
            if not cv2.imwrite(str(destination), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 94]):
                raise OSError(f"cannot write extracted frame: {filename}")
            record = FrameRecord(
                frame_id=frame_id,
                file_name=filename,
                video_id=video_id,
                source_id=source_id,
                source_file_name=input_video.name,
                source_sha256=source_hash,
                frame_sha256=sha256_file(destination),
                timestamp_seconds=round(timestamp, 3),
                frame_index=frame_index,
                width=int(frame.shape[1]),
                height=int(frame.shape[0]),
                source_fps=round(source_fps, 6),
                camera_type=camera_type,
                quality=infer_quality(width, height) if quality == "auto" else quality,
                lighting=infer_lighting(luma) if lighting == "auto" else lighting,
                authorization_origin=authorization_origin,
                split=split,
                blur_score=round(sharpness, 4),
                mean_luma=round(luma, 4),
                green_ratio=round(pitch.green_ratio, 6),
                tactical_view_score=round(pitch.tactical_view_score, 6),
                match_id=match_id or video_id,
            )
            accepted.append(record)
            counters["accepted"] += 1
            recent_hashes.append(frame_hash)
            recent_hashes = recent_hashes[-max(1, duplicate_window) :]
            timestamp += every_seconds
    finally:
        capture.release()
    manifest_path = output_dir / "manifest.json"
    manifest_payload = {
        "schema_version": 1,
        "video_id": video_id,
        "source_id": source_id,
        "source_file_name": input_video.name,
        "source_sha256": source_hash,
        "source_fps": source_fps,
        "source_resolution": [width, height],
        "duration_seconds": round(duration, 3),
        "authorization_origin": authorization_origin,
        "sampling": {
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "every_seconds": every_seconds,
            "max_frames": max_frames,
            "min_blur": min_blur,
            "min_luma": min_luma,
            "max_luma": max_luma,
            "duplicate_hamming": duplicate_hamming,
            "wide_only": wide_only,
            "min_tactical_score": min_tactical_score,
        },
        "counters": counters,
        "frames": [record.to_dict() for record in accepted],
        "privacy_note": "No absolute input path is stored.",
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    return manifest_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract authorized local football frames for MatchIQ V3.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dataset", type=Path, help="Optional external V3 dataset root for manifest registration.")
    parser.add_argument("--source-id", default="unapproved-local-source")
    parser.add_argument("--authorization-origin", default="unverified")
    parser.add_argument("--every-seconds", type=float, default=3.0)
    parser.add_argument("--max-frames", type=int, default=150)
    parser.add_argument("--start-seconds", type=float, default=0.0)
    parser.add_argument("--end-seconds", type=float)
    parser.add_argument("--min-blur", type=float, default=35.0)
    parser.add_argument("--min-luma", type=float, default=12.0)
    parser.add_argument("--max-luma", type=float, default=245.0)
    parser.add_argument("--duplicate-hamming", type=int, default=4)
    parser.add_argument("--wide-only", action="store_true")
    parser.add_argument("--min-tactical-score", type=float, default=0.3)
    parser.add_argument("--camera-type", default="unknown")
    parser.add_argument("--lighting", default="auto")
    parser.add_argument("--quality", default="auto")
    parser.add_argument("--match-id", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = extract_frames(
        input_video=args.input,
        output_dir=args.output,
        source_id=args.source_id,
        every_seconds=args.every_seconds,
        max_frames=args.max_frames,
        start_seconds=args.start_seconds,
        end_seconds=args.end_seconds,
        min_blur=args.min_blur,
        min_luma=args.min_luma,
        max_luma=args.max_luma,
        duplicate_hamming=args.duplicate_hamming,
        wide_only=args.wide_only,
        min_tactical_score=args.min_tactical_score,
        camera_type=args.camera_type,
        lighting=args.lighting,
        quality=args.quality,
        authorization_origin=args.authorization_origin,
        match_id=args.match_id,
    )
    if args.dataset:
        paths = DatasetPaths.from_root(args.dataset)
        paths.initialize()
        records = [FrameRecord.from_dict(item) for item in result["frames"]]
        append_unique_records(paths.frame_manifest, records)
    print(json.dumps({"status": "completed", "frames": result["counters"]["accepted"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
