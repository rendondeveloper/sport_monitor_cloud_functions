"""
Get Competitors By Event - Obtener todos los competidores de un evento

Obtiene la lista de competidores de la subcolección participants,
ordenados por fecha de registro descendente. Soporta filtros opcionales
por categoría y equipo.

Requiere Bearer token.
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[get_competitors_by_event]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _get_collection_path(event_id: str) -> str:
    """Construye la ruta de la colección de participantes."""
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )


def _convert_documents_to_list(
    event_id: str,
    documents: List[Tuple[str, Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Convierte lista de documentos de Firestore a lista de dicts de respuesta."""
    result = []
    for doc_id, doc_data in documents:
        competition_category = doc_data.get("competitionCategory", {})
        competitor = {
            "id": doc_id,
            "eventId": event_id,
            "competitionCategory": {
                "pilotNumber": competition_category.get("pilotNumber", ""),
                "registrationCategory": competition_category.get(
                    "registrationCategory", ""
                ),
            },
            "registrationDate": convert_firestore_value(
                doc_data.get("registrationDate")
            ),
            "team": doc_data.get("team", ""),
            "score": doc_data.get("score", 0),
            "timesToStart": doc_data.get("timesToStart", []),
            "createdAt": convert_firestore_value(doc_data.get("createdAt")),
            "updatedAt": convert_firestore_value(doc_data.get("updatedAt")),
        }
        result.append(competitor)
    return result


# ============================================================================
# ENDPOINT
# ============================================================================


@https_fn.on_request()
def get_competitors_by_event(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene todos los competidores de un evento.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Query Parameters:
    - eventId: string (requerido) - ID del evento
    - category: string (opcional) - Filtrar por categoría de registro
    - team: string (opcional) - Filtrar por equipo

    Ordenamiento: registrationDate descendente (más recientes primero).

    Returns:
    - 200: Array JSON directo de competidores (vacío si no hay resultados)
    - 400: Bad Request - eventId faltante
    - 401: Unauthorized - token inválido o faltante
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["GET"], "get_competitors_by_event", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token
        if not verify_bearer_token(req, "get_competitors_by_event"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Extraer parámetros
        event_id = (req.args.get("eventId") or "").strip()

        # Fallback: extraer de path
        if not event_id:
            path_parts = [p for p in (req.path or "").split("/") if p]
            if "get-competitors-by-event" in path_parts:
                idx = path_parts.index("get-competitors-by-event")
                if idx + 1 < len(path_parts):
                    event_id = path_parts[idx + 1]

        if not event_id:
            LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Filtros opcionales
        category = (req.args.get("category") or "").strip()
        team = (req.args.get("team") or "").strip()

        helper = FirestoreHelper()
        collection_path = _get_collection_path(event_id)

        # Construir filtros
        filters = []
        if category:
            filters.append(
                {
                    "field": "competitionCategory.registrationCategory",
                    "operator": "==",
                    "value": category,
                }
            )
        if team:
            filters.append(
                {
                    "field": "team",
                    "operator": "==",
                    "value": team,
                }
            )

        # Ejecutar query con ordenamiento
        documents = helper.query_documents(
            collection_path,
            filters=filters if filters else None,
            order_by=[("registrationDate", "desc")],
        )

        # Convertir y retornar (array directo, sin wrapper)
        result = _convert_documents_to_list(event_id, documents)

        return https_fn.Response(
            json.dumps(result, ensure_ascii=False),
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
