from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class CloudProvider:
    id: str
    name: str
    env_keys: tuple
    upload_label: str

    def is_configured(self) -> bool:
        return all(os.getenv(key, "").strip() for key in self.env_keys)

    def public_status(self) -> Dict[str, object]:
        configured = self.is_configured()
        return {
            "id": self.id,
            "name": self.name,
            "configured": configured,
            "connected": False,
            "status": "configured" if configured else "not_configured",
            "label": "Configurato, login cloud da collegare" if configured else "Non configurato",
            "upload_label": self.upload_label,
            "supports_oauth": self.id in {"google_drive", "dropbox", "onedrive"},
            "supports_bucket": self.id == "s3",
            "message": (
                "Provider pronto lato server, manca il collegamento utente."
                if configured
                else "Provider disponibile come modulo futuro. Nessun token e nessuna connessione finta."
            ),
        }


PROVIDERS = {
    "google_drive": CloudProvider(
        id="google_drive",
        name="Google Drive",
        env_keys=("GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET"),
        upload_label="Importa video autorizzati da Drive",
    ),
    "dropbox": CloudProvider(
        id="dropbox",
        name="Dropbox",
        env_keys=("DROPBOX_CLIENT_ID", "DROPBOX_CLIENT_SECRET"),
        upload_label="Importa video autorizzati da Dropbox",
    ),
    "onedrive": CloudProvider(
        id="onedrive",
        name="Microsoft OneDrive",
        env_keys=("ONEDRIVE_CLIENT_ID", "ONEDRIVE_CLIENT_SECRET"),
        upload_label="Importa video autorizzati da OneDrive",
    ),
    "s3": CloudProvider(
        id="s3",
        name="Amazon S3",
        env_keys=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"),
        upload_label="Archivio video su bucket S3",
    ),
}


def list_cloud_providers() -> List[Dict[str, object]]:
    return [provider.public_status() for provider in PROVIDERS.values()]


def get_cloud_provider_status(provider_id: str) -> Dict[str, object]:
    provider = PROVIDERS.get(str(provider_id or "").strip().lower())
    if not provider:
        return {
            "id": provider_id,
            "configured": False,
            "connected": False,
            "status": "unknown_provider",
            "message": "Provider cloud non riconosciuto.",
        }
    return provider.public_status()
