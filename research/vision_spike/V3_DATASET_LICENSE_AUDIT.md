# MatchIQ Vision Engine V3 - Dataset and License Audit

Audit date: 2026-07-16. This is a technical screening record, not legal advice.

## Decision

**No external football image/video dataset is approved for commercial MatchIQ
fine-tuning at the start of V3. The training gate is `DATASET_NOT_READY`.**

V3 may use only locally held footage for which MatchIQ has a written authorization
that explicitly permits frame extraction, annotation, commercial model training,
commercial use of derived weights, and the required retention period. Raw frames,
annotations, manifests containing private provenance, and weights remain outside Git.

## Candidate-source audit

| Source | Origin | Data terms | Modification | Commercial use | Commercial weight training | Redistribution | V3 status |
|---|---|---|---|---|---|---|---|
| SoccerNet video data | `https://www.soccer-net.org/faq` | Research-only video access under NDA; underlying matches are copyrighted | Research workflow only | **No** | **No commercial use established** | No raw redistribution | Rejected |
| SoccerNet code | `https://github.com/SoccerNet/SoccerNet/blob/master/LICENSE` | MIT code license | Yes | Yes for code | Not a data authorization | Code notice required | Code only, not training data |
| SoccerChat/SoccerNet-derived video | `https://huggingface.co/datasets/SimulaMet/SoccerChat/blob/main/LICENSE` | Non-commercial academic research | Research only | **No** | **No** | No raw video redistribution | Rejected |
| ISSIA-CNR Soccer | historical references; no current authoritative commercial data license verified | License unavailable/unclear | Unverified | Unverified | Unverified | Unverified | Rejected |
| Roboflow Universe community football datasets | source-specific terms vary | No single dataset with verified chain of rights approved in this audit | Unverified per source | Unverified per source | Unverified per source | Unverified per source | Rejected until individual legal audit |
| MatchIQ-authorized local footage | external local source registry plus written authorization | Must be explicit per match/source | Required | Required | Required | Raw redistribution normally disabled | Conditionally eligible |

The MIT license visible in the SoccerNet code repository applies to software, not
to the copyrighted match videos. SoccerNet's official FAQ expressly says its data
is not intended for commercial use and advises commercial projects to collect their
own videos. Therefore no SoccerNet frames are downloaded, extracted, or trained on.

## Required source-registry fields

Every local source must be recorded in external
`vision_dataset_v3/manifests/sources.json` with:

- stable anonymous `source_id`;
- name, author/owner, and non-personal origin reference;
- license/authorization name and reference;
- explicit modification, commercial-use, commercial-training, and redistribution flags;
- attribution obligations;
- media/camera types, available annotations, classes, image count, and MatchIQ relevance;
- status `approved`, `pending`, or `rejected`.

A source is eligible only when all three permissions (modification, commercial use,
commercial weight training) are true and the authorization reference is present.

## RF-DETR format and license boundary

RF-DETR 1.8.3 code and the Small COCO weight remain Apache-2.0 as documented in
`RFDETR_LICENSE_AUDIT.md`. Official RF-DETR documentation accepts COCO datasets in
`train`, `valid`, and `test` directories with `_annotations.coco.json`. The model
license does not grant rights to any future football training images.

## Current availability

- Approved sources: 0
- Approved annotated images: 0
- Approved matches: 0
- Training allowed: no
- Current status: `DATASET_NOT_READY`
