"""GET /api/events/checklists/list?eventId="""

import logging

from firebase_functions import https_fn
from utils.firestore_helper import FirestoreHelper

from checklists import checklist_common as common
from checklists.checklist_paths import checklists_collection_path

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[list_checklists]"


def handle_list(req: https_fn.Request, user_id: str) -> https_fn.Response:
    event_id = common.parse_event_id_from_query(req)
    _, error_response = common.assert_event_crm_access(event_id or "", user_id)
    if error_response is not None:
        return error_response

    try:
        helper = FirestoreHelper()
        rows = helper.query_documents(checklists_collection_path(event_id))
        summaries = [
            common.build_checklist_summary(helper, event_id, checklist_id, data)
            for checklist_id, data in rows
        ]
        return common.json_response({"result": summaries})
    except Exception as error:
        LOG.error("%s Error: %s", LOG_PREFIX, error, exc_info=True)
        return common.empty_response(500)
