# MatchIQ Vision Engine - Football-Specific Detection Spike V3

Report date: 2026-07-16. Scope: isolated research only.

## Executive result

**V3 status: `DATASET_NOT_READY`. Decision gate: RED.**

The V3 preparation, annotation, validation, split, fine-tuning, evaluation, and
visual-comparison pipeline is implemented and covered by synthetic tests. Training
was not executed because no commercially authorized football dataset is currently
registered and the mandatory minimums are not met. No metric has been fabricated.

This result closes the engineering-preparation part of V3 without starting V4 and
without changing the MatchIQ product.

## V2 baseline preserved

RF-DETR Small COCO 1.8.3 remains the reference detector. On the three preserved
V2 clips, standard 512 preprocessing produced 9.5916 persons/frame, detections on
100% of sampled frames, active tracks on 93.33%, 88.19% median exploratory manual
coverage, 29 manually counted false positives, 2.0780 pipeline FPS, 222.40 ms
average latency, 2,191.04 MB peak RSS, and 179.63 MB peak VRAM. These exploratory
figures are preserved from V2 and are not V3 accuracy metrics.

The COCO model recognizes generic `person`; it does not honestly distinguish
player, goalkeeper, referee, and ball. The V2 implementation and outputs were not
modified.

## Dataset and legal gate

The V3 canonical classes are:

1. `player`
2. `goalkeeper`
3. `referee`
4. `ball`

Current approved sources, images, matches, and annotations are all zero. SoccerNet
and SoccerNet-derived video data were rejected for commercial fine-tuning. The MIT
license of the SoccerNet code does not authorize use of match video. Community
datasets remain rejected until their individual chain of rights is documented.

Only MatchIQ-held footage with written permission for extraction, annotation,
commercial model training, commercial derived weights, and the required retention
period is eligible. Raw data and private provenance remain outside Git.

## Implemented V3 pipeline

- External, configurable dataset scaffold with raw, extracted, annotation, image,
  label, manifest, report, cache, checkpoint, log, and training-output boundaries.
- Local frame extraction by interval with temporal sampling, wide-view filtering,
  black/overexposed, blur, and near-duplicate rejection.
- Anonymous provenance manifest with source hash, timestamp, FPS, resolution,
  camera type, lighting, quality, authorization origin, and match identifier.
- COCO JSON schema for the four football classes, difficult/uncertain/ignore flags,
  negative images, and documented annotation rules.
- Validator for readability, bounding boxes, IDs, duplicates, class distribution,
  metadata, provenance, licenses, leakage, split integrity, and contact sheets.
- Deterministic split by complete match, with target ratios 70/15/15 and a frozen,
  hashed test manifest. Consecutive frames cannot cross splits.
- RF-DETR export in `train`, `valid`, and `test` COCO directories.
- Centralized RF-DETR Small fine-tuning configuration and prudent augmentations.
- Mandatory gate for data, license, volume, classes, split, frozen test, disk, and
  hardware, plus explicit confirmation before a real training starts.
- Frozen-test COCO baseline and football-checkpoint evaluators with per-class,
  small-object, ball, scene, staff/public, latency, and FPS metrics.
- V2/V3 comparison runner, class-aware overlays, and
  `ORIGINAL | COCO | FOOTBALL V3` contact sheets.

## Training configuration

The prepared configuration starts from RF-DETR Small COCO at 512 px. It uses batch
size 2, gradient accumulation 4, learning rate 0.0001, encoder learning rate
0.00001, 40 epochs, 2 warmup epochs, weight decay 0.0001, seed 42, two workers,
mixed precision on CUDA, validation every epoch, and early stopping with patience
8. Horizontal flip, prudent light/contrast/color changes, light Gaussian blur, and
light noise are enabled. Vertical flips, extreme rotation, and destructive crops
are excluded.

Minimum training requirements are 500 images, 3 matches, 500 player examples,
50 goalkeeper examples, 50 referee examples, 150 ball examples, 8 GB free disk,
an approved source registry, a valid dataset, a match-level split, and a frozen
test set.

## Current hardware and execution

The verified V2 research workstation has an NVIDIA GeForce RTX 3050 Laptop GPU
with 6 GB VRAM. The dedicated environment used RF-DETR 1.8.3 and PyTorch
2.13.0+cu130. The V3 gate supports CUDA or an explicitly selected CPU path, but
no heavy training was run in V3.

Training duration, loss curves, validation metrics, test metrics, per-class
precision/recall/mAP, confusion matrix, ball recall, V3 FPS, V3 latency, V3 RAM,
V3 VRAM, and real V3 overlays/contact sheets are therefore not available. They
must only be produced after the same frozen dataset and test set pass the gate.

## Reproducible workflow

```powershell
$dataset = "C:\datasets\matchiq-v3"

.\.venv\Scripts\python.exe -m research.vision_spike.v3.scaffold `
  --dataset $dataset --repository-root (Get-Location)

.\.venv\Scripts\python.exe -m research.vision_spike.v3.extract_frames `
  --input "C:\authorized\match.mp4" `
  --output "$dataset\raw\match-001" `
  --dataset $dataset --source-id source-001 `
  --authorization-origin "written-authorization-reference" `
  --match-id match-001 --every-seconds 3 --max-frames 150 --wide-only

.\.venv\Scripts\python.exe -m research.vision_spike.v3.validate_dataset `
  --dataset $dataset

.\.venv\Scripts\python.exe -m research.vision_spike.v3.split_dataset `
  --dataset $dataset --train-ratio 0.70 --val-ratio 0.15 --seed 42

& "$env:TEMP\matchiq-rfdetr-venv\Scripts\python.exe" `
  -m research.vision_spike.v3.training_gate --dataset $dataset

& "$env:TEMP\matchiq-rfdetr-venv\Scripts\python.exe" `
  -m research.vision_spike.v3.evaluate_dataset `
  --dataset $dataset --mode coco --device cuda

& "$env:TEMP\matchiq-rfdetr-venv\Scripts\python.exe" `
  -m research.vision_spike.v3.train_rfdetr `
  --dataset $dataset --confirm-training
```

The final command still refuses to train unless every gate check passes.

## Limits and next recommendation

The infrastructure is not evidence that the football-specific model works. The
next permitted action is to collect and annotate 500-1,500 diverse, authorized
images from at least three matches, with at least 60% wide tactical shots and
enough goalkeeper, referee, ball, and negative staff/public examples. Then run the
validator, freeze the match-level split, execute the COCO baseline, pass the gate,
fine-tune once, and compare COCO versus football V3 on the untouched test split.

Do not begin V4, tracking changes, team association, field calibration, events,
tactical metrics, or product integration from this result.

