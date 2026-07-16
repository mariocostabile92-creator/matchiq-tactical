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

## Local installation

The spike has its own dependency file. Do not merge it into the product requirements.

```powershell
cd C:\Users\Mario\Desktop\matchiq-tactical\matchiq-tactical\backend
.\.venv\Scripts\python.exe -m pip install -r research\vision_spike\requirements.txt
```

No detector weights or match videos are stored in the repository.

## CLI

Create a short local clip without copying it into the repository:

```powershell
.\.venv\Scripts\python.exe -m research.vision_spike.make_clip `
  --input "C:\path\to\full-match.mp4" `
  --output "$env:TEMP\matchiq-vision-spike\clip.mp4" `
  --start 00:01:00 `
  --duration 30
```

Run the experiment:

```powershell
.\.venv\Scripts\python.exe -m research.vision_spike.cli `
  --input "$env:TEMP\matchiq-vision-spike\clip.mp4" `
  --output "$env:TEMP\matchiq-vision-spike\run" `
  --device auto `
  --frame-stride 15 `
  --max-seconds 30
```

Use `--no-overlay` for a metrics-only run. `auto` falls back to CPU when no
supported CUDA detector is configured. Use `--help` to inspect every centralized
parameter.

## Outputs

Each run writes only below the selected output directory:

- `manifest.json`: versioned state, configuration, input fingerprint, and failures.
- `frames.jsonl`: frame-level detections, temporary tracks, pitch, and team estimates.
- `metrics.json`: throughput, latency, memory, and aggregate diagnostic metrics.
- `evaluation.md`: automatic metrics plus the manual-review gate.
- `overlay.mp4`: optional visual diagnostic, never a product export.
- `frames/`: a small deterministic sample for manual inspection.

An interrupted or failed run leaves a readable manifest and can be restarted in a
new output directory. Input videos are opened read-only and are never uploaded.

## Real-video benchmark

Three 30-second clips from the same 1920x1080, 30 fps youth match were processed
locally. The timestamps were deliberately spread across the match.

| Source interval | Sampled frames | Pipeline FPS | Avg latency | Avg persons | Pitch visible | Frames with tracks | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| 01:00-01:30 | 60 | 6.2043 | 40.5282 ms | 0.2500 | 70.00% | 16.67% | 417.29 MB |
| 20:00-20:30 | 30 | 4.1132 | 42.8436 ms | 0.6333 | 96.67% | 23.33% | 390.66 MB |
| 80:00-80:30 | 30 | 4.2960 | 41.1178 ms | 0.6000 | 100.00% | 33.33% | 390.73 MB |

These numbers are diagnostics, not accuracy claims. The clips have no ground-truth
annotations, so precision, recall, MOTA, and IDF1 are intentionally not reported.

## Test commands

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_vision_spike.py"
.\.venv\Scripts\python.exe -m py_compile (Get-ChildItem research\vision_spike -Filter *.py).FullName
```

The isolated suite also checks that the spike does not import product routers,
register routes, access the product database, or write video/model assets into Git.

## Decision gate

**YELLOW - continue research, do not integrate into the product.**

The streaming pipeline, contracts, recovery, overlay, and local evaluation workflow
are feasible. The generic OpenCV HOG baseline misses most distant football players,
creates unstable tracks, has no ball model, and cannot distinguish player,
goalkeeper, referee, or staff. Product integration is therefore blocked until a
football-specific detector and annotated evaluation set demonstrate acceptable
recall, track stability, and resource cost.

See `FEASIBILITY_REPORT.md` for the evidence and the recommended V1 gate. The spike
stops here and does not start V1.

## RF-DETR feasibility benchmark V2

V2 keeps the V0 reader, tracker, pitch heuristic, team clustering, clips, frame
stride, outputs, and decision criteria unchanged. Only the detector and its
preprocessing mode vary. The implementation remains research-only and is not
imported by the MatchIQ product.

Create a dedicated environment; do not install these packages into the product
environment and do not merge them into the product requirements:

```powershell
python -m venv "$env:TEMP\matchiq-rfdetr-venv"
& "$env:TEMP\matchiq-rfdetr-venv\Scripts\python.exe" -m pip install `
  -r research\vision_spike\requirements-rfdetr.txt
```

Run one or more controlled variants:

```powershell
& "$env:TEMP\matchiq-rfdetr-venv\Scripts\python.exe" `
  -m research.vision_spike.benchmark `
  --clip-root "$env:TEMP\matchiq-vision-spike" `
  --output-root "$env:TEMP\matchiq-vision-spike-v2" `
  --device cuda `
  --variant rfdetr_small_standard `
  --variant rfdetr_small_highres `
  --variant rfdetr_small_tiled
```

Generate contact sheets and the manual exploratory coverage summary:

```powershell
& "$env:TEMP\matchiq-rfdetr-venv\Scripts\python.exe" `
  -m research.vision_spike.manual_evaluation `
  --clip-root "$env:TEMP\matchiq-vision-spike" `
  --output-root "$env:TEMP\matchiq-vision-spike-v2" `
  --review "$env:TEMP\matchiq-vision-spike-v2\comparison\manual_review.json"
```

Each variant/clip directory contains `overlay.mp4`, `detections.jsonl`,
`tracks.jsonl`, `metrics.json`, `run_manifest.json`, and `evaluation.md`.
Comparison JSON, CSV, Markdown, overlays, contact sheets, and manual-review files
are written below `vision_output_v2/comparison` or the caller-selected equivalent.
Videos, weights, frames, overlays, datasets, and run outputs remain ignored by Git.

See `RFDETR_V2_REPORT.md`, `RFDETR_LICENSE_AUDIT.md`, and
`RFDETR_FINE_TUNING_PLAN.md` for the controlled results and decision.
