"""
services/smtp_service.py

Email delivery via Gmail SMTP using Python standard library smtplib.
Replaces SendGrid — no external email provider dependency.

Called by Celery workers (sync context) — uses smtplib (sync, stdlib).
Called with platform-default credentials from settings, or per-tenant
credentials passed explicitly for tenant-provided email channels.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import settings

logger = logging.getLogger(__name__)


def _send_via_smtp(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_name: str,
    to_email: str,
    subject: str,
    body_text: str,
) -> str:
    """
    Core SMTP send function.
    Uses STARTTLS on port 587 (Gmail standard).
    Returns a pseudo message ID for logging.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{smtp_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(body_text, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())

    message_id = f"smtp-{smtp_user}-{hash(to_email + subject) & 0xFFFFFFFF:08x}"
    return message_id


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    reraise=True,
)
def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    *,
    smtp_credentials: dict | None = None,
) -> str:
    """
    Send a transactional email.

    If smtp_credentials is provided (tenant-specific), use those.
    Otherwise fall back to platform-default settings from .env.

    smtp_credentials shape:
        {smtp_host, smtp_port, smtp_user, smtp_password, from_name}
    """
    creds = smtp_credentials or {}

    host = creds.get("smtp_host") or settings.SMTP_HOST
    port = int(creds.get("smtp_port") or settings.SMTP_PORT)
    user = creds.get("smtp_user") or settings.SMTP_USER
    password = creds.get("smtp_password") or settings.SMTP_PASSWORD
    from_name = creds.get("from_name") or settings.SMTP_FROM_NAME

    message_id = _send_via_smtp(
        smtp_host=host,
        smtp_port=port,
        smtp_user=user,
        smtp_password=password,
        from_name=from_name,
        to_email=to_email,
        subject=subject,
        body_text=body_text,
    )

    logger.info(
        "email_sent",
        extra={
            "to": _mask_email(to_email),
            "subject": subject,
            "via": user[:4] + "***",
            "message_id": message_id,
        },
    )
    return message_id


def test_smtp_connection(credentials: dict) -> bool:
    """
    Validate SMTP credentials by attempting login.
    Used in channel setup — returns True on success, raises on failure.
    """
    try:
        with smtplib.SMTP(
            credentials.get("smtp_host", "smtp.gmail.com"),
            int(credentials.get("smtp_port", 587)),
            timeout=10,
        ) as server:
            server.ehlo()
            server.starttls()
            server.login(
                credentials["smtp_user"],
                credentials["smtp_password"],
            )
        return True
    except Exception as exc:
        logger.warning("smtp_test_failed", extra={"error": str(exc)})
        raise


def _mask_email(email: str) -> str:
    """Mask email for logs — never log full PII."""
    parts = email.split("@")
    if len(parts) != 2:
        return "***"
    local = parts[0][:2] + "***"
    return f"{local}@{parts[1]}"
