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

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.graph.builder import compile_graph
from backend.graph.state import GraphState

logger = logging.getLogger(__name__)

# In-memory graph cache: {cache_key: compiled_graph}
# Compiled LangGraph objects contain LLM client instances that cannot be
# safely pickled to Redis. An in-memory dict is safe and fast enough for
# development and single-process production deployments.
# Cache is invalidated automatically when the version number changes.
_graph_cache: dict[str, Any] = {}


async def _get_or_compile_graph(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    graph_id: uuid.UUID,
) -> tuple[Any, int]:
    """
    Returns (compiled_graph, version).
    Uses in-memory cache keyed by (graph_id, version).
    Recompiles from DB on cache miss (version change or server restart).
    """
    from backend.repositories.graph_repo import get_graph_by_id, get_graph_version

    graph = await get_graph_by_id(db, tenant_id, graph_id)
    if not graph or not graph.is_deployed:
        raise ValueError(f"No deployed graph found for graph_id={graph_id}")

    cache_key = f"graph:{graph_id}:v{graph.active_version}"

    if cache_key in _graph_cache:
        logger.debug("graph_cache_hit", extra={"cache_key": cache_key})
        return _graph_cache[cache_key], graph.active_version

    # Cache miss — compile from DB
    version_row = await get_graph_version(
        db, tenant_id, graph_id, graph.active_version
    )
    if not version_row:
        raise ValueError(
            f"Graph version {graph.active_version} not found for graph_id={graph_id}"
        )

    compiled = compile_graph(version_row.definition, str(tenant_id))
    _graph_cache[cache_key] = compiled

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

    # Build initial state — only serialisable GraphState fields here.
    # db (AsyncSession) and tenant_config are passed via LangGraph's config
    # "configurable" dict so they survive state merges across nodes.
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
    }

    # Set request-scoped context vars so every node can read db + tenant_config
    # without them being in GraphState (LangGraph strips non-schema keys).
    from backend.graph.context import current_db, current_tenant_config
    token_db = current_db.set(db)
    token_cfg = current_tenant_config.set(tenant_config)

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
    finally:
        # Always reset context vars after execution
        current_db.reset(token_db)
        current_tenant_config.reset(token_cfg)

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
