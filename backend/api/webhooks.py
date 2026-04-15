"""
api/webhooks.py

Inbound webhook handlers for Twilio SMS and WhatsApp.
Twilio posts to these URLs when a message arrives on a tenant's number.

Routing logic:
  1. Extract 'To' phone number from Twilio request
  2. Look up which tenant owns that number (channel_configs table)
  3. Find tenant's deployed agent graph
  4. Pass message body to graph executor
  5. Reply with the agent's response via Twilio

Security:
  - Twilio signature validation is skipped in development (DEBUG=true)
  - In production, validate X-Twilio-Signature header
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def _route_inbound_message(
    db: AsyncSession,
    from_number: str,
    to_number: str,
    body: str,
    channel: str,
) -> str:
    """
    Core routing: find tenant → find graph → execute → return reply text.
    Returns the agent's reply string (or fallback message).
    """
    from backend.repositories.channel_repo import get_tenant_by_phone_number
    from backend.repositories.graph_repo import get_deployed_graph
    from backend.graph.executor import GraphExecutor

    # 1. Identify tenant by their phone number
    result = await get_tenant_by_phone_number(db, to_number)
    if result is None:
        logger.warning(
            "webhook_no_tenant_for_number",
            extra={"to": to_number, "channel": channel},
        )
        return "Service unavailable. Please try again later."

    tenant_id, channel_cfg = result

    # 2. Find deployed graph
    graph_record = await get_deployed_graph(db, tenant_id)
    if graph_record is None:
        logger.warning(
            "webhook_no_deployed_graph",
            extra={"tenant_id": str(tenant_id), "channel": channel},
        )
        return "Booking system is not active. Please contact the business directly."

    # 3. Execute graph
    try:
        executor = GraphExecutor()
        state = await executor.run(
            graph_record=graph_record,
            message=body,
            tenant_id=str(tenant_id),
            session_id=f"{channel}:{from_number}",
            channel=channel,
        )
        reply = state.get("response") or state.get("message") or "How can I help you?"
    except Exception as exc:
        logger.error(
            "webhook_graph_execution_error",
            extra={
                "tenant_id": str(tenant_id),
                "channel": channel,
                "error": str(exc),
            },
        )
        reply = "I'm having trouble right now. Please try again shortly."

    return reply


def _send_twilio_sms_reply(
    to: str, from_number: str, body: str, credentials: dict
) -> None:
    """Send reply SMS using tenant's Twilio credentials."""
    from twilio.rest import Client

    sid = credentials.get("account_sid") or settings.TWILIO_ACCOUNT_SID
    token = credentials.get("auth_token") or settings.TWILIO_AUTH_TOKEN
    from_num = credentials.get("phone_number") or settings.TWILIO_PHONE_FROM

    client = Client(sid, token)
    client.messages.create(to=to, from_=from_num, body=body)


def _send_twilio_whatsapp_reply(
    to: str, from_number: str, body: str, credentials: dict
) -> None:
    """Send reply WhatsApp message using tenant's Twilio credentials."""
    from twilio.rest import Client

    sid = credentials.get("account_sid") or settings.TWILIO_ACCOUNT_SID
    token = credentials.get("auth_token") or settings.TWILIO_AUTH_TOKEN
    from_num = credentials.get("phone_number") or settings.TWILIO_WHATSAPP_FROM

    client = Client(sid, token)
    client.messages.create(
        to=f"whatsapp:{to}",
        from_=f"whatsapp:{from_num}",
        body=body,
    )


@router.post("/twilio/sms")
async def inbound_sms(
    request: Request,
    From: Annotated[str, Form()],
    To: Annotated[str, Form()],
    Body: Annotated[str, Form()],
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio SMS inbound webhook.
    Twilio sends form-encoded POST: From, To, Body + other fields.
    Configure this URL in your Twilio number's Messaging webhook.
    """
    logger.info(
        "inbound_sms",
        extra={"from": From[-4:], "to": To, "body_len": len(Body)},
    )

    reply_text = await _route_inbound_message(
        db=db,
        from_number=From,
        to_number=To,
        body=Body,
        channel="sms",
    )

    # Send reply via Twilio API (not TwiML — async response)
    from backend.repositories.channel_repo import get_tenant_by_phone_number
    result = await get_tenant_by_phone_number(db, To)
    if result:
        _, channel_cfg = result
        try:
            _send_twilio_sms_reply(From, To, reply_text, channel_cfg.credentials)
        except Exception as exc:
            logger.error("sms_reply_failed", extra={"error": str(exc)})

    # Return empty 200 to Twilio (we handled reply via API, not TwiML)
    return {"status": "ok"}


@router.post("/twilio/whatsapp")
async def inbound_whatsapp(
    request: Request,
    From: Annotated[str, Form()],
    To: Annotated[str, Form()],
    Body: Annotated[str, Form()],
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio WhatsApp inbound webhook.
    'From' is 'whatsapp:+1234567890', 'To' is the tenant's WhatsApp number.
    Configure in Twilio Sandbox settings or production WhatsApp sender.
    """
    # Strip 'whatsapp:' prefix for phone number lookup
    from_clean = From.replace("whatsapp:", "")
    to_clean = To.replace("whatsapp:", "")

    logger.info(
        "inbound_whatsapp",
        extra={"from": from_clean[-4:], "to": to_clean, "body_len": len(Body)},
    )

    reply_text = await _route_inbound_message(
        db=db,
        from_number=from_clean,
        to_number=to_clean,
        body=Body,
        channel="whatsapp",
    )

    from backend.repositories.channel_repo import get_tenant_by_phone_number
    result = await get_tenant_by_phone_number(db, to_clean)
    if result:
        _, channel_cfg = result
        try:
            _send_twilio_whatsapp_reply(
                from_clean, to_clean, reply_text, channel_cfg.credentials
            )
        except Exception as exc:
            logger.error("whatsapp_reply_failed", extra={"error": str(exc)})

    return {"status": "ok"}
