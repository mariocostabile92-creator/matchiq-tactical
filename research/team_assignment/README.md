# VE-003 Team Assignment

VE-003 assigns existing VE-002 `person` detections to anonymous jersey-color
groups:

- `TEAM_A`
- `TEAM_B`
- `UNKNOWN`

It does not run RF-DETR and does not import a detector. It reads the VE-002
manifest and per-image JSON reports, loads the referenced source images, extracts
a torso-only jersey ROI, builds HSV/LAB color features, and applies deterministic
two-cluster K-Means across one VE-002 manifest.

## Run

```powershell
.\.venv\Scripts\python.exe -m research.team_assignment `
  --manifest reports\ve-002-1-rfdetr-real\comparison\rfdetr\player_detection_manifest.json `
  --output reports\ve-003-team-assignment
```

The output contains:

- `team_assignment_manifest.json`
- `team_assignment_report.html`
- per-image JSON reports under `json/`
- debug images under `debug/`

## Safety behavior

The labels are anonymous and deterministic. A player becomes `UNKNOWN` when the
torso ROI is unusable, the two color clusters are not sufficiently separated, or
the individual assignment is ambiguous. VE-003 does not identify goalkeepers,
referees, player identities, roles, tracking, or tactical behavior.

One manifest is expected to represent one match with stable kits. Cross-match
manifests should be split before running VE-003.

