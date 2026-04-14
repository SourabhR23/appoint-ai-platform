"""
services/twilio_service.py

Wrapper around Twilio SDK for SMS and WhatsApp sends.
Called by Celery workers — never called directly from routes.

All secrets come from settings — never hardcoded (R5).
"""

import logging

from tenacity import retry, stop_after_attempt, wait_exponential
from twilio.rest import Client

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Client is instantiated once per module load
_twilio_client: Client | None = None


def get_twilio_client() -> Client:
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _twilio_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    reraise=True,
)
def send_sms(to: str, body: str) -> str:
    """
    Send an SMS via Twilio.
    Retries up to 3 times with exponential backoff (R8).
    Returns the Twilio message SID.
    """
    client = get_twilio_client()
    message = client.messages.create(
        from_=settings.TWILIO_PHONE_FROM,
        to=to,
        body=body,
    )
    logger.info(
        "sms_sent",
        extra={"to": _mask_phone(to), "sid": message.sid, "status": message.status},
    )
    return message.sid


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    reraise=True,
)
def send_whatsapp(to: str, body: str) -> str:
    """
    Send a WhatsApp message via Twilio.
    Requires Twilio WhatsApp-enabled number (sandbox or approved).
    Retries up to 3 times with exponential backoff (R8).
    """
    client = get_twilio_client()
    message = client.messages.create(
        from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
        to=f"whatsapp:{to}",
        body=body,
    )
    logger.info(
        "whatsapp_sent",
        extra={"to": _mask_phone(to), "sid": message.sid, "status": message.status},
    )
    return message.sid


def _mask_phone(phone: str) -> str:
    """Mask phone for logs — never log PII in full (R13, security)."""
    if len(phone) < 5:
        return "***"
    return phone[:3] + "****" + phone[-2:]
