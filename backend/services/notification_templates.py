"""
services/notification_templates.py

Default notification message templates.
Tenant can override any template in their config JSONB under "notification_templates".

Template variables use Python .format() style: {name}, {service}, {date}, {time}.
"""

from datetime import datetime
from typing import Optional

DEFAULT_TEMPLATES: dict[str, str] = {
    "booking_confirmation": (
        "Hi {name}, your appointment for {service} on {date} at {time} is confirmed. "
        "Reply CANCEL to cancel. Ref: {ref}"
    ),
    "reschedule_confirmation": (
        "Hi {name}, your appointment has been rescheduled to {date} at {time}. "
        "Reply CANCEL if you need to cancel. Ref: {ref}"
    ),
    "reminder_24h": (
        "Reminder: Your {service} appointment is tomorrow, {date} at {time}. "
        "Reply CONFIRM to confirm or CANCEL to cancel."
    ),
    "reminder_1h": (
        "Your {service} appointment is in 1 hour at {time}. See you soon!"
    ),
    "cancellation": (
        "Your appointment on {date} at {time} has been cancelled. "
        "Reply BOOK to make a new appointment."
    ),
    "no_show": (
        "We missed you today! Your {service} appointment at {time} was marked as missed. "
        "Reply BOOK to reschedule."
    ),
}


def render_template(
    template_key: str,
    context: dict,
    tenant_templates: Optional[dict] = None,
) -> str:
    """
    Renders a notification message for the given template key.

    Precedence: tenant override → default template.

    Args:
        template_key: e.g. "booking_confirmation"
        context: dict with name, service, date, time, ref etc.
        tenant_templates: from tenant.config["notification_templates"]

    Returns:
        Rendered string ready to send.
    """
    overrides = tenant_templates or {}
    template_str = overrides.get(template_key) or DEFAULT_TEMPLATES.get(template_key)

    if not template_str:
        return f"Appointment update for {context.get('name', 'Customer')}."

    try:
        return template_str.format(**context)
    except KeyError:
        # If a variable is missing, return the raw template rather than crashing
        return template_str


def build_context_from_slot(
    patient_name: str,
    service_name: str,
    slot_utc: datetime,
    appointment_ref: str,
    timezone_str: str = "Asia/Kolkata",
) -> dict:
    """
    Builds the template context dict from appointment data.
    Converts UTC slot to the tenant's local timezone for display.
    """
    import pytz

    tz = pytz.timezone(timezone_str)
    local_slot = slot_utc.astimezone(tz)

    return {
        "name": patient_name,
        "service": service_name,
        "date": local_slot.strftime("%d %b %Y"),
        "time": local_slot.strftime("%I:%M %p"),
        "ref": appointment_ref[:8].upper(),
    }
