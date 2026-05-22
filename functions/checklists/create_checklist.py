"""POST /api/events/checklists/create"""

import logging

from firebase_functions import https_fn
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper

from checklists import checklist_common as common
from checklists.checklist_participant_service import (
    create_participant_doc,
    required_ids_from_items,
)
from checklists.checklist_paths import checklists_collection_path

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_checklist]"


def handle_create(req: https_fn.Request, user_id: str) -> https_fn.Response:
    body = common.parse_body(req)
    if body is None:
        return common.empty_response(400)

    event_id = (body.get("eventId") or "").strip()
    title = (body.get("title") or "").strip()
    visibility_mode = common.validate_visibility_mode(body.get("visibilityMode"))
    items = common.normalize_items(body.get("items"))
    assigned_ids = common.normalize_assigned_ids(body.get("assignedParticipantIds"))

    if not title or visibility_mode is None or items is None:
        return common.empty_response(400)

    _, error_response = common.assert_event_crm_access(event_id, user_id)
    if error_response is not None:
        return error_response

    try:
        helper = FirestoreHelper()
        now = get_current_timestamp()
        checklist_id = helper.create_document(
            checklists_collection_path(event_id),
            {
                "title": title,
                "visibilityMode": visibility_mode,
                "createdAt": now,
                "updatedAt": now,
            },
        )
        stored_items = common.persist_template_items(
            helper, event_id, checklist_id, items
        )
        required_ids = required_ids_from_items(stored_items)
        for participant_id in assigned_ids:
            create_participant_doc(
                helper, event_id, checklist_id, participant_id, required_ids
            )

        detail = common.build_checklist_detail(
            helper,
            event_id,
            checklist_id,
            helper.get_document(checklists_collection_path(event_id), checklist_id),
        )
        return common.json_response(detail, status=201)
    except Exception as error:
        LOG.error("%s Error: %s", LOG_PREFIX, error, exc_info=True)
        return common.empty_response(500)
