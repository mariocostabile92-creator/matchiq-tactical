"""
usage_guard.py
MatchIQ Tactical - Usage Guard PRO

V8.0.1 Plan & Limits API

Gestisce:
- controllo limiti Free/Pro/Scout/Owner
- tracking utilizzo API
- blocco feature premium
- risposta JSON elegante per frontend
- limiti frontend-ready per Dashboard / Scout / Export / PDF
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
# OWNER CONFIG
# =========================================================

OWNER_EMAILS = {
    "mario.costabile92@outlook.it"
}


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
    "export_report",
    "full_scout",
    "pro_player_cards",
    "pro_tactical_signals",
}


FEATURE_TO_DAILY_LIMIT = {
    "scout": "scout_daily",
    "full_analysis": "full_analysis_daily",
    "live_matches": "live_matches_daily",
    "pdf_export": "pdf_export_daily",
}


# =========================================================
# PLAN CONFIG - FRONTEND READY
# =========================================================

PLAN_FEATURES = {
    "guest": {
        "label": "Guest",
        "is_guest": True,
        "is_free": False,
        "is_pro": False,
        "is_scout": False,
        "is_owner": False,

        "max_live_matches": 3,
        "scout_enabled": False,
        "scout_preview": True,
        "scout_max_players": 0,
        "player_cards_limit": 0,

        "export_enabled": False,
        "pdf_enabled": False,
        "watchlist_enabled": False,
        "advanced_timeline_enabled": False,
        "advanced_signals_enabled": False,
        "ai_match_insight_enabled": False,

        "cta": "Accedi o crea un account gratuito per provare MatchIQ.",
        "upgrade_message": "Accedi per usare la dashboard e sbloccare la preview Scout."
    },

    "free": {
        "label": "Free",
        "is_guest": False,
        "is_free": True,
        "is_pro": False,
        "is_scout": False,
        "is_owner": False,

        "max_live_matches": 5,
        "scout_enabled": True,
        "scout_preview": True,
        "scout_max_players": 4,
        "player_cards_limit": 4,

        "export_enabled": False,
        "pdf_enabled": False,
        "watchlist_enabled": False,
        "advanced_timeline_enabled": False,
        "advanced_signals_enabled": False,
        "ai_match_insight_enabled": False,

        "cta": "Passa a Pro",
        "upgrade_message": "Passa a Pro per sbloccare Scout completo, export, PDF e segnali avanzati."
    },

    "pro": {
        "label": "Pro",
        "is_guest": False,
        "is_free": False,
        "is_pro": True,
        "is_scout": False,
        "is_owner": False,

        "max_live_matches": 999,
        "scout_enabled": True,
        "scout_preview": False,
        "scout_max_players": 999,
        "player_cards_limit": 999,

        "export_enabled": True,
        "pdf_enabled": True,
        "watchlist_enabled": True,
        "advanced_timeline_enabled": True,
        "advanced_signals_enabled": True,
        "ai_match_insight_enabled": True,

        "cta": "Piano Pro attivo",
        "upgrade_message": "Hai accesso alle funzioni Pro."
    },

    "scout": {
        "label": "Scout",
        "is_guest": False,
        "is_free": False,
        "is_pro": True,
        "is_scout": True,
        "is_owner": False,

        "max_live_matches": 999,
        "scout_enabled": True,
        "scout_preview": False,
        "scout_max_players": 999,
        "player_cards_limit": 999,

        "export_enabled": True,
        "pdf_enabled": True,
        "watchlist_enabled": True,
        "advanced_timeline_enabled": True,
        "advanced_signals_enabled": True,
        "ai_match_insight_enabled": True,

        "cta": "Piano Scout attivo",
        "upgrade_message": "Hai accesso completo alle funzioni Scout."
    },

    "owner": {
        "label": "Owner",
        "is_guest": False,
        "is_free": False,
        "is_pro": True,
        "is_scout": True,
        "is_owner": True,

        "max_live_matches": 999,
        "scout_enabled": True,
        "scout_preview": False,
        "scout_max_players": 999,
        "player_cards_limit": 999,

        "export_enabled": True,
        "pdf_enabled": True,
        "watchlist_enabled": True,
        "advanced_timeline_enabled": True,
        "advanced_signals_enabled": True,
        "ai_match_insight_enabled": True,

        "cta": "Owner Pro",
        "upgrade_message": "Accesso owner completo."
    }
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

    if plan in ["owner", "admin"]:
        return "owner"

    if plan not in ["free", "pro", "scout", "owner"]:
        return "free"

    return plan


def is_owner_user(user):
    if not user:
        return False

    email = str(user.get("email") or "").lower().strip()
    role = str(user.get("role") or "").lower().strip()
    plan = str(
        user.get("plan")
        or user.get("piano")
        or user.get("subscription")
        or ""
    ).lower().strip()

    return (
        email in OWNER_EMAILS
        or role in ["owner", "admin"]
        or plan in ["owner", "admin"]
        or bool(user.get("is_owner"))
    )


def get_effective_plan(user):
    """
    Piano effettivo robusto.
    - None => guest
    - Mario/admin => owner
    - altri => free/pro/scout
    """

    if not user:
        return "guest"

    if is_owner_user(user):
        return "owner"

    raw_plan = (
        user.get("plan")
        or user.get("piano")
        or user.get("subscription")
        or "free"
    )

    return normalize_plan(raw_plan)


def is_pro_user(user):
    plan = get_effective_plan(user)
    return plan in ["pro", "scout", "owner"]


def is_scout_user(user):
    plan = get_effective_plan(user)
    return plan in ["scout", "owner"]


def get_user_plan(user):
    return get_effective_plan(user)


def build_plan_features(plan):
    plan = normalize_plan(plan) if plan != "guest" else "guest"
    return dict(PLAN_FEATURES.get(plan, PLAN_FEATURES["free"]))


def build_frontend_limits(user):
    plan = get_effective_plan(user)
    features = build_plan_features(plan)

    return {
        "plan": plan,
        "label": features["label"],
        "features": features,
        "limits": {
            "max_live_matches": features["max_live_matches"],
            "scout_enabled": features["scout_enabled"],
            "scout_preview": features["scout_preview"],
            "scout_max_players": features["scout_max_players"],
            "player_cards_limit": features["player_cards_limit"],
            "export_enabled": features["export_enabled"],
            "pdf_enabled": features["pdf_enabled"],
            "watchlist_enabled": features["watchlist_enabled"],
            "advanced_timeline_enabled": features["advanced_timeline_enabled"],
            "advanced_signals_enabled": features["advanced_signals_enabled"],
            "ai_match_insight_enabled": features["ai_match_insight_enabled"],
        },
        "cta": features["cta"],
        "upgrade_message": features["upgrade_message"]
    }


def is_feature_enabled_for_user(user, feature):
    plan_data = build_frontend_limits(user)
    limits = plan_data["limits"]

    feature_map = {
        "export_report": "export_enabled",
        "scout_report": "export_enabled",
        "pdf_export": "pdf_enabled",
        "watchlist_cloud": "watchlist_enabled",
        "advanced_timeline": "advanced_timeline_enabled",
        "advanced_scout": "advanced_signals_enabled",
        "ai_match_insight": "ai_match_insight_enabled",
        "full_scout": "advanced_signals_enabled",
        "pro_player_cards": "advanced_signals_enabled",
        "pro_tactical_signals": "advanced_signals_enabled",
    }

    key = feature_map.get(feature)

    if not key:
        return True

    return bool(limits.get(key))


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
    Blocca feature premium per utenti free/guest.
    Owner/Pro/Scout passano.
    """

    if feature == "owner":
        if is_owner_user(user):
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
                "owner_required": True,
                "feature": feature,
                "plan": get_user_plan(user),
                "message": "Questa funzione è riservata all'owner."
            }
        )

    if feature not in PREMIUM_FEATURES:
        return {
            "allowed": True,
            "feature": feature,
            "plan": get_user_plan(user)
        }

    if is_feature_enabled_for_user(user, feature):
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
    Blocca funzioni ultra-pro riservate al piano scout/owner.
    """

    if is_scout_user(user):
        return {
            "allowed": True,
            "feature": "scout_plan",
            "plan": get_user_plan(user)
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

    frontend_limits = build_frontend_limits(user)

    if not user:
        response["usage"] = {
            "plan": "guest",
            "feature": feature,
            "auth_required": True,
            "limits": frontend_limits["limits"],
            "features": frontend_limits["features"],
            "cta": frontend_limits["cta"],
            "upgrade_message": frontend_limits["upgrade_message"]
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
        ),
        "limits": frontend_limits["limits"],
        "features": frontend_limits["features"],
        "cta": frontend_limits["cta"],
        "upgrade_message": frontend_limits["upgrade_message"]
    }

    return response


def build_account_limits_response(user):
    """
    Ritorna limiti piano + utilizzo giornaliero.
    V8.0.1: risposta pronta per frontend Free/Pro UI.
    """

    frontend_limits = build_frontend_limits(user)
    plan = frontend_limits["plan"]

    if not user:
        return {
            "success": True,
            "authenticated": False,
            "auth_required": False,
            "plan": "guest",
            "label": "Guest",
            "limits": frontend_limits["limits"],
            "features": frontend_limits["features"],
            "usage_today": {},
            "cta": frontend_limits["cta"],
            "upgrade_message": frontend_limits["upgrade_message"]
        }

    try:
        db_limits = get_plan_limits(plan)
    except Exception:
        db_limits = {}

    try:
        usage = get_usage_summary(user["id"])
    except Exception:
        usage = {}

    return {
        "success": True,
        "authenticated": True,
        "plan": plan,
        "label": frontend_limits["label"],
        "limits": frontend_limits["limits"],
        "features": frontend_limits["features"],
        "db_limits": db_limits,
        "usage_today": usage,
        "cta": frontend_limits["cta"],
        "upgrade_message": frontend_limits["upgrade_message"]
    }