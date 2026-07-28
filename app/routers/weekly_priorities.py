from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.weekly_priority import (
    WeeklyPriorityDetailResponse,
    WeeklyPriorityListResponse,
    WeeklyPriorityRecord,
    WeeklyPriorityStaffRequest,
)
from app.services import weekly_priority_service
from usage_guard import require_user


router = APIRouter(prefix="/api/weekly-priorities", tags=["weekly-priorities"])


@router.get("", response_model=WeeklyPriorityListResponse)
def list_weekly_priorities(
    include_dismissed: bool = Query(default=False),
    user=Depends(require_user),
):
    items = weekly_priority_service.list_current(
        int(user["id"]),
        include_dismissed=include_dismissed,
    )
    return WeeklyPriorityListResponse(
        data=[WeeklyPriorityRecord(**item) for item in items]
    )


@router.get("/{priority_id}", response_model=WeeklyPriorityDetailResponse)
def get_weekly_priority(priority_id: str, user=Depends(require_user)):
    item = weekly_priority_service.detail(int(user["id"]), priority_id)
    if not item:
        raise HTTPException(status_code=404, detail="Priorità settimanale non trovata")
    return WeeklyPriorityDetailResponse(data=WeeklyPriorityRecord(**item))


@router.put("/{priority_id}/staff", response_model=WeeklyPriorityDetailResponse)
def update_weekly_priority(
    priority_id: str,
    payload: WeeklyPriorityStaffRequest,
    user=Depends(require_user),
):
    if payload.status == "MODIFIED" and not any(
        (payload.topic, payload.phase, payload.priority_level, payload.staff_reason)
    ):
        raise HTTPException(
            status_code=422,
            detail="Indica almeno una modifica o una motivazione",
        )
    item = weekly_priority_service.set_staff_status(
        int(user["id"]),
        priority_id,
        status=payload.status,
        staff_reason=payload.staff_reason,
        topic=payload.topic,
        phase=payload.phase,
        priority_level=payload.priority_level,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Priorità settimanale non trovata")
    return WeeklyPriorityDetailResponse(data=WeeklyPriorityRecord(**item))
