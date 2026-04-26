"""
Lista los eventos del usuario autenticado (filtrado por creator).
Opcionalmente filtra por status.

Método: GET /api/event-management/{userId}/list?status= — el userId va en la URL (no se obtiene del token).
Alias vía event_route: GET /api/events/{userId}/list?status= (mismo criterio: userId solo en path).
Headers: Authorization Bearer (requerido)
Query params: status (opcional)
Returns: 200 array de eventos (puede ser []) | 401 no autorizado | 500 error interno
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[list_events]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _build_filters(user_id: str, status: str) -> list:
    """Construye los filtros de la query. Siempre filtra por creator."""
    filters = [{"field": "creator", "operator": "==", "value": user_id}]
    if status:
        filters.append({"field": "status", "operator": "==", "value": status})
    return filters


def _build_event_list(docs: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Convierte documentos Firestore a lista de respuesta con campos permitidos."""
    result = []
    for event_id, data in docs:
        item = {
            "name": data.get("name"),
            "status": data.get("status"),
            "date": data.get("date"),
            "location": data.get("location"),
            "typeEvent": data.get("typeEvent"),
            "id": event_id,
        }
        result.append(item)
    return result


def _sort_events_by_created_at_desc(
    docs: List[Tuple[str, Dict[str, Any]]],
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Ordena por createdAt desc en memoria.

    Se usa como fallback cuando Firestore no puede ejecutar order_by por índices.
    """
    return sorted(docs, key=lambda item: item[1].get("createdAt") or "", reverse=True)


# ============================================================================
# HANDLER
# ============================================================================


def handle_list(req: https_fn.Request, user_id: str) -> https_fn.Response:
    """
    Retorna todos los eventos del usuario autenticado.

    Params:
    - user_id: uid tomado del path por el router (no del token)
    - req.args.status: filtro opcional por estado del evento

    Returns:
    - 200: array de eventos (puede ser [])
    - 500: error interno
    """
    status = (req.args.get("status") or "").strip()

    try:
        filters = _build_filters(user_id, status)

        helper = FirestoreHelper()
        try:
            docs = helper.query_documents(
                FirestoreCollections.EVENTS,
                filters=filters,
                order_by=[("createdAt", "desc")],
            )
        except Exception as query_error:
            LOG.warning(
                "%s Query con order_by falló; reintentando sin order_by. error=%s",
                LOG_PREFIX,
                query_error,
            )
            docs = helper.query_documents(
                FirestoreCollections.EVENTS,
                filters=filters,
            )
            docs = _sort_events_by_created_at_desc(docs)
        response = _build_event_list(docs)

        return https_fn.Response(
            json.dumps(response, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except Exception as e:
        LOG.error("%s Error interno: %s", LOG_PREFIX, e, exc_info=True)
        return https_fn.Response("", status=500, headers={"Access-Control-Allow-Origin": "*"})
