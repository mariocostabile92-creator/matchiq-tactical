from datetime import datetime

from fastapi import APIRouter, Query

from app.utils.safe import safe_int
from app.utils.cache import cache_valid

router = APIRouter(prefix="/api", tags=["live"])


def create_live_router(
    get_live_matches_func,
    live_matches_cache,
    live_matches_cache_seconds,
):
    @router.get("/live")
    def api_live(top_only: bool = Query(False)):
        return get_live_matches_func(top_only=top_only)

    return router