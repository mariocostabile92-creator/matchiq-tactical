"""
payments.py
MatchIQ Tactical - Stripe Payments V1

Gestisce:
- creazione checkout Stripe
- piani Pro / Scout
- webhook Stripe
- upgrade automatico piano utente
"""

import os
import stripe

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from auth import get_current_user

from database import (
    update_user_plan,
    create_subscription,
    get_active_subscription
)


# =========================================================
# STRIPE CONFIG
# =========================================================

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

STRIPE_PRICE_PRO_MONTHLY = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "")
STRIPE_PRICE_SCOUT_MONTHLY = os.getenv("STRIPE_PRICE_SCOUT_MONTHLY", "")

FRONTEND_SUCCESS_URL = os.getenv(
    "FRONTEND_SUCCESS_URL",
    "http://127.0.0.1:8000/success.html"
)

FRONTEND_CANCEL_URL = os.getenv(
    "FRONTEND_CANCEL_URL",
    "http://127.0.0.1:8000/pricing.html"
)

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


router = APIRouter(prefix="/api/payments", tags=["Payments"])


# =========================================================
# MODELS
# =========================================================

class CheckoutRequest(BaseModel):
    plan: str


# =========================================================
# HELPERS
# =========================================================

def get_price_id_for_plan(plan: str):
    plan = (plan or "").lower().strip()

    if plan == "pro":
        return STRIPE_PRICE_PRO_MONTHLY

    if plan == "scout":
        return STRIPE_PRICE_SCOUT_MONTHLY

    return None


def validate_stripe_config():
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_SECRET_KEY non configurata"
        )


def get_plan_from_price(price_id: str):
    if price_id == STRIPE_PRICE_PRO_MONTHLY:
        return "pro"

    if price_id == STRIPE_PRICE_SCOUT_MONTHLY:
        return "scout"

    return "free"


# =========================================================
# CHECKOUT
# =========================================================

@router.post("/create-checkout-session")
def create_checkout_session(
    data: CheckoutRequest,
    current_user=Depends(get_current_user)
):
    validate_stripe_config()

    plan = data.plan.lower().strip()
    price_id = get_price_id_for_plan(plan)

    if not price_id:
        raise HTTPException(
            status_code=400,
            detail="Piano non valido o PRICE_ID mancante"
        )

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=current_user["email"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1
                }
            ],
            success_url=FRONTEND_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=FRONTEND_CANCEL_URL,
            metadata={
                "user_id": str(current_user["id"]),
                "plan": plan
            },
            subscription_data={
                "metadata": {
                    "user_id": str(current_user["id"]),
                    "plan": plan
                }
            }
        )

        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id,
            "plan": plan
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# CURRENT SUBSCRIPTION
# =========================================================

@router.get("/subscription")
def current_subscription(current_user=Depends(get_current_user)):
    subscription = get_active_subscription(current_user["id"])

    return {
        "success": True,
        "plan": current_user.get("plan", "free"),
        "subscription": subscription
    }


# =========================================================
# WEBHOOK
# =========================================================

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

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
        raise HTTPException(
            status_code=400,
            detail=f"Webhook non valido: {str(e)}"
        )

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        handle_checkout_completed(obj)

    elif event_type == "customer.subscription.updated":
        handle_subscription_updated(obj)

    elif event_type == "customer.subscription.deleted":
        handle_subscription_deleted(obj)

    elif event_type == "invoice.payment_failed":
        handle_payment_failed(obj)

    return {
        "received": True,
        "type": event_type
    }


# =========================================================
# WEBHOOK HANDLERS
# =========================================================

def handle_checkout_completed(session):
    metadata = session.get("metadata", {}) or {}

    user_id = metadata.get("user_id")
    plan = metadata.get("plan", "pro")

    if not user_id:
        return

    try:
        user_id = int(user_id)
    except Exception:
        return

    subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    update_user_plan(user_id, plan)

    create_subscription(
        user_id=user_id,
        plan=plan,
        provider="stripe",
        provider_customer_id=customer_id or "",
        provider_subscription_id=subscription_id or "",
        current_period_start="",
        current_period_end=""
    )


def handle_subscription_updated(subscription):
    metadata = subscription.get("metadata", {}) or {}

    user_id = metadata.get("user_id")
    plan = metadata.get("plan")

    if not user_id:
        return

    try:
        user_id = int(user_id)
    except Exception:
        return

    if not plan:
        items = subscription.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id")
            plan = get_plan_from_price(price_id)

    status = subscription.get("status", "")

    if status in ["active", "trialing"]:
        update_user_plan(user_id, plan or "pro")
    else:
        update_user_plan(user_id, "free")


def handle_subscription_deleted(subscription):
    metadata = subscription.get("metadata", {}) or {}
    user_id = metadata.get("user_id")

    if not user_id:
        return

    try:
        user_id = int(user_id)
    except Exception:
        return

    update_user_plan(user_id, "free")


def handle_payment_failed(invoice):
    subscription_id = invoice.get("subscription")

    # Per ora non retrocediamo subito a free.
    # Lo farà Stripe con subscription.deleted se il pagamento fallisce definitivamente.
    print("Pagamento fallito:", subscription_id)