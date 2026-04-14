"""
agents/base.py

Abstract BaseAgent class that every agent must extend.

Rules enforced:
- Agents are stateless (R4): no instance-level mutable state.
- Every agent has a name, cost_weight, input/output schemas (from CLAUDE.md).
- run() always returns a GraphState dict — never raises unhandled exceptions (R14).
- Agents receive tenant_id through GraphState — never from instance-level config.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base for all agent nodes.

    Subclasses must define:
      - name (str): unique key matching agent registry
      - display_name (str): human-readable label for UI
      - cost_weight (float): billing units per execution
      - run(state: dict) -> dict: the agent logic

    Design choice: we use plain dicts (GraphState TypedDict) for state instead of
    Pydantic models because LangGraph natively works with TypedDicts and supports
    state merging via Annotated[list, operator.add].
    """

    name: str = ""
    display_name: str = ""
    cost_weight: float = 1.0

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce that subclasses define required class attributes."""
        super().__init_subclass__(**kwargs)
        required = ["name", "display_name", "cost_weight"]
        for attr in required:
            if not getattr(cls, attr, None) and cls.__name__ != "BaseAgent":
                raise TypeError(
                    f"Agent class '{cls.__name__}' must define '{attr}'."
                )

    @abstractmethod
    async def run(self, state: dict) -> dict:
        """
        Execute agent logic.

        Args:
            state: GraphState dict — contains all conversation context.

        Returns:
            Updated GraphState dict. Must always return a dict, even on error.
            On error: set state["error"] and state["next_node"] = "escalation_agent".
        """
        raise NotImplementedError

    def _error_state(self, state: dict, message: str, exc: Exception | None = None) -> dict:
        """
        Builds a graceful error state that routes to escalation (R14).
        Call this inside any except block in run().
        """
        logger.error(
            "agent_error",
            extra={
                "agent": self.name,
                "tenant_id": state.get("tenant_id"),
                "error": str(exc) if exc else message,
            },
        )
        return {
            **state,
            "error": message,
            "next_node": "escalation_agent",
        }
