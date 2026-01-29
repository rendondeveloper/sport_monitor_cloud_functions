import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value


@https_fn.on_request()
def update_competitor_status(req: https_fn.Request) -> https_fn.Response:
    """
    Actualiza el estado de un competidor en un checkpoint específico.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)
    - Content-Type: application/json (requerido)

    Path Parameters:
    - eventId: ID del evento (requerido)
    - dayOfRaceId: ID del día de carrera (requerido)
    - competitorId: ID del competidor (requerido)
    - checkpointId: ID del checkpoint (requerido)

    Request Body:
    {
        "status": "check",
        "checkpointDisableName": "Nombre del Checkpoint",
        "note": "Nota opcional"
    }

    Returns:
    - 200: Estado actualizado exitosamente
    - 400: Bad Request - parámetros faltantes o inválidos
    - 401: Unauthorized - token inválido o faltante
    - 404: Not Found - competidor o checkpoint no encontrado
    - 500: Internal Server Error

    Nota: Actualiza el documento en:
          events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/
          competitors/{competitorId}/checkpoints/{checkpointId}
    """
    # Validar CORS y método HTTP
    validation_response = validate_request(
        req, ["PUT"], "update_competitor_status", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token
        if not verify_bearer_token(req, "update_competitor_status"):
            logging.warning("update_competitor_status: Token inválido o faltante")
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Unauthorized",
                        "error": "Token inválido o faltante",
                    },
                    ensure_ascii=False,
                ),
                status=401,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # Extraer parámetros del path
        path = req.path
        logging.info("update_competitor_status: Path recibido: %s", path)
        path_parts = [p for p in path.split("/") if p]
        logging.info("update_competitor_status: Path parts: %s", path_parts)

        event_id: Optional[str] = None
        day_of_race_id: Optional[str] = None
        competitor_id: Optional[str] = None
        checkpoint_id: Optional[str] = None

        try:
            # Buscar el patrón /update-competitor-status/{eventId}/{dayOfRaceId}/{competitorId}/{checkpointId}
            if "update-competitor-status" in path_parts:
                status_index = path_parts.index("update-competitor-status")
                if status_index + 4 < len(path_parts):
                    event_id = path_parts[status_index + 1]
                    day_of_race_id = path_parts[status_index + 2]
                    competitor_id = path_parts[status_index + 3]
                    checkpoint_id = path_parts[status_index + 4]
                    logging.info(
                        "update_competitor_status: Parámetros extraídos - eventId: %s, dayOfRaceId: %s, competitorId: %s, checkpointId: %s",
                        event_id,
                        day_of_race_id,
                        competitor_id,
                        checkpoint_id,
                    )
        except (ValueError, IndexError) as e:
            logging.warning(
                "update_competitor_status: Error extrayendo parámetros del path: %s", e
            )

        # Validar parámetros del path
        if not event_id or event_id.strip() == "":
            logging.warning("update_competitor_status: eventId faltante o vacío")
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": "eventId es requerido",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        if not day_of_race_id or day_of_race_id.strip() == "":
            logging.warning("update_competitor_status: dayOfRaceId faltante o vacío")
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": "dayOfRaceId es requerido",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        if not competitor_id or competitor_id.strip() == "":
            logging.warning("update_competitor_status: competitorId faltante o vacío")
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": "competitorId es requerido",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        if not checkpoint_id or checkpoint_id.strip() == "":
            logging.warning("update_competitor_status: checkpointId faltante o vacío")
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": "checkpointId es requerido",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # Parsear request body
        try:
            request_data = req.get_json(silent=True)
            if request_data is None:
                logging.warning(
                    "update_competitor_status: Request body inválido o faltante"
                )
                return https_fn.Response(
                    json.dumps(
                        {
                            "success": False,
                            "message": "Bad Request",
                            "error": "Request body inválido o faltante",
                        },
                        ensure_ascii=False,
                    ),
                    status=400,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
        except (ValueError, TypeError) as e:
            logging.warning("update_competitor_status: Error parseando JSON: %s", e)
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": "Request body inválido",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # Validar campos del request body
        status = request_data.get("status")
        if not status or status.strip() == "":
            logging.warning("update_competitor_status: status faltante o vacío")
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": "status es requerido",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        checkpoint_disable_name = request_data.get("checkpointDisableName", "")
        note = request_data.get("note")

        # Validar que checkpointDisableName esté presente si status es 'out', 'outStart' o 'outLast'
        if status in ["out", "outStart", "outLast"]:
            if not checkpoint_disable_name or checkpoint_disable_name.strip() == "":
                logging.warning(
                    "update_competitor_status: checkpointDisableName requerido para status %s",
                    status,
                )
                return https_fn.Response(
                    json.dumps(
                        {
                            "success": False,
                            "message": "Bad Request",
                            "error": "checkpointDisableName es requerido cuando status es 'out', 'outStart' o 'outLast'",
                        },
                        ensure_ascii=False,
                    ),
                    status=400,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "Access-Control-Allow-Origin": "*",
                    },
                )

        # Inicializar Firestore
        db = firestore.client()
        tracking_id = f"{event_id}_{day_of_race_id}"
        # Construir ruta del documento del checkpoint
        checkpoint_path = (
            f"{FirestoreCollections.EVENT_TRACKING}/{event_id}/"
            f"{FirestoreCollections.EVENT_TRACKING_COMPETITOR_TRACKING}/{tracking_id}/"
            f"{FirestoreCollections.EVENT_TRACKING_COMPETITOR}/{competitor_id}/"
            f"{FirestoreCollections.EVENT_TRACKING_CHECKPOINTS}/{checkpoint_id}"
        )
        checkpoint_ref = db.document(checkpoint_path)

        # Verificar que el checkpoint exista
        checkpoint_doc = checkpoint_ref.get()
        if not checkpoint_doc.exists:
            logging.warning(
                "update_competitor_status: Checkpoint no encontrado: %s",
                checkpoint_path,
            )
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Not Found",
                        "error": "Checkpoint no encontrado",
                    },
                    ensure_ascii=False,
                ),
                status=404,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # Obtener nombre del checkpoint si no se proporciona checkpointDisableName
        checkpoint_data = checkpoint_doc.to_dict()
        checkpoint_name = checkpoint_data.get("name", "") if checkpoint_data else ""
        if not checkpoint_disable_name and status in ["out", "outStart", "outLast"]:
            checkpoint_disable_name = checkpoint_name

        # Construir datos de actualización
        now = datetime.utcnow()
        update_data: Dict[str, Any] = {
            "statusCompetitor": status,
            "passTime": now,
            "updatedAt": now,
        }

        # Lógica condicional: establecer checkpointDisable y checkpointDisableName
        if status in ["out", "outStart", "outLast"]:
            update_data["checkpointDisable"] = checkpoint_id
            update_data["checkpointDisableName"] = checkpoint_disable_name
        else:
            update_data["checkpointDisable"] = None
            update_data["checkpointDisableName"] = None

        # Agregar note si está presente
        if note is not None:
            update_data["note"] = note

        # Actualizar documento en Firestore
        logging.info(
            "update_competitor_status: Actualizando checkpoint %s con datos: %s",
            checkpoint_path,
            update_data,
        )
        checkpoint_ref.update(update_data)

        # Retornar respuesta exitosa
        response_data = {
            "success": True,
        }

        return https_fn.Response(
            json.dumps(response_data, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "PUT, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("update_competitor_status: Error de validación: %s", e)
        return https_fn.Response(
            json.dumps(
                {
                    "success": False,
                    "message": "Bad Request",
                    "error": str(e),
                },
                ensure_ascii=False,
            ),
            status=400,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("update_competitor_status: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            json.dumps(
                {
                    "success": False,
                    "message": "Internal Server Error",
                    "error": "Error procesando la solicitud",
                },
                ensure_ascii=False,
            ),
            status=500,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
            },
        )
