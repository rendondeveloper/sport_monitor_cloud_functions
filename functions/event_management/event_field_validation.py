"""Validación de campos raíz en event_management."""

from typing import Any, Dict, Tuple

ALLOWED_EVENT_SOURCES = frozenset({"app", "web"})
ALLOWED_TYPE_EVENTS = frozenset({"individual", "organization"})


def _is_valid_enum_string(value: Any, allowed: frozenset) -> bool:
    return isinstance(value, str) and value.strip() != "" and value in allowed


def _is_valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_valid_boolean(value: Any) -> bool:
    return isinstance(value, bool)


def validate_source_type_event_for_create(body: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Create exige campos raíz obligatorios con valores válidos:
    - source: app|web
    - typeEvent: individual|organization
    - duration: numérico
    - sendNotifications: booleano

    Returns:
        (True, "") si OK; (False, nombre_campo) si falta o es inválido.
    """
    source = body.get("source")
    type_event = body.get("typeEvent")
    duration = body.get("duration")
    send_notifications = body.get("sendNotifications")
    if not _is_valid_enum_string(source, ALLOWED_EVENT_SOURCES):
        return False, "source"
    if not _is_valid_enum_string(type_event, ALLOWED_TYPE_EVENTS):
        return False, "typeEvent"
    if not _is_valid_number(duration):
        return False, "duration"
    if not _is_valid_boolean(send_notifications):
        return False, "sendNotifications"
    return True, ""


def validate_source_type_event_for_update(body: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Update: si vienen campos raíz, deben ser válidos.
    """
    if "source" in body and not _is_valid_enum_string(body.get("source"), ALLOWED_EVENT_SOURCES):
        return False, "source"
    if "typeEvent" in body and not _is_valid_enum_string(body.get("typeEvent"), ALLOWED_TYPE_EVENTS):
        return False, "typeEvent"
    if "duration" in body and not _is_valid_number(body.get("duration")):
        return False, "duration"
    if "sendNotifications" in body and not _is_valid_boolean(body.get("sendNotifications")):
        return False, "sendNotifications"
    return True, ""
