# RF-DETR V2 - Conditional Football Fine-tuning Plan

No training is performed in this sprint. This plan becomes relevant only after
data-rights, privacy, licensing, annotation budget, and product approval.

## Dataset target

- 500-1,500 legally usable annotated images for the first controlled iteration.
- At least 60% wide tactical views; the remainder may cover medium shots,
  close-ups, camera cuts, benches, low light, shadows, occlusion, and set pieces.
- Split by match, never by random frame, to prevent near-duplicate leakage.
- Keep a held-out set from different matches, venues, cameras, and kit colors.
- Record source, owner, authorization, retention period, and permitted purposes.

## Classes

Initial classes: `player`, `goalkeeper`, `referee`, and `ball`. Staff, spectators,
and ambiguous persons should be explicitly excluded or annotated as hard negatives.
Player identity and jersey OCR are separate future tasks and must not be inferred
from these classes.

## Annotation policy

- Tight visible-object boxes with a written occlusion/truncation convention.
- Label tiny players consistently or mark them ignored below a documented size.
- Double-review at least 10% of images and resolve class disagreements.
- Include wide frames with crowds, technical areas, advertising, and shadows as
  hard negatives.
- Track dataset and annotation-tool versions in an immutable manifest.

## Evaluation

- Report mAP and per-class precision/recall only on held-out annotated data.
- Add size buckets, especially small/distant players and ball.
- Report manual wide-frame player coverage and false positives outside the pitch.
- Evaluate track continuity and identity switches only with track ground truth.
- Re-run the exact three V0/V2 clips as a regression check, not as the test set.

## Entry gate

Start training only when dataset rights and model redistribution terms are signed
off, the annotation guide is frozen, and the target hardware budget is approved.
No trained weight may enter the product without its own source, dataset, license,
version, checksum, performance, and privacy audit.
