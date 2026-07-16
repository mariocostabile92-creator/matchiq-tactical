# RF-DETR V2 - License and Weight Audit

Audit date: 2026-07-16. This document covers only the isolated feasibility spike.

## Code package

| Field | Verified value |
|---|---|
| Package | `rfdetr` |
| Version used | `1.8.3` |
| Official repository | `https://github.com/roboflow/rf-detr` |
| Official documentation | `https://rfdetr.roboflow.com/develop/` |
| Package index | `https://pypi.org/project/rfdetr/` |
| Declared code license | Apache-2.0 |
| Commercial position | Permissive, subject to retaining notices and reviewing all transitive dependencies before distribution. |

No RF-DETR code, package, or model is bundled into MatchIQ's production runtime.
The dependency is pinned only in `requirements-rfdetr.txt` for a dedicated local
research environment.

## Model weight used

| Field | Verified value |
|---|---|
| Model | RF-DETR Small COCO |
| Mode | Generic COCO `person` detection |
| Source | `https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth` |
| Official model card | `https://huggingface.co/Roboflow/rf-detr-small` |
| Declared weight license | Apache-2.0 |
| Declared training data | COCO 2017 object detection, 80-category label space |
| Training-data rights position | The model card identifies COCO 2017, but this sprint does not treat the model license as a blanket license for the underlying images. No COCO image or annotation is redistributed. |
| Local size | 386,045,550 bytes |
| SHA-256 | `d81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33` |
| Repository status | Not committed; temporary local cache only |

The benchmark maps only the source class `person` to MatchIQ's generic `person`.
It does not infer player, goalkeeper, referee, team, identity, or ball from the
COCO weight. Those fields remain `unknown` or unsupported.

## Football-specific weight audit

No football-specific RF-DETR weight with a verified official source, explicit
commercially compatible license, documented dataset rights, version, checksum,
and usage restrictions was found and approved for this sprint. Therefore:

- football-specific mode is reported as `unavailable`;
- no unverified community weight was downloaded;
- no dataset was downloaded or trained;
- no role or ball class is fabricated;
- the repository contains only a future fine-tuning plan.

## Runtime dependencies

The research environment used RF-DETR 1.8.3, PyTorch 2.13.0+cu130,
Torchvision 0.28.0+cu130, OpenCV headless 4.13.0.92, and NumPy 2.4.4. PyTorch
was installed from its official distribution channel for the local CUDA 13
environment. A release and transitive-license audit is still required before any
future redistribution or server deployment.

## Compliance boundary

No cloud inference, external API, frame upload, or telemetry service was used.
The input video and all derived data stayed on the workstation. This audit is a
technical record, not legal advice, and does not authorize product integration.
