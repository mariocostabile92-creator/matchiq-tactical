from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def make_clip(input_path: Path, output_path: Path, *, start_seconds: float, duration_seconds: float) -> Path:
    if not input_path.is_file():
        raise ValueError(f"input video not found: {input_path}")
    if start_seconds < 0 or duration_seconds <= 0:
        raise ValueError("start must be non-negative and duration must be positive")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(start_seconds),
        "-i",
        str(input_path),
        "-t",
        str(duration_seconds),
        "-map",
        "0:v:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        str(output_path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is not installed or is not available on PATH") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {completed.stderr.strip() or 'unknown error'}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("ffmpeg completed without producing a readable clip")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a local test clip for the Vision Spike.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--start-seconds", type=float, default=0.0)
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)
    try:
        path = make_clip(
            args.input,
            args.output,
            start_seconds=args.start_seconds,
            duration_seconds=args.duration_seconds,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Clip creation failed: {exc}")
        return 2
    print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
