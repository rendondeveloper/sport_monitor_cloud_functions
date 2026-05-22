import logging
from typing import Optional

from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper


def get_event_if_owner(event_id: str, user_id: str) -> Optional[dict]:
    """
    Retorna el evento si existe y pertenece al usuario autenticado.
    """
    helper = FirestoreHelper()
    event = helper.get_document(FirestoreCollections.EVENTS, event_id)
    if event is None:
        return None
    if (event.get("creator") or "").strip() != user_id:
        logging.warning(
            "event_owner_helper: Acceso denegado eventId=%s creator=%s uid=%s",
            event_id,
            event.get("creator"),
            user_id,
        )
        return None
    return event


def assert_event_owner(event_id: str, user_id: str) -> bool:
    """
    True si el evento existe y su creator coincide con user_id.
    """
    return get_event_if_owner(event_id, user_id) is not None


def get_event_if_owner_or_staff(event_id: str, user_id: str) -> Optional[dict]:
    """
    Retorna el evento si el usuario es el creador o staff del evento.
    """
    event = get_event_if_owner(event_id, user_id)
    if event is not None:
        return event

    helper = FirestoreHelper()
    staff_path = (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_STAFF}"
    )
    staff_doc = helper.get_document(staff_path, user_id)
    if staff_doc is None:
        event_doc = helper.get_document(FirestoreCollections.EVENTS, event_id)
        if event_doc is None:
            return None
        logging.warning(
            "event_owner_helper: Acceso denegado (no owner/staff) eventId=%s uid=%s",
            event_id,
            user_id,
        )
        return None

    event_doc = helper.get_document(FirestoreCollections.EVENTS, event_id)
    return event_doc
