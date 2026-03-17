"""
Eventos suscritos del usuario - Obtiene los eventos en los que el userId está suscrito (membership).

Lógica de negocio únicamente. La validación CORS y Bearer token la realiza user_route.
Lee users/{userId}/membership, resuelve cada evento y su event_content, devuelve respuesta paginada.
Solo la respuesta 200 retorna JSON; errores retornan cuerpo vacío.
"""

import json
import logging
from typing import Any, Dict, List

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from models.paginated_response import PaginatedResponse
from utils.firestore_helper import FirestoreHelper
from utils.helpers import convert_firestore_value

_CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}
_JSON_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def _resolve_user_id(helper: FirestoreHelper, user_id: str) -> str | None:
    """Retorna userId si el documento users/{userId} existe, None si no."""
    if not user_id or not user_id.strip():
        return None
    user_id = user_id.strip()
    doc = helper.get_document(FirestoreCollections.USERS, user_id)
    return user_id if doc is not None else None


def _build_event_item(
    event_id: str,
    event_doc: Dict[str, Any],
    event_content_doc: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Construye un ítem de evento para la respuesta: id, name, description, status, startDateTime, endEvent, imageUrl."""
    name = event_doc.get("name")
    description = event_doc.get("description")
    status = event_doc.get("status")

    start_date_time = None
    end_event = None
    image_url = None
    if event_content_doc:
        start_date_time = event_content_doc.get("startEvent")
        end_event = event_content_doc.get("endEvent")
        image_url = event_content_doc.get("photoMain")

    return {
        "id": event_id,
        "name": convert_firestore_value(name),
        "description": convert_firestore_value(description),
        "status": convert_firestore_value(status),
        "startDateTime": convert_firestore_value(start_date_time),
        "endEvent": convert_firestore_value(end_event),
        "imageUrl": convert_firestore_value(image_url),
    }


def handle(req: https_fn.Request) -> https_fn.Response:
    """
    GET /api/users/subscribedEvents?userId=xxx&limit=50&page=1

    Retorna eventos en los que el usuario está suscrito (membership), paginados.
    - 200: JSON con result (lista de eventos) y pagination. Única respuesta con cuerpo JSON.
    - 400: userId faltante o vacío (sin cuerpo).
    - 404: usuario no existe o membership vacío (sin cuerpo).
    - 500: error interno (sin cuerpo).
    """
    try:
        user_id_param = (req.args.get("userId") or "").strip()
        if not user_id_param:
            logging.warning("subscribed_events: userId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers=_CORS_HEADERS,
            )

        limit_param = req.args.get("limit", "50")
        page_param = req.args.get("page", "1")
        try:
            limit = min(int(limit_param), 100)
            page = int(page_param)
        except (TypeError, ValueError):
            limit = 50
            page = 1
        if limit < 1:
            limit = 50
        if page < 1:
            page = 1

        helper = FirestoreHelper()
        user_id = _resolve_user_id(helper, user_id_param)
        if user_id is None:
            logging.warning(
                "subscribed_events: Usuario no encontrado (userId=%s)",
                user_id_param,
            )
            return https_fn.Response(
                "",
                status=404,
                headers=_CORS_HEADERS,
            )

        membership_path = f"{FirestoreCollections.USERS}/{user_id}/{FirestoreCollections.USER_MEMBERSHIP}"
        event_ids: List[str] = helper.list_document_ids(membership_path)
        if not event_ids:
            logging.info(
                "subscribed_events: Colección membership vacía para userId=%s",
                user_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers=_CORS_HEADERS,
            )

        event_ids_sorted = sorted(event_ids)
        total = len(event_ids_sorted)
        start = (page - 1) * limit
        event_ids_page = event_ids_sorted[start : start + limit]
        has_more = total > start + limit
        last_doc_id = event_ids_page[-1] if event_ids_page and has_more else None

        items: List[Dict[str, Any]] = []
        for event_id in event_ids_page:
            event_doc = helper.get_document(FirestoreCollections.EVENTS, event_id)
            if event_doc is None:
                continue
            event_content_path = f"{FirestoreCollections.EVENTS}/{event_id}/{FirestoreCollections.EVENT_CONTENT}"
            event_content_results = helper.query_documents(event_content_path, limit=1)
            event_content_doc = event_content_results[0][1] if event_content_results else None
            items.append(_build_event_item(event_id, event_doc, event_content_doc))

        paginated = PaginatedResponse.create(
            items=items,
            limit=limit,
            page=page,
            has_more=has_more,
            last_doc_id=last_doc_id,
        )
        response_data = paginated.to_dict()
        return https_fn.Response(
            json.dumps(response_data, ensure_ascii=False),
            status=200,
            headers=_JSON_HEADERS,
        )

    except ValueError as e:
        logging.error("subscribed_events: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers=_CORS_HEADERS,
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("subscribed_events: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers=_CORS_HEADERS,
        )
