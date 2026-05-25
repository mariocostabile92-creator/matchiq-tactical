"""
usage_guard.py
MatchIQ Tactical - Usage Guard PRO

Gestisce:
- controllo limiti Free/Pro/Scout
- tracking utilizzo API
- blocco feature premium
- risposta JSON elegante per frontend
"""

from fastapi import HTTPException, Header

from security import decode_access_token

from database import (
    get_user_by_id,
    get_plan_limits,
    can_use_feature,
    track_api_usage,
    get_today_usage,
    get_usage_summary
)


# =========================================================
# FEATURE CONFIG
# =========================================================

PREMIUM_FEATURES = {
    "advanced_scout",
    "advanced_timeline",
    "pdf_export",
    "scout_report",
    "watchlist_cloud",
    "ai_match_insight",
}


FEATURE_TO_DAILY_LIMIT = {
    "scout": "scout_daily",
    "full_analysis": "full_analysis_daily",
    "live_matches": "live_matches_daily",
    "pdf_export": "pdf_export_daily",
}


# =========================================================
# AUTH HELPERS
# =========================================================

def get_optional_user(authorization: str = Header(None)):
    """
    Ritorna user se token valido.
    Se token mancante/non valido, ritorna None.
    Utile per endpoint pubblici con limiti guest/free.
    """

    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_access_token(token)

    if not payload:
        return None

    try:
        user_id = int(payload.get("sub"))
    except Exception:
        return None

    user = get_user_by_id(user_id)

    if not user:
        return None

    if not user.get("is_active"):
        return None

    return user


def require_user(authorization: str = Header(None)):
    """
    Richiede login obbligatorio.
    """

    user = get_optional_user(authorization)

    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "auth_required": True,
                "message": "Login richiesto per usare questa funzione."
            }
        )

    return user


# =========================================================
# PLAN HELPERS
# =========================================================

def normalize_plan(plan: str):
    plan = (plan or "free").lower().strip()

    if plan not in ["free", "pro", "scout"]:
        return "free"

    return plan


def is_pro_user(user):
    if not user:
        return False

    plan = normalize_plan(user.get("plan"))

    return plan in ["pro", "scout"]


def is_scout_user(user):
    if not user:
        return False

    return normalize_plan(user.get("plan")) == "scout"


def get_user_plan(user):
    if not user:
        return "guest"

    return normalize_plan(user.get("plan"))


# =========================================================
# LIMIT CHECKS
# =========================================================

def build_limit_response(feature, user, usage_check):
    plan = get_user_plan(user)

    return {
        "success": False,
        "allowed": False,
        "upgrade_required": True,
        "feature": feature,
        "plan": plan,
        "used": usage_check.get("used", 0),
        "limit": usage_check.get("limit", 0),
        "message": (
            f"Hai raggiunto il limite giornaliero per {feature}. "
            "Passa a Pro per continuare."
        )
    }


def check_daily_limit(user, feature):
    """
    Controlla limite giornaliero da database.py.
    """

    if not user:
        return {
            "allowed": False,
            "reason": "Login richiesto",
            "used": 0,
            "limit": 0,
            "plan": "guest"
        }

    return can_use_feature(
        user_id=user["id"],
        feature=feature
    )


def enforce_daily_limit(user, feature, endpoint):
    """
    Blocca se il limite è raggiunto.
    Se ok, traccia utilizzo.
    """

    usage_check = check_daily_limit(user, feature)

    if not usage_check.get("allowed"):
        raise HTTPException(
            status_code=402,
            detail=build_limit_response(
                feature=feature,
                user=user,
                usage_check=usage_check
            )
        )

    track_api_usage(
        user_id=user["id"],
        endpoint=endpoint,
        feature=feature
    )

    return {
        "allowed": True,
        "feature": feature,
        "plan": get_user_plan(user),
        "used": usage_check.get("used", 0) + 1,
        "limit": usage_check.get("limit")
    }


# =========================================================
# PREMIUM CHECKS
# =========================================================

def enforce_premium_feature(user, feature):
    """
    Blocca feature premium per utenti free.
    """

    if feature not in PREMIUM_FEATURES:
        return {
            "allowed": True,
            "feature": feature,
            "plan": get_user_plan(user)
        }

    if is_pro_user(user):
        return {
            "allowed": True,
            "feature": feature,
            "plan": get_user_plan(user)
        }

    raise HTTPException(
        status_code=402,
        detail={
            "success": False,
            "allowed": False,
            "upgrade_required": True,
            "feature": feature,
            "plan": get_user_plan(user),
            "message": "Questa funzione è disponibile solo con il piano Pro."
        }
    )


def enforce_scout_feature(user):
    """
    Blocca funzioni ultra-pro riservate al piano scout.
    """

    if is_scout_user(user):
        return {
            "allowed": True,
            "feature": "scout_plan",
            "plan": "scout"
        }

    raise HTTPException(
        status_code=402,
        detail={
            "success": False,
            "allowed": False,
            "upgrade_required": True,
            "feature": "scout_plan",
            "plan": get_user_plan(user),
            "message": "Questa funzione è disponibile solo con il piano Scout."
        }
    )


# =========================================================
# GUEST MODE
# =========================================================

def enforce_guest_or_user_limit(user, feature, endpoint):
    """
    Per ora:
    - guest non autorizzato sulle feature pesanti
    - utenti loggati controllati tramite DB
    """

    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "auth_required": True,
                "feature": feature,
                "message": "Devi effettuare il login per usare questa funzione."
            }
        )

    return enforce_daily_limit(
        user=user,
        feature=feature,
        endpoint=endpoint
    )


# =========================================================
# RESPONSE HELPERS
# =========================================================

def attach_usage_info(response, user, feature):
    """
    Aggiunge info uso al JSON di risposta.
    """

    if not isinstance(response, dict):
        return response

    if not user:
        response["usage"] = {
            "plan": "guest",
            "feature": feature,
            "auth_required": True
        }
        return response

    used = get_today_usage(
        user_id=user["id"],
        feature=feature
    )

    usage_check = can_use_feature(
        user_id=user["id"],
        feature=feature
    )

    response["usage"] = {
        "plan": get_user_plan(user),
        "feature": feature,
        "used": used,
        "limit": usage_check.get("limit"),
        "remaining": (
            None
            if usage_check.get("limit") is None
            else max(0, usage_check.get("limit") - used)
        )
    }

    return response


def build_account_limits_response(user):
    """
    Ritorna limiti piano + utilizzo giornaliero.
    """

    if not user:
        return {
            "success": False,
            "auth_required": True,
            "message": "Login richiesto"
        }

    plan = get_user_plan(user)
    limits = get_plan_limits(plan)
    usage = get_usage_summary(user["id"])

    return {
        "success": True,
        "plan": plan,
        "limits": limits,
        "usage_today": usage
    }