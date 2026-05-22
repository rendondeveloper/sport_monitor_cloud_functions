"""Rutas Firestore para checklists de evento."""

from models.firestore_collections import FirestoreCollections


def checklists_collection_path(event_id: str) -> str:
    return f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_CHECKLISTS}"


def checklist_document_path(event_id: str, checklist_id: str) -> str:
    return f"{checklists_collection_path(event_id)}/{checklist_id}"


def items_collection_path(event_id: str, checklist_id: str) -> str:
    return f"{checklist_document_path(event_id, checklist_id)}/{FirestoreCollections.CHECKLIST_ITEMS}"


def participants_collection_path(event_id: str, checklist_id: str) -> str:
    return (
        f"{checklist_document_path(event_id, checklist_id)}"
        f"/{FirestoreCollections.CHECKLIST_PARTICIPANTS}"
    )


def event_participants_collection_path(event_id: str) -> str:
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )
