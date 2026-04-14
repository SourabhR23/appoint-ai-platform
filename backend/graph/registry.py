"""
graph/registry.py

Single source of truth for all available agent types.
The frontend uses this list to populate the sidebar node library.
The compiler uses it to instantiate agents from graph JSON.

To add a new agent:
1. Create the class in agents/
2. Import it here
3. Add an entry to AGENT_REGISTRY

No other file should need changing.
"""

from typing import Type

from backend.agents.base import BaseAgent
from backend.agents.intent_classifier import IntentClassifierAgent
from backend.agents.booking_agent import BookingAgent
from backend.agents.reschedule_agent import RescheduleAgent
from backend.agents.cancellation_agent import CancellationAgent
from backend.agents.status_checker import StatusCheckerAgent
from backend.agents.notification_agent import NotificationAgent
from backend.agents.escalation_agent import EscalationAgent


# Registry: agent type key → agent class
# Key must match the `name` attribute on the class.
AGENT_REGISTRY: dict[str, Type[BaseAgent]] = {
    IntentClassifierAgent.name: IntentClassifierAgent,
    BookingAgent.name: BookingAgent,
    RescheduleAgent.name: RescheduleAgent,
    CancellationAgent.name: CancellationAgent,
    StatusCheckerAgent.name: StatusCheckerAgent,
    NotificationAgent.name: NotificationAgent,
    EscalationAgent.name: EscalationAgent,
}

# Metadata for frontend sidebar — cost_weight, display_name, icon, category
AGENT_METADATA: list[dict] = [
    {
        "type": IntentClassifierAgent.name,
        "display_name": IntentClassifierAgent.display_name,
        "cost_weight": IntentClassifierAgent.cost_weight,
        "category": "processing",
        "description": "Classifies the user's intent (book, cancel, reschedule, check).",
    },
    {
        "type": BookingAgent.name,
        "display_name": BookingAgent.display_name,
        "cost_weight": BookingAgent.cost_weight,
        "category": "appointment",
        "description": "Creates a new appointment after checking slot availability.",
    },
    {
        "type": RescheduleAgent.name,
        "display_name": RescheduleAgent.display_name,
        "cost_weight": RescheduleAgent.cost_weight,
        "category": "appointment",
        "description": "Moves an existing appointment to a new time slot.",
    },
    {
        "type": CancellationAgent.name,
        "display_name": CancellationAgent.display_name,
        "cost_weight": CancellationAgent.cost_weight,
        "category": "appointment",
        "description": "Soft-cancels an appointment and sends confirmation.",
    },
    {
        "type": StatusCheckerAgent.name,
        "display_name": StatusCheckerAgent.display_name,
        "cost_weight": StatusCheckerAgent.cost_weight,
        "category": "appointment",
        "description": "Retrieves appointment details by phone or reference ID.",
    },
    {
        "type": NotificationAgent.name,
        "display_name": NotificationAgent.display_name,
        "cost_weight": NotificationAgent.cost_weight,
        "category": "output",
        "description": "Sends confirmations via email, SMS, or WhatsApp.",
    },
    {
        "type": EscalationAgent.name,
        "display_name": EscalationAgent.display_name,
        "cost_weight": EscalationAgent.cost_weight,
        "category": "output",
        "description": "Hands off to a human agent when automation cannot resolve the request.",
    },
]


def get_agent_class(agent_type: str) -> Type[BaseAgent]:
    """
    Returns the agent class for the given type key.
    Raises ValueError if the type is not registered.
    """
    cls = AGENT_REGISTRY.get(agent_type)
    if cls is None:
        raise ValueError(
            f"Unknown agent type '{agent_type}'. "
            f"Registered types: {list(AGENT_REGISTRY.keys())}"
        )
    return cls
