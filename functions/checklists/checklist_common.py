"""Utilidades compartidas para handlers de checklists."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from firebase_functions import https_fn
from utils.datetime_helper import get_current_timestamp
from utils.event_owner_helper import get_event_if_owner_or_staff
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)

_VISIBILITY_MODES = frozenset({"participants", "eventDates"})
_CORS = {"Access-Control-Allow-Origin": "*"}


def json_response(payload: Any, status: int = 200) -> https_fn.Response:
    return https_fn.Response(
        json.dumps(payload),
        status=status,
        headers={**_CORS, "Content-Type": "application/json"},
    )


def empty_response(status: int) -> https_fn.Response:
    return https_fn.Response("", status=status, headers=_CORS)


def parse_event_id_from_query(req: https_fn.Request) -> Optional[str]:
    return (req.args.get("eventId") or "").strip() or None


def parse_checklist_id_from_query(req: https_fn.Request) -> Optional[str]:
    return (req.args.get("checklistId") or "").strip() or None


def parse_body(req: https_fn.Request) -> Optional[Dict[str, Any]]:
    body = req.get_json(silent=True)
    return body if isinstance(body, dict) else None


def assert_event_crm_access(
    event_id: str, user_id: str
) -> Tuple[Optional[Dict[str, Any]], Optional[https_fn.Response]]:
    if not event_id:
        return None, empty_response(400)
    if get_event_if_owner_or_staff(event_id, user_id) is None:
        return None, empty_response(404)
    return {"eventId": event_id}, None


def validate_visibility_mode(mode: Any) -> Optional[str]:
    value = (mode or "").strip()
    if value not in _VISIBILITY_MODES:
        return None
    return value


def normalize_assigned_ids(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    return [str(participant_id).strip() for participant_id in raw if str(participant_id).strip()]


def normalize_items(raw: Any) -> Optional[List[Dict[str, Any]]]:
    if not isinstance(raw, list):
        return None
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            return None
        name = (item.get("name") or "").strip()
        if not name:
            return None
        order_value = item.get("order")
        order = index if order_value is None else int(order_value)
        normalized.append(
            {
                "name": name,
                "description": item.get("description") or "",
                "photoUrl": item.get("photoUrl"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "isRequired": bool(item.get("isRequired", False)),
                "order": order,
            }
        )
    return normalized


def build_item_progress_template(required_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    return {item_id: {"check": False, "updateDate": None} for item_id in required_ids}


def compute_is_completed(item_progress: Dict[str, Dict[str, Any]]) -> bool:
    if not item_progress:
        return True
    return all(entry.get("check") is True for entry in item_progress.values())


def build_item_response(item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item_id,
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "photoUrl": data.get("photoUrl"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "isRequired": bool(data.get("isRequired", False)),
        "order": data.get("order", 0),
        "createdAt": data.get("createdAt"),
        "updatedAt": data.get("updatedAt"),
    }


def load_checklist_items(
    helper: FirestoreHelper, event_id: str, checklist_id: str
) -> List[Dict[str, Any]]:
    from checklists.checklist_paths import items_collection_path

    rows = helper.query_documents(
        items_collection_path(event_id, checklist_id),
        order_by=[("order", "asc")],
    )
    return [build_item_response(item_id, data) for item_id, data in rows]


def build_assigned_participant_response(
    participant_id: str, data: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "id": participant_id,
        "name": data.get("participantName") or "",
        "pilotNumber": data.get("pilotNumber") or "",
    }


def load_assigned_participants(
    helper: FirestoreHelper, event_id: str, checklist_id: str
) -> List[Dict[str, Any]]:
    from checklists.checklist_paths import participants_collection_path

    rows = helper.query_documents(
        participants_collection_path(event_id, checklist_id),
    )
    participants = [
        build_assigned_participant_response(participant_id, data)
        for participant_id, data in rows
    ]
    return sorted(participants, key=lambda row: row["id"])


def build_checklist_detail(
    helper: FirestoreHelper,
    event_id: str,
    checklist_id: str,
    checklist_data: Dict[str, Any],
) -> Dict[str, Any]:
    items = load_checklist_items(helper, event_id, checklist_id)
    assigned_participants = load_assigned_participants(helper, event_id, checklist_id)
    return {
        "id": checklist_id,
        "eventId": event_id,
        "title": checklist_data.get("title", ""),
        "visibilityMode": checklist_data.get("visibilityMode", ""),
        "items": items,
        "assignedParticipantIds": assigned_participants,
        "createdAt": checklist_data.get("createdAt"),
        "updatedAt": checklist_data.get("updatedAt"),
    }


def build_checklist_summary(
    helper: FirestoreHelper,
    event_id: str,
    checklist_id: str,
    checklist_data: Dict[str, Any],
) -> Dict[str, Any]:
    from checklists.checklist_paths import items_collection_path, participants_collection_path

    item_count = len(helper.list_document_ids(items_collection_path(event_id, checklist_id)))
    assigned_count = len(
        helper.list_document_ids(participants_collection_path(event_id, checklist_id))
    )
    return {
        "id": checklist_id,
        "title": checklist_data.get("title", ""),
        "visibilityMode": checklist_data.get("visibilityMode", ""),
        "itemCount": item_count,
        "assignedCount": assigned_count,
        "createdAt": checklist_data.get("createdAt"),
        "updatedAt": checklist_data.get("updatedAt"),
    }


def persist_template_items(
    helper: FirestoreHelper,
    event_id: str,
    checklist_id: str,
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    from checklists.checklist_paths import items_collection_path

    now = get_current_timestamp()
    path = items_collection_path(event_id, checklist_id)
    operations = []
    stored_items: List[Dict[str, Any]] = []
    for item in items:
        item_id = helper.new_document_id(path)
        payload = {
            "name": item["name"],
            "description": item["description"],
            "photoUrl": item.get("photoUrl"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "isRequired": item["isRequired"],
            "order": item["order"],
            "createdAt": now,
            "updatedAt": now,
        }
        operations.append((path, item_id, payload))
        stored_items.append(build_item_response(item_id, payload))

    if operations:
        helper.batch_set(operations)

    return sorted(stored_items, key=lambda row: row.get("order", 0))


def delete_all_subcollection_docs(helper: FirestoreHelper, collection_path: str) -> None:
    for doc_id in helper.list_document_ids(collection_path):
        helper.delete_document(collection_path, doc_id)
