"""
agents/intent_classifier.py

Classifies the user's intent from their raw message using the configured LLM.

Intent categories:
  book        — user wants to book a new appointment
  reschedule  — user wants to change an existing appointment
  cancel      — user wants to cancel
  check       — user wants to see their appointment details
  other       — anything else (routes to escalation)

Design:
- LLM call is wrapped in try/except to ensure graph never crashes (R14).
- Prompt is a template — stored here separately from orchestration logic.
- Output is validated: only accepted values are set; unknown values → "other".
- cost_weight = 0.5 (from agent registry in SKILLS.md).
"""

import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.base import BaseAgent
from backend.core.config import settings

logger = logging.getLogger(__name__)

VALID_INTENTS = {
    "book", "reschedule", "cancel", "check",
    "list_services", "list_staff", "check_slots",
    "other",
}

SYSTEM_PROMPT = """You are an intent classifier for an appointment booking system.

Classify the user's message into exactly ONE of these intents:
- book: user wants to book a new appointment
- reschedule: user wants to change an existing appointment time
- cancel: user wants to cancel an appointment
- check: user wants to know their appointment details or status
- list_services: user asks what services/treatments/prices are available
- list_staff: user asks who the staff/doctors/stylists are
- check_slots: user asks about available time slots or appointment availability for a date
- other: anything else (greetings, unclear requests)

Respond ONLY with a valid JSON object like this:
{"intent": "book", "confidence": 0.95, "reasoning": "user asked to book"}

Do not include any other text — only the JSON object.
"""


class IntentClassifierAgent(BaseAgent):
    name = "intent_classifier"
    display_name = "Intent Classifier"
    cost_weight = 0.5

    def __init__(self) -> None:
        # LLM is instantiated once per agent instance.
        # Agents are not singletons — a fresh instance is created per graph compile.
        # No state is stored on self beyond the LLM client.
        self._llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0,          # deterministic classification
            max_tokens=100,         # intent response is tiny
        )

    async def run(self, state: dict) -> dict:
        """
        Classify intent from state["user_input"].
        Returns state with "intent" and "next_node" set.
        """
        user_input = state.get("user_input", "")

        if not user_input.strip():
            return {
                **state,
                "intent": "other",
                "next_node": "escalation_agent",
                "response": "I didn't receive your message. Could you please try again?",
            }

        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_input),
            ]

            ai_response = await self._llm.ainvoke(messages)
            raw_content = ai_response.content.strip()

            # Parse and validate the JSON response
            parsed = json.loads(raw_content)
            intent = parsed.get("intent", "other")

            # Safety: only accept known intents
            if intent not in VALID_INTENTS:
                intent = "other"

            logger.info(
                "intent_classified",
                extra={
                    "tenant_id": state.get("tenant_id"),
                    "session_id": state.get("session_id"),
                    "intent": intent,
                    "confidence": parsed.get("confidence"),
                },
            )

            return {
                **state,
                "intent": intent,
                "next_node": intent,  # conditional edges use this to route
            }

        except json.JSONDecodeError as exc:
            logger.warning(
                "intent_classifier_json_error",
                extra={"error": str(exc), "raw": raw_content[:200]},
            )
            # Graceful fallback — don't crash the graph
            return {**state, "intent": "other", "next_node": "escalation_agent"}

        except Exception as exc:
            return self._error_state(
                state,
                "I had trouble understanding your request. Let me connect you to support.",
                exc,
            )
