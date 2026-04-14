"""
graph/builder.py

Converts a saved React Flow graph definition (JSON) into an executable LangGraph.

Flow:
  Frontend saves JSON → stored in graph_versions.definition
  builder.compile_graph(definition) → LangGraph CompiledStateGraph
  Compiled graph is cached in Redis by (graph_id, version)

Compiler rules (CLAUDE.md):
- Every node type must exist in AGENT_REGISTRY — raises ValueError otherwise.
- Graph must have exactly one entry node.
- Conditional edges map state["intent"] to target node IDs.
- Direct edges use add_edge().
- On END: use langgraph.graph.END sentinel.
"""

import json
import logging
from typing import Any

from langgraph.graph import END, StateGraph

from backend.graph.registry import get_agent_class
from backend.graph.state import GraphState

logger = logging.getLogger(__name__)


def compile_graph(graph_definition: dict, tenant_id: str) -> Any:
    """
    Compile a React Flow JSON definition into an executable LangGraph.

    Args:
        graph_definition: dict with "nodes" and "edges" lists.
        tenant_id: Used for logging; injected into agent instances.

    Returns:
        A compiled LangGraph StateGraph ready to invoke.

    Raises:
        ValueError: if the graph is invalid (unknown agent type, missing entry node, etc.)
    """
    nodes: list[dict] = graph_definition.get("nodes", [])
    edges: list[dict] = graph_definition.get("edges", [])

    if not nodes:
        raise ValueError("Graph must have at least one node.")

    # ── Step 1: Find entry node ────────────────────────────────────────────────
    # Entry node is the first node in the list OR nodes marked as "entry" type.
    # For MVP: intent_classifier is always the entry point.
    entry_node = _find_entry_node(nodes)
    if not entry_node:
        raise ValueError(
            "Graph must have an entry node. "
            "Ensure intent_classifier or a channel node is the first node."
        )

    # ── Step 2: Build the StateGraph ──────────────────────────────────────────
    workflow = StateGraph(GraphState)

    # Register all nodes
    for node_def in nodes:
        node_id: str = node_def["id"]
        node_type: str = node_def["type"]
        node_config: dict = node_def.get("config", {})

        agent_class = get_agent_class(node_type)  # raises ValueError on unknown type
        agent_instance = agent_class()

        # Wrap run() to inject node_config into state before execution
        async def make_node_fn(agent=agent_instance, config=node_config):
            async def node_fn(state: dict) -> dict:
                # Merge node-level config into state so agent can read it
                enriched = {**state, "node_config": config}
                return await agent.run(enriched)
            return node_fn

        import asyncio
        node_fn = asyncio.get_event_loop().run_until_complete(make_node_fn())
        workflow.add_node(node_id, node_fn)

    workflow.set_entry_point(entry_node["id"])

    # ── Step 3: Register edges ────────────────────────────────────────────────
    # Group conditional edges by source node
    conditional_targets: dict[str, dict[str, str]] = {}

    for edge in edges:
        source: str = edge["source"]
        target: str = edge["target"]
        condition: str | None = edge.get("condition")

        # Resolve "__end__" string to LangGraph END sentinel
        resolved_target = END if target == "__end__" else target

        if condition:
            # Conditional edge: route based on state["intent"] or state["next_node"]
            if source not in conditional_targets:
                conditional_targets[source] = {}
            conditional_targets[source][condition] = resolved_target
        else:
            workflow.add_edge(source, resolved_target)

    # Register all conditional edges
    for source, condition_map in conditional_targets.items():
        # Router function reads state["next_node"] set by each agent
        def make_router(cm: dict):
            def router(state: dict) -> str:
                # Prefer explicit next_node from agent over intent
                next_node = state.get("next_node") or state.get("intent", "other")
                return cm.get(next_node, END)
            return router

        workflow.add_conditional_edges(source, make_router(condition_map), condition_map)

    compiled = workflow.compile()

    logger.info(
        "graph_compiled",
        extra={
            "tenant_id": tenant_id,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "entry_node": entry_node["id"],
        },
    )

    return compiled


def _find_entry_node(nodes: list[dict]) -> dict | None:
    """
    Entry node rules (in priority order):
    1. Node explicitly marked as entry (type == "entry" or config.is_entry == True)
    2. First intent_classifier node
    3. First node in the list (fallback)
    """
    for node in nodes:
        if node.get("config", {}).get("is_entry"):
            return node

    for node in nodes:
        if node.get("type") == "intent_classifier":
            return node

    return nodes[0] if nodes else None
