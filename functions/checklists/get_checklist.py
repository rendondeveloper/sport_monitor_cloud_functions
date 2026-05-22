"""GET /api/events/checklists/get?eventId=&checklistId="""

import logging

from firebase_functions import https_fn
from utils.firestore_helper import FirestoreHelper

from checklists import checklist_common as common
from checklists.checklist_paths import checklists_collection_path

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[get_checklist]"


def handle_get(req: https_fn.Request, user_id: str) -> https_fn.Response:
    event_id = common.parse_event_id_from_query(req)
    checklist_id = common.parse_checklist_id_from_query(req)
    if not checklist_id:
        return common.empty_response(400)

    _, error_response = common.assert_event_crm_access(event_id or "", user_id)
    if error_response is not None:
        return error_response

    try:
        helper = FirestoreHelper()
        checklist_data = helper.get_document(
            checklists_collection_path(event_id), checklist_id
        )
        if checklist_data is None:
            return common.empty_response(404)

        detail = common.build_checklist_detail(
            helper, event_id, checklist_id, checklist_data
        )
        return common.json_response(detail)
    except Exception as error:
        LOG.error("%s Error: %s", LOG_PREFIX, error, exc_info=True)
        return common.empty_response(500)
