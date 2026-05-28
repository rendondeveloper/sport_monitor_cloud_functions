"""GET /api/events/checklists/participant-progress"""

import logging
from typing import Any, Dict, List, Tuple

from firebase_functions import https_fn
from utils.firestore_helper import FirestoreHelper

from checklists import checklist_common as common
from checklists.checklist_paths import (
    checklists_collection_path,
    participants_collection_path,
)

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[get_participant_progress]"

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 20


def _parse_limit(raw: Any) -> int:
    try:
        value = int(raw) if raw is not None else _DEFAULT_LIMIT
    except (TypeError, ValueError):
        value = _DEFAULT_LIMIT
    return max(1, min(value, _MAX_LIMIT))


def _matches_search(row: Dict[str, Any], search: str) -> bool:
    if not search:
        return True
    needle = search.lower()
    for field in ("participantName", "email", "pilotNumber", "participantId"):
        value = str(row.get(field) or "").lower()
        if needle in value:
            return True
    return False


def _build_progress_row(
    participant_id: str,
    participant_data: Dict[str, Any],
    template_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    item_progress = participant_data.get("itemProgress") or {}
    progress_items = []
    for template_item in template_items:
        item_id = template_item["id"]
        progress_entry = item_progress.get(item_id) or {}
        progress_items.append(
            {
                "itemId": item_id,
                "name": template_item.get("name", ""),
                "photoUrl": template_item.get("photoUrl"),
                "isRequired": common.effective_is_required_for_participant(
                    template_item, participant_id
                ),
                "check": bool(progress_entry.get("check", False)),
                "updateDate": progress_entry.get("updateDate"),
            }
        )
    return {
        "participantId": participant_id,
        "participantName": participant_data.get("participantName"),
        "pilotNumber": participant_data.get("pilotNumber"),
        "items": progress_items,
        "isCompleted": bool(participant_data.get("isCompleted", False)),
        "lastUpdateDate": participant_data.get("lastUpdateDate"),
    }


def handle_participant_progress(
    req: https_fn.Request, user_id: str
) -> https_fn.Response:
    event_id = common.parse_event_id_from_query(req)
    checklist_id = common.parse_checklist_id_from_query(req)
    if not event_id or not checklist_id:
        return common.empty_response(400)

    limit = _parse_limit(req.args.get("limit"))
    cursor = (req.args.get("cursor") or "").strip() or None
    search = (req.args.get("search") or "").strip().lower()

    try:
        helper = FirestoreHelper()
        if helper.get_document(checklists_collection_path(event_id), checklist_id) is None:
            return common.empty_response(404)

        template_items = common.load_checklist_items(helper, event_id, checklist_id)
        participant_rows: List[Tuple[str, Dict[str, Any]]] = helper.query_documents(
            participants_collection_path(event_id, checklist_id),
        )
        participant_rows.sort(key=lambda row: row[0])

        built_rows = [
            _build_progress_row(
                participant_id,
                data,
                common.items_for_participant_progress(template_items, participant_id),
            )
            for participant_id, data in participant_rows
        ]
        filtered_rows = [row for row in built_rows if _matches_search(row, search)]

        start_index = 0
        if cursor:
            for index, row in enumerate(filtered_rows):
                if row["participantId"] == cursor:
                    start_index = index + 1
                    break

        page_rows = filtered_rows[start_index : start_index + limit]
        has_more = start_index + limit < len(filtered_rows)
        last_doc_id = page_rows[-1]["participantId"] if page_rows else None

        participant_count = len(participant_rows)
        completed_count = sum(
            1 for _, data in participant_rows if data.get("isCompleted") is True
        )
        incomplete_count = participant_count - completed_count

        return common.json_response(
            {
                "result": page_rows,
                "pagination": {
                    "hasMore": has_more,
                    "lastDocId": last_doc_id,
                    "count": len(page_rows),
                    "limit": limit,
                },
                "summary": {
                    "assignedCount": participant_count,
                    "completedCount": completed_count,
                    "incompleteCount": incomplete_count,
                },
            }
        )
    except Exception as error:
        LOG.error("%s Error: %s", LOG_PREFIX, error, exc_info=True)
        return common.empty_response(500)
