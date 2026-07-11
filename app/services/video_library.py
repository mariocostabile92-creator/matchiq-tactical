from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from fastapi import HTTPException, UploadFile


VIDEO_LIBRARY_ROOT = Path(os.getenv("VIDEO_LIBRARY_DIR", "storage/video_library")).resolve()
VIDEO_STORAGE_BACKEND = os.getenv("VIDEO_STORAGE_BACKEND", "local").strip().lower() or "local"
MAX_UPLOAD_BYTES = int(os.getenv("VIDEO_LIBRARY_MAX_UPLOAD_MB", "450")) * 1024 * 1024
IMPORT_TIMEOUT_SECONDS = float(os.getenv("VIDEO_IMPORT_TIMEOUT_SECONDS", "6"))
IMPORT_MAX_REDIRECTS = int(os.getenv("VIDEO_IMPORT_MAX_REDIRECTS", "4"))
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
ALLOWED_VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-m4v",
    "application/octet-stream",
}
BLOCKED_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "application/json",
    "text/xml",
    "application/xml",
}


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
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )
    except ValueError:
        return False


def _resolves_to_private_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    for address in addresses:
        ip_value = address[4][0]
        if _is_private_host(ip_value):
            return True
    return False


def _assert_safe_import_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Inserisci un link http o https autorizzato.")
    if _is_private_host(parsed.hostname or ""):
        raise HTTPException(status_code=400, detail="Link non valido per motivi di sicurezza.")
    if _resolves_to_private_host(parsed.hostname or ""):
        raise HTTPException(status_code=400, detail="Il dominio del link risolve verso una rete privata.")
    if len(parsed.geturl()) > 1200:
        raise HTTPException(status_code=400, detail="Link troppo lungo.")
    return parsed.geturl()


def _extension_from_url(url: str) -> str:
    return Path(urlparse(url).path or "").suffix.lower()


def _normalize_content_type(value: str) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _request_import_probe(session: requests.Session, url: str) -> requests.Response:
    headers = {
        "User-Agent": "MatchIQ-VideoImport/1.0",
        "Accept": "video/*,application/octet-stream;q=0.8,*/*;q=0.2",
    }
    try:
        response = session.head(url, allow_redirects=False, timeout=IMPORT_TIMEOUT_SECONDS, headers=headers)
        if response.status_code in {405, 403}:
            response = session.get(
                url,
                allow_redirects=False,
                timeout=IMPORT_TIMEOUT_SECONDS,
                headers={**headers, "Range": "bytes=0-0"},
                stream=True,
            )
        return response
    except requests.Timeout:
        raise HTTPException(status_code=408, detail="Timeout nel controllo del link video.")
    except requests.RequestException:
        raise HTTPException(status_code=400, detail="Link video non raggiungibile.")


def validate_import_url(url: str) -> dict:
    current_url = _assert_safe_import_url(url)
    redirect_chain = []
    session = requests.Session()
    session.max_redirects = IMPORT_MAX_REDIRECTS

    response = None
    for _ in range(IMPORT_MAX_REDIRECTS + 1):
        response = _request_import_probe(session, current_url)
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location", "")
            if not location:
                raise HTTPException(status_code=400, detail="Redirect video non valido.")
            next_url = _assert_safe_import_url(urljoin(current_url, location))
            redirect_chain.append(next_url)
            current_url = next_url
            continue
        break
    else:
        raise HTTPException(status_code=400, detail="Troppi redirect nel link video.")

    if response is None:
        raise HTTPException(status_code=400, detail="Link video non verificabile.")

    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"Il server sorgente risponde con errore {response.status_code}.")

    content_type = _normalize_content_type(response.headers.get("Content-Type", ""))
    extension = _extension_from_url(current_url)
    content_length = response.headers.get("Content-Length")
    size_bytes = 0
    if content_length and str(content_length).isdigit():
        size_bytes = int(content_length)
        if size_bytes > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Il video remoto supera il limite massimo consentito.")

    if content_type in BLOCKED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Il link sembra una pagina web, non un file video diretto.")

    has_video_type = content_type.startswith("video/") or content_type in ALLOWED_VIDEO_CONTENT_TYPES
    has_video_extension = extension in ALLOWED_EXTENSIONS
    if not has_video_type and not has_video_extension:
        raise HTTPException(status_code=400, detail="Il link non sembra puntare a un video diretto supportato.")

    return {
        "url": current_url,
        "content_type": content_type or "",
        "size_bytes": size_bytes,
        "redirects": redirect_chain,
        "extension": extension,
    }


def user_library_dir(user_id: int) -> Path:
    path = VIDEO_LIBRARY_ROOT / str(int(user_id))
    path.mkdir(parents=True, exist_ok=True)
    return path


class LocalVideoStorage:
    backend = "local"

    def save_upload(self, user_id: int, upload: UploadFile, title: str = "") -> dict:
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
            "storage_backend": self.backend,
            "storage_key": str(target.relative_to(VIDEO_LIBRARY_ROOT)),
            "file_path": str(target),
            "file_name": safe_name,
            "size_bytes": bytes_written,
            "mime_type": upload.content_type or "video/mp4",
        }

    def resolve_path(self, file_path: str = "", storage_key: str = "") -> Path:
        if storage_key:
            path = (VIDEO_LIBRARY_ROOT / storage_key).resolve()
        else:
            path = Path(file_path or "").resolve()
        if VIDEO_LIBRARY_ROOT not in path.parents:
            raise HTTPException(status_code=400, detail="Percorso video non valido.")
        return path

    def delete(self, file_path: str = "", storage_key: str = "") -> None:
        try:
            path = self.resolve_path(file_path=file_path, storage_key=storage_key)
            if path.exists():
                path.unlink()
        except Exception:
            pass


def get_video_storage():
    if VIDEO_STORAGE_BACKEND != "local":
        raise HTTPException(
            status_code=501,
            detail="Storage video esterno non configurato. Imposta VIDEO_STORAGE_BACKEND=local o collega un provider.",
        )
    return LocalVideoStorage()


def parse_asset_metadata(asset: dict) -> dict:
    metadata = (asset or {}).get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return metadata if isinstance(metadata, dict) else {}


def save_uploaded_video(user_id: int, upload: UploadFile, title: str = "") -> dict:
    return get_video_storage().save_upload(user_id, upload, title)


def resolve_library_file(asset: dict) -> Path:
    metadata = parse_asset_metadata(asset or {})
    backend = metadata.get("storage_backend") or metadata.get("storage") or "local"
    if backend not in {"local", "local_file"}:
        raise HTTPException(status_code=501, detail="Storage video non supportato da questo server.")
    return get_video_storage().resolve_path(
        file_path=(asset or {}).get("file_path") or "",
        storage_key=metadata.get("storage_key") or "",
    )


def remove_library_file(file_path: Optional[str], metadata: Optional[dict] = None) -> None:
    metadata = metadata or {}
    backend = metadata.get("storage_backend") or metadata.get("storage") or "local"
    if backend not in {"local", "local_file"}:
        return
    get_video_storage().delete(file_path=file_path or "", storage_key=metadata.get("storage_key") or "")


def storage_descriptor(saved: dict) -> dict:
    return {
        "storage": saved.get("storage_backend") or "local",
        "storage_backend": saved.get("storage_backend") or "local",
        "storage_key": saved.get("storage_key") or "",
    }
