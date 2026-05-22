"""PUT /api/events/checklists/update"""

import logging

from firebase_functions import https_fn
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper

from checklists import checklist_common as common
from checklists.checklist_participant_service import (
    required_ids_from_items,
    sync_participants_for_assigned_ids,
)
from checklists.checklist_paths import checklists_collection_path, items_collection_path

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[update_checklist]"


def handle_update(req: https_fn.Request, user_id: str) -> https_fn.Response:
    body = common.parse_body(req)
    if body is None:
        return common.empty_response(400)

    event_id = (body.get("eventId") or "").strip()
    checklist_id = (body.get("checklistId") or body.get("id") or "").strip()
    title = (body.get("title") or "").strip()
    visibility_mode = common.validate_visibility_mode(body.get("visibilityMode"))
    items = common.normalize_items(body.get("items"))
    assigned_ids = common.normalize_assigned_ids(body.get("assignedParticipantIds"))

    if not checklist_id or not title or visibility_mode is None or items is None:
        return common.empty_response(400)

    _, error_response = common.assert_event_crm_access(event_id, user_id)
    if error_response is not None:
        return error_response

    try:
        helper = FirestoreHelper()
        collection_path = checklists_collection_path(event_id)
        existing = helper.get_document(collection_path, checklist_id)
        if existing is None:
            return common.empty_response(404)

        now = get_current_timestamp()
        helper.update_document(
            collection_path,
            checklist_id,
            {
                "title": title,
                "visibilityMode": visibility_mode,
                "updatedAt": now,
            },
        )

        common.delete_all_subcollection_docs(
            helper, items_collection_path(event_id, checklist_id)
        )
        stored_items = common.persist_template_items(
            helper, event_id, checklist_id, items
        )
        sync_participants_for_assigned_ids(
            helper,
            event_id,
            checklist_id,
            assigned_ids,
            required_ids_from_items(stored_items),
        )

        detail = common.build_checklist_detail(
            helper,
            event_id,
            checklist_id,
            helper.get_document(collection_path, checklist_id),
        )
        return common.json_response(detail)
    except Exception as error:
        LOG.error("%s Error: %s", LOG_PREFIX, error, exc_info=True)
        return common.empty_response(500)
