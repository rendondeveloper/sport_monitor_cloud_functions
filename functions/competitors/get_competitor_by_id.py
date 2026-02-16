"""
Get Competitor By ID - Obtener un competidor específico por su ID

Obtiene el documento del competidor desde la subcolección participants
de un evento. Retorna los datos básicos de competición.

Requiere Bearer token.
"""

import json
import logging
from typing import Any, Dict

from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value

LOG = logging.getLogger(__name__)
LOG_PREFIX = "[get_competitor_by_id]"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def _get_collection_path(event_id: str) -> str:
    """Construye la ruta de la colección de participantes."""
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )


def _convert_document_to_dict(
    doc_id: str,
    doc_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Convierte documento de Firestore a diccionario de respuesta."""
    competition_category = doc_data.get("competitionCategory", {})

    return {
        "id": doc_id,
        "eventId": doc_data.get("eventId", ""),
        "competitionCategory": {
            "pilotNumber": competition_category.get("pilotNumber", ""),
            "registrationCategory": competition_category.get(
                "registrationCategory", ""
            ),
        },
        "registrationDate": convert_firestore_value(doc_data.get("registrationDate")),
        "team": doc_data.get("team", ""),
        "score": doc_data.get("score", 0),
        "timesToStart": doc_data.get("timesToStart", []),
        "createdAt": convert_firestore_value(doc_data.get("createdAt")),
        "updatedAt": convert_firestore_value(doc_data.get("updatedAt")),
    }


# ============================================================================
# ENDPOINT
# ============================================================================


@https_fn.on_request()
def get_competitor_by_id(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene un competidor específico por su ID.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Query/Path Parameters:
    - eventId: string (requerido) - ID del evento
    - competitorId: string (requerido) - ID del competidor

    Returns:
    - 200: Objeto JSON directo con datos del competidor
    - 400: Bad Request - parámetros faltantes
    - 401: Unauthorized - token inválido o faltante
    - 404: Not Found - competidor no encontrado
    - 500: Internal Server Error
    """
    validation_response = validate_request(
        req, ["GET"], "get_competitor_by_id", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token
        if not verify_bearer_token(req, "get_competitor_by_id"):
            LOG.warning("%s Token inválido o faltante", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Extraer parámetros: query params
        event_id = (req.args.get("eventId") or "").strip()
        competitor_id = (req.args.get("competitorId") or "").strip()

        # Fallback: extraer de path si no vienen en query
        if not event_id or not competitor_id:
            path_parts = [p for p in (req.path or "").split("/") if p]
            if "get-competitor-by-id" in path_parts:
                idx = path_parts.index("get-competitor-by-id")
                if not event_id and idx + 1 < len(path_parts):
                    event_id = path_parts[idx + 1]
                if not competitor_id and idx + 2 < len(path_parts):
                    competitor_id = path_parts[idx + 2]

        if not event_id:
            LOG.warning("%s eventId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if not competitor_id:
            LOG.warning("%s competitorId faltante o vacío", LOG_PREFIX)
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        helper = FirestoreHelper()
        collection_path = _get_collection_path(event_id)

        # Obtener documento
        doc_data = helper.get_document(collection_path, competitor_id)

        if doc_data is None:
            LOG.warning(
                "%s Competidor no encontrado: %s en evento %s",
                LOG_PREFIX,
                competitor_id,
                event_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Convertir y retornar
        result = _convert_document_to_dict(competitor_id, doc_data)

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
