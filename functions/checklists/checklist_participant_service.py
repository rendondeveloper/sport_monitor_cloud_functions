"""Sync de subcolección participants/{userId} para checklists v3."""

import logging
from typing import Any, Dict, List, Optional

from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper

from checklists.checklist_common import (
    build_item_progress_template,
    compute_is_completed,
    compute_is_completed_required,
    mandatory_item_ids_for_pilot,
    progress_item_ids_for_pilot,
)
from checklists.checklist_paths import (
    event_participants_collection_path,
    participants_collection_path,
)

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[checklist_participant_service]"


def _denormalize_participant_fields(
    helper: FirestoreHelper, event_id: str, participant_id: str
) -> Dict[str, Optional[str]]:
    event_participant = helper.get_document(
        event_participants_collection_path(event_id), participant_id
    )
    pilot_number = ""
    if event_participant:
        category = event_participant.get("competitionCategory") or {}
        pilot_number = str(category.get("pilotNumber") or "")

    user_doc = helper.get_document(FirestoreCollections.USERS, participant_id)
    participant_name = ""
    email = ""
    if user_doc:
        email = str(user_doc.get("email") or "")
        personal_rows = helper.query_documents(
            f"{FirestoreCollections.USERS}/{participant_id}/personalData",
            limit=1,
        )
        if personal_rows and len(personal_rows[0]) == 2:
            _, personal = personal_rows[0]
            full_name = str(personal.get("fullName") or "").strip()
            if full_name:
                participant_name = full_name
            else:
                first_name = str(personal.get("firstName") or "").strip()
                last_name = str(personal.get("lastName") or "").strip()
                if first_name and last_name:
                    participant_name = f"{first_name} {last_name}".strip()
                else:
                    participant_name = str(personal.get("name") or "").strip()

    return {
        "participantName": participant_name or None,
        "pilotNumber": pilot_number or None,
        "email": email or None,
    }


def _merge_item_progress(
    existing_progress: Dict[str, Dict[str, Any]],
    new_item_ids: List[str],
) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for item_id in new_item_ids:
        if item_id in existing_progress:
            merged[item_id] = {
                "check": existing_progress[item_id].get("check", False),
                "updateDate": existing_progress[item_id].get("updateDate"),
            }
        else:
            merged[item_id] = {"check": False, "updateDate": None}
    return merged


def create_participant_doc(
    helper: FirestoreHelper,
    event_id: str,
    checklist_id: str,
    participant_id: str,
    progress_item_ids: List[str],
    required_item_ids: List[str],
) -> None:
    now = get_current_timestamp()
    item_progress = build_item_progress_template(progress_item_ids)
    denorm = _denormalize_participant_fields(helper, event_id, participant_id)
    payload = {
        "itemProgress": item_progress,
        "isCompleted": compute_is_completed_required(item_progress, required_item_ids),
        "lastUpdateDate": None,
        "assignedAt": now,
        "updatedAt": now,
        **denorm,
    }
    helper.create_document_with_id(
        participants_collection_path(event_id, checklist_id),
        participant_id,
        payload,
    )


def sync_all_event_participants(
    helper: FirestoreHelper,
    event_id: str,
    checklist_id: str,
    stored_items: List[Dict[str, Any]],
) -> None:
    path = participants_collection_path(event_id, checklist_id)
    event_ids = helper.list_document_ids(event_participants_collection_path(event_id))
    target_ids = set(event_ids)
    existing_ids = set(helper.list_document_ids(path))

    for removed_id in existing_ids - target_ids:
        helper.delete_document(path, removed_id)

    for participant_id in target_ids:
        required_ids = mandatory_item_ids_for_pilot(stored_items, participant_id)
        progress_ids = progress_item_ids_for_pilot(stored_items, participant_id)
        if participant_id in existing_ids:
            existing = helper.get_document(path, participant_id) or {}
            item_progress = _merge_item_progress(
                existing.get("itemProgress") or {},
                progress_ids,
            )
            denorm = _denormalize_participant_fields(helper, event_id, participant_id)
            helper.update_document(
                path,
                participant_id,
                {
                    "itemProgress": item_progress,
                    "isCompleted": compute_is_completed_required(
                        item_progress, required_ids
                    ),
                    "updatedAt": get_current_timestamp(),
                    **denorm,
                },
            )
        else:
            create_participant_doc(
                helper,
                event_id,
                checklist_id,
                participant_id,
                progress_ids,
                required_ids,
            )
