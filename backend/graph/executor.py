"""
graph/executor.py

Executes a compiled LangGraph for a given tenant and chat message.

Responsibilities:
1. Load (or compile) the graph from Redis cache.
2. Inject DB session, tenant config, and context into initial state.
3. Run the graph and return the final response.
4. Record a billing event for nodes executed.

Caching strategy:
- Cache key: "graph:{graph_id}:v{version}"
- TTL: 1 hour (graphs don't change frequently)
- On cache miss: compile from graph_versions.definition and cache.
"""

import json
import logging
import pickle
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.graph.builder import compile_graph
from backend.graph.state import GraphState

logger = logging.getLogger(__name__)

# Redis client for compiled graph caching
_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis_client


async def _get_or_compile_graph(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    graph_id: uuid.UUID,
) -> tuple[any, int]:
    """
    Returns (compiled_graph, version).
    Tries Redis cache first, compiles from DB on miss.
    """
    from backend.repositories.graph_repo import get_graph_by_id, get_graph_version

    graph = await get_graph_by_id(db, tenant_id, graph_id)
    if not graph or not graph.is_deployed:
        raise ValueError(f"No deployed graph found for graph_id={graph_id}")

    cache_key = f"graph:{graph_id}:v{graph.active_version}"
    redis = get_redis()

    # Try cache
    cached = await redis.get(cache_key)
    if cached:
        logger.debug("graph_cache_hit", extra={"cache_key": cache_key})
        return pickle.loads(cached), graph.active_version

    # Cache miss — compile from DB
    version_row = await get_graph_version(
        db, tenant_id, graph_id, graph.active_version
    )
    if not version_row:
        raise ValueError(
            f"Graph version {graph.active_version} not found for graph_id={graph_id}"
        )

    compiled = compile_graph(version_row.definition, str(tenant_id))

    # Cache for 1 hour
    await redis.setex(cache_key, 3600, pickle.dumps(compiled))
    logger.info("graph_compiled_and_cached", extra={"cache_key": cache_key})

    return compiled, graph.active_version


async def execute_graph(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    graph_id: uuid.UUID,
    user_input: str,
    session_id: str,
    channel: str,
    sender_identifier: str | None,
    tenant_config: dict,
) -> GraphState:
    """
    Main entry point for the /chat endpoint.
    Runs the compiled graph and returns the final state.
    """
    execution_id = str(uuid.uuid4())

    compiled_graph, version = await _get_or_compile_graph(db, tenant_id, graph_id)

    # Build initial state — injecting DB + tenant context
    initial_state: GraphState = {
        "tenant_id": str(tenant_id),
        "session_id": session_id,
        "user_input": user_input,
        "channel": channel,
        "sender_identifier": sender_identifier or "",
        "messages": [{"role": "user", "content": user_input}],
        "intent": "",
        "appointment_id": "",
        "response": "",
        "next_node": "",
        "error": "",
        "escalated": False,
        "notification_status": "",
        # Injected runtime context (not stored in DB)
        "db": db,
        "tenant_config": tenant_config,
    }

    try:
        final_state = await compiled_graph.ainvoke(initial_state)
    except Exception as exc:
        logger.error(
            "graph_execution_error",
            extra={
                "tenant_id": str(tenant_id),
                "graph_id": str(graph_id),
                "execution_id": execution_id,
                "error": str(exc),
            },
        )
        raise

    # ── Record billing event (async, non-blocking) ─────────────────────────────
    # In Phase 1 / trial: just log. Stripe integration is Phase 2.
    logger.info(
        "graph_execution_completed",
        extra={
            "tenant_id": str(tenant_id),
            "graph_id": str(graph_id),
            "execution_id": execution_id,
            "intent": final_state.get("intent"),
            "escalated": final_state.get("escalated"),
        },
    )

    return final_state
