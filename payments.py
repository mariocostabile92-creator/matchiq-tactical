"""
payments.py
MatchIQ Tactical - Stripe Payments V8.1.2 Production

Gestisce:
- Checkout Stripe per MatchIQ Pro mensile / annuale
- Blocco checkout per utenti già Pro/Admin/Owner
- Stripe Customer Portal per gestione abbonamento
- Webhook Stripe sicuro
- Upgrade automatico users.plan = 'pro'
- Downgrade a free su cancellazione abbonamento
- Compatibilità con database.py V8.1
"""

import os
import logging
from typing import Optional

import stripe
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from auth import get_current_user

from database import (
    update_user_plan,
    create_subscription,
    get_active_subscription,
    get_user_by_email,
    get_user_by_stripe_customer,
    get_subscription_by_provider_id,
)

try:
    from database import (
        update_user_stripe_customer,
        upsert_subscription_by_provider,
    )
except Exception:
    update_user_stripe_customer = None
    upsert_subscription_by_provider = None


logger = logging.getLogger("matchiq.payments")

router = APIRouter(prefix="/api/payments", tags=["Payments"])


# =========================================================
# STRIPE CONFIG
# =========================================================

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

STRIPE_PRICE_PRO_MONTHLY = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "").strip()
STRIPE_PRICE_PRO_YEARLY = os.getenv("STRIPE_PRICE_PRO_YEARLY", "").strip()

APP_BASE_URL = os.getenv(
    "APP_BASE_URL",
    "https://matchiq-tactical-production.up.railway.app"
).rstrip("/")

OWNER_EMAILS = {
    "mario.costabile92@outlook.it",
}

PROTECTED_PLANS = {
    "pro",
    "admin",
    "owner",
    "scout",
    "pro_monthly",
    "pro_yearly",
}

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# =========================================================
# MODELS
# =========================================================

class CheckoutRequest(BaseModel):
    plan: str = "pro_monthly"


# =========================================================
# HELPERS
# =========================================================

def validate_stripe_config():
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_SECRET_KEY non configurata"
        )

    if not (
        STRIPE_SECRET_KEY.startswith("sk_live_")
        or STRIPE_SECRET_KEY.startswith("sk_test_")
        or STRIPE_SECRET_KEY.startswith("rk_live_")
        or STRIPE_SECRET_KEY.startswith("rk_test_")
    ):
        logger.warning(
            "[STRIPE] STRIPE_SECRET_KEY ha prefisso inatteso: %s",
            STRIPE_SECRET_KEY[:3]
        )


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def normalize_user_plan(plan: str) -> str:
    return str(plan or "").strip().lower()


def is_owner_email(email: str) -> bool:
    return normalize_email(email) in OWNER_EMAILS


def is_paid_plan(plan: str) -> bool:
    return normalize_user_plan(plan) in PROTECTED_PLANS


def normalize_checkout_plan(plan: str) -> str:
    value = (plan or "").lower().strip()

    aliases = {
        "pro": "pro_monthly",
        "monthly": "pro_monthly",
        "mensile": "pro_monthly",
        "pro_mensile": "pro_monthly",
        "pro_monthly": "pro_monthly",

        "yearly": "pro_yearly",
        "annual": "pro_yearly",
        "annuale": "pro_yearly",
        "pro_annuale": "pro_yearly",
        "pro_yearly": "pro_yearly",
    }

    return aliases.get(value, "pro_monthly")


def get_price_id_for_checkout_plan(plan: str) -> Optional[str]:
    normalized = normalize_checkout_plan(plan)

    if normalized == "pro_monthly":
        return STRIPE_PRICE_PRO_MONTHLY

    if normalized == "pro_yearly":
        return STRIPE_PRICE_PRO_YEARLY

    return None


def get_public_plan_from_checkout_plan(plan: str) -> str:
    normalized = normalize_checkout_plan(plan)

    if normalized in ["pro_monthly", "pro_yearly"]:
        return "pro"

    return "free"


def get_plan_from_price(price_id: str) -> str:
    if price_id and price_id == STRIPE_PRICE_PRO_MONTHLY:
        return "pro"

    if price_id and price_id == STRIPE_PRICE_PRO_YEARLY:
        return "pro"

    return "free"


