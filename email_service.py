"""
Legacy email compatibility layer.

Il servizio email attivo dell'app e' brevo_service.py. Questo modulo resta
importabile per compatibilita' con vecchi import e delega l'invio a Brevo.
"""

from html import escape

from brevo_service import (
    is_email_configured,
    send_email_api as _send_email_api,
)


def send_email_api(to_email: str, subject: str, text_body: str, html_body: str = ""):
    return _send_email_api(to_email, subject, text_body, html_body)


def _matchiq_email_html(title: str, intro: str, button_label: str, url: str):
    safe_title = escape(title or "")
    safe_intro = escape(intro or "")
    safe_button_label = escape(button_label or "")
    safe_url = escape(url or "")

    return f"""
    <div style="font-family:Arial,sans-serif;background:#050814;color:#ffffff;padding:24px;border-radius:18px">
      <div style="max-width:560px;margin:0 auto;background:#07101f;border:1px solid rgba(255,255,255,.12);border-radius:18px;padding:24px">
        <h2 style="margin:0 0 12px;font-size:24px;line-height:1.15">{safe_title}</h2>
        <p style="color:#c7d7f2;line-height:1.6;margin:0 0 18px">{safe_intro}</p>
        <p style="margin:0 0 18px">
          <a href="{safe_url}" style="display:inline-block;background:#00f5a0;color:#06111c;padding:13px 18px;border-radius:12px;font-weight:800;text-decoration:none">
            {safe_button_label}
          </a>
        </p>
        <p style="color:#aebee7;font-size:13px;line-height:1.5;margin:0">
          Se il pulsante non funziona, copia questo link:<br>
          <span style="word-break:break-all">{safe_url}</span>
        </p>
      </div>
    </div>
    """


def send_verification_email(to_email: str, verification_link: str):
    subject = "Verifica il tuo account MatchIQ"
    text = (
        "Ciao,\n\n"
        "per completare la registrazione su MatchIQ Tactical apri questo link:\n"
        f"{verification_link}\n\n"
        "Se non hai richiesto tu questo account, ignora questa email.\n\n"
        "MatchIQ Tactical"
    )
    html = _matchiq_email_html(
        "Verifica il tuo account MatchIQ",
        "Per completare la registrazione clicca il pulsante qui sotto.",
        "Verifica email",
        verification_link,
    )
    return send_email_api(to_email, subject, text, html)


def send_password_reset_email(to_email: str, reset_link: str):
    subject = "Reset password MatchIQ"
    text = (
        "Ciao,\n\n"
        "per reimpostare la password MatchIQ apri questo link:\n"
        f"{reset_link}\n\n"
        "Se non hai richiesto tu il reset, ignora questa email.\n\n"
        "MatchIQ Tactical"
    )
    html = _matchiq_email_html(
        "Reset password MatchIQ",
        "Clicca il pulsante qui sotto per reimpostare la password.",
        "Reimposta password",
        reset_link,
    )
    return send_email_api(to_email, subject, text, html)
