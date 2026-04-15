# Agent System & Graph Architecture

## Overview

The AppointAI platform uses a **modular agent-based architecture** powered by **LangGraph**. Instead of a monolithic chatbot, we decompose the appointment workflow into specialized agents, each with a single responsibility. Agents are orchestrated via a visual **graph** that defines the conversation flow.

### Why This Design?

| Goal | Solution |
|---|---|
| Handle multiple intents (book, reschedule, cancel, check status) | Separate agent per intent + intent classifier |
| Make changes without rewriting the whole flow | Modular agents plugged into graph |
| Let non-technical users customize flow | Visual graph builder (drag-drop nodes/edges) |
| Trace what happened in a conversation | Each agent logs structured input/output |
| Reuse agents across channels (SMS, WhatsApp, web) | Agents are channel-agnostic |

---

## Agent Architecture Pattern

Every agent follows the same pattern:

```python
class BookingAgent(BaseAgent):
    name = "booking_agent"                    # Unique ID
    display_name = "Appointment Booking"      # User-friendly name
    cost_weight = 1.5                         # Billing multiplier for LLM calls
    
    class InputSchema(BaseModel):             # What agent accepts
        tenant_id: UUID
        service_id: UUID
        preferred_datetime: datetime
        
    class OutputSchema(BaseModel):            # What agent produces
        success: bool
        appointment_id: Optional[UUID]
        message: str
    
    async def run(self, state: GraphState) -> GraphState:
        # 1. Extract from state
        # 2. Validate inputs
        # 3. Call LLM or perform action
        # 4. Update state
        # 5. Return
```

**Why structured schemas?**
- Input: guarantees agent receives clean data
- Output: caller knows exactly what to expect
- LLM: can't hallucinate field names

---

## The 7 Agents Explained

### 1. **Intent Classifier** ← Entry Point

**Role:** Understand what the customer wants.

**Input:** Raw message text  
**Output:** Detected intent + extracted entities

**Example Flow:**
```
Customer: "Can I book an appointment with Dr. Patel tomorrow at 3 PM?"
     ↓
Intent Classifier (calls LLM)
     ↓
Output: {
  "intent": "book",
  "service_name": "consultation",
  "preferred_datetime": "2026-04-16 15:00",
  "staff_name": "Dr. Patel"
}
```

**Why it exists:**
- Different intents → different agents. Classifier is the router.
- One LLM call upfront saves multiple wrong calls later.

**Interview answer:**
> "Every conversation starts here. The intent classifier is like a receptionist who listens to the customer and says 'Oh, you want to book? Let me get the booking specialist.' It extracts the customer's intent (book/reschedule/cancel/check) and relevant details (service, date, staff) in one structured call, then routes to the right agent."

---

### 2. **Booking Agent** ← Core Business Logic

**Role:** Create a new appointment.

**Input:**
```python
{
  "tenant_id": UUID,
  "service_id": UUID,
  "staff_id": UUID,
  "preferred_datetime": datetime,
  "customer_phone": str,
  "customer_name": str
}
```

**Output:**
```python
{
  "success": bool,
  "appointment_id": UUID (if success),
  "confirmed_slot": datetime,
  "message": str  # "Your appointment is confirmed for..."
}
```

**Example Workflow:**
```
Intent: "book"
     ↓
Booking Agent:
  1. Look up service (duration, buffer)
  2. Check staff availability (walk slot algo)
  3. Reserve slot (INSERT appointment)
  4. Return confirmed time
     ↓
Output: { success: true, appointment_id: "...", confirmed_slot: "2026-04-16 15:30" }
```

**Why it exists:**
- Isolates booking logic from conversation flow
- Can be reused by manual UI booking (same INSERT code)
- Easy to test without LLM

**Interview answer:**
> "The booking agent owns the core business logic: checking availability and creating the appointment. It doesn't care how the request arrived (WhatsApp, SMS, web form). It validates the service exists, staff can work that time, and creates the appointment record. If we later want an admin dashboard to book manually, same agent runs the logic."

---

### 3. **Reschedule Agent** ← Change Existing Appointment

**Role:** Move an existing appointment to a new slot.

**Input:**
```python
{
  "tenant_id": UUID,
  "appointment_id": UUID,
  "new_preferred_datetime": datetime,
  "reason": str (optional)
}
```

**Output:**
```python
{
  "success": bool,
  "new_slot": datetime (if success),
  "message": str
}
```

