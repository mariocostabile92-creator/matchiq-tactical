"""
auth.py
MatchIQ Tactical - Auth Routes V8.4 Email Verification Required Password Reset + Email Verification

Gestisce:
- registrazione utenti
- login utenti
- profilo utente autenticato
- piani free/pro/scout/owner
- richiesta reset password
- conferma reset password
- richiesta verifica email
- conferma verifica email
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
    create_email_verification_token,
    get_valid_email_verification_token,
    mark_email_verification_token_used,
    mark_user_email_verified,
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
EMAIL_VERIFICATION_TOKEN_MINUTES = int(os.getenv("EMAIL_VERIFICATION_TOKEN_MINUTES", "1440"))

# In produzione possiamo tenere questo a 0 quando avremo email automatica.
# Per ora serve per testare il reset senza SMTP.
PASSWORD_RESET_EXPOSE_LINK = os.getenv("PASSWORD_RESET_EXPOSE_LINK", "1") == "1"

# MVP/test: espone verification_link nella risposta.
# Quando colleghiamo Brevo/SMTP, imposta EMAIL_VERIFICATION_EXPOSE_LINK=0.
EMAIL_VERIFICATION_EXPOSE_LINK = os.getenv("EMAIL_VERIFICATION_EXPOSE_LINK", "1") == "1"


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


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirmRequest(BaseModel):
    token: str


# =========================================================
# HELPERS
# =========================================================

def utc_now_dt():
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime):
    return dt.astimezone(timezone.utc).isoformat()


def hash_reset_token(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_email_verification_token(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_reset_link(token: str):
    return f"{APP_PUBLIC_URL}/reset-password.html?token={token}"


def build_email_verification_link(token: str):
    return f"{APP_PUBLIC_URL}/verify-email.html?token={token}"


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



def create_verification_for_user(user: dict):
    """
    Genera e salva un token verifica email per un utente attivo.
    Ritorna il link in chiaro solo per MVP/test.
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_email_verification_token(raw_token)

    expires_at_dt = utc_now_dt() + timedelta(minutes=EMAIL_VERIFICATION_TOKEN_MINUTES)
    expires_at = iso_utc(expires_at_dt)

    create_email_verification_token(
        user_id=user["id"],
        token_hash=token_hash,
        expires_at=expires_at
    )

    return build_email_verification_link(raw_token)

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

    verification_link = create_verification_for_user(user)

    response = {
        "success": True,
        "message": "Registrazione completata. Verifica la tua email per completare l'account.",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "plan": user["plan"],
            "email_verified": bool(user.get("email_verified")),
            "email_verified_at": user.get("email_verified_at")
        }
    }

    if EMAIL_VERIFICATION_EXPOSE_LINK:
        response["verification_link"] = verification_link
        response["dev_note"] = (
            "Verification link esposto solo per MVP/test. "
            "Quando colleghi email automatica, imposta EMAIL_VERIFICATION_EXPOSE_LINK=0."
        )

    return response


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

    if not user.get("email_verified"):
        raise HTTPException(
            status_code=403,
            detail="Devi verificare la tua email prima di accedere."
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
            "plan": user["plan"],
            "email_verified": bool(user.get("email_verified")),
            "email_verified_at": user.get("email_verified_at")
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
            "email_verified": bool(current_user.get("email_verified")),
            "email_verified_at": current_user.get("email_verified_at"),
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

# =========================================================
# EMAIL VERIFICATION ROUTES
# =========================================================

@router.post("/email-verification/request")
def request_email_verification(data: EmailVerificationRequest):
    """
    Richiede un nuovo link di verifica email.

    Per sicurezza ritorna success True anche se l'email non esiste.
    In modalità MVP/test restituisce verification_link se EMAIL_VERIFICATION_EXPOSE_LINK=1.
    Più avanti colleghiamo Brevo/SMTP e togliamo verification_link dalla risposta.
    """
    init_db()

    email = data.email.lower().strip()
    user = get_user_by_email(email)

    public_message = (
        "Se l'email è registrata, riceverai le istruzioni per verificare l'account."
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

    if user.get("email_verified"):
        return {
            "success": True,
            "message": "Email già verificata."
        }

    verification_link = create_verification_for_user(user)

    response = {
        "success": True,
        "message": public_message,
        "expires_in_minutes": EMAIL_VERIFICATION_TOKEN_MINUTES
    }

    if EMAIL_VERIFICATION_EXPOSE_LINK:
        response["verification_link"] = verification_link
        response["dev_note"] = (
            "Verification link esposto solo per MVP/test. "
            "Quando colleghi email automatica, imposta EMAIL_VERIFICATION_EXPOSE_LINK=0."
        )

    return response


@router.post("/email-verification/confirm")
def confirm_email_verification(data: EmailVerificationConfirmRequest):
    """
    Conferma verifica email con token.
    """
    init_db()

    token = (data.token or "").strip()

    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token verifica email mancante"
        )

    token_hash = hash_email_verification_token(token)
    verification_row = get_valid_email_verification_token(token_hash)

    if not verification_row:
        raise HTTPException(
            status_code=400,
            detail="Token non valido o già utilizzato"
        )

    if not verification_row.get("is_active"):
        raise HTTPException(
            status_code=403,
            detail="Utente disattivato"
        )

    expires_at = parse_iso_datetime(verification_row.get("expires_at"))

    if not expires_at or expires_at < utc_now_dt():
        try:
            mark_email_verification_token_used(verification_row["id"])
        except Exception:
            pass

        raise HTTPException(
            status_code=400,
            detail="Token scaduto. Richiedi una nuova verifica email."
        )

    mark_user_email_verified(verification_row["user_id"])
    mark_email_verification_token_used(verification_row["id"])

    return {
        "success": True,
        "message": "Email verificata correttamente."
    }

