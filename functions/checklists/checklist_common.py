"""Utilidades compartidas para handlers de checklists."""

import json
import logging
from typing import Any, Dict, List, Optional

from firebase_functions import https_fn
from utils.datetime_helper import get_current_timestamp
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


def validate_visibility_mode(mode: Any) -> Optional[str]:
    value = (mode or "").strip()
    if value not in _VISIBILITY_MODES:
        return None
    return value


def normalize_optional_url(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def normalize_checklist_fields(body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "description": (body.get("description") or "").strip()
        if body.get("description") is not None
        else "",
        "photoUrl": normalize_optional_url(body.get("photoUrl")),
    }


def body_has_deprecated_assigned_field(body: Dict[str, Any]) -> bool:
    return "assignedParticipantIds" in body


_CHECKLIST_PATCH_KEYS = frozenset({"title", "description", "photoUrl", "visibilityMode"})
_ITEM_PATCH_KEYS = frozenset(
    {
        "name",
        "description",
        "photoUrl",
        "latitude",
        "longitude",
        "isRequired",
        "participantIds",
        "order",
    }
)
_PARTICIPANT_PATCH_KEYS = frozenset({"participantName", "pilotNumber", "email"})
_PARTICIPANT_FORBIDDEN_KEYS = frozenset(
    {"itemProgress", "isCompleted", "lastUpdateDate", "assignedAt"}
)


def is_real_item_patch_id(item_id: str) -> bool:
    """True for non-empty ids that are not client-side placeholders (client-*)."""
    normalized = (item_id or "").strip()
    return bool(normalized) and not normalized.startswith("client-")


def item_patch_affects_participants(entry: Dict[str, Any]) -> bool:
    return "isRequired" in entry or "participantIds" in entry


def item_patch_has_updatable_fields(entry: Dict[str, Any]) -> bool:
    return any(key in entry for key in _ITEM_PATCH_KEYS)


def participant_patch_has_updatable_fields(entry: Dict[str, Any]) -> bool:
    return any(key in entry for key in _PARTICIPANT_PATCH_KEYS)


def has_updatable_fields(
    body: Dict[str, Any],
    item_patches: List[Dict[str, Any]],
    participant_patches: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    if any(key in body for key in _CHECKLIST_PATCH_KEYS):
        return True
    if any(any(key in entry for key in _ITEM_PATCH_KEYS) for entry in item_patches):
        return True
    if participant_patches and any(
        participant_patch_has_updatable_fields(entry) for entry in participant_patches
    ):
        return True
    return False


def _validate_item_patch_entry(entry: Dict[str, Any]) -> bool:
    if "name" in entry and not (entry.get("name") or "").strip():
        return False
    if "isRequired" in entry and bool(entry.get("isRequired")):
        if "participantIds" in entry and normalize_participant_ids(entry.get("participantIds")):
            return False
    if "order" in entry:
        try:
            int(entry["order"])
        except (TypeError, ValueError):
            return False
    return True


def parse_item_patches(raw: Any) -> Optional[List[Dict[str, Any]]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None

    patches: List[Dict[str, Any]] = []
    seen_ids: set = set()
    for entry in raw:
        if not isinstance(entry, dict):
            return None
        item_id = (entry.get("id") or "").strip()
        if not item_id:
            continue
        if item_id in seen_ids:
            return None
        if not _validate_item_patch_entry(entry):
            return None

        patch_entry: Dict[str, Any] = {"id": item_id}
        for key in _ITEM_PATCH_KEYS:
            if key in entry:
                patch_entry[key] = entry[key]
        patches.append(patch_entry)
        seen_ids.add(item_id)

    return patches


def build_item_create_payload(entry: Dict[str, Any], now: str) -> Dict[str, Any]:
    """
    Payload para crear un item nuevo en Firestore a partir de un patch parcial.

    Se aceptan entries parciales y se rellenan defaults compatibles con build_item_response().
    """
    payload: Dict[str, Any] = {
        "name": (entry.get("name") or "").strip() if "name" in entry else "",
        "description": entry.get("description") or "" if "description" in entry else "",
        "photoUrl": normalize_optional_url(entry.get("photoUrl")) if "photoUrl" in entry else None,
        "latitude": entry.get("latitude") if "latitude" in entry else None,
        "longitude": entry.get("longitude") if "longitude" in entry else None,
        "isRequired": bool(entry.get("isRequired", False)) if "isRequired" in entry else False,
        "participantIds": normalize_participant_ids(entry.get("participantIds"))
        if "participantIds" in entry
        else [],
        "order": int(entry["order"]) if "order" in entry else 0,
        "createdAt": now,
        "updatedAt": now,
    }
    return payload


def parse_participant_patches(raw: Any) -> Optional[List[Dict[str, Any]]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None

    patches: List[Dict[str, Any]] = []
    seen_ids: set = set()
    for entry in raw:
        if not isinstance(entry, dict):
            return None
        if any(key in entry for key in _PARTICIPANT_FORBIDDEN_KEYS):
            return None

        participant_id = (entry.get("id") or "").strip()
        if not participant_id:
            continue
        if participant_id in seen_ids:
            return None

        patch_entry: Dict[str, Any] = {"id": participant_id}
        for key in _PARTICIPANT_PATCH_KEYS:
            if key in entry:
                patch_entry[key] = entry[key]
        patches.append(patch_entry)
        seen_ids.add(participant_id)

    return patches


def build_participant_patch_payload(entry: Dict[str, Any], now: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"updatedAt": now}

    if "participantName" in entry:
        payload["participantName"] = entry.get("participantName")
    if "pilotNumber" in entry:
        payload["pilotNumber"] = entry.get("pilotNumber")
    if "email" in entry:
        payload["email"] = entry.get("email")

    return payload


def build_checklist_patch(body: Dict[str, Any], now: str) -> Optional[Dict[str, Any]]:
    patch: Dict[str, Any] = {}

    if "title" in body:
        title = (body.get("title") or "").strip()
        if not title:
            return None
        patch["title"] = title

    if "description" in body:
        patch["description"] = (
            (body.get("description") or "").strip()
            if body.get("description") is not None
            else ""
        )

    if "photoUrl" in body:
        patch["photoUrl"] = normalize_optional_url(body.get("photoUrl"))

    if "visibilityMode" in body:
        visibility_mode = validate_visibility_mode(body.get("visibilityMode"))
        if visibility_mode is None:
            return None
        patch["visibilityMode"] = visibility_mode

    if not patch:
        return {}

    patch["updatedAt"] = now
    return patch


def build_item_patch_payload(entry: Dict[str, Any], now: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"updatedAt": now}

    if "name" in entry:
        payload["name"] = (entry.get("name") or "").strip()
    if "description" in entry:
        payload["description"] = entry.get("description") or ""
    if "photoUrl" in entry:
        payload["photoUrl"] = normalize_optional_url(entry.get("photoUrl"))
    if "latitude" in entry:
        payload["latitude"] = entry.get("latitude")
    if "longitude" in entry:
        payload["longitude"] = entry.get("longitude")
    if "isRequired" in entry:
        payload["isRequired"] = bool(entry.get("isRequired", False))
    if "participantIds" in entry:
        payload["participantIds"] = normalize_participant_ids(entry.get("participantIds"))
    if "order" in entry:
        payload["order"] = int(entry["order"])

    return payload


def validate_item_patches_event_participants(
    helper: FirestoreHelper, event_id: str, patches: List[Dict[str, Any]]
) -> bool:
    from checklists.checklist_paths import event_participants_collection_path

    path = event_participants_collection_path(event_id)
    for patch in patches:
        if "participantIds" not in patch:
            continue
        for participant_id in normalize_participant_ids(patch.get("participantIds")):
            if helper.get_document(path, participant_id) is None:
                return False
    return True


def normalize_participant_ids(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    return [str(participant_id).strip() for participant_id in raw if str(participant_id).strip()]


def item_participant_ids(item: Dict[str, Any]) -> List[str]:
    return normalize_participant_ids(item.get("participantIds"))


def item_is_targeted(item: Dict[str, Any]) -> bool:
    return len(item_participant_ids(item)) > 0


def item_is_visible_for_pilot(item: Dict[str, Any], pilot_id: str) -> bool:
    # Items opcionales (isRequired=False) son visibles para todos, aunque tengan participantIds.
    if not bool(item.get("isRequired", False)):
        return True
    targeted_ids = item_participant_ids(item)
    if targeted_ids:
        return pilot_id in targeted_ids
    return True


def item_is_mandatory_for_pilot(item: Dict[str, Any], pilot_id: str) -> bool:
    # Items opcionales (isRequired=False) NO son obligatorios, aunque tengan participantIds.
    if not bool(item.get("isRequired", False)):
        return False
    targeted_ids = item_participant_ids(item)
    if targeted_ids:
        return pilot_id in targeted_ids
    return True


def effective_is_required_for_participant(item: Dict[str, Any], participant_id: str) -> bool:
    """
    Determina si un item debe reportarse como requerido para un participante específico.

    Regla (participant-progress):
    - Si el item tiene participantIds, solo es requerido para quienes estén incluidos.
      Esto aplica incluso cuando isRequired=False en el template.
    - Si el item NO tiene participantIds, se respeta isRequired como viene en el template.

    Nota: normalize/patch prohíben isRequired=True junto con participantIds; este helper
    mantiene comportamiento seguro aunque llegaran datos inconsistentes.
    """
    targeted_ids = item_participant_ids(item)
    if targeted_ids:
        return participant_id in targeted_ids
    return bool(item.get("isRequired", False))


def mandatory_item_ids_for_pilot(items: List[Dict[str, Any]], pilot_id: str) -> List[str]:
    return [item["id"] for item in items if item_is_mandatory_for_pilot(item, pilot_id)]


def mandatory_items_for_pilot(
    items: List[Dict[str, Any]], pilot_id: str
) -> List[Dict[str, Any]]:
    return [item for item in items if item_is_mandatory_for_pilot(item, pilot_id)]


def visible_items_for_pilot(
    items: List[Dict[str, Any]], pilot_id: str
) -> List[Dict[str, Any]]:
    return [item for item in items if item_is_visible_for_pilot(item, pilot_id)]


def items_for_participant_progress(
    items: List[Dict[str, Any]], pilot_id: str
) -> List[Dict[str, Any]]:
    """
    Items que deben mostrarse en participant-progress para un piloto:

    - Todos los items opcionales (isRequired=False) para todos los participantes.
    - Todos los items obligatorios aplicables al piloto (isRequired=True; y si
      existe targeting, se respeta para requeridos).
    """
    result: List[Dict[str, Any]] = []
    for item in items:
        if not bool(item.get("isRequired", False)):
            result.append(item)
            continue
        if item_is_mandatory_for_pilot(item, pilot_id):
            result.append(item)
    return result


def progress_item_ids_for_pilot(items: List[Dict[str, Any]], pilot_id: str) -> List[str]:
    """IDs de items a guardar en itemProgress (opcionales + requeridos aplicables)."""
    return [item["id"] for item in items_for_participant_progress(items, pilot_id)]


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
        participant_ids = normalize_participant_ids(item.get("participantIds"))
        is_required = bool(item.get("isRequired", False))
        if is_required and participant_ids:
            return None
        order_value = item.get("order")
        order = index if order_value is None else int(order_value)
        normalized.append(
            {
                "name": name,
                "description": item.get("description") or "",
                "photoUrl": normalize_optional_url(item.get("photoUrl")),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "isRequired": is_required,
                "participantIds": participant_ids,
                "order": order,
            }
        )
    return normalized


def validate_items_event_participants(
    helper: FirestoreHelper, event_id: str, items: List[Dict[str, Any]]
) -> bool:
    from checklists.checklist_paths import event_participants_collection_path

    path = event_participants_collection_path(event_id)
    for item in items:
        for participant_id in item_participant_ids(item):
            if helper.get_document(path, participant_id) is None:
                return False
    return True


def build_item_progress_template(required_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    return {item_id: {"check": False, "updateDate": None} for item_id in required_ids}


def compute_is_completed(item_progress: Dict[str, Dict[str, Any]]) -> bool:
    if not item_progress:
        return True
    return all(entry.get("check") is True for entry in item_progress.values())


def compute_is_completed_required(
    item_progress: Dict[str, Dict[str, Any]], required_ids: List[str]
) -> bool:
    """Evalúa completion solo para los items requeridos."""
    if not required_ids:
        return True
    return all((item_progress.get(item_id) or {}).get("check") is True for item_id in required_ids)


def build_item_response(item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item_id,
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "photoUrl": data.get("photoUrl"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "isRequired": bool(data.get("isRequired", False)),
        "participantIds": normalize_participant_ids(data.get("participantIds")),
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


def build_checklist_detail(
    helper: FirestoreHelper,
    event_id: str,
    checklist_id: str,
    checklist_data: Dict[str, Any],
) -> Dict[str, Any]:
    items = load_checklist_items(helper, event_id, checklist_id)
    return {
        "id": checklist_id,
        "eventId": event_id,
        "title": checklist_data.get("title", ""),
        "description": checklist_data.get("description", ""),
        "photoUrl": checklist_data.get("photoUrl"),
        "visibilityMode": checklist_data.get("visibilityMode", ""),
        "items": items,
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
    participant_count = len(
        helper.list_document_ids(participants_collection_path(event_id, checklist_id))
    )
    return {
        "id": checklist_id,
        "title": checklist_data.get("title", ""),
        "description": checklist_data.get("description", ""),
        "photoUrl": checklist_data.get("photoUrl"),
        "visibilityMode": checklist_data.get("visibilityMode", ""),
        "itemCount": item_count,
        "assignedCount": participant_count,
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
            "participantIds": item.get("participantIds", []),
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
