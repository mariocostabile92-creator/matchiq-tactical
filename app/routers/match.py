from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/match", tags=["match"])


def create_match_router(
    get_cached_full_analysis_func,
    generate_match_pdf_func,
    get_optional_user_func,
    is_owner_or_paid_user_func,
    enforce_premium_feature_func,
    enforce_guest_or_user_limit_func,
    logger,
    pdf_public_beta=True,
):
    @router.get("/{match_id}/full-analysis")
    def full_analysis(match_id: int):
        return get_cached_full_analysis_func(match_id)

    return router