from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import CATEGORY_IDS, CLASS_NAMES


@dataclass(frozen=True, slots=True)
class CategoryDefinition:
    id: int
    name: str
    supercategory: str = "football"

    def to_coco(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "supercategory": self.supercategory}


CATEGORIES = tuple(CategoryDefinition(CATEGORY_IDS[name], name) for name in CLASS_NAMES)


def coco_categories() -> list[dict[str, Any]]:
    return [item.to_coco() for item in CATEGORIES]


def validate_category_schema(categories: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    actual_ids: set[int] = set()
    actual_names: set[str] = set()
    for category in categories:
        try:
            category_id = int(category["id"])
            name = str(category["name"]).strip().lower()
        except (KeyError, TypeError, ValueError):
            errors.append("each category requires an integer id and a name")
            continue
        if category_id in actual_ids:
            errors.append(f"duplicate category id: {category_id}")
        if name in actual_names:
            errors.append(f"duplicate category name: {name}")
        actual_ids.add(category_id)
        actual_names.add(name)
        expected_id = CATEGORY_IDS.get(name)
        if expected_id is None:
            errors.append(f"unsupported V3 category: {name}")
        elif expected_id != category_id:
            errors.append(f"category {name} must use id {expected_id}, got {category_id}")
    missing = set(CLASS_NAMES) - actual_names
    if missing:
        errors.append(f"missing V3 categories: {', '.join(sorted(missing))}")
    return errors


def empty_coco_dataset() -> dict[str, Any]:
    return {
        "info": {
            "description": "MatchIQ Vision Engine V3 football detection dataset",
            "version": "3.0",
        },
        "licenses": [],
        "categories": coco_categories(),
        "images": [],
        "annotations": [],
    }
