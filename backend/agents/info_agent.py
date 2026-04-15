"""
agents/info_agent.py

Handles informational queries with zero LLM tokens wherever possible:

  list_services  → DB query → formatted service catalogue (0 tokens)
  list_staff     → DB query → formatted staff roster (0 tokens)
  check_slots    → date/service extracted via regex → DB slot computation (0 tokens)
                   LLM is used as fallback ONLY when regex cannot parse the date.

Sub-intent detection inside this agent is keyword-based — no LLM call.
If the intent classifier routes "list_services", "list_staff", or "check_slots"
directly, the sub-intent is taken from state["intent"].
If routed as generic "info" the agent detects sub-intent from user_input keywords.

Slot computation replicates the algorithm from api/slots.py:
  - Walk staff working windows in (duration + buffer) steps
  - Mark a slot taken if it overlaps any confirmed/pending appointment
"""

import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base import BaseAgent
from backend.models.appointment import Appointment

logger = logging.getLogger(__name__)

# ── Keyword sets for sub-intent detection ────────────────────────────────────
_SERVICE_KEYWORDS = {
    "service", "services", "offering", "offerings", "treatment", "treatments",
    "procedure", "procedures", "price", "prices", "cost", "costs", "menu",
    "what do you offer", "what can", "haircut", "therapy",
}
_STAFF_KEYWORDS = {
    "staff", "doctor", "doctors", "stylist", "stylists", "therapist",
    "therapists", "expert", "experts", "who", "team", "barber", "barbers",
    "consultant", "consultants", "person", "employee", "employees",
}
_SLOT_KEYWORDS = {
    "slot", "slots", "available", "availability", "free", "open",
    "when", "time", "appointment", "book", "schedule",
}

WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Month name → number for regex-based date parsing
_MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


# ── Pure helpers (no DB, no LLM) ─────────────────────────────────────────────

def _detect_sub_intent(intent: str, user_input: str) -> str:
    """
    Returns one of: list_services | list_staff | info_both | check_slots.
    Uses state["intent"] as primary signal; falls back to keyword scan.
    """
    if intent in ("list_services", "list_staff", "check_slots"):
        return intent

    text = user_input.lower()
    wants_service = bool(_SERVICE_KEYWORDS & set(text.split()) or
                         any(kw in text for kw in _SERVICE_KEYWORDS if " " in kw))
    wants_staff = bool(_STAFF_KEYWORDS & set(text.split()) or
                       any(kw in text for kw in _STAFF_KEYWORDS if " " in kw))
    wants_slots = bool(_SLOT_KEYWORDS & set(text.split()) or
                       any(kw in text for kw in _SLOT_KEYWORDS if " " in kw))

    if wants_slots:
        return "check_slots"
    if wants_service and wants_staff:
        return "info_both"
    if wants_service:
        return "list_services"
    if wants_staff:
        return "list_staff"
    return "info_both"  # default: show everything


def _extract_date_from_text(text: str) -> Optional[date]:
    """
    Regex-based date extraction — no LLM.
    Handles: today, tomorrow, day names, ISO dates, DD/MM/YYYY, "April 16", "16 April".
    Returns None if no date can be parsed (caller should then ask the user or use LLM).
    """
    text = text.lower()
    today = date.today()

    if "today" in text:
        return today
    if "tomorrow" in text:
        return today + timedelta(days=1)

    # "next <weekday>" or just "<weekday>"
    for i, day_name in enumerate(WEEKDAY_NAMES):
        if day_name in text:
            days_ahead = (i - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # "next monday" means next week if today is monday
            return today + timedelta(days=days_ahead)

    # ISO: YYYY-MM-DD
    m = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b', text)
    if m:
        try:
            day, month = int(m.group(1)), int(m.group(2))
            year = int(m.group(3)) if m.group(3) else today.year
            if year < 100:
                year += 2000
            return date(year, month, day)
        except ValueError:
            pass

    # "April 16" or "16 April" or "16th April"
    m = re.search(
        r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)\b|\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\b',
        text,
    )
    if m:
        if m.group(1):  # "16 April"
            day, month_str = int(m.group(1)), m.group(2)
        else:           # "April 16"
            day, month_str = int(m.group(4)), m.group(3)
        month = _MONTH_MAP.get(month_str)
        if month:
            try:
                return date(today.year, month, day)
            except ValueError:
                pass

    return None


def _parse_time(date_obj: date, time_str: str) -> datetime:
    h, m = map(int, time_str.split(":"))
    return datetime(date_obj.year, date_obj.month, date_obj.day, h, m, tzinfo=timezone.utc)


