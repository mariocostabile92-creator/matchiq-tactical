import os

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
@router.get("/{match_id}/live-flow")
def live_flow_analysis(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "live_flow": full["live_flow"]
    }
@router.get("/{match_id}/live-brain")
def live_brain_analysis(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "live_brain": full.get("live_brain", {})
    }
@router.get("/{match_id}/tactical-coach")
def tactical_coach_analysis(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "tactical_coach": full["tactical_coach"]
    }
@router.get("/{match_id}/future-prediction")
def future_prediction_analysis(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    return {
        "match_id": match_id,
        "future_prediction": full["future_prediction"]
    }
@router.get("/{match_id}/pdf-report")
def pdf_report(match_id: int):
    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    try:
        pdf = generate_match_pdf_func(full)

        return {
            "match_id": match_id,
            "success": True,
            "pdf_report": pdf
        }

    except Exception as e:
        return {
            "match_id": match_id,
            "success": False,
            "error": str(e)
        }
@router.get("/{match_id}/download-pdf")
def download_pdf_report(
    match_id: int,
    user=Depends(get_optional_user_func)
):
    if not pdf_public_beta:
        if not is_owner_or_paid_user_func(user):
            enforce_premium_feature_func(
                user=user,
                feature="pdf_export"
            )

        enforce_guest_or_user_limit_func(
            user=user,
            feature="pdf_export",
            endpoint="/api/match/download-pdf"
        )

    full = get_cached_full_analysis_func(match_id)

    if "error" in full:
        return full

    try:
        pdf = generate_match_pdf_func(full)
        pdf_path = pdf.get("pdf_path") if isinstance(pdf, dict) else None

        if not pdf_path:
            return {
                "match_id": match_id,
                "success": False,
                "error": "PDF path non trovato"
            }

        absolute_path = os.path.abspath(pdf_path)

        if not os.path.exists(absolute_path):
            return {
                "match_id": match_id,
                "success": False,
                "error": "PDF non trovato"
            }

        filename = os.path.basename(absolute_path)

        return FileResponse(
            path=absolute_path,
            media_type="application/pdf",
            filename=filename
        )

    except Exception as e:
        logger.exception("PDF DOWNLOAD ERROR")
        return {
            "match_id": match_id,
            "success": False,
            "error": str(e)
        }
