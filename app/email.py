import smtplib
from email.message import EmailMessage

from flask import current_app


def _smtp_configured():
    cfg = current_app.config
    return bool(cfg.get("SMTP_HOST") and cfg.get("SMTP_USER") and cfg.get("SMTP_PASSWORD") and cfg.get("SMTP_FROM"))


def _send(to_addr, subject, body):
    cfg = current_app.config
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["SMTP_FROM"]
    msg["To"] = to_addr
    msg.set_content(body)
    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=10) as server:
        server.starttls()
        server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        server.send_message(msg)


def notify_owner_new_request(est):
    if not _smtp_configured():
        current_app.logger.info("Email not configured - skipping owner notification for request %s", est.id)
        return False
    owner_email = current_app.config.get("OWNER_NOTIFY_EMAIL") or current_app.config.get("SMTP_FROM")
    if not owner_email:
        return False
    body = (
        f"New free estimate request from {est.name}\n"
        f"Phone: {est.phone}\n"
        f"Email: {est.email or 'n/a'}\n"
        f"Address: {est.address}\n"
        f"Preferred: {est.preferred_date or 'n/a'} {est.preferred_time or ''}\n\n"
        f"Details:\n{est.description or '(none provided)'}"
    )
    try:
        _send(owner_email, f"New Estimate Request - {est.name}", body)
        return True
    except Exception:
        current_app.logger.exception("Failed to send owner notification email")
        return False


def confirm_customer_request(est):
    if not _smtp_configured() or not est.email:
        return False
    body = (
        f"Hi {est.name},\n\n"
        "Thanks for requesting a free estimate from Dr Blinds Decor & Services LLC! "
        "We received your request and will reach out shortly to confirm a time.\n\n"
        "Remember - estimates are always free.\n\n"
        "Dr Blinds Decor & Services LLC"
    )
    try:
        _send(est.email, "We received your free estimate request", body)
        return True
    except Exception:
        current_app.logger.exception("Failed to send customer confirmation email")
        return False