**Example:**
```
Customer: "Can I move my 3 PM appointment to 5 PM instead?"
     ↓
Intent: "reschedule"
     ↓
Reschedule Agent:
  1. Find appointment by ID
  2. Check availability at 5 PM
  3. Release old slot, reserve new slot
  4. Return new time
     ↓
Message: "Your appointment has been moved to 5:00 PM tomorrow."
```

**Why separate from Booking Agent?**
- Reschedule has extra complexity: release old slot, validate new one
- Different validations (is this appointment cancellable? Staff available?)
- Separate agent = easier to test + maintain

**Interview answer:**
> "We could combine reschedule into the booking agent, but reschedule has different logic: find existing appointment, release the old slot, check new availability. Separating it makes the code clearer and easier to test each scenario independently."

---

### 4. **Cancellation Agent** ← Soft Delete

**Role:** Cancel an existing appointment.

**Input:**
```python
{
  "tenant_id": UUID,
  "appointment_id": UUID,
  "reason": str
}
```

**Output:**
```python
{
  "success": bool,
  "message": str  # "Your appointment has been cancelled..."
}
```

**Example:**
```
Customer: "I need to cancel my 3 PM appointment tomorrow."
     ↓
Cancellation Agent:
  1. Find appointment
  2. Check cancellation window (e.g., 24h before allowed)
  3. Soft-delete (set deleted_at timestamp, don't hard delete)
  4. Log reason in audit trail
     ↓
Output: { success: true, message: "Cancelled successfully..." }
```

**Why soft delete?**
- Keep full audit trail (important for clinics, salons)
- Can support "undo" UX if needed
- Financial reconciliation (what was refunded?)

**Interview answer:**
> "Cancellation soft-deletes the appointment. We never hard-delete because businesses need to audit why customers cancelled. Maybe you'll see a pattern: 'Friday cancellations spike at 5 PM.' That data informs your marketing. Hard delete loses that."

---

### 5. **Status Checker** ← Read-Only Query

**Role:** Look up upcoming appointments.

**Input:**
```python
{
  "tenant_id": UUID,
  "customer_phone": str
}
```

**Output:**
```python
{
  "has_upcoming": bool,
  "appointments": [
    {
      "service_name": str,
      "staff_name": str,
      "datetime": datetime
    }
  ],
  "message": str  # "You have 1 appointment tomorrow at 3 PM..."
}
```

**Example:**
```
Customer: "When's my next appointment?"
     ↓
Status Checker:
  1. Query appointments WHERE customer_phone=... AND datetime > NOW
  2. Return upcoming list
     ↓
Output: { has_upcoming: true, appointments: [...], message: "You have..." }
```

**Why separate agent?**
- Read-only, no LLM call needed (deterministic lookup)
- Fast response (no inference latency)
- Reusable by dashboard UI

**Interview answer:**
> "Status checker doesn't call the LLM — it's just a database query. Why make it an agent? Consistency. Every interaction goes through the graph, so we get unified logging and error handling. Also, if we later want to add AI reasoning ('based on your history, you might want to reschedule'), we upgrade the agent without changing the graph."

---

### 6. **Notification Agent** ← Async Delivery

**Role:** Send confirmation/reminder (SMS, WhatsApp, email).

**Input:**
```python
{
  "tenant_id": UUID,
  "appointment_id": UUID,
  "customer_phone": str,
  "customer_email": str,
  "channel": str  # "sms" | "whatsapp" | "email"
}
```

**Output:**
```python
{
  "sent": bool,
  "provider_message_id": str,  # Twilio SID, etc.
  "message": str
}
```

**Example:**
```
Booking Agent returns success
     ↓
Notification Agent:
  1. Enqueue Celery task (non-blocking)
  2. Render template (e.g., "Your appointment with Dr. Patel...")
  3. Send via Twilio/Gmail
  4. Log to notification_logs table
     ↓
Output: { sent: true, provider_message_id: "...", message: "Confirmation sent" }
```

**Why async (Celery)?**
- Don't block customer waiting for email to send
- If SMS fails, retry 3× with backoff
- Audit trail (notification_logs) for compliance

**Interview answer:**
> "Notification doesn't block. When you book an appointment, we immediately return the confirmation to the customer, then asynchronously send the SMS/email via Celery workers. If delivery fails, we retry. This way customer experience is instant, and delivery is reliable in the background."

---

### 7. **Escalation Agent** ← Exception Handling

**Role:** Alert human when agent can't handle request.

**Input:**
```python
{
  "tenant_id": UUID,
  "reason": str,  # Why escalation needed
  "context": dict  # Full conversation state
}
```

