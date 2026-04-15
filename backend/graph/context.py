"""
graph/context.py

Request-scoped context variables for injecting runtime resources into agent nodes.

Problem: SQLAlchemy AsyncSession and tenant_config cannot be stored in LangGraph
GraphState (they get stripped during state merges) and LangGraph's config-passing
API varies across versions.

Solution: Python contextvars — set once per request in executor.py, read by each
node in builder.py. Thread-safe and async-safe.
"""

from contextvars import ContextVar
from typing import Any, Optional

# Set before each graph invocation. Reset in a finally block.
current_db: ContextVar[Optional[Any]] = ContextVar("current_db", default=None)
current_tenant_config: ContextVar[dict] = ContextVar("current_tenant_config", default={})
