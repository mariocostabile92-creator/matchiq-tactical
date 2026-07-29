import logging
from typing import Any, Dict, Iterable, Optional


PIPELINE_LOGGER = logging.getLogger("matchiq.intelligence.pipeline")
PIPELINE_STATUSES = {"START", "SUCCESS", "SKIPPED", "FAILED"}


def canonical_ids(values: Iterable[Any]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def log_pipeline_step(
    *,
    step: str,
    status: str,
    user_id: int,
    canonical_match_id: str,
    detail: Optional[Dict[str, Any]] = None,
    exc_info: bool = False,
) -> None:
    normalized_status = str(status or "").upper()
    if normalized_status not in PIPELINE_STATUSES:
        raise ValueError(f"Unsupported pipeline status: {status}")
    event = {
        "event": "intelligence_pipeline",
        "step": str(step),
        "status": normalized_status,
        "user_id": int(user_id),
        "canonical_match_id": str(canonical_match_id),
        "detail": detail or {},
    }
    level = logging.ERROR if normalized_status == "FAILED" else logging.INFO
    PIPELINE_LOGGER.log(
        level,
        "intelligence_pipeline step=%s status=%s canonical_match_id=%s",
        event["step"],
        event["status"],
        event["canonical_match_id"],
        extra={"pipeline_event": event},
        exc_info=exc_info,
    )
