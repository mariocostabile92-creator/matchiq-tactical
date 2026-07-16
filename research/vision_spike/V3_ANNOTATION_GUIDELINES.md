# MatchIQ Vision Engine V3 - Annotation Guidelines

Version 1.0, frozen before the first production-eligible annotation batch.

## Scope and format

Use COCO object detection boxes with the fixed category mapping:

| ID | Class | Meaning |
|---:|---|---|
| 1 | `player` | Active outfield player on the pitch |
| 2 | `goalkeeper` | Goalkeeper identifiable from match context |
| 3 | `referee` | Referee or assistant referee clearly identifiable |
| 4 | `ball` | Visible football, including identifiable partial occlusion |

Boxes must be tight around the visible object, remain inside image bounds, and use
COCO `[x, y, width, height]` pixels. Never infer identity, team, jersey number, or
role from position alone. Mark uncertain/difficult cases in annotation attributes;
do not force a class when evidence is insufficient.

## Player

Annotate a person actively participating on the field, including small distant
players, partially occluded players, players on the ground, and players close to
the touchline. Do not annotate coaches, staff, spectators, ball persons, or inactive
bench occupants as `player`.

## Goalkeeper

Use `goalkeeper` only when kit and match context make the role identifiable. If a
distant or ambiguous figure cannot reliably be distinguished, use `player` and set
`attributes.role_uncertain=true`, or use an ignore region if the annotation tool
supports it. Do not infer goalkeeper solely from location in the penalty area.

## Referee

Annotate referees and assistant referees only when kit/context are clear. Do not
force the class for a small ambiguous person. Fourth officials and technical-area
staff are not `referee` unless they are visibly officiating the match action.

## Ball

Use a tight box around the visible ball. Annotate partial occlusion when the ball
is still identifiable. Add `attributes.difficult=true` for extremely small,
motion-blurred, or heavily occluded balls. Do not annotate white field marks,
advertising, socks, heads, or compression artifacts. Never invent the ball position.

## Non-field people and negative images

Spectators, coaches, staff, substitutes, ball persons, and unrelated people are
background in V3. Include representative hard-negative images and mark empty
images with `is_negative=true` in image metadata. A future `non_field_person` class
may be evaluated only after enough consistent labels exist and an ablation proves
that it reduces false positives without harming touchline players.

## Occlusion, truncation, and visibility

- `attributes.occluded=true`: a meaningful portion is hidden.
- `attributes.truncated=true`: the object crosses the image boundary.
- `attributes.difficult=true`: extremely small, blurred, or ambiguous but still valid.
- `attributes.role_uncertain=true`: person is real but goalkeeper/referee role is uncertain.

Exclude objects that cannot be localized with a defensible box. Tiny objects below
4 pixels in either dimension require reviewer confirmation.

## Quality control

- Double-review at least 10% of images.
- Resolve every player/goalkeeper/referee disagreement before freezing a split.
- Review all ball boxes and all negative images.
- Include crowd, bench, technical-area, shadow, glare, night, compression, and
  touchline examples as hard cases.
- Keep frames from the same match in one split only.
- Never annotate or redistribute footage without an approved source registry entry.
