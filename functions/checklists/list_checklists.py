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
    if not event_id:
        return common.empty_response(400)

    try:
        helper = FirestoreHelper()
        collection_path = checklists_collection_path(event_id)

        LOG.info(
            "%s eventId=%s  firestorePath=%s",
            LOG_PREFIX,
            event_id,
            collection_path,
        )

        rows = helper.query_documents(collection_path)
        LOG.info(
            "%s eventId=%s firestorePath=%s documentsFound=%d",
            LOG_PREFIX,
            event_id,
            collection_path,
            len(rows),
        )
        summaries = [
            common.build_checklist_summary(helper, event_id, checklist_id, data)
            for checklist_id, data in rows
        ]
        # Array JSON directo (mismo patrón que catálogos/competitors); sin wrapper `result`.
        return common.json_response(summaries)
    except Exception as error:
        LOG.error("%s Error: %s", LOG_PREFIX, error, exc_info=True)
        return common.empty_response(500)
