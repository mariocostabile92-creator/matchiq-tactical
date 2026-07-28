# TVCalib third-party audit

Audit date: 2026-07-28.

## Upstream provenance

- Repository: `https://github.com/MM4SPA/tvcalib`
- Commit: `1222c5230af2742395d74918ed6f34eb2b9bf7f9`
- Commit date: 2023-12-02
- TVCalib source license: MIT
- Segmentation submodule:
  `https://github.com/jtheiner/sn-calibration-segmentation`
- Segmentation commit:
  `ffdb3088ffb6c89f28249f330d2e9ca6be3c8094`
- Segmentation license: **unverified**; no license file was found in the
  checked-out submodule.
- Checkpoint referenced by the official README: `train_59.pt`, hosted on
  TIB cloud.
- Checkpoint license/terms: **unverified**; no separate terms were found in
  the official repository or download instructions.

## Reproducibility audit

The official environment pins:

- Python 3.9
- PyTorch 1.11.0
- torchvision 0.12.0
- CUDA toolkit 11.3
- NumPy 1.19.5
- OpenCV headless 4.5.5.62
- PyTorch Lightning 1.5.10
- Kornia 0.6.3

The MatchIQ research environment uses Python 3.11.9, NumPy 2.4.1,
OpenCV 4.13.0 and PyTorch 2.13.0 CPU. Installing the official TVCalib stack
inside that environment would risk breaking VE-002/003/004 and is forbidden.

## Decision

Status: **BLOCKED for executable benchmark and redistribution**.

The MatchIQ adapter therefore uses an external subprocess boundary. No
TVCalib, segmentation, or checkpoint code is copied into MatchIQ. A separate
runtime can be connected only after:

1. written clarification of the submodule and checkpoint usage terms;
2. a reproducible isolated environment;
3. a bridge that emits the documented MatchIQ JSON contract;
4. a real professional and amateur benchmark passing the quality gate.

This is a legal/reproducibility block, not a technical claim that TVCalib
cannot work.

## VE-005C isolation

The `matchiq-hybrid` adapter is an original MatchIQ implementation based only
on NumPy and OpenCV already declared by the project. It does not copy, import,
invoke, or redistribute TVCalib, PnLCalib, their submodules, or their
checkpoints. The existing TVCalib adapter remains available as a separate,
blocked external boundary and is not selected by the VE-005C command.
