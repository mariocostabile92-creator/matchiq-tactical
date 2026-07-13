import re
from typing import Any, Dict


MAX_CONTEXT_ITEMS = 30
MAX_TEXT = 1200
FORBIDDEN_CERTAINTY = ("garantisce", "sicuramente", "senza dubbio", "risolvera", "funzionera")
INJECTION_MARKERS = ("ignore previous", "system prompt", "developer message", "jailbreak", "ignora le istruzioni")


def clean_text(value: Any, limit: int = MAX_TEXT) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", str(value or ""))
    lowered = text.lower()
    for marker in INJECTION_MARKERS:
        if marker in lowered:
            text = re.sub(re.escape(marker), "[contenuto rimosso]", text, flags=re.IGNORECASE)
    return " ".join(text.split())[:limit]


def sanitize_context(value: Any, depth: int = 0) -> Any:
    if depth > 3: return None
    if isinstance(value, dict):
        return {clean_text(k, 60): sanitize_context(v, depth + 1) for k, v in list(value.items())[:MAX_CONTEXT_ITEMS]}
    if isinstance(value, list): return [sanitize_context(v, depth + 1) for v in value[:MAX_CONTEXT_ITEMS]]
    if isinstance(value, (int, float, bool)) or value is None: return value
    return clean_text(value)


def cautious(text: str) -> str:
    result = clean_text(text, 2000)
    for word in FORBIDDEN_CERTAINTY:
        result = re.sub(rf"\b{re.escape(word)}\b", "puo contribuire a", result, flags=re.IGNORECASE)
    return result


def validate_staff_action(payload: Dict[str, Any]) -> None:
    if payload["action"] == "selected" and not payload.get("option_id"):
        raise ValueError("Seleziona un'opzione prima di confermare la decisione")
    if payload["action"] != "selected" and payload.get("option_id"):
        raise ValueError("Questa azione non richiede un'opzione")
