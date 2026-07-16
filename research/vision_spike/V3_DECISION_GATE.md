# MatchIQ Vision Engine V3 - Decision Gate

Decision date: 2026-07-16.

## Current decision

**RED - `DATASET_NOT_READY`.**

This is a controlled stop, not a failed training run. The preparation pipeline is
ready, but no approved real dataset is available and training was not executed.

| Gate | Current result | Required result |
|---|---|---|
| Authorized sources | 0 | Every source approved for modification, commercial use, and commercial training |
| Annotated images | 0 | At least 500 |
| Independent matches | 0 | At least 3 |
| Player examples | 0 | At least 500 |
| Goalkeeper examples | 0 | At least 50 |
| Referee examples | 0 | At least 50 |
| Ball examples | 0 | At least 150 |
| Dataset validator | No real dataset | `VALID`, no critical errors |
| Match-level split | No real dataset | Reproducible 70/15/15 assignments |
| Frozen test set | No real dataset | Image IDs, match IDs, and stable SHA-256 |
| Disk and hardware | Gate implemented | At least 8 GB free and realistic CPU/CUDA selection |

## Promotion rules

V3 can become YELLOW only after a legal dataset passes the training gate and a
reproducible fine-tuning/evaluation run demonstrates useful player detection but
still has unstable roles, ball detection, or staff/public filtering.

V3 can become GREEN for isolated V4 research only when the frozen test set shows:

- useful player detection in wide tactical views;
- coherent per-class precision, recall, mAP50, and mAP50-95;
- median manual coverage of at least 85%;
- a significant staff/public false-positive reduction versus COCO;
- acceptable goalkeeper and referee distinction;
- at least 90% active tracking with the unchanged V2 IoU tracker;
- sustainable FPS, latency, RAM, and VRAM;
- reproducible training and no licensing issue.

Ball detection is evaluated separately. Weak ball recall may keep V3 YELLOW without
invalidating an otherwise useful player detector, but it must be reported honestly.

Even a GREEN research result does not authorize product integration. It only permits
a separately approved V4 tracking and team-association study.

