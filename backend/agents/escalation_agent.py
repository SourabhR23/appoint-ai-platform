"""
agents/escalation_agent.py

Human handoff agent — terminal node for any flow that can't be automated.
Triggered when:
- intent = "other"
- any agent catches an unhandled error and routes here
- LLM confidence is too low

Records escalation in logs for staff to follow up.
cost_weight = 0.5
"""

import logging
import uuid
from datetime import datetime, timezone

from backend.agents.base import BaseAgent

logger = logging.getLogger(__name__)

DEFAULT_HANDOFF_MESSAGE = (
    "I'm connecting you to our support team. "
    "A staff member will reach out to you shortly. "
    "You can also call us directly during business hours."
)


class EscalationAgent(BaseAgent):
    name = "escalation_agent"
    display_name = "Escalation Agent"
    cost_weight = 0.5

    async def run(self, state: dict) -> dict:
        tenant_id_str = state.get("tenant_id", "")
        session_id = state.get("session_id", "")
        error = state.get("error")
        intent = state.get("intent", "other")

        logger.warning(
            "conversation_escalated",
            extra={
                "tenant_id": tenant_id_str,
                "session_id": session_id,
                "intent": intent,
                "error": error,
                "channel": state.get("channel"),
                "sender": state.get("sender_identifier"),
                "escalated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        # In a real system this would also:
        # - Create an escalation record in DB
        # - Send Slack/email alert to the tenant's staff
        # - For WhatsApp: initiate handoff protocol
        # These are deferred to Phase 2.

        response = DEFAULT_HANDOFF_MESSAGE
        if error:
            # Don't expose internal error details to user (security)
            response = (
                "I encountered an issue and need to escalate this to our team. "
                + DEFAULT_HANDOFF_MESSAGE
            )

        return {
            **state,
            "escalated": True,
            "response": response,
            "next_node": "__end__",
        }
