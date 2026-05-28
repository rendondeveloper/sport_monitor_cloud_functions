"""PUT /api/events/checklists/update — actualización parcial (patch-only)."""

import logging

from firebase_functions import https_fn
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper

from checklists import checklist_common as common
from checklists.checklist_participant_service import sync_all_event_participants
from checklists.checklist_paths import (
    checklists_collection_path,
    items_collection_path,
    participants_collection_path,
)

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[update_checklist]"


def handle_update(req: https_fn.Request, user_id: str) -> https_fn.Response:
    body = common.parse_body(req)
    if body is None:
        return common.empty_response(400)

    if common.body_has_deprecated_assigned_field(body):
        logging.warning("%s assignedParticipantIds is no longer supported", LOG_PREFIX)
        return common.empty_response(400)

    event_id = (body.get("eventId") or "").strip()
    checklist_id = (body.get("checklistId") or body.get("id") or "").strip()
    if not event_id or not checklist_id:
        return common.empty_response(400)

    item_patches = common.parse_item_patches(body.get("items"))
    if item_patches is None:
        return common.empty_response(400)

    participant_patches = common.parse_participant_patches(body.get("participants"))
    if participant_patches is None:
        return common.empty_response(400)

    if not common.has_updatable_fields(body, item_patches, participant_patches):
        return common.empty_response(400)

    try:
        now = get_current_timestamp()
        checklist_patch = common.build_checklist_patch(body, now)
        if checklist_patch is None:
            return common.empty_response(400)

        helper = FirestoreHelper()
        if not common.validate_item_patches_event_participants(helper, event_id, item_patches):
            logging.warning("%s Invalid participantIds in items", LOG_PREFIX)
            return common.empty_response(400)

        collection_path = checklists_collection_path(event_id)
        if helper.get_document(collection_path, checklist_id) is None:
            return common.empty_response(404)

        if checklist_patch:
            helper.update_document(collection_path, checklist_id, checklist_patch)

        items_path = items_collection_path(event_id, checklist_id)
        for entry in item_patches:
            item_id = entry["id"]
            if not common.item_patch_has_updatable_fields(entry):
                continue
            existing_item = helper.get_document(items_path, item_id)
            if existing_item is None:
                if common.is_real_item_patch_id(item_id):
                    return common.empty_response(404)
                # client-* ids son placeholders del cliente: crear doc con ID autogenerado.
                if not (entry.get("name") or "").strip():
                    return common.empty_response(400)
                helper.create_document(
                    items_path,
                    common.build_item_create_payload(entry, now),
                )
                continue
            helper.update_document(
                items_path,
                item_id,
                common.build_item_patch_payload(entry, now),
            )

        participants_path = participants_collection_path(event_id, checklist_id)
        for entry in participant_patches:
            participant_id = entry["id"]
            if not common.participant_patch_has_updatable_fields(entry):
                continue
            if helper.get_document(participants_path, participant_id) is None:
                return common.empty_response(404)
            helper.update_document(
                participants_path,
                participant_id,
                common.build_participant_patch_payload(entry, now),
            )

        needs_sync = (
            "visibilityMode" in body
            or any(common.item_patch_affects_participants(entry) for entry in item_patches)
        )
        if needs_sync:
            stored_items = common.load_checklist_items(helper, event_id, checklist_id)
            sync_all_event_participants(helper, event_id, checklist_id, stored_items)

        stored_items = common.load_checklist_items(helper, event_id, checklist_id)
        return common.json_response(
            {
                "eventId": event_id,
                "checklistId": checklist_id,
                "items": [{"id": item["id"]} for item in stored_items],
            }
        )
    except Exception as error:
        LOG.error("%s Error: %s", LOG_PREFIX, error, exc_info=True)
        return common.empty_response(500)
