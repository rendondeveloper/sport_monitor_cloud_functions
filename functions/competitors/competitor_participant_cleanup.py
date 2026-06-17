"""
Limpieza de subcolecciones del participante bajo un evento.

Borra referencias event-scoped creadas por create_competitor_user:
- events/{eventId}/participants/{userId}/emergencyContacts/*
- events/{eventId}/participants/{userId}/vehicle/*
"""

import logging

from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)


def _participant_base_path(event_id: str, user_id: str) -> str:
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}/{user_id}"
    )


def _delete_subcollection_docs(
    helper: FirestoreHelper,
    collection_path: str,
    collection_label: str,
    log_prefix: str,
) -> None:
    try:
        doc_ids = helper.list_document_ids(collection_path)
        for doc_id in doc_ids:
            try:
                helper.delete_document(collection_path, doc_id)
                LOG.info(
                    "%s participante subcol %s/%s eliminado",
                    log_prefix,
                    collection_label,
                    doc_id,
                )
            except Exception as e:
                LOG.warning(
                    "%s error eliminando participante subcol %s/%s: %s",
                    log_prefix,
                    collection_label,
                    doc_id,
                    e,
                )
    except Exception as e:
        LOG.warning(
            "%s error listando participante subcol %s (puede no existir): %s",
            log_prefix,
            collection_label,
            e,
        )


def delete_participant_event_subcollections(
    helper: FirestoreHelper,
    user_id: str,
    event_id: str,
    log_prefix: str,
) -> None:
    """
    Elimina subcolecciones del participante en el evento antes de borrar su documento raíz.
    No toca datos en users/{userId}.
    """
    base = _participant_base_path(event_id, user_id)

    ec_path = f"{base}/{FirestoreCollections.PARTICIPANT_EMERGENCY_CONTACTS}"
    _delete_subcollection_docs(
        helper,
        ec_path,
        FirestoreCollections.PARTICIPANT_EMERGENCY_CONTACTS,
        log_prefix,
    )

    vehicle_path = f"{base}/{FirestoreCollections.PARTICIPANT_VEHICLE}"
    _delete_subcollection_docs(
        helper,
        vehicle_path,
        FirestoreCollections.PARTICIPANT_VEHICLE,
        log_prefix,
    )
