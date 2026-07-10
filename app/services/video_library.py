from __future__ import annotations

import ipaddress
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile


VIDEO_LIBRARY_ROOT = Path(os.getenv("VIDEO_LIBRARY_DIR", "storage/video_library")).resolve()
MAX_UPLOAD_BYTES = int(os.getenv("VIDEO_LIBRARY_MAX_UPLOAD_MB", "450")) * 1024 * 1024
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


def _safe_slug(value: str, fallback: str = "video") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip()).strip("-._")
    return (cleaned or fallback)[:90]


def _assert_safe_video_name(filename: str) -> str:
    safe_name = _safe_slug(Path(filename or "video.mp4").name, "video.mp4")
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato video non supportato. Usa mp4, mov, m4v o webm.")
    return safe_name


def _is_private_host(hostname: str) -> bool:
    if not hostname:
        return True
    host = hostname.strip().lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    except ValueError:
        return False


def validate_import_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Inserisci un link http o https autorizzato.")
    if _is_private_host(parsed.hostname or ""):
        raise HTTPException(status_code=400, detail="Link non valido per motivi di sicurezza.")
    if len(parsed.geturl()) > 1200:
        raise HTTPException(status_code=400, detail="Link troppo lungo.")
    return parsed.geturl()


def user_library_dir(user_id: int) -> Path:
    path = VIDEO_LIBRARY_ROOT / str(int(user_id))
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_uploaded_video(user_id: int, upload: UploadFile, title: str = "") -> dict:
    safe_name = _assert_safe_video_name(upload.filename or "")
    asset_name = f"{_safe_slug(title or Path(safe_name).stem)}-{os.urandom(6).hex()}{Path(safe_name).suffix.lower()}"
    target = user_library_dir(user_id) / asset_name
    bytes_written = 0

    with target.open("wb") as out_file:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                try:
                    target.unlink(missing_ok=True)
                except Exception:
                    pass
                raise HTTPException(status_code=413, detail="Video troppo grande per la libreria.")
            out_file.write(chunk)

    return {
        "file_path": str(target),
        "file_name": safe_name,
        "size_bytes": bytes_written,
        "mime_type": upload.content_type or "video/mp4",
    }


def remove_library_file(file_path: Optional[str]) -> None:
    if not file_path:
        return
    try:
        path = Path(file_path).resolve()
        if VIDEO_LIBRARY_ROOT in path.parents and path.exists():
            path.unlink()
    except Exception:
        pass
