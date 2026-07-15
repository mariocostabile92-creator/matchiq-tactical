# MatchIQ Vision Engine - Feasibility Spike V0

Research-only local pipeline. It is not imported by MatchIQ Coach AI, exposes no web route,
uses no product database, and sends no video to external services.

## Initial audit

- Product runtime: Python 3.11 on Railway; local test interpreter currently Python 3.14.
- Local video tools: FFmpeg/FFprobe 8.1.1 available.
- Local hardware: NVIDIA RTX 3050 6 GB detected, but V0 is CPU-first and does not use CUDA.
- Product dependencies before the spike: no OpenCV, NumPy, PyTorch, detector, tracker, or model weights.
- Existing repository: no reusable detection code and no committed video/model weights over 25 MB.
- Isolation: all code and dependencies live below `research/vision_spike`.

## Dependency and license decision

| Dependency | Version | License | Use | Commercial note |
|---|---:|---|---|---|
| OpenCV headless | 4.13.0.92 | Apache-2.0 | Video IO, built-in HOG person detector, masks, overlay | Permissive for commercial use; no external model weight is downloaded. |
| NumPy | 2.4.1 | BSD-3-Clause | Frame arrays, color features, deterministic clustering | Permissive; retain notices when redistributed. |
| FFmpeg executable | local 8.1.1 build | GPLv3 build on this workstation | Optional short-clip helper only | Not bundled. This local binary has GPL features enabled and must not be redistributed with a proprietary product without a separate compliance review. |
| IoU tracker | MatchIQ spike code | Project code | Temporary short-window track IDs | No third-party tracker dependency. |

OpenCV 4.5+ is Apache-2.0 according to the OpenCV license page. NumPy uses the
modified BSD license. FFmpeg is LGPL by default but becomes GPL when built with GPL
components; the workstation binary reports `--enable-gpl` and is therefore treated as GPL.

## Explicit limits

- `person` means a generic person detection, not a confirmed player, goalkeeper, or referee.
- Track IDs are temporary and are not real identities.
- Team clusters are probabilistic color groups and may remain `unknown`.
- Ball boxes are never invented. V0 leaves ball detection disabled unless a real adapter exists.
- Pitch detection is a green-area heuristic, not geometric calibration or homography.
- No tactical event or phase recognition is claimed.

Installation and CLI commands are documented after the implementation is complete.
