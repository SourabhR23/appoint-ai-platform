"""
services/sendgrid_service.py

Wrapper around SendGrid for transactional email.
Called by Celery workers only — not from routes directly.
"""

import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import settings

logger = logging.getLogger(__name__)

_sendgrid_client: SendGridAPIClient | None = None


def get_sendgrid_client() -> SendGridAPIClient:
    global _sendgrid_client
    if _sendgrid_client is None:
        _sendgrid_client = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    return _sendgrid_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    reraise=True,
)
def send_email(to_email: str, subject: str, body_text: str) -> str:
    """
    Send a transactional email via SendGrid.
    Returns the SendGrid message ID from response headers.
    """
    message = Mail(
        from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
        to_emails=to_email,
        subject=subject,
        plain_text_content=body_text,
    )

    client = get_sendgrid_client()
    response = client.send(message)
    message_id = response.headers.get("X-Message-Id", "unknown")

    logger.info(
        "email_sent",
        extra={
            "to": _mask_email(to_email),
            "subject": subject,
            "status_code": response.status_code,
            "message_id": message_id,
        },
    )
    return message_id


def _mask_email(email: str) -> str:
    """Mask email for logs — never log full PII."""
    parts = email.split("@")
    if len(parts) != 2:
        return "***"
    local = parts[0][:2] + "***"
    return f"{local}@{parts[1]}"