def _compute_slots_for_windows(
    date_obj: date,
    windows: list,
    duration_minutes: int,
    interval_minutes: int,
    booked: list,
) -> list:
    """Returns list of {start, end, available} dicts for one staff member."""
    slots = []
    slot_dur = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=interval_minutes)

    for window in windows:
        current = _parse_time(date_obj, window["start"])
        window_end = _parse_time(date_obj, window["end"])
        while current + slot_dur <= window_end:
            slot_end = current + slot_dur
            taken = any(current < b_end and slot_end > b_start for b_start, b_end in booked)
            slots.append({
                "start": current.strftime("%H:%M"),
                "end": slot_end.strftime("%H:%M"),
                "available": not taken,
            })
            current += step
    return slots


# ── Response formatters (plain text, chat-friendly) ──────────────────────────

def _format_services(services: list) -> str:
    if not services:
        return "No services are currently available."

    # Group by category
    categories: dict[str, list] = {}
    for s in services:
        cat = s.category or "General"
        categories.setdefault(cat, []).append(s)

    lines = ["Here are our available services:\n"]
    for cat, items in sorted(categories.items()):
        lines.append(f"{cat}:")
        for s in items:
            price = f"Rs.{s.price_paise // 100}" if s.price_paise else "free"
            lines.append(f"  - {s.name} ({s.duration_minutes} min, {price})")
        lines.append("")

    lines.append("Which service would you like to book?")
    return "\n".join(lines).strip()


def _format_staff(staff_list: list) -> str:
    if not staff_list:
        return "No staff members are currently available."

    lines = ["Our team:"]
    for s in staff_list:
        spec = f" - {s.specialization}" if s.specialization else ""
        lines.append(f"  - {s.full_name}{spec}")

    lines.append("\nWould you like to book with one of them?")
    return "\n".join(lines).strip()


def _format_slots(service_name: str, date_obj: date, staff_slots: list) -> str:
    if not staff_slots:
        return (
            f"No staff are available for {service_name} on "
            f"{date_obj.strftime('%d %b %Y')} (no working hours configured)."
        )

    lines = [f"Available slots for **{service_name}** on {date_obj.strftime('%A, %d %b %Y')}:\n"]
    any_free = False

    for entry in staff_slots:
        free = [sl for sl in entry["slots"] if sl["available"]]
        if not free:
            lines.append(f"  {entry['staff_name']}: fully booked")
            continue
        any_free = True
        times = ", ".join(sl["start"] for sl in free[:8])
        if len(free) > 8:
            times += f" (+{len(free) - 8} more)"
        lines.append(f"  **{entry['staff_name']}**: {times}")

    if not any_free:
        lines.append("\nAll slots are fully booked for this day.")
        lines.append("Would you like to check another date?")
    else:
        lines.append("\nWhich time works for you?")

    return "\n".join(lines).strip()


# ── Agent ─────────────────────────────────────────────────────────────────────

