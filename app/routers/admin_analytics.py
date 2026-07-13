import logging

from fastapi import APIRouter, Depends, HTTPException

from app.routers.admin_beta import require_admin_token
from database import get_admin_analytics

logger = logging.getLogger("matchiq")

router = APIRouter()


@router.get("/api/admin/analytics")
def admin_analytics(admin_ok: bool = Depends(require_admin_token)):
    try:
        data = get_admin_analytics()
        return {
            "ok": True,
            **data
        }
    except Exception:
        logger.exception("[ADMIN ANALYTICS] Errore caricamento analytics")
        raise HTTPException(status_code=500, detail="Impossibile caricare le analytics")
