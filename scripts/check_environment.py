"""Non-destructive environment validation for MatchIQ Coach AI."""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_IMPORTS = {
    "fastapi": "FastAPI",
    "uvicorn": "Uvicorn",
    "requests": "Requests",
    "dotenv": "python-dotenv",
    "pydantic": "Pydantic",
    "stripe": "Stripe",
    "reportlab": "ReportLab",
    "jose": "python-jose",
    "multipart": "python-multipart",
    "email_validator": "email-validator",
    "psycopg2": "psycopg2-binary",
}
OPTIONAL_VISION_IMPORTS = {
    "numpy": "NumPy",
    "cv2": "OpenCV",
    "rfdetr": "RF-DETR",
    "torch": "PyTorch",
    "torchvision": "TorchVision",
}
ESSENTIAL_PATHS = (
    "main.py",
    "database.py",
    "app",
    "frontend",
    "tests",
    "requirements.txt",
    "runtime.txt",
)
INITIALIZERS = (
    ("database", "init_db"),
    ("app.services.knowledge_service", "initialize_foundation"),
    ("app.services.voice_coach_intelligence_service", "initialize_voice_coach_intelligence"),
    ("app.services.pattern_intelligence_service", "initialize_pattern_intelligence"),
    ("app.services.training_planner_service", "initialize_training_planner"),
    ("app.services.weekly_briefing_service", "initialize_weekly_briefing"),
    ("app.services.knowledge_intelligence_service", "initialize_knowledge_intelligence"),
    ("app.services.tactical_assistant_service", "initialize_tactical_assistant"),
    ("app.services.tactical_identity_service", "initialize_tactical_identity"),
    ("app.services.decision_engine_service", "initialize_decision_engine"),
    ("app.services.club_intelligence_service", "initialize_club_intelligence"),
)


class CheckResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def ok(self, message: str) -> None:
        print(f"[OK] {message}")

    def warning(self, message: str) -> None:
        self.warnings.append(message)
        print(f"[WARNING] {message}")

    def error(self, message: str) -> None:
        self.errors.append(message)
        print(f"[ERROR] {message}")


def check_python(result: CheckResult) -> None:
    version = sys.version_info
    if (version.major, version.minor) == (3, 11):
        result.ok(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        result.error(
            f"Python 3.11 richiesto; interprete attivo: "
            f"{version.major}.{version.minor}.{version.micro}"
        )


def check_working_directory(result: CheckResult) -> None:
    if Path.cwd().resolve() == ROOT:
        result.ok(f"Directory di lavoro: {ROOT}")
    else:
        result.error(f"Eseguire lo script dalla root backend: {ROOT}")


def check_paths(result: CheckResult) -> None:
    for relative in ESSENTIAL_PATHS:
        if (ROOT / relative).exists():
            result.ok(f"Percorso presente: {relative}")
        else:
            result.error(f"Percorso mancante: {relative}")


def check_imports(result: CheckResult) -> None:
    for module_name, label in RUNTIME_IMPORTS.items():
        try:
            importlib.import_module(module_name)
            result.ok(f"Dipendenza runtime: {label}")
        except Exception as exc:
            result.error(f"Dipendenza runtime non importabile: {label} ({exc})")

    for module_name, label in OPTIONAL_VISION_IMPORTS.items():
        try:
            importlib.import_module(module_name)
            result.ok(f"Dipendenza Vision opzionale: {label}")
        except Exception:
            result.warning(f"Dipendenza Vision opzionale non installata: {label}")


def check_environment_variables(result: CheckResult) -> None:
    if os.getenv("JWT_SECRET_KEY", "").strip() or os.getenv("SECRET_KEY", "").strip():
        result.ok("Segreto JWT configurato (valore non mostrato)")
    else:
        result.warning(
            "JWT_SECRET_KEY assente: consentito solo in locale; obbligatorio su Railway"
        )

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        result.warning("DATABASE_URL assente: verra usato SQLite locale all'avvio reale")
        return

    parsed = urlparse(database_url)
    if parsed.scheme in {"postgres", "postgresql"} and parsed.hostname and parsed.path:
        result.ok("DATABASE_URL PostgreSQL formalmente valida (valore non mostrato)")
    else:
        result.error("DATABASE_URL presente ma non e una URL PostgreSQL valida")


def check_fastapi_import(result: CheckResult) -> None:
    temporary_secret = False
    if not os.getenv("JWT_SECRET_KEY") and not os.getenv("SECRET_KEY"):
        os.environ["JWT_SECRET_KEY"] = "environment-check-only-" + ("x" * 48)
        temporary_secret = True

    sys.path.insert(0, str(ROOT))
    try:
        with ExitStack() as stack:
            for module_name, attribute in INITIALIZERS:
                module = importlib.import_module(module_name)
                stack.enter_context(patch.object(module, attribute, return_value=None))
            main = importlib.import_module("main")
            from fastapi import FastAPI

            if isinstance(getattr(main, "app", None), FastAPI):
                result.ok("Applicazione FastAPI importabile senza inizializzare il database")
            else:
                result.error("main.app non e un'istanza FastAPI")
    except Exception as exc:
        result.error(f"Import dell'applicazione FastAPI fallito: {exc}")
    finally:
        if temporary_secret:
            os.environ.pop("JWT_SECRET_KEY", None)
        if sys.path and sys.path[0] == str(ROOT):
            sys.path.pop(0)


def main() -> int:
    result = CheckResult()
    print("MatchIQ Coach AI - verifica ambiente")
    check_python(result)
    check_working_directory(result)
    check_paths(result)
    check_imports(result)
    check_environment_variables(result)
    if not result.errors:
        check_fastapi_import(result)

    print(
        f"\nEsito: {len(result.errors)} errori, "
        f"{len(result.warnings)} warning."
    )
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
