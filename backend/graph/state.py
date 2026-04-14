"""
graph/state.py

GraphState TypedDict — the shared state passed between all agent nodes.

Design rules (R4):
- State is the ONLY way agents share context. No instance-level variables.
- LangGraph merges state dicts between nodes.
- `messages` uses Annotated[list, operator.add] so each node's messages are appended,
  not overwritten (LangGraph convention).
- All fields are Optional where the agent populating them hasn't run yet.
"""

import operator
from typing import Annotated, List, Optional
from typing_extensions import TypedDict


class GraphState(TypedDict, total=False):
    """
    Shared state flowing through the agent graph.

    Fields are populated progressively as nodes execute:
    - Entry agent sets: tenant_id, session_id, user_input, channel, sender_identifier
    - Intent classifier sets: intent
    - Booking agent sets: appointment_id, confirmed_slot
    - Notification agent sets: notification_status
    - Escalation agent sets: escalated
    - Any agent can set: error, next_node, response
    """

    # ── Core context (set by entry agent) ──────────────────────────────────────
    tenant_id: str               # UUID string — injected from JWT, not from user
    session_id: str              # Client session for conversation continuity
    user_input: str              # The raw message from the user
    channel: str                 # webchat | whatsapp | sms
    sender_identifier: str       # Phone number or session token

    # ── Conversation history ───────────────────────────────────────────────────
    # Annotated with operator.add → LangGraph appends, not replaces
    messages: Annotated[List[dict], operator.add]

    # ── Intent ────────────────────────────────────────────────────────────────
    # Set by IntentClassifier: book | reschedule | cancel | check | other
    intent: str

    # ── Appointment context ────────────────────────────────────────────────────
    appointment_id: str          # UUID string of the booked/targeted appointment
    patient_name: str
    patient_phone: str
    patient_email: str
    service_id: str              # UUID string
    staff_id: str                # UUID string
    requested_datetime: str      # ISO 8601 string from user input
    confirmed_slot: str          # ISO 8601 UTC after booking is confirmed
    slot_end_datetime: str

    # ── Output ────────────────────────────────────────────────────────────────
    response: str                # Final text response to send to user
    notification_status: str     # queued | sent | failed

    # ── Routing ───────────────────────────────────────────────────────────────
    next_node: str               # Used by conditional edges to route to next agent
    error: str                   # Error message if something went wrong
    escalated: bool              # True when handed off to human
