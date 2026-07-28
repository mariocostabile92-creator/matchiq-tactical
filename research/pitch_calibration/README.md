# VE-005B / VE-005C - Pitch Calibration Research

Isolated research integration for estimating a soccer-pitch calibration and
projecting existing VE-004 foot points into canonical pitch coordinates.
VE-005B keeps the external TVCalib bridge; VE-005C adds the original
`matchiq-hybrid` classical-geometry adapter.

It is not imported by the production backend, frontend, API, Video AI, Coach,
or database.

## Current status

**BLOCKED for a real TVCalib benchmark.**

The MatchIQ integration layer is implemented and tested, but the official
TVCalib runtime cannot yet be treated as reproducible or redistributable:

- TVCalib code is MIT;
- the required segmentation submodule has no discoverable license file;
- the pretrained checkpoint has no separate usage terms in the upstream
  repository;
- the official stack targets Python 3.9 / PyTorch 1.11 / NumPy 1.19.5;
- the MatchIQ Vision environment is Python 3.11.9 and must remain untouched.

See `THIRD_PARTY_AUDIT.md`.

VE-005C does not import TVCalib, PnLCalib, GPL code, external model weights, or
new neural networks. It uses the NumPy and OpenCV dependencies already present
in the research environment. Its automatic estimates remain experimental and
must not be treated as measured ground truth.

## Architecture

The module separates:

- `contracts.py`: versioned inputs and outputs;
- `sequence_loader.py`: image, directory, video, VE-003, and VE-004 inputs;
- `adapters/`: external calibration boundary;
- `field_model.py`: semantic 105 x 68 canonical pitch;
- `field_evidence.py`: grass, white-line, region, and optional circle evidence;
- `line_detection.py` and `keypoint_detection.py`: classical geometry;
- `correspondence_solver.py`: explicit semantic hypotheses and ambiguity;
- `homography_solver.py` and `geometric_refinement.py`: normalized estimation,
  RANSAC, refinement, and diagnostics;
- `temporal_validation.py`: visual cuts, compatible smoothing, and confidence
  decay;
- `quality_gate.py`: matrix, geometry, projection, and temporal checks;
- `projection.py`: foot-point projection;
- `renderer.py`: debug overlays and minimaps;
- `reports.py`: JSON, HTML, and CSV reports;
- `runner.py`: orchestration only;
- `cli.py`: research commands.

No TVCalib source or weights are vendored.

## MatchIQ hybrid commands

Run the automatic research calibrator on a video:

```powershell
.\.venv\Scripts\python.exe -m research.pitch_calibration calibrate-video `
  --adapter matchiq-hybrid `
  --source match.mkv `
  --output reports\ve005c-video `
  --sample-interval 2 `
  --maximum-frames 20 `
  --camera-profile fixed `
  --keyframe-frequency 1 `
  --seed 7
```

Run it on a VE-004 manifest without rerunning RF-DETR or ByteTrack:

```powershell
.\.venv\Scripts\python.exe -m research.pitch_calibration calibrate-sequence `
  --adapter matchiq-hybrid `
  --source reports\ve004b-amateur-validation\ve004b\tracking_manifest.json `
  --output reports\ve005c-amateur-contiguous `
  --maximum-frames 60
```

All thresholds are experimental CLI options and are serialized in the output.
`--camera-profile smartphone` changes only classical evidence parameters; it
does not claim automatic camera-motion compensation.

## Commands

Inspect the external runtime:

```powershell
.\.venv\Scripts\python.exe -m research.pitch_calibration inspect-environment
```

Run an image:

```powershell
.\.venv\Scripts\python.exe -m research.pitch_calibration calibrate-image `
  --input frame.jpg `
  --output reports\ve005b-image
```

Run a VE-004 sequence without rerunning RF-DETR:

```powershell
.\.venv\Scripts\python.exe -m research.pitch_calibration calibrate-sequence `
  --source reports\ve004b-amateur-validation\ve004b\tracking_manifest.json `
  --output reports\ve005b-amateur
```

Run a video with configurable sampling:

```powershell
.\.venv\Scripts\python.exe -m research.pitch_calibration calibrate-video `
  --source match.mkv `
  --sample-interval 2 `
  --maximum-frames 20 `
  --output reports\ve005b-video
```

Run paired professional/amateur inputs:

```powershell
.\.venv\Scripts\python.exe -m research.pitch_calibration benchmark `
  --professional path\to\professional-input `
  --amateur path\to\amateur-input `
  --output reports\ve005b-benchmark