**Output:**
```python
{
  "escalated": bool,
  "ticket_id": UUID,
  "message": str  # "I'm connecting you with our team..."
}
```

**Example:**
```
Customer: "I want to book with someone who's bilingual."
     ↓
Intent Classifier: intent="other" (not standard booking)
     ↓
Escalation Agent:
  1. Create support ticket
  2. Alert business owner
  3. Return ticket ID to customer
     ↓
Output: { escalated: true, ticket_id: "...", message: "A team member will help you..." }
```

**Why it exists:**
- Agents have guardrails; unexpected requests go to humans
- Prevents "hallucination" (agent making up something)
- Captures unmet use cases (feedback for product)

**Interview answer:**
> "Real conversations have edge cases. 'I want to book at a location you didn't mention,' 'I have a medical emergency.' The escalation agent doesn't try to solve these. It creates a ticket, alerts the business owner, and tells the customer 'Someone will help you shortly.' This prevents the agent from confidently giving wrong info."

---

## The Graph System

### What is a Graph?

A **graph** is a visual flowchart of agents + decision rules. Each node is an agent; each edge is a condition.

```
┌──────────────────┐
│ Intent Classifier│
└────────┬─────────┘
         │
    ┌────┴──────────────────────────┐
    │                               │
    ↓                               ↓
┌──────────┐   ┌──────────┐  ┌──────────────┐
│   Book   │   │Reschedule│  │  Cancellation│
└────┬─────┘   └────┬─────┘  └──────┬───────┘
     │              │                │
     └──────────────┴────────────────┘
              │
              ↓
    ┌──────────────────┐
    │   Notification   │
    └────────┬─────────┘
             │
        ┌────┴──────────────┐
        │                   │
        ↓                   ↓
    ┌─────────┐    ┌──────────────┐
    │ Success │    │  Escalation  │
    └─────────┘    └──────────────┘
```

### Why Graph Instead of Monolithic Chatbot?

| Monolithic Bot | Graph System |
|---|---|
| One giant prompt handles everything | Each agent has focused prompt |
| Hard to change flow without breaking things | Change graph visually, agents stay stable |
| Customer doesn't control flow | Business owner customizes graph (templates) |
| Can't reuse agents | Same agent in multiple graphs |
| Hallucination risk (agent tries everything) | Clear boundaries (agent only does its job) |

### Example: Multiple Graphs

**MedCare Clinic (Full Booking Suite):**
```
Intent → [Book + Reschedule + Cancel + Status] → Notification
```

**Gloss & Glow Salon (Booking Only):**
```
Intent → [Book] → Notification
```

**Another tenant (Info Only):**
```
Intent → [Status] → (no booking, no notification)
```

**Same agents, different graphs!** Easy to customize per tenant.

---

## The GraphState: Shared Memory

All agents read/write to a shared `GraphState`:

```python
class GraphState(TypedDict):
    tenant_id: str
    session_id: str
    message: str                        # Current user input
    conversation_history: list          # Full chat history
    intent: Optional[str]               # Extracted by classifier
    extracted_entities: dict            # service_id, staff_id, datetime, etc.
    appointment_id: Optional[UUID]      # Current appointment being modified
    response: str                        # Final message to send back
    success: bool                        # Did agent succeed?
    error: Optional[str]                # Error message if failed
```

**Why?**
- Agents pass data cleanly (no hidden globals)
- Easy to log full state for debugging
- Testable (mock state, run agent, check output)

---

## Interview Scenarios

### Scenario 1: "Why not just build one big LLM chatbot?"

**Answer:**
> "A single prompt-based chatbot sounds simple, but breaks in production. Imagine you tell it 'book an appointment' and it hallucinates: 'I've booked you with Dr. Smith on March 50th.' Our graph approach uses specialized agents. The Booking Agent has guardrails: it only works with real staff/services/slots. If Dr. Smith isn't in the database, booking fails cleanly, and we escalate to a human. This is how healthcare systems need to behave — deterministically, with audit trails."

### Scenario 2: "How do you prevent the AI from making mistakes?"

**Answer:**
> "We don't rely on the AI alone. Each agent validates before acting. The Booking Agent checks: Is the service real? Is the staff available? Only then does it INSERT. The agent can't just say 'yeah, I booked you' — it has to actually write to the database and return a real appointment_id. If the query fails, it returns success=false and escalates. This architecture shifts trust from 'hoping the LLM is right' to 'verifying the system did the action.'"

### Scenario 3: "Why separate the Notification Agent?"

