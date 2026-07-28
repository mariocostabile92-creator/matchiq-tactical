# VE-004B ByteTrack Baseline

VE-004B is an isolated research runner. It associates existing VE-002 player
detections across a temporal sequence and carries VE-003 team metadata as
diagnostics. It does not run RF-DETR, team clustering, OpenAI, calibration, or
tactical interpretation.

## Dependency

Install the exact research dependency after the existing Vision environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\research\tracking\requirements.txt
```

The pinned implementation is Roboflow Trackers `2.5.0.post0`, using
`ByteTrackTracker`.

## Input contract

`--source` accepts:

- a VE-003 `team_assignment_manifest.json`;
- one VE-003 per-frame JSON report;
- a directory containing VE-003 per-frame JSON reports.

The source must represent one or more ordered, contiguous segments. VE-004B
does not infer timing silently:

- `source.frame_index` and `source.timestamp_seconds`/`timestamp_ms` are used
  when present;
- `frame_*` and `t*ms` filename metadata is used when present;
- otherwise the manifest order and the explicitly supplied `--fps` are used.

To force a reset at a cut or a new sequence, use a different
`source.segment_id` in the per-frame reports. The same tracker instance is
reset with `tracker.reset()`; IDs remain unique inside the VE-004B run.

## Run

```powershell
.\.venv\Scripts\python.exe -m research.tracking `
  --source reports\ve003-sequence\team_assignment_manifest.json `
  --output reports\ve004b-sequence `
  --fps 5
```

Available controls:

- high and low detection thresholds;
- IoU match threshold;
- lost-track buffer;
- minimum confirmed frames;
- effective FPS;
- maximum detections per frame;
- minimum box area.

## Outputs

- `tracking_manifest.json`: versioned machine-readable run, frame,
  observation, and track data;
- `tracking_report.html`: simple human-readable report;
- `debug/*.jpg`: original boxes plus temporary track IDs and trajectories.

Each confirmed observation includes the temporary track ID, source VE-002
detection ID, frame and timestamp, bbox, foot point, detector confidence,
input confidence stage, track state, gap information, and VE-003 diagnostics.

The installed ByteTrack package returns only rows backed by detections. It
does not expose prediction-only rows or per-association scores. VE-004B
therefore reports `predicted_observations = 0` and marks association scores as
unavailable instead of fabricating them.

## Limits

- image-space tracking only;
- no field calibration or homography;
- no player identity or ReID;
- no tactical meaning;
- team assignment never gates association;
- switch warnings are preliminary heuristics until ground truth exists.
