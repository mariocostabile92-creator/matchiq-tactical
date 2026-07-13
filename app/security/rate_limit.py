import hashlib
import ipaddress
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request


@dataclass
class _Bucket:
    started_at: float
    hits: int


_LOCK = threading.Lock()
_BUCKETS = {}
_LAST_CLEANUP = 0.0


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def client_ip(request: Request) -> str:
    direct = str(getattr(getattr(request, "client", None), "host", "") or "unknown")
    if not _truthy(os.getenv("TRUST_PROXY_HEADERS", "0")):
        return direct

    forwarded = str(request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
    try:
        return str(ipaddress.ip_address(forwarded)) if forwarded else direct
    except ValueError:
        return direct


def _key(request: Request, scope: str, identity: Optional[str]) -> str:
    raw = f"{scope}|{client_ip(request)}|{str(identity or '').strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cleanup(now: float, max_age: int = 7200) -> None:
    global _LAST_CLEANUP
    if now - _LAST_CLEANUP < 300:
        return
    stale = [key for key, bucket in _BUCKETS.items() if now - bucket.started_at > max_age]
    for key in stale:
        _BUCKETS.pop(key, None)
    _LAST_CLEANUP = now


def enforce_rate_limit(
    request: Request,
    scope: str,
    limit: int,
    window_seconds: int,
    identity: Optional[str] = None,
) -> None:
    now = time.monotonic()
    bucket_key = _key(request, scope, identity)
    with _LOCK:
        _cleanup(now)
        bucket = _BUCKETS.get(bucket_key)
        if bucket is None or now - bucket.started_at >= window_seconds:
            _BUCKETS[bucket_key] = _Bucket(started_at=now, hits=1)
            return
        if bucket.hits >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket.started_at)))
            raise HTTPException(
                status_code=429,
                detail="Troppe richieste. Riprova tra poco.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.hits += 1


def clear_rate_limit(request: Request, scope: str, identity: Optional[str] = None) -> None:
    with _LOCK:
        _BUCKETS.pop(_key(request, scope, identity), None)


def reset_rate_limits_for_tests() -> None:
    global _LAST_CLEANUP
    with _LOCK:
        _BUCKETS.clear()
        _LAST_CLEANUP = 0.0
