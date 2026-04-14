"""
api/chat.py

POST /api/v1/chat/{graph_id} — Execute the deployed agent graph for a chat message.

This is the real-time endpoint used by:
- Web chat widget
- WhatsApp webhook
- SMS webhook

Rate limiting: 100 req/min per tenant (R9) via Redis sliding window.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import get_current_tenant
from backend.graph.executor import execute_graph
from backend.models.tenant import Tenant
from backend.schemas.graph import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


async def _check_rate_limit(tenant_id: str, redis_url: str) -> None:
    """
    Redis sliding window rate limiter (R9).
    Key: "rl:chat:{tenant_id}" with 60s TTL.
    Raises 429 if limit exceeded.
    """
    import redis.asyncio as aioredis

    redis = aioredis.from_url(redis_url)
    key = f"rl:chat:{tenant_id}"

    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)  # 60-second window

        if count > settings.RATE_LIMIT_CHAT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {settings.RATE_LIMIT_CHAT} requests/minute.",
            )
    finally:
        await redis.aclose()


@router.post(
    "/{graph_id}",
    response_model=ChatResponse,
)
async def process_chat_message(
    graph_id: uuid.UUID,
    data: ChatRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Entry point for all chat-based bookings.

    1. Rate limit check.
    2. Execute the deployed agent graph.
    3. Return the agent's response.

    The graph executor handles all LangGraph state transitions internally.
    """
    # Rate limit check (R9)
    await _check_rate_limit(str(tenant.id), settings.REDIS_URL)

    # Inject tenant context needed by agents
    tenant_config = {
        **tenant.config,
        "timezone": tenant.timezone,
    }

    try:
        final_state = await execute_graph(
            db=db,
            tenant_id=tenant.id,
            graph_id=graph_id,
            user_input=data.message,
            session_id=data.session_id,
            channel=data.channel,
            sender_identifier=data.sender_identifier,
            tenant_config=tenant_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(
            "chat_execution_error",
            extra={
                "tenant_id": str(tenant.id),
                "graph_id": str(graph_id),
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your message. Please try again.",
        )

    return ChatResponse(
        session_id=data.session_id,
        response=final_state.get("response", "I'm unable to process your request right now."),
        intent=final_state.get("intent"),
        appointment_id=(
            uuid.UUID(final_state["appointment_id"])
            if final_state.get("appointment_id")
            else None
        ),
        next_action=final_state.get("next_node"),
        error=final_state.get("error") if final_state.get("escalated") else None,
    )
