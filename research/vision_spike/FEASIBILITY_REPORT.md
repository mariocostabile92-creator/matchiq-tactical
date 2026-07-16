# MatchIQ Vision Engine - Feasibility Report V0

## Executive decision

**Gate: YELLOW for continued isolated research; RED for product integration today.**

The local architecture is technically viable, deterministic, privacy-preserving,
and sufficiently isolated. The selected generic person detector is not a viable
football detector: it misses most distant players, produces weak boxes in wide
views, and cannot support reliable team shape, tactical phase, or player tracking.

V1 must not begin automatically. It should be approved only after the model and data
requirements below are accepted.

## 1. Repository and environment audit

- Real repository root: the directory containing `main.py` and `research/`.
- Product runtime: Python 3.11 on Railway.
- Local spike interpreter: Python 3.14.6 in the existing local virtual environment.
- Local video tools: FFmpeg and FFprobe 8.1.1.
- Local hardware: NVIDIA GeForce RTX 3050 Laptop GPU, 6 GB VRAM.
- V0 execution: CPU only. GPU presence is recorded but no CUDA detector is used.
- Existing product requirements had no OpenCV, NumPy, PyTorch, detector, tracker,
  or CV model weights before this spike.
- No existing reusable computer-vision detector/tracker was found in the product.
- No video or model asset above 25 MB was committed.

## 2. Selected baseline and licenses

| Component | Selection | License/compliance position |
|---|---|---|
| Frame/video IO | OpenCV headless 4.13.0.92 | Apache-2.0, isolated dependency |
| Person baseline | OpenCV HOG | Generic person detector; no external weights |
| Tracking | MatchIQ deterministic IoU tracker | Temporary IDs, project code |
| Pitch visibility | MatchIQ HSV green-area heuristic | Diagnostic only |
| Team estimate | MatchIQ LAB two-cluster experiment | Probabilistic, unknown fallback |
| Arrays/features | NumPy 2.4.1 | BSD-3-Clause |
| Clip helper | Local FFmpeg executable | GPL-enabled local build, not bundled |

The local FFmpeg executable must not be redistributed with a proprietary product
without a dedicated licensing review. The spike invokes it only as an optional
developer-side helper.

## 3. Architecture created

The implementation is isolated below `research/vision_spike` and separates:

- centralized configuration;
- versioned JSON contracts;
- streaming video reader;
- detector interface and generic HOG adapter;
- deterministic IoU tracker;
- pitch visibility heuristic;
- team color clustering experiment;
- overlay renderer;
- metrics and evaluation writer;
- orchestration pipeline;
- CLI and short-clip helper;
- isolated tests.

No frontend, product route, public API, authentication, database, service worker,
PWA manifest, Coach, Video AI, Video Hub, Live, or Scout file was changed.

## 4. CLI and configuration

The CLI accepts a local input file and an explicit output directory. Centralized
parameters include device preference, frame stride, maximum duration, detector
confidence, detector width, tracker IoU/lifetime, pitch thresholds, team-cluster
thresholds, overlay enablement, and output sampling.

Configuration is serialized into `manifest.json`, making each run reproducible.
Unsupported GPU selection falls back to CPU and records the effective device.

## 5. Real-video evaluation

Input source: one local 4.73 GB youth match, 1920x1080, approximately 30 fps,
duration 5802 seconds. Three separate 30-second excerpts were created in the OS
temporary directory and never copied into the repository.

| Interval | Frames | FPS | Detector latency | Persons/frame | Tracks created | Active-track frames | Pitch visible | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 01:00-01:30 | 60 | 6.2043 | 40.5282 ms | 0.2500 | 5 | 16.67% | 70.00% | 417.29 MB |
| 20:00-20:30 | 30 | 4.1132 | 42.8436 ms | 0.6333 | 12 | 23.33% | 96.67% | 390.66 MB |
| 80:00-80:30 | 30 | 4.2960 | 41.1178 ms | 0.6000 | 8 | 33.33% | 100.00% | 390.73 MB |

Ball detections: zero by design. V0 has no ball detector and never fabricates a
ball box. Team labels frequently remain `unknown`; labels `team_a` and `team_b`
are color clusters, not identified clubs.

## 6. Manual inspection

The first run was inspected at three overlay timestamps and across its deterministic
sample set:

| Relative timestamp | Scene | Detector result | Manual finding |
|---|---|---|---|
| 00:07 | Close-up staff/coach | One generic person box | Box is plausible, but this is not a player identity and is not tactically useful. |
| 00:15 | Wide corner-kick scene | One weak/large person box | Severe false negatives: roughly ten or more visible people are missed. Tracking is unusable. |
| 00:29 | Close-up staff/coach | No detection | Acceptable non-detection, but confirms broadcast cuts need scene filtering. |

Additional center samples at match times 20:07 and 78:32 showed respectively a
goalkeeper close-up and a valid wide build-up view. This demonstrates that uniform
time sampling alone cannot guarantee tactical value.

## 7. Observed errors and limits

- Distant players are usually too small for the generic HOG detector.
- Wide tactical views suffer severe false negatives.
- Occasional boxes are oversized or poorly localized.
- Close-ups of coaches/staff may be detected as generic persons.
- Temporary tracks disappear when detections are missed and are not identities.
- Team clustering is underdetermined when detections are few or lighting is uneven.
- Green-area pitch detection can be positive on non-tactical close-ups containing
  enough grass and does not calibrate pitch geometry.
- No ball, goalkeeper, referee, jersey number, homography, tactical event, or phase
  recognition exists in V0.
- No accuracy metric is claimed because no annotated ground truth exists.

## 8. Robustness and safety tests

The isolated suite covers configuration, contracts, serialization, video metadata,
timestamps, frame stride, corrupted input, short clips, cleanup, cancellation,
model failure, CPU fallback, deterministic tracking, pitch/team heuristics, overlay,
JSON outputs, CLI help/run behavior, memory accounting, and resource closure.

Safety tests verify that the spike does not import product routers, expose routes,
access the product database, or commit video/model assets. Failed runs retain a
diagnostic manifest instead of leaving an ambiguous partial state.

## 9. Privacy and product impact

- Video remains local and is opened read-only.
- No cloud or external AI API is called.
- No frame, metadata, or derived output leaves the workstation.
- Outputs are written only to the caller-selected local directory.
- Product behavior is unchanged because the spike has no integration point.
- No deployment or push is part of this work.

## 10. Recommended V1 entry criteria

Proceed only with an explicitly approved second spike that includes:

1. A football-specific detector with a commercially compatible model and weights.
2. A small, legally usable annotated validation set covering wide views, close-ups,
   lighting changes, occlusion, set pieces, and camera cuts.
3. Separate classes or validated post-processing for player, goalkeeper, referee,
   and ball.
4. A stronger tracker evaluated with track continuity and identity-switch metrics.
5. Scene/tactical-view filtering before player analysis.
6. Ground-truth metrics such as precision, recall, mAP, IDF1, and track coverage.
7. A target hardware budget and benchmark on the actual Railway/deployment plan.
8. A model-license and video-data compliance review before any product integration.

Until those criteria are met, the present code is a research harness only.

## 11. Commits

- `a8933a6` scaffold and contracts
- `f195817` local video reader and detector adapter
- `7f8e5c9` temporary tracking pipeline
- `e63ba7a` pitch visibility and team clustering experiments
- `fcccf54` overlays and structured evaluation outputs
- `f5916b7` isolated feasibility and safety coverage
- `ffcc4c9` recovery and local clip hardening

No push was performed.
