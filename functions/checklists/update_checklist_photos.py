"""PUT /api/events/checklists/update-photos — actualización parcial de fotos."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.datetime_helper import get_current_timestamp
from utils.firestore_helper import FirestoreHelper

from checklists import checklist_common as common
from checklists.checklist_paths import checklists_collection_path, items_collection_path

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[update_checklist_photos]"


def _parse_item_photo_updates(
    raw: Any,
) -> Optional[List[Tuple[str, Optional[str]]]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    updates: List[Tuple[str, Optional[str]]] = []
    seen_ids = set()
    for entry in raw:
        if not isinstance(entry, dict):
            return None
        item_id = (entry.get("id") or "").strip()
        if not item_id or item_id in seen_ids:
            return None
        if "photoUrl" not in entry:
            return None
        seen_ids.add(item_id)
        updates.append((item_id, common.normalize_optional_url(entry.get("photoUrl"))))
    return updates


def _parse_body(
    body: Dict[str, Any],
) -> Optional[Tuple[str, str, bool, Optional[str], List[Tuple[str, Optional[str]]]]]:
    event_id = (body.get("eventId") or "").strip()
    if not event_id:
        return None

    has_cover_photo_key = "photoUrl" in body
    cover_photo_url = (
        common.normalize_optional_url(body.get("photoUrl"))
        if has_cover_photo_key
        else None
    )

    item_updates = _parse_item_photo_updates(body.get("items"))
    if item_updates is None:
        return None

    if not has_cover_photo_key and not item_updates:
        return None

    checklist_id = (body.get("checklistId") or body.get("id") or "").strip()
    if item_updates and not checklist_id:
        return None

    return event_id, checklist_id, has_cover_photo_key, cover_photo_url, item_updates


def handle_update_photos(req: https_fn.Request, user_id: str) -> https_fn.Response:
    body = common.parse_body(req)
    if body is None:
        return common.empty_response(400)

    parsed = _parse_body(body)
    if parsed is None:
        return common.empty_response(400)

    event_id, checklist_id, has_cover_photo_key, cover_photo_url, item_updates = parsed

    try:
        helper = FirestoreHelper()
        now = get_current_timestamp()
        checklists_path = checklists_collection_path(event_id)

        if has_cover_photo_key:
            if checklist_id:
                if helper.get_document(checklists_path, checklist_id) is None:
                    return common.empty_response(404)
                helper.update_document(
                    checklists_path,
                    checklist_id,
                    {"photoUrl": cover_photo_url, "updatedAt": now},
                )
            else:
                event_doc = helper.get_document(FirestoreCollections.EVENTS, event_id)
                if event_doc is None:
                    return common.empty_response(404)
                helper.update_document(
                    FirestoreCollections.EVENTS,
                    event_id,
                    {"photoUrl": cover_photo_url, "updatedAt": now},
                )

        if item_updates:
            if helper.get_document(checklists_path, checklist_id) is None:
                return common.empty_response(404)

            items_path = items_collection_path(event_id, checklist_id)
            for item_id, photo_url in item_updates:
                if helper.get_document(items_path, item_id) is None:
                    return common.empty_response(404)
                helper.update_document(
                    items_path,
                    item_id,
                    {"photoUrl": photo_url, "updatedAt": now},
                )

        if checklist_id:
            checklist_data = helper.get_document(checklists_path, checklist_id)
            if checklist_data is None:
                return common.empty_response(404)
            detail = common.build_checklist_detail(
                helper, event_id, checklist_id, checklist_data
            )
            return common.json_response(detail)

        return common.empty_response(200)
    except Exception as error:
        LOG.error("%s Error: %s", LOG_PREFIX, error, exc_info=True)
        return common.empty_response(500)
