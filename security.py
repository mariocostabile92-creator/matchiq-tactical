"""
security.py
MatchIQ Tactical - Security Layer
Versione stabile senza passlib/bcrypt
"""

import os
import base64
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from jose import jwt, JWTError


logger = logging.getLogger("matchiq.security")


def load_jwt_secret(secret_file: str | None = None) -> str:
    configured = (
        os.getenv("JWT_SECRET_KEY", "").strip()
        or os.getenv("SECRET_KEY", "").strip()
    )
    if configured:
        if len(configured) < 32:
            logger.warning("[SECURITY] JWT secret configurato troppo corto; usare almeno 32 caratteri")
        return configured

    path = Path(
        secret_file
        or os.getenv("JWT_SECRET_FILE", "").strip()
        or Path(__file__).resolve().parent / "storage" / ".jwt_secret"
    )
    try:
        if path.exists():
            stored = path.read_text(encoding="utf-8").strip()
            if len(stored) >= 32:
                return stored

        path.parent.mkdir(parents=True, exist_ok=True)
        generated = secrets.token_urlsafe(64)
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(generated)
        except FileExistsError:
            stored = path.read_text(encoding="utf-8").strip()
            if len(stored) >= 32:
                return stored
        logger.warning(
            "[SECURITY] JWT_SECRET_KEY non configurata: uso un segreto locale. "
            "Configurare JWT_SECRET_KEY in produzione per mantenere valide le sessioni dopo i deploy."
        )
        return generated
    except OSError:
        logger.exception("[SECURITY] Impossibile persistere il segreto JWT locale")
        return secrets.token_urlsafe(64)


SECRET_KEY = load_jwt_secret()
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