**Answer:**
> "Three reasons: First, notifications are async — we don't want customers waiting for SMS to send. Second, notifications fail independently. A booking can succeed but the SMS fails; we retry it. Third, it's reusable. When we add the dashboard, the same notification code works there. Separating concerns makes each agent testable and maintainable."

### Scenario 4: "Can a tenant modify the graph?"

**Answer:**
> "Yes. We provide template graphs (Full Booking Suite, Booking Only, Info Only). Advanced tenants can use the Graph Builder UI to drag-drop agents and edges. The system validates the graph structure (e.g., 'you can't send a message to Booking Agent if you haven't classified intent first'). This lets non-technical users customize without touching code."

### Scenario 5: "How do you handle errors?"

**Answer:**
> "Every agent has a try-catch. If booking fails (staff unavailable), the agent returns success=false + error_message. The graph routes to the Escalation Agent, which creates a support ticket. The customer sees: 'I couldn't complete your booking. A team member will reach out shortly.' This beats a cryptic error. We also log every state transition and agent output for debugging."

---

## Interview Summary (60 Seconds)

> "Our system uses LangGraph to orchestrate specialized agents. Instead of one big chatbot, we have Intent Classifier (routes), Booking/Reschedule/Cancellation (core logic), Status Checker (info), Notification (delivery), and Escalation (human fallback). Each agent has input/output schemas so it can't hallucinate. Agents read/write a shared GraphState, which we log for audits. Tenants define their flow as a graph (visual), so a clinic can enable booking+reschedule, while a salon uses booking-only. This architecture is deterministic (database queries, not guesses), reusable (same agents in different graphs), and maintainable (change one agent without touching others)."

---

## Technical Deep Dive: Why LangGraph?

### What is LangGraph?

LangGraph is a Python library for building **stateful agent systems**. It lets you:
- Define nodes (agents) and edges (transitions)
- Maintain state across agent calls
- Handle loops (e.g., agent fails → retry)
- Serialize/deserialize conversation state (for persistence)

### Why Not Just Chain?

**LangChain Chains** = linear: agent1 → agent2 → agent3

**LangGraph** = conditional flow: agent1 → [if error then escalate, else notify]

For appointment booking, you need conditions (is intent "book"? Is staff available?), so LangGraph is the right fit.

### Why Not Custom Code?

We could hand-write the routing logic in Python, but LangGraph gives us:
- Visual representation (helps PMs understand flow)
- Built-in state management (less boilerplate)
- Redis caching of compiled graphs (fast execution)
- Serialization (save/load conversation state)

---

## Deployment View

```
Customer sends WhatsApp message
        ↓
Backend receives on /webhooks/twilio/whatsapp
        ↓
GraphExecutor loads compiled graph from Redis cache
        ↓
Inputs: GraphState (tenant_id, session_id, message)
        ↓
Graph executes:
  1. Intent Classifier node (LLM call)
  2. Route to appropriate agent (Book/Reschedule/etc.)
  3. Agent executes (DB query, validation, LLM if needed)
  4. Update GraphState
  5. Route to Notification node
  6. Return response
        ↓
Backend sends reply via Twilio API
```

**Performance:**
- Compiled graphs cached in Redis (no recompilation per message)
- Typical execution: 2–4 seconds (1-2 LLM calls + DB queries)
- Scales to thousands of concurrent conversations (async I/O)

---

## Summary Table

| Agent | Type | LLM? | DB Access? | Use Case |
|---|---|---|---|---|
| Intent Classifier | Router | Yes | No | Understand customer intent |
| Booking | Action | Yes | Yes | Create appointment |
| Reschedule | Action | Yes | Yes | Modify appointment |
| Cancellation | Action | No | Yes | Soft-delete appointment |
| Status Checker | Query | No | Yes | Lookup upcoming appts |
| Notification | Delivery | No | Yes | Send SMS/email async |
| Escalation | Fallback | No | Yes | Create support ticket |

---

## Key Takeaways for Interviews

1. **Modular = Maintainable:** Each agent is independently testable and deployable.
2. **Schema-Driven = Safe:** Input/output schemas prevent hallucination.
3. **Graph = Customizable:** Non-technical users can build graphs, not code.
4. **Async = Responsive:** Notifications don't block customer experience.
5. **Auditability = Compliance:** Every state transition is logged for audit trails.
6. **Reusable = Cost-Effective:** Same agents work across channels (SMS, WhatsApp, web).

This design is what separates a toy chatbot from production-grade appointment automation.
