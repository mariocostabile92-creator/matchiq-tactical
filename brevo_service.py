"""
brevo_service.py
MatchIQ Tactical - Brevo SMTP service V8.5.2 Debug
"""
import os
import smtplib
import traceback
from email.message import EmailMessage
from email.utils import formataddr

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or "587")
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER).strip()
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "smtp").strip().lower()


def is_email_configured():
    return bool(SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASSWORD and EMAIL_FROM)


def _sender_tuple():
    # Brevo accetta meglio From semplice o mittente verificato.
    if "<" in EMAIL_FROM and ">" in EMAIL_FROM:
        return EMAIL_FROM
    return formataddr(("MatchIQ Tactical", EMAIL_FROM))


def send_email_smtp(to_email: str, subject: str, text_body: str, html_body: str = ""):
    print(f"[EMAIL] provider={EMAIL_PROVIDER} configured={is_email_configured()} host={SMTP_HOST} port={SMTP_PORT} user_set={bool(SMTP_USER)} from={EMAIL_FROM}", flush=True)

    if not is_email_configured():
        print("[EMAIL ERROR] SMTP non configurato: controlla variabili Railway", flush=True)
        return {"success": False, "error": "SMTP non configurato"}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _sender_tuple()
    msg["To"] = to_email
    msg.set_content(text_body or "")

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        print(f"[EMAIL] sending to={to_email} subject={subject}", flush=True)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL] sent ok to={to_email}", flush=True)
        return {"success": True, "error": None}
    except Exception as exc:
        print(f"[EMAIL ERROR] {type(exc).__name__}: {exc}", flush=True)
        print(traceback.format_exc(), flush=True)
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def send_verification_email(to_email: str, verification_link: str):
    subject = "Verifica il tuo account MatchIQ"
    text = f"Ciao,\n\nper completare la registrazione su MatchIQ Tactical apri questo link:\n{verification_link}\n\nSe non hai richiesto tu questo account, ignora questa email.\n\nMatchIQ Tactical"
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#050814;color:#ffffff;padding:24px;border-radius:16px">
      <h2>Verifica il tuo account MatchIQ</h2>
      <p>Per completare la registrazione clicca il pulsante qui sotto.</p>
      <p><a href="{verification_link}" style="display:inline-block;background:#00f5a0;color:#06111c;padding:12px 18px;border-radius:12px;font-weight:800;text-decoration:none">Verifica email</a></p>
      <p style="color:#aebee7;font-size:13px">Se il pulsante non funziona, copia questo link:<br>{verification_link}</p>
    </div>
    """
    return send_email_smtp(to_email, subject, text, html)


def send_password_reset_email(to_email: str, reset_link: str):
    subject = "Reset password MatchIQ"
    text = f"Ciao,\n\nper reimpostare la password MatchIQ apri questo link:\n{reset_link}\n\nSe non hai richiesto tu il reset, ignora questa email.\n\nMatchIQ Tactical"
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#050814;color:#ffffff;padding:24px;border-radius:16px">
      <h2>Reset password MatchIQ</h2>
      <p>Clicca il pulsante qui sotto per reimpostare la password.</p>
      <p><a href="{reset_link}" style="display:inline-block;background:#00f5a0;color:#06111c;padding:12px 18px;border-radius:12px;font-weight:800;text-decoration:none">Reimposta password</a></p>
      <p style="color:#aebee7;font-size:13px">Se il pulsante non funziona, copia questo link:<br>{reset_link}</p>
    </div>
    """
    return send_email_smtp(to_email, subject, text, html)
