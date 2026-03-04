"""
List Competitors By Event - Lista paginada de competidores de un evento

Obtiene los competidores de la subcolección participants con paginación por cursor.
Devuelve por cada competidor: id (documento), nombre, categoría, número, equipo.

Requiere Bearer token. Región: us-east4.
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from models.paginated_response import PaginatedResponse
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[list_competitors_by_event]"

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100

_USER_PERSONAL_DATA = getattr(
    FirestoreCollections, "USER_PERSONAL_DATA", "personalData"
)


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _get_collection_path(event_id: str) -> str:
    """Construye la ruta de la colección de participantes del evento."""
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )


def _get_user_full_name(helper: FirestoreHelper, user_id: str) -> str:
    """
    Obtiene el fullName del usuario desde users/{userId}/personalData (primer documento).
    Retorna cadena vacía si no hay datos.
    """
    path = (
        f"{FirestoreCollections.USERS}/{user_id}/{_USER_PERSONAL_DATA}"
    )
    try:
        ids = helper.list_document_ids(path)
        if not ids:
            return ""
        doc = helper.get_document(path, ids[0])
        if doc:
            return (doc.get("fullName") or "").strip()
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.warning("%s No se pudo obtener nombre para userId=%s: %s", LOG_PREFIX, user_id, e)
    return ""


def _load_category_map(helper: FirestoreHelper, event_id: str) -> Dict[str, str]:
    """
    Carga el mapa id→nombre de las categorías del evento.

    Retorna dict vacío si no hay categorías o hay un error. Si el id no está
    en el mapa, _build_competitor_item devuelve el valor raw como fallback.
    """
    path = (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_CATEGORIES}"
    )
    try:
        results = helper.query_documents(path)
        return {doc_id: (doc_data.get("name") or doc_id) for doc_id, doc_data in results}
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.warning("%s No se pudo cargar el mapa de categorías: %s", LOG_PREFIX, e)
        return {}


def _build_competitor_item(
    helper: FirestoreHelper,
    doc_id: str,
    doc_data: Dict[str, Any],
    category_map: Dict[str, str],
) -> Dict[str, Any]:
    """Construye un item de la lista: id, name, category, number, team."""
    comp_cat = doc_data.get("competitionCategory") or {}
    name = _get_user_full_name(helper, doc_id)
    raw_category = comp_cat.get("registrationCategory", "")
    category_name = category_map.get(raw_category, raw_category)
    return {
        "id": doc_id,
        "name": name,
        "category": category_name,
        "number": comp_cat.get("pilotNumber", ""),
        "team": doc_data.get("team", ""),
    }


# ============================================================================
# ENDPOINT
# ============================================================================


@https_fn.on_request(region="us-east4")
def list_competitors_by_event(req: https_fn.Request) -> https_fn.Response:
    """
    Lista competidores de un evento con paginación por cursor.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Query Parameters:
    - eventId: string (requerido) - ID del evento
    - limit: int (opcional) - Tamaño de página (default 20, máx 100)
    - cursor: string (opcional) - ID del último documento de la página anterior (lastDocId)

    Returns:
    - 200: JSON array directo de { id, name, category, number, team }
    - 400: Bad Request - eventId faltante o limit inválido
    - 401: Unauthorized - token inválido o faltante
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["GET"], "list_competitors_by_event", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        if not verify_bearer_token(req, "list_competitors_by_event"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        event_id = (req.args.get("eventId") or "").strip()
        if not event_id:
            path_parts = [p for p in (req.path or "").split("/") if p]
            if "list-competitors-by-event" in path_parts:
                idx = path_parts.index("list-competitors-by-event")
                if idx + 1 < len(path_parts):
                    event_id = path_parts[idx + 1].strip()
        if not event_id:
            LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        limit_raw = req.args.get("limit", str(_DEFAULT_PAGE_SIZE)).strip()
        try:
            limit = int(limit_raw) if limit_raw else _DEFAULT_PAGE_SIZE
        except ValueError:
            limit = _DEFAULT_PAGE_SIZE
        if limit < 1:
            limit = _DEFAULT_PAGE_SIZE
        if limit > _MAX_PAGE_SIZE:
            limit = _MAX_PAGE_SIZE

        cursor = (req.args.get("cursor") or req.args.get("lastDocId") or "").strip()

        helper = FirestoreHelper()
        collection_path = _get_collection_path(event_id)

        category_map = _load_category_map(helper, event_id)

        # Pedir limit+1 para saber si hay más páginas
        documents: List[Tuple[str, Dict[str, Any]]] = helper.query_documents(
            collection_path,
            order_by=[("registrationDate", "desc")],
            limit=limit + 1,
            start_after_doc_id=cursor if cursor else None,
        )

        has_more = len(documents) > limit
        if has_more:
            documents = documents[:limit]

        competitors = [
            _build_competitor_item(helper, doc_id, doc_data, category_map)
            for doc_id, doc_data in documents
            if isinstance(doc_data, dict)
        ]

        last_doc_id = documents[-1][0] if documents else None
        paginated = PaginatedResponse.create(
            items=competitors,
            limit=limit,
            page=1,
            has_more=has_more,
            last_doc_id=last_doc_id,
        )
        body = paginated.to_dict()

        return https_fn.Response(
            json.dumps(body, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        LOG.error("%s Error de validación: %s", LOG_PREFIX, e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
