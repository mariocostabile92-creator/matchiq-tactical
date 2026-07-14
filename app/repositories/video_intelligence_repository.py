from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Optional

from database import get_video_asset, update_video_asset_status, utc_now


INTELLIGENCE_KEY = "video_intelligence"


def _metadata(asset: Optional[dict]) -> Dict[str, Any]:
    value = (asset or {}).get("metadata") or {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = {}
    return value if isinstance(value, dict) else {}


def load_project(user_id: int, asset_id: int) -> Optional[Dict[str, Any]]:
    asset = get_video_asset(user_id, asset_id)
    if not asset:
        return None
    project = _metadata(asset).get(INTELLIGENCE_KEY)
    if not isinstance(project, dict):
        return None
    result = deepcopy(project)
    result["video_asset_id"] = asset_id
    result["asset_status"] = asset.get("status") or "ready"
    return result


def save_project(
    user_id: int,
    asset_id: int,
    project: Dict[str, Any],
    *,
    status: str = "processing",
    stage: str = "project",
    progress: int = 0,
    error: str = "",
) -> Optional[Dict[str, Any]]:
    payload = deepcopy(project)
    payload["updated_at"] = utc_now()
    updated = update_video_asset_status(
        user_id=user_id,
        asset_id=asset_id,
        status=status,
        progress=progress,
        stage=stage,
        error=error,
        metadata_patch={INTELLIGENCE_KEY: payload},
    )
    return load_project(user_id, asset_id) if updated else None

