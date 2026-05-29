"""
auth.py
MatchIQ Tactical - Auth Routes V8.2 Password Reset

Gestisce:
- registrazione utenti
- login utenti
- profilo utente autenticato
- piani free/pro/scout/owner
- richiesta reset password
- conferma reset password
"""

import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr

from database import (
    init_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    create_password_reset_token,
    get_valid_password_reset_token,
    mark_password_reset_token_used,
    update_user_password,
)

from security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)


router = APIRouter(prefix="/api/auth", tags=["Auth"])


# =========================================================
# CONFIG
# =========================================================

APP_PUBLIC_URL = os.getenv(
    "APP_PUBLIC_URL",
    "https://matchiq-tactical-production.up.railway.app"
).rstrip("/")

PASSWORD_RESET_TOKEN_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "30"))

# In produzione possiamo tenere questo a 0 quando avremo email automatica.
# Per ora serve per testare il reset senza SMTP.
PASSWORD_RESET_EXPOSE_LINK = os.getenv("PASSWORD_RESET_EXPOSE_LINK", "1") == "1"


# =========================================================
# MODELS
# =========================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    password: str


# =========================================================
# HELPERS
# =========================================================

def utc_now_dt():
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime):
    return dt.astimezone(timezone.utc).isoformat()


def hash_reset_token(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_reset_link(token: str):
    return f"{APP_PUBLIC_URL}/reset-password.html?token={token}"


def parse_iso_datetime(value: str):
    if not value:
        return None

    try:
        fixed = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(fixed)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token mancante")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token non valido")

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Token scaduto o non valido")

    user_id = int(payload.get("sub"))
    user = get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="Utente non trovato")

    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="Utente disattivato")

    return user


# =========================================================
# AUTH ROUTES
# =========================================================

@router.post("/register")
def register(data: RegisterRequest):
    init_db()

    email = data.email.lower().strip()

    existing_user = get_user_by_email(email)

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email già registrata"
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="La password deve contenere almeno 6 caratteri"
        )

    password_hash = hash_password(data.password)

    user_id = create_user(
        email=email,
        password_hash=password_hash,
        plan="free"
    )

    user = get_user_by_id(user_id)

    token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        plan=user["plan"]
    )

    return {
        "success": True,
        "message": "Registrazione completata",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "plan": user["plan"]
        }
    }


@router.post("/login")
def login(data: LoginRequest):
    init_db()

    email = data.email.lower().strip()
    user = get_user_by_email(email)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email o password non corretti"
        )

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Email o password non corretti"
        )

    if not user.get("is_active"):
        raise HTTPException(
            status_code=403,
            detail="Utente disattivato"
        )

    token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        plan=user["plan"]
    )

    return {
        "success": True,
        "message": "Login effettuato",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "plan": user["plan"]
        }
    }


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return {
        "success": True,
        "user": {
            "id": current_user["id"],
            "email": current_user["email"],
            "plan": current_user["plan"],
            "is_active": current_user["is_active"],
            "created_at": current_user["created_at"]
        }
    }


# =========================================================
# PASSWORD RESET ROUTES
# =========================================================

@router.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest):
    """
    Richiede reset password.

    Per sicurezza ritorna sempre success True, anche se l'email non esiste.
    In modalità MVP/test restituisce reset_link se PASSWORD_RESET_EXPOSE_LINK=1.
    Più avanti colleghiamo SMTP/SendGrid/Brevo e togliamo reset_link dalla risposta.
    """
    init_db()

    email = data.email.lower().strip()
    user = get_user_by_email(email)

    public_message = (
        "Se l'email è registrata, riceverai le istruzioni per reimpostare la password."
    )

    if not user:
        return {
            "success": True,
            "message": public_message
        }

    if not user.get("is_active"):
        return {
            "success": True,
            "message": public_message
        }

    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_reset_token(raw_token)

    expires_at_dt = utc_now_dt() + timedelta(minutes=PASSWORD_RESET_TOKEN_MINUTES)
    expires_at = iso_utc(expires_at_dt)

    create_password_reset_token(
        user_id=user["id"],
        token_hash=token_hash,
        expires_at=expires_at
    )

    reset_link = build_reset_link(raw_token)

    response = {
        "success": True,
        "message": public_message,
        "expires_in_minutes": PASSWORD_RESET_TOKEN_MINUTES
    }

    if PASSWORD_RESET_EXPOSE_LINK:
        response["reset_link"] = reset_link
        response["dev_note"] = (
            "Reset link esposto solo per MVP/test. "
            "Quando colleghi email automatica, imposta PASSWORD_RESET_EXPOSE_LINK=0."
        )

    return response


@router.post("/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirmRequest):
    """
    Conferma reset password con token e nuova password.
    """
    init_db()

    token = (data.token or "").strip()
    new_password = data.password or ""

    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token reset mancante"
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="La password deve contenere almeno 6 caratteri"
        )

    token_hash = hash_reset_token(token)
    reset_row = get_valid_password_reset_token(token_hash)

    if not reset_row:
        raise HTTPException(
            status_code=400,
            detail="Token non valido o già utilizzato"
        )

    if not reset_row.get("is_active"):
        raise HTTPException(
            status_code=403,
            detail="Utente disattivato"
        )

    expires_at = parse_iso_datetime(reset_row.get("expires_at"))

    if not expires_at or expires_at < utc_now_dt():
        try:
            mark_password_reset_token_used(reset_row["id"])
        except Exception:
            pass

        raise HTTPException(
            status_code=400,
            detail="Token scaduto. Richiedi un nuovo reset password."
        )

    new_hash = hash_password(new_password)

    update_user_password(
        user_id=reset_row["user_id"],
        password_hash=new_hash
    )

    mark_password_reset_token_used(reset_row["id"])

    return {
        "success": True,
        "message": "Password aggiornata correttamente. Ora puoi accedere con la nuova password."
    }