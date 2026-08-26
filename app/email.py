import json
import urllib.request

from flask import current_app


def _configured():
    cfg = current_app.config
    return bool(cfg.get("RESEND_API_KEY") and cfg.get("RESEND_FROM_EMAIL"))


def _send(to_addr, subject, body):
    cfg = current_app.config
    payload = json.dumps(
        {
            "from": cfg["RESEND_FROM_EMAIL"],
            "to": [to_addr],
            "subject": subject,
            "text": body,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg['RESEND_API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": "dr-blinds-website/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"Resend API returned status {resp.status}")


def notify_owner_new_request(est):
    if not _configured():
        current_app.logger.info("Email not configured - skipping owner notification for request %s", est.id)
        return False
    owner_email = current_app.config.get("OWNER_NOTIFY_EMAIL")
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
    if not _configured() or not est.email:
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