def get_billing_interval_from_price(price_id: str) -> str:
    if price_id and price_id == STRIPE_PRICE_PRO_YEARLY:
        return "yearly"

    if price_id and price_id == STRIPE_PRICE_PRO_MONTHLY:
        return "monthly"

    return ""


def safe_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def ts_to_iso(value) -> str:
    if not value:
        return ""

    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except Exception:
        return ""




def stripe_obj_to_dict(obj):
    """Converte in modo sicuro StripeObject/list/dict in strutture Python normali."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    try:
        return obj.to_dict_recursive()
    except Exception:
        pass
    try:
        return dict(obj)
    except Exception:
        return {}


def extract_subscription_period(subscription) -> tuple[str, str]:
    subscription = stripe_obj_to_dict(subscription)
    current_period_start = subscription.get("current_period_start") or ""
    current_period_end = subscription.get("current_period_end") or ""

    return (
        ts_to_iso(current_period_start),
        ts_to_iso(current_period_end),
    )


def get_user_id_from_metadata(metadata) -> Optional[int]:
    metadata = stripe_obj_to_dict(metadata)
    if not metadata:
        return None

    raw = metadata.get("user_id")

    if not raw:
        return None

    try:
        return int(raw)
    except Exception:
        return None


def resolve_user_id_from_stripe_object(obj) -> Optional[int]:
    """Recupera user_id anche se Stripe non invia metadata.user_id."""
    data = stripe_obj_to_dict(obj)
    metadata = stripe_obj_to_dict(data.get("metadata", {}) or {})
    user_id = get_user_id_from_metadata(metadata)
    if user_id:
        return user_id

    subscription_id = data.get("id") or data.get("subscription") or data.get("subscription_id") or ""
    if subscription_id:
        try:
            saved_subscription = stripe_obj_to_dict(get_subscription_by_provider_id(subscription_id))
            if saved_subscription and saved_subscription.get("user_id"):
                return int(saved_subscription["user_id"])
        except Exception:
            logger.exception("[STRIPE] fallback user_id da provider_subscription_id fallito")

    customer_id = data.get("customer") or data.get("customer_id") or data.get("provider_customer_id") or ""
    if customer_id:
        try:
            user = stripe_obj_to_dict(get_user_by_stripe_customer(customer_id))
            if user and user.get("id"):
                return int(user["id"])
        except Exception:
            logger.exception("[STRIPE] fallback user_id da stripe_customer_id fallito")

    email = normalize_email(data.get("customer_email") or data.get("email") or data.get("receipt_email") or "")
    if email:
        try:
            user = stripe_obj_to_dict(get_user_by_email(email))
            if user and user.get("id"):
                return int(user["id"])
        except Exception:
            logger.exception("[STRIPE] fallback user_id da email fallito")

    return None


def get_subscription_first_price_id(subscription) -> str:
    subscription = stripe_obj_to_dict(subscription)
    try:
        items = subscription.get("items", {}).get("data", [])
        if not items:
            return ""

        price = items[0].get("price", {}) or {}
        return price.get("id") or ""
    except Exception:
        return ""


def get_subscription_customer_id(subscription: dict) -> str:
    if not subscription:
        return ""

    return (
        subscription.get("provider_customer_id")
        or subscription.get("stripe_customer_id")
        or subscription.get("customer_id")
        or subscription.get("customer")
        or ""
    )


def get_current_user_plan(current_user: dict) -> str:
    return normalize_user_plan(
        current_user.get("plan")
        or current_user.get("piano")
        or "free"
    )


def user_already_has_paid_access(current_user: dict) -> tuple[bool, str]:
    email = normalize_email(current_user.get("email"))
    plan = get_current_user_plan(current_user)

    if is_owner_email(email):
        return True, "Account owner/admin già abilitato a Pro."

    if is_paid_plan(plan):
        return True, "Hai già un piano Pro attivo."

    try:
        user_id = current_user.get("id")
        if user_id:
            active_subscription = get_active_subscription(user_id)
            if active_subscription:
                return True, "Hai già un abbonamento attivo."
    except Exception:
        logger.exception("[STRIPE] Impossibile verificare subscription attiva")

    return False, ""


def upsert_subscription_safe(
    user_id: int,
    plan: str,
    customer_id: str,
    subscription_id: str,
    status: str = "active",
    current_period_start: str = "",
    current_period_end: str = "",
):
    if update_user_stripe_customer and customer_id:
        try:
            update_user_stripe_customer(user_id, customer_id)
        except Exception:
            logger.exception("[STRIPE] update_user_stripe_customer failed")

    if upsert_subscription_by_provider and subscription_id:
        try:
            return upsert_subscription_by_provider(
                user_id=user_id,
                plan=plan,
                status=status,
                provider="stripe",
                provider_customer_id=customer_id or "",
                provider_subscription_id=subscription_id or "",
                current_period_start=current_period_start or "",
                current_period_end=current_period_end or "",
            )
        except Exception:
            logger.exception("[STRIPE] upsert_subscription_by_provider failed, fallback create_subscription")

    try:
        return create_subscription(
            user_id=user_id,
            plan=plan,
            provider="stripe",
            provider_customer_id=customer_id or "",
            provider_subscription_id=subscription_id or "",
            current_period_start=current_period_start or "",
            current_period_end=current_period_end or "",
        )
    except Exception:
        logger.exception("[STRIPE] create_subscription failed")
        return None


# =========================================================
# CHECKOUT
# =========================================================

@router.post("/create-checkout-session")
def create_checkout_session(
    data: CheckoutRequest,
    current_user=Depends(get_current_user)
):
    validate_stripe_config()

    if not isinstance(current_user, dict):
        raise HTTPException(status_code=401, detail="Utente non autenticato")

    user_id = current_user.get("id")
    email = current_user.get("email")

    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Utente non valido")

    already_paid, already_paid_message = user_already_has_paid_access(current_user)

    if already_paid:
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "ok": False,
                "already_pro": True,
                "message": already_paid_message,
                "plan": current_user.get("plan") or current_user.get("piano") or "pro",
                "email": normalize_email(email)
            }
        )

    checkout_plan = normalize_checkout_plan(data.plan)
    public_plan = get_public_plan_from_checkout_plan(checkout_plan)
    price_id = get_price_id_for_checkout_plan(checkout_plan)

    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=f"Price ID mancante per piano {checkout_plan}"
        )

    success_url = (
        f"{APP_BASE_URL}/index.html"
        f"?payment=success"
        f"&plan={checkout_plan}"
        f"&session_id={{CHECKOUT_SESSION_ID}}"
        f"&v=10051"
    )

    cancel_url = (
        f"{APP_BASE_URL}/index.html"
        f"?payment=cancel"
        f"&plan={checkout_plan}"
        f"&v=10051"
    )

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=str(email).lower().strip(),
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user_id),
                "plan": public_plan,
                "checkout_plan": checkout_plan,
                "billing_interval": get_billing_interval_from_price(price_id)
            },
            subscription_data={
                "metadata": {
                    "user_id": str(user_id),
                    "plan": public_plan,
                    "checkout_plan": checkout_plan,
                    "billing_interval": get_billing_interval_from_price(price_id)
                }
            },
            allow_promotion_codes=True
        )

        return {
            "success": True,
            "ok": True,
            "checkout_url": session.url,
            "url": session.url,
            "session_id": session.id,
            "plan": public_plan,
            "checkout_plan": checkout_plan,
            "price_id": price_id
        }

    except stripe.error.AuthenticationError as e:
        logger.exception("[STRIPE] Authentication error")
        raise HTTPException(
            status_code=500,
            detail=f"Stripe authentication error: {str(e)}"
        )

    except stripe.error.StripeError as e:
        logger.exception("[STRIPE] Stripe error")
        raise HTTPException(
            status_code=500,
            detail=f"Stripe error: {str(e)}"
        )

    except Exception as e:
        logger.exception("[STRIPE] Checkout session error")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/checkout")
def create_checkout_session_alias(
    data: CheckoutRequest,
    current_user=Depends(get_current_user)
):
    return create_checkout_session(data, current_user)


# =========================================================
# CUSTOMER PORTAL
# =========================================================

@router.post("/create-portal-session")
def create_portal_session(current_user=Depends(get_current_user)):
    validate_stripe_config()

    if not isinstance(current_user, dict):
        raise HTTPException(status_code=401, detail="Utente non autenticato")

    user_id = current_user.get("id")
    email = normalize_email(current_user.get("email"))
    plan = get_current_user_plan(current_user)

    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Utente non valido")

    if is_owner_email(email):
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "ok": False,
                "owner": True,
                "message": "Account owner/admin: non hai un abbonamento Stripe da gestire.",
                "plan": "owner",
                "email": email
            }
        )

    active_subscription = None

    try:
        active_subscription = get_active_subscription(user_id)
    except Exception:
        logger.exception("[STRIPE] get_active_subscription failed in customer portal")

    customer_id = get_subscription_customer_id(active_subscription or {})

    if not customer_id:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "ok": False,
                "no_subscription": True,
                "message": "Nessun abbonamento Stripe attivo trovato per questo account.",
                "plan": plan,
                "email": email
            }
        )

    return_url = f"{APP_BASE_URL}/account.html?portal=return&v=10051"

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )

        return {
            "success": True,
            "ok": True,
            "portal_url": session.url,
            "url": session.url,
            "customer_id": customer_id
        }

    except stripe.error.StripeError as e:
        logger.exception("[STRIPE] Customer portal error")
        raise HTTPException(
            status_code=500,
            detail=f"Stripe portal error: {str(e)}"
        )

    except Exception as e:
        logger.exception("[STRIPE] Customer portal generic error")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# CURRENT SUBSCRIPTION
# =========================================================

@router.get("/subscription")
def current_subscription(current_user=Depends(get_current_user)):
    if not isinstance(current_user, dict):
        raise HTTPException(status_code=401, detail="Utente non autenticato")

    subscription = get_active_subscription(current_user["id"])

    return {
        "success": True,
        "ok": True,
        "plan": current_user.get("plan") or current_user.get("piano") or "free",
        "is_owner": is_owner_email(current_user.get("email")),
        "email": normalize_email(current_user.get("email")),
        "subscription": subscription
    }


# =========================================================
# STRIPE HEALTH
# =========================================================

@router.get("/stripe-status")
def stripe_status():
    return {
        "ok": True,
        "stripe_secret_configured": bool(STRIPE_SECRET_KEY),
        "stripe_secret_prefix": STRIPE_SECRET_KEY[:7] + "..." if STRIPE_SECRET_KEY else "",
        "webhook_secret_configured": bool(STRIPE_WEBHOOK_SECRET),
        "price_pro_monthly_configured": bool(STRIPE_PRICE_PRO_MONTHLY),
        "price_pro_yearly_configured": bool(STRIPE_PRICE_PRO_YEARLY),
        "app_base_url": APP_BASE_URL,
        "customer_portal_endpoint": "/api/payments/create-portal-session"
    }


# =========================================================
# WEBHOOK
# =========================================================

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("[STRIPE] STRIPE_WEBHOOK_SECRET non configurato")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=STRIPE_WEBHOOK_SECRET
            )
        else:
            event = stripe.Event.construct_from(
                await request.json(),
                stripe.api_key
            )

    except Exception as e:
        logger.exception("[STRIPE] Webhook invalid")
        raise HTTPException(
            status_code=400,
            detail=f"Webhook non valido: {str(e)}"
        )

    event_type = event["type"]
    obj = event["data"]["object"]

    logger.info("[STRIPE WEBHOOK] %s", event_type)

    try:
        if event_type == "checkout.session.completed":
            handle_checkout_completed(obj)

        elif event_type == "customer.subscription.created":
            handle_subscription_updated(obj)

        elif event_type == "customer.subscription.updated":
            handle_subscription_updated(obj)

        elif event_type == "customer.subscription.deleted":
            handle_subscription_deleted(obj)

        elif event_type == "invoice.payment_failed":
            handle_payment_failed(obj)

        elif event_type == "invoice.payment_succeeded":
            handle_payment_succeeded(obj)

    except Exception:
        logger.exception("[STRIPE WEBHOOK] Handler failed")
        raise HTTPException(status_code=500, detail="Errore gestione webhook")

    return {
        "received": True,
        "ok": True,
        "type": event_type
    }


# =========================================================
# WEBHOOK HANDLERS
# =========================================================

def handle_checkout_completed(session):
    session = stripe_obj_to_dict(session)
    metadata = session.get("metadata", {}) or {}

    user_id = get_user_id_from_metadata(metadata)
    public_plan = metadata.get("plan") or "pro"

    if not user_id:
        logger.warning("[STRIPE] checkout.session.completed senza user_id")
        return

    subscription_id = session.get("subscription") or ""
    customer_id = session.get("customer") or ""

    period_start = ""
    period_end = ""

    if subscription_id:
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            period_start, period_end = extract_subscription_period(subscription)
        except Exception:
            logger.exception("[STRIPE] impossibile recuperare subscription period")

    update_user_plan(user_id, public_plan)

    upsert_subscription_safe(
        user_id=user_id,
        plan=public_plan,
        customer_id=customer_id,
        subscription_id=subscription_id,
        status="active",
        current_period_start=period_start,
        current_period_end=period_end
    )

    logger.info("[STRIPE] User %s upgraded to %s", user_id, public_plan)


def handle_subscription_updated(subscription):
    subscription = stripe_obj_to_dict(subscription)
    metadata = stripe_obj_to_dict(subscription.get("metadata", {}) or {})

    user_id = resolve_user_id_from_stripe_object(subscription)

    if not user_id:
        logger.warning(
            "[STRIPE] subscription.updated senza user_id recuperabile subscription=%s customer=%s",
            subscription.get("id") or "",
            subscription.get("customer") or ""
        )
        return

    price_id = get_subscription_first_price_id(subscription)
    plan = metadata.get("plan") or get_plan_from_price(price_id) or "pro"

    status = subscription.get("status") or ""
    customer_id = subscription.get("customer") or ""
    subscription_id = subscription.get("id") or ""

    period_start, period_end = extract_subscription_period(subscription)

    if status in ["active", "trialing"]:
        update_user_plan(user_id, plan)

        upsert_subscription_safe(
            user_id=user_id,
            plan=plan,
            customer_id=customer_id,
            subscription_id=subscription_id,
            status="active",
            current_period_start=period_start,
            current_period_end=period_end
        )

        logger.info("[STRIPE] Subscription active user=%s plan=%s", user_id, plan)

    elif status in ["past_due", "unpaid", "incomplete", "incomplete_expired", "canceled"]:
        update_user_plan(user_id, "free")

        upsert_subscription_safe(
            user_id=user_id,
            plan="free",
            customer_id=customer_id,
            subscription_id=subscription_id,
            status=status,
            current_period_start=period_start,
            current_period_end=period_end
        )

        logger.info("[STRIPE] Subscription inactive user=%s status=%s", user_id, status)


def handle_subscription_deleted(subscription):
    subscription = stripe_obj_to_dict(subscription)
    metadata = stripe_obj_to_dict(subscription.get("metadata", {}) or {})

    user_id = resolve_user_id_from_stripe_object(subscription)

    if not user_id:
        logger.warning(
            "[STRIPE] subscription.deleted senza user_id recuperabile subscription=%s customer=%s",
            subscription.get("id") or "",
            subscription.get("customer") or ""
        )
        return

    customer_id = subscription.get("customer") or ""
    subscription_id = subscription.get("id") or ""
    period_start, period_end = extract_subscription_period(subscription)

    update_user_plan(user_id, "free")

    upsert_subscription_safe(
        user_id=user_id,
        plan="free",
        customer_id=customer_id,
        subscription_id=subscription_id,
        status="cancelled",
        current_period_start=period_start,
        current_period_end=period_end
    )

    logger.info("[STRIPE] Subscription deleted user=%s downgraded free", user_id)


def handle_payment_failed(invoice):
    invoice = stripe_obj_to_dict(invoice)
    subscription_id = invoice.get("subscription") or ""
    customer_id = invoice.get("customer") or ""

    logger.warning(
        "[STRIPE] Pagamento fallito subscription=%s customer=%s",
        subscription_id,
        customer_id
    )


def handle_payment_succeeded(invoice):
    invoice = stripe_obj_to_dict(invoice)
    subscription_id = invoice.get("subscription") or ""
    customer_id = invoice.get("customer") or ""

    logger.info(
        "[STRIPE] Pagamento riuscito subscription=%s customer=%s",
        subscription_id,
        customer_id
    )