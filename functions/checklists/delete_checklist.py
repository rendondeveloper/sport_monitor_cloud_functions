"""DELETE /api/events/checklists/delete?eventId=&checklistId="""

import logging

from firebase_functions import https_fn
from utils.firestore_helper import FirestoreHelper

from checklists import checklist_common as common
from checklists.checklist_paths import (
    checklists_collection_path,
    items_collection_path,
    participants_collection_path,
)

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[delete_checklist]"


def handle_delete(req: https_fn.Request, user_id: str) -> https_fn.Response:
    event_id = common.parse_event_id_from_query(req)
    checklist_id = common.parse_checklist_id_from_query(req)
    if not event_id or not checklist_id:
        return common.empty_response(400)

    try:
        helper = FirestoreHelper()
        collection_path = checklists_collection_path(event_id)
        if helper.get_document(collection_path, checklist_id) is None:
            return common.empty_response(404)

        common.delete_all_subcollection_docs(
            helper, items_collection_path(event_id, checklist_id)
        )
        common.delete_all_subcollection_docs(
            helper, participants_collection_path(event_id, checklist_id)
        )
        helper.delete_document(collection_path, checklist_id)
        return common.empty_response(204)
    except Exception as error:
        LOG.error("%s Error: %s", LOG_PREFIX, error, exc_info=True)
        return common.empty_response(500)
