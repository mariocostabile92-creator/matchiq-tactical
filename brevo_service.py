"""
brevo_service.py
MatchIQ Tactical - Brevo API service V8.6
Usa Brevo HTTP API invece di SMTP per evitare timeout porta 587 su Railway.
"""

import os
import json
import traceback
import urllib.request
import urllib.error
from html import escape

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", "mario.costabile92@outlook.it").strip()
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "MatchIQ Tactical").strip() or "MatchIQ Tactical"
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def is_email_configured():
    return bool(BREVO_API_KEY and EMAIL_FROM)


def _safe_error(exc):
    try:
        return f"{type(exc).__name__}: {exc}"
    except Exception:
        return "Errore email sconosciuto"


def send_email_api(to_email: str, subject: str, text_body: str, html_body: str = ""):
    print(
        f"[BREVO API] configured={is_email_configured()} api_key_set={bool(BREVO_API_KEY)} from={EMAIL_FROM}",
        flush=True,
    )

    if not is_email_configured():
        print("[BREVO API ERROR] BREVO_API_KEY o EMAIL_FROM non configurati su Railway", flush=True)
        return {"success": False, "error": "BREVO_API_KEY o EMAIL_FROM non configurati"}

    payload = {
        "sender": {"name": EMAIL_FROM_NAME, "email": EMAIL_FROM},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": text_body or "",
    }

    if html_body:
        payload["htmlContent"] = html_body

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        BREVO_API_URL,
        data=data,
        method="POST",
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        },
    )

    try:
        print(f"[BREVO API] sending to={to_email} subject={subject}", flush=True)
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = getattr(response, "status", 200)

        print(f"[BREVO API] sent ok to={to_email} status={status} body={body[:300]}", flush=True)
        return {"success": True, "error": None, "status": status, "body": body}

    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        print(f"[BREVO API ERROR] HTTP {exc.code}: {body[:800]}", flush=True)
        return {"success": False, "error": f"HTTP {exc.code}: {body}"}

    except Exception as exc:
        print(f"[BREVO API ERROR] {_safe_error(exc)}", flush=True)
        print(traceback.format_exc(), flush=True)
        return {"success": False, "error": _safe_error(exc)}


def send_verification_email(to_email: str, verification_link: str):
    safe_link = escape(verification_link or "")
    subject = "Verifica il tuo account MatchIQ"
    text = (
        "Ciao,\n\n"
        "per completare la registrazione su MatchIQ Tactical apri questo link:\n"
        f"{verification_link}\n\n"
        "Se non hai richiesto tu questo account, ignora questa email.\n\n"
        "MatchIQ Tactical"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#050814;color:#ffffff;padding:24px;border-radius:16px">
      <h2>Verifica il tuo account MatchIQ</h2>
      <p>Per completare la registrazione clicca il pulsante qui sotto.</p>
      <p><a href="{safe_link}" style="display:inline-block;background:#00f5a0;color:#06111c;padding:12px 18px;border-radius:12px;font-weight:800;text-decoration:none">Verifica email</a></p>
      <p style="color:#aebee7;font-size:13px">Se il pulsante non funziona, copia questo link:<br>{safe_link}</p>
    </div>
    """
    return send_email_api(to_email, subject, text, html)


def send_password_reset_email(to_email: str, reset_link: str):
    safe_link = escape(reset_link or "")
    subject = "Reset password MatchIQ"
    text = (
        "Ciao,\n\n"
        "per reimpostare la password MatchIQ apri questo link:\n"
        f"{reset_link}\n\n"
        "Se non hai richiesto tu il reset, ignora questa email.\n\n"
        "MatchIQ Tactical"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#050814;color:#ffffff;padding:24px;border-radius:16px">
      <h2>Reset password MatchIQ</h2>
      <p>Clicca il pulsante qui sotto per reimpostare la password.</p>
      <p><a href="{safe_link}" style="display:inline-block;background:#00f5a0;color:#06111c;padding:12px 18px;border-radius:12px;font-weight:800;text-decoration:none">Reimposta password</a></p>
      <p style="color:#aebee7;font-size:13px">Se il pulsante non funziona, copia questo link:<br>{safe_link}</p>
    </div>
    """
    return send_email_api(to_email, subject, text, html)
