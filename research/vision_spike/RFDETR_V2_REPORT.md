# MatchIQ Vision Engine - RF-DETR Feasibility Spike V2

## Executive result

**Research gate: GREEN for a next isolated detector/tracker study. Product gate:
RED until football-specific classes, ground truth, tracking validation, and a
deployment budget exist.**

RF-DETR Small materially changes the feasibility result on wide football views.
Across ten manually reviewed wide tactical frames, standard preprocessing reached
88.19% median manual exploratory coverage and active tracks were present in 93.33%
of processed frames. These are exploratory manual observations, not precision,
recall, mAP, MOTA, or IDF1.

## Controlled design

The three 30-second V0 clips, frame strides, reader, pitch heuristic, team color
experiment, deterministic IoU tracker, overlay, metrics, and decision criteria were
preserved. Only the detector and preprocessing changed.

| Variant | Model input | Description |
|---|---:|---|
| `baseline_opencv` | V0 | Generic OpenCV HOG baseline rerun in the current harness |
| `rfdetr_small_standard` | 512 | Aspect-preserving letterbox, one inference per sampled frame |
| `rfdetr_small_highres` | 960 | Aspect-preserving high-resolution letterbox |
| `rfdetr_small_tiled` | 512 per tile | 960 px overlapping tiles, 20% overlap, global-coordinate restoration and NMS/deduplication |

Medium was not run: Small already answered the feasibility question, while the
priority order required standard, high-resolution, and tiled comparisons first.
No football-specific weight was used because no safely verified approved weight
was available.

## Environment

- Workstation: NVIDIA GeForce RTX 3050 Laptop GPU, 6 GB VRAM.
- Dedicated environment: RF-DETR 1.8.3, PyTorch 2.13.0+cu130,
  Torchvision 0.28.0+cu130, OpenCV headless 4.13.0.92, NumPy 2.4.4.
- Model: RF-DETR Small COCO, 386,045,550 bytes.
- Weight SHA-256: `d81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33`.
- Inference: local CUDA, half precision enabled, batch size 1.
- Privacy: no upload, cloud inference, external model API, or product database.

The dedicated RF-DETR environment resolved a development build reporting OpenCV
5.0.0, where the legacy `HOGDescriptor` used only by V0 is unavailable. The V2-only
32-test suite passes there. The combined V0/V2 suite and fresh OpenCV baseline were
run in the original isolated spike environment with OpenCV 4.13.0. This dependency
split is intentional and reinforces that the product requirements must remain
untouched.

## Aggregate benchmark

The fresh V0 rerun and all RF-DETR variants processed the same 120 sampled frames.
Pipeline FPS excludes one-time model loading; model load is reported separately.
Per-frame latency includes detector plus the preserved tracker/pitch/team work.

| Variant | Persons/frame | Detection frames | Active-track frames | Pipeline FPS | Avg latency | Peak RSS | Peak VRAM | Outside pitch | Duplicates removed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| OpenCV V0 rerun | 0.8667 | 54.17% | 29.17% | 2.3295 | 217.43 ms | 443.20 MB | 0 MB | 22.30% | 0 |
| RF-DETR standard | 9.5916 | 100% | 93.33% | 2.0780 | 222.40 ms | 2,191.04 MB | 179.63 MB | 22.16% | 0 |
| RF-DETR highres | 10.4250 | 100% | 93.33% | 1.9457 | 277.36 ms | 2,257.79 MB | 298.47 MB | 27.23% | 0 |
| RF-DETR tiled | 16.6417 | 100% | 93.33% | 1.2554 | 563.20 ms | 1,993.62 MB | 179.63 MB | 48.03% | 3,081 |

One-time maximum model load was 26.34 seconds for standard, 23.26 seconds for
high-resolution, and 22.23 seconds for tiled. The weight size was identical.

The original V0 report recorded 4.1-6.2 FPS and roughly 40 ms detector latency.
The fresh baseline above uses the current full diagnostic harness and includes
additional pitch/team/tracking/serialization work in the measured loop; it is the
valid apples-to-apples comparator for V2. The original V0 figures remain preserved
in `FEASIBILITY_REPORT.md` and are not silently overwritten.

## Manual exploratory review

Fifteen timestamps were reviewed: 7, 12, 15, 22, and 29 seconds in each clip.
Ten were classified as wide tactical frames. For every variant the review records
clearly visible people, correct detections, misses, false positives, duplicates,
staff/crowd detections, pitch visibility, tactical utility, and notes.

| Variant | Wide frames | Median manual exploratory coverage | Manual FP | Manual duplicates | Track frames | Gate |
|---|---:|---:|---:|---:|---:|---|
| OpenCV V0 rerun | 10 | 0.00% | 5 | 0 | 29.17% | RED |
| RF-DETR standard | 10 | 88.19% | 29 | 0 | 93.33% | GREEN |
| RF-DETR highres | 10 | 92.26% | 35 | 0 | 93.33% | GREEN |
| RF-DETR tiled | 10 | 100.00% | 139 | 30 | 93.33% | GREEN by coverage rule, operationally rejected |

The tiled mode passes the narrow coverage formula but is not the recommended
configuration: it generates 139 manual false positives, 30 duplicates, 48.03%
outside-pitch detections, and 563 ms average latency. The preferred V2 research
configuration is **RF-DETR Small standard**. High-resolution is an optional second
pass for selected difficult frames, not a default live path.

## Visual evidence and outputs

Every run contains `overlay.mp4`, `detections.jsonl`, `tracks.jsonl`,
`metrics.json`, `run_manifest.json`, and `evaluation.md`. The comparison directory
contains JSON/CSV/Markdown aggregates, twelve copied overlays, fifteen contact
sheets, `manual_review.json`, and `manual_coverage_summary.json`. All files are
outside the repository under the OS temporary directory and ignored by Git.

## Honest class mapping

The model supplies generic COCO `person`. MatchIQ stores it as `person` with role,
team, and identity left unknown. Goalkeeper, referee, player, and ball are not
claimed. The existing two-color team experiment remains probabilistic and is not
a club identification system.

## Failure modes

- Spectators, bench personnel, coaches, and staff can be detected as persons.
- Tiled inference amplifies crowd and technical-area false positives.
- Bright sun, deep shadow, occlusion, tiny players, and camera cuts remain hard.
- The pitch heuristic is not homography and cannot reliably remove every off-pitch box.
- The deterministic IoU tracker creates many short tracks and is not identity tracking.
- No annotated ground truth exists, so the manual result cannot be promoted to an
  accuracy claim.
- No ball, role, jersey, team identity, tactical phase, or event recognition exists.
- The local GPU result does not establish Railway cost or latency feasibility.

## Decision

The research question is answered positively: a modern, commercially compatible
generic detector can find enough people in MatchIQ's wide footage to make a future
football-specific vision pipeline plausible. This does not make the feature ready
for users. The next approved study should focus on pitch filtering, a stronger
tracker, annotated ground truth, and legally controlled football fine-tuning.

V2 stops here. It does not start fine-tuning, V1 product integration, frontend work,
new routes, or deployment.
