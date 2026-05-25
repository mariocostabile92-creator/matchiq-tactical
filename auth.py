"""
auth.py
MatchIQ Tactical - Auth Routes

Gestisce:
- registrazione utenti
- login utenti
- profilo utente autenticato
- piani free/pro/scout
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr

from database import (
    init_db,
    create_user,
    get_user_by_email,
    get_user_by_id
)

from security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)


router = APIRouter(prefix="/api/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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


@router.post("/register")
def register(data: RegisterRequest):
    init_db()

    existing_user = get_user_by_email(data.email)

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
        email=data.email,
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

    user = get_user_by_email(data.email)

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