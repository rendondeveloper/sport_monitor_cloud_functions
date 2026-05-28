"""POST /api/events/checklists/create"""

import logging

from firebase_functions import https_fn
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper

from checklists import checklist_common as common
from checklists.checklist_participant_service import sync_all_event_participants
from checklists.checklist_paths import checklists_collection_path

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[create_checklist]"


def handle_create(req: https_fn.Request, user_id: str) -> https_fn.Response:
    body = common.parse_body(req)
    if body is None:
        return common.empty_response(400)

    if common.body_has_deprecated_assigned_field(body):
        logging.warning("%s assignedParticipantIds is no longer supported", LOG_PREFIX)
        return common.empty_response(400)

    event_id = (body.get("eventId") or "").strip()
    title = (body.get("title") or "").strip()
    visibility_mode = common.validate_visibility_mode(body.get("visibilityMode"))
    items = common.normalize_items(body.get("items"))

    if not event_id or not title or visibility_mode is None or items is None:
        return common.empty_response(400)

    try:
        helper = FirestoreHelper()
        if not common.validate_items_event_participants(helper, event_id, items):
            logging.warning("%s Invalid participantIds in items", LOG_PREFIX)
            return common.empty_response(400)

        now = get_current_timestamp()
        checklist_fields = common.normalize_checklist_fields(body)
        checklist_id = helper.create_document(
            checklists_collection_path(event_id),
            {
                "title": title,
                "description": checklist_fields["description"],
                "photoUrl": checklist_fields["photoUrl"],
                "visibilityMode": visibility_mode,
                "createdAt": now,
                "updatedAt": now,
            },
        )
        stored_items = common.persist_template_items(
            helper, event_id, checklist_id, items
        )
        sync_all_event_participants(helper, event_id, checklist_id, stored_items)

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