```

## External TVCalib bridge contract

After legal and environment gates are resolved, configure
`MATCHIQ_TVCALIB_COMMAND`. The command receives:

```text
--image <absolute path> --json-stdout
```

It must write exactly one JSON object to stdout:

```json
{
  "status": "ESTIMATED",
  "homography_image_to_pitch": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "homography_pitch_to_image": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "camera_parameters": null,
  "model_confidence": 0.75,
  "reprojection_error_px": 8.2,
  "coverage_score": 0.72,
  "valid_image_region": {"bbox_xyxy": [0, 0, 1920, 1080]},
  "calibration_origin": "tvcalib",
  "detected_field_elements": [],
  "ambiguity_flags": [],
  "diagnostics": {}
}
```

Unknown, invalid, timed-out, or unlicensed runtimes never produce fabricated
calibrations. The frame is marked `UNCALIBRATED`.

## Output contract

Every run creates:

- `calibration_manifest.json`;
- `projected_tracks.json`;
- `benchmark_summary.json`;
- `calibration_frames.csv`;
- `report.html`;
- `evidence_manifest.json`;
- `correspondence_manifest.json`;
- diagnostic images when enabled.

Calibration status is one of:

- `VALIDATED`;
- `ESTIMATED`;
- `AMBIGUOUS`;
- `UNCALIBRATED`;
- `REJECTED`.

Confidences are separate:

- evidence;
- correspondence;
- model;
- geometric;
- temporal;
- projection;
- overall.

`canonical_meters` means coordinates on the configured canonical 105 x 68
reference. It is not a claim about real physical dimensions. `physical_meters`
remains null unless both real pitch dimensions are supplied.

Every VE-004 foot point also receives `projection_valid` and an explicit
`exclusion_reason`. Points are retained for audit even when projection is
refused.

## Quality gate

The gate checks:

- finite 3 x 3 matrix;
- invertibility and determinant;
- condition number;
- reprojection error when available;
- player foot points inside the canonical pitch;
- temporal jump between consecutive calibrations;
- explicit orientation ambiguity flags;
- missing diagnostics.

Only non-rejected homographies above the configurable projection-confidence
threshold can project observations. All thresholds are CLI options, serialized
under `configuration.quality_thresholds`, and remain experimental.

## Camera segments

A sequence starts at `camera_segment_001`. A temporal jump opens a new segment.
This prevents smoothing or propagation across an apparent cut, zoom jump, pan,
or camera change. Segment boundaries are diagnostic until a real TVCalib
benchmark validates thresholds.

## Known limitations

- TVCalib execution is blocked by the third-party gate above.
- The MatchIQ hybrid adapter is a first automatic classical baseline, not a
  production calibrator.
- Left/right and camera-orientation symmetries remain `AMBIGUOUS` when visual
  evidence cannot resolve them safely.
- Weak, worn, shadowed, partially visible, or broadcast-obscured lines may
  produce `UNCALIBRATED` or `REJECTED` frames.
- No professional VE-004 sequence is currently persisted in reports; local
  professional videos can still be sampled directly.
- No ground-truth homographies are available for the local professional and
  amateur videos.
- Quality thresholds are provisional and must be validated on authorized data.
- Successful execution, geometric plausibility, and measured calibration
  accuracy are reported as distinct concepts.

## Relationship with VE-004 and VE-006

VE-005B consumes existing VE-004 manifests and projects the recorded
`foot_point_xy`; it never reruns RF-DETR, team assignment, or tracking. A future
VE-006 may consume only records where `projection_valid` is true, while keeping
excluded records available for audit. VE-005B does not implement tactical
interpretation.

## Reproducing the blocked benchmark

The local amateur VE-004 manifest contains 60 real frames spanning 11.8
contiguous seconds. The available professional manifest contains only five
frames, below the required minimum of ten. With no approved external bridge,
the following command intentionally produces `UNCALIBRATED` diagnostics:

```powershell
.\.venv\Scripts\python.exe -m research.pitch_calibration calibrate-sequence `
  --input reports\ve004b-amateur-validation\ve004b\tracking_manifest.json `
  --output reports\ve005b-blocked-amateur `
  --maximum-frames 60
```

Observed blocking reason:

```text
MATCHIQ_TVCALIB_COMMAND is not configured
```

Do not configure the bridge until the segmentation-submodule and checkpoint
terms are clarified and an isolated Python 3.9 runtime is reproducible.