class InfoAgent(BaseAgent):
    name = "info_agent"
    display_name = "Info Agent"
    cost_weight = 0.1  # Near-zero cost — mostly DB queries, no LLM in common path

    async def run(self, state: dict) -> dict:
        db: AsyncSession | None = state.get("db")
        tenant_id_str: str = state.get("tenant_id", "")

        if not db or not tenant_id_str:
            return self._error_state(state, "Info system unavailable. Please try again.", None)

        tenant_id = uuid.UUID(tenant_id_str)
        user_input: str = state.get("user_input", "")
        intent: str = state.get("intent", "")

        sub = _detect_sub_intent(intent, user_input)

        try:
            if sub == "list_services":
                return await self._handle_list_services(state, db, tenant_id)

            if sub == "list_staff":
                return await self._handle_list_staff(state, db, tenant_id)

            if sub == "check_slots":
                return await self._handle_check_slots(state, db, tenant_id)

            # info_both — show services + staff together
            return await self._handle_info_both(state, db, tenant_id)

        except Exception as exc:
            return self._error_state(state, "Could not retrieve information. Please try again.", exc)

    # ── Handlers ─────────────────────────────────────────────────────────────

    async def _handle_list_services(self, state: dict, db: AsyncSession, tenant_id: uuid.UUID) -> dict:
        from backend.repositories.service_repo import list_services
        services = await list_services(db, tenant_id)

        logger.info(
            "info_agent_list_services",
            extra={"tenant_id": str(tenant_id), "count": len(services)},
        )
        return {
            **state,
            "response": _format_services(services),
            "next_node": "__end__",
        }

    async def _handle_list_staff(self, state: dict, db: AsyncSession, tenant_id: uuid.UUID) -> dict:
        from backend.repositories.staff_repo import list_staff
        staff = await list_staff(db, tenant_id)

        logger.info(
            "info_agent_list_staff",
            extra={"tenant_id": str(tenant_id), "count": len(staff)},
        )
        return {
            **state,
            "response": _format_staff(staff),
            "next_node": "__end__",
        }

    async def _handle_info_both(self, state: dict, db: AsyncSession, tenant_id: uuid.UUID) -> dict:
        from backend.repositories.service_repo import list_services
        from backend.repositories.staff_repo import list_staff

        services, staff = await list_services(db, tenant_id), await list_staff(db, tenant_id)

        response = _format_services(services) + "\n\n" + _format_staff(staff)
        logger.info(
            "info_agent_list_both",
            extra={"tenant_id": str(tenant_id)},
        )
        return {**state, "response": response, "next_node": "__end__"}

    async def _handle_check_slots(
        self, state: dict, db: AsyncSession, tenant_id: uuid.UUID
    ) -> dict:
        from backend.repositories.service_repo import find_service_by_name, list_services
        from backend.repositories.staff_repo import list_staff

        user_input: str = state.get("user_input", "")

        # ── 1. Extract date (regex, no LLM) ───────────────────────────────────
        date_obj = _extract_date_from_text(user_input)
        if not date_obj:
            return {
                **state,
                "response": (
                    "Which date would you like to check availability for? "
                    "Please specify a date (e.g. 'tomorrow', 'Monday', '16 April')."
                ),
                "next_node": "__end__",
            }

        if date_obj < date.today():
            return {
                **state,
                "response": "That date is in the past. Please choose a future date.",
                "next_node": "__end__",
            }

        # ── 2. Extract service name (keyword scan, no LLM) ────────────────────
        # Try to find a service name mentioned in the user input
        all_services = await list_services(db, tenant_id)
        matched_service = None
        text_lower = user_input.lower()

        for svc in all_services:
            if svc.name.lower() in text_lower:
                matched_service = svc
                break

        if not matched_service:
            # Word-boundary token match: "hair" must appear as a whole word,
            # so "haircut" in user input won't accidentally match "Hair Colour".
            for svc in all_services:
                for token in svc.name.lower().split():
                    if len(token) > 3 and re.search(r'\b' + re.escape(token) + r'\b', text_lower):
                        matched_service = svc
                        break
                if matched_service:
                    break

        if not matched_service:
            names = ", ".join(s.name for s in all_services[:8])
            return {
                **state,
                "response": (
                    f"Which service would you like to check slots for?\n"
                    f"Available: {names}"
                ),
                "next_node": "__end__",
            }

        # ── 3. Compute slots (DB query + pure arithmetic, no LLM) ────────────
        duration_minutes = matched_service.duration_minutes
        buffer_minutes = matched_service.buffer_minutes
        interval_minutes = duration_minutes + buffer_minutes

        # Determine relevant staff
        all_staff = await list_staff(db, tenant_id)
        if matched_service.staff_ids:
            staff_list = [s for s in all_staff if str(s.id) in matched_service.staff_ids]
        else:
            staff_list = all_staff

        if not staff_list:
            return {
                **state,
                "response": f"No staff are assigned to {matched_service.name}.",
                "next_node": "__end__",
            }

        weekday = WEEKDAY_NAMES[date_obj.weekday()]
        day_start = datetime(date_obj.year, date_obj.month, date_obj.day, 0, 0, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        relevant_ids = [s.id for s in staff_list]
        appt_result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.staff_id.in_(relevant_ids),
                    Appointment.slot_datetime >= day_start,
                    Appointment.slot_datetime < day_end,
                    Appointment.status.in_(["confirmed", "pending"]),
                )
            )
        )
        all_appts = list(appt_result.scalars().all())

        staff_slots = []
        for s in staff_list:
            windows = s.working_hours.get(weekday, [])
            if not windows:
                continue
            booked = [
                (a.slot_datetime, a.slot_end_datetime)
                for a in all_appts
                if a.staff_id == s.id
            ]
            slots = _compute_slots_for_windows(
                date_obj, windows, duration_minutes, interval_minutes, booked
            )
            staff_slots.append({
                "staff_name": s.full_name,
                "specialization": s.specialization,
                "slots": slots,
            })

        logger.info(
            "info_agent_check_slots",
            extra={
                "tenant_id": str(tenant_id),
                "service": matched_service.name,
                "date": str(date_obj),
            },
        )

        return {
            **state,
            "response": _format_slots(matched_service.name, date_obj, staff_slots),
            "next_node": "__end__",
        }
