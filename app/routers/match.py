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
@router.get("/{match_id}/players")
def player_ratings(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "players_analysis": full["players_analysis"]
    }
@router.get("/{match_id}/pressure")
def pressure_analysis(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "pressure_engine": full["pressure_engine"]
    }
@router.get("/{match_id}/win-probability")
def win_probability_analysis(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "win_probability": full["win_probability"]
    }
@router.get("/{match_id}/xg")
def xg_analysis(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "xg_analysis": full["xg_analysis"]
    }
@router.get("/{match_id}/ai-commentary")
def ai_commentary_analysis(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "ai_commentary": full.get("ai_commentary", {})
    }
@router.get("/{match_id}/live-engine")
def live_engine_analysis(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "live_engine": full["live_engine"]
    }