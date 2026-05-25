"""
security.py
MatchIQ Tactical - Security Layer
Versione stabile senza passlib/bcrypt
"""

import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from jose import jwt, JWTError


SECRET_KEY = "MATCHIQ_SUPER_SECRET_KEY_CHANGE_THIS"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

PBKDF2_ITERATIONS = 260000


def hash_password(password: str) -> str:
    password = str(password)[:72]
    salt = os.urandom(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS
    )

    return (
        base64.b64encode(salt).decode("utf-8")
        + "$"
        + base64.b64encode(password_hash).decode("utf-8")
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        password = str(password)[:72]

        salt_b64, hash_b64 = stored_hash.split("$", 1)
        salt = base64.b64decode(salt_b64)
        original_hash = base64.b64decode(hash_b64)

        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS
        )

        return hmac.compare_digest(new_hash, original_hash)

    except Exception:
        return False


def create_access_token(user_id: int, email: str, plan: str):
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    payload = {
        "sub": str(user_id),
        "email": email,
        "plan": plan,
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        return None