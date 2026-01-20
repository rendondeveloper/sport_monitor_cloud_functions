import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value


@https_fn.on_request()
def all_competitor_tracking(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene todos los competidores de un evento y día de carrera específico,
    incluyendo TODOS los checkpoints de cada competidor (sin filtrar por checkpoint específico).

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Path Parameters:
    - eventId: ID del evento (requerido, viene en la URL)
    - dayOfRaceId: ID del día de carrera (requerido, viene en la URL)

    Query Parameters (alternativa):
    - eventId: ID del evento (si no viene en path)
    - dayOfRaceId: ID del día de carrera (si no viene en path)

    Returns:
    - 200: {"success": True} - Operación exitosa
    - 400: Bad Request - parámetros faltantes o inválidos
    - 401: Unauthorized - token inválido o faltante
    - 500: Internal Server Error

    Nota: Consulta events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors
          y para cada competidor obtiene TODOS sus checkpoints desde
          competitors/{competitorId}/checkpoints.
          No aplica filtros, retorna todos los competidores con todos sus checkpoints.
    """
    # Validar CORS y método HTTP
    validation_response = validate_request(
        req, ["GET"], "all_competitor_tracking", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token (solo para autenticación)
        if not verify_bearer_token(req, "all_competitor_tracking"):
            logging.warning("all_competitor_tracking: Token inválido o faltante")
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

        # Obtener parámetros de query parameters primero
        event_id = req.args.get("eventId")
        day_of_race_id = req.args.get("dayOfRaceId")

        # Si no vienen en query params, intentar extraerlos del path
        # La URL será: /api/checkpoint/all_competitor_tracking/{eventId}/{dayOfRaceId}
        if (
            not event_id
            or event_id.strip() == ""
            or not day_of_race_id
            or day_of_race_id.strip() == ""
        ):
            path = req.path
            logging.info("all_competitor_tracking: Path recibido: %s", path)
            path_parts = [p for p in path.split("/") if p]  # Filtrar strings vacíos
            logging.info("all_competitor_tracking: Path parts: %s", path_parts)

            try:
                # Buscar el índice de "all_competitor_tracking" o "all-competitor-tracking"
                tracking_key = None
                if "all_competitor_tracking" in path_parts:
                    tracking_key = "all_competitor_tracking"
                elif "all-competitor-tracking" in path_parts:
                    tracking_key = "all-competitor-tracking"

                if tracking_key:
                    tracking_index = path_parts.index(tracking_key)
                    if tracking_index + 2 < len(path_parts):
                        if not event_id or event_id.strip() == "":
                            event_id = path_parts[tracking_index + 1]
                        if not day_of_race_id or day_of_race_id.strip() == "":
                            day_of_race_id = path_parts[tracking_index + 2]
                        logging.info(
                            "all_competitor_tracking: Parámetros extraídos - eventId: %s, dayOfRaceId: %s",
                            event_id,
                            day_of_race_id,
                        )
            except (ValueError, IndexError) as e:
                logging.warning(
                    "all_competitor_tracking: Error extrayendo parámetros del path: %s",
                    e,
                )

        # Validar que todos los parámetros estén presentes
        if not event_id or event_id.strip() == "":
            logging.warning("all_competitor_tracking: eventId faltante o vacío")
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
            logging.warning("all_competitor_tracking: dayOfRaceId faltante o vacío")
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

        # Inicializar Firestore
        db = firestore.client()

        # Construir ruta base para tracking
        tracking_id = f"{event_id}_{day_of_race_id}"

        # 1. Obtener todos los competidores
        # events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors
        logging.info(
            "all_competitor_tracking: Obteniendo competidores para eventId=%s, dayOfRaceId=%s, trackingId=%s",
            event_id,
            day_of_race_id,
            tracking_id,
        )
        competitors_ref = (
            db.collection(FirestoreCollections.EVENT_TRACKING)
            .document(event_id)
            .collection(FirestoreCollections.EVENT_TRACKING_COMPETITOR_TRACKING)
            .document(tracking_id)
            .collection(FirestoreCollections.EVENT_TRACKING_COMPETITOR)
        )
        competitors_snapshot = competitors_ref.get()

        if not competitors_snapshot:
            # Si no hay competidores, retornar éxito
            return https_fn.Response(
                json.dumps(
                    {"success": True},
                    ensure_ascii=False,
                ),
                status=200,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                },
            )

        # 2. Para cada competidor, obtener TODOS sus checkpoints
        competitor_tracking_list: List[Dict[str, Any]] = []

        for competitor_doc in competitors_snapshot:
            try:
                competitor_data = competitor_doc.to_dict()
                if competitor_data is None:
                    continue

                competitor_id = competitor_doc.id

                # Construir ruta a TODOS los checkpoints del competidor
                # events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors/{competitorId}/checkpoints
                checkpoints_ref = (
                    db.collection(FirestoreCollections.EVENT_TRACKING)
                    .document(event_id)
                    .collection(FirestoreCollections.EVENT_TRACKING_COMPETITOR_TRACKING)
                    .document(tracking_id)
                    .collection(FirestoreCollections.EVENT_TRACKING_COMPETITOR)
                    .document(competitor_id)
                    .collection(FirestoreCollections.EVENT_TRACKING_CHECKPOINTS)
                )

                checkpoints_snapshot = checkpoints_ref.get()

                # Construir lista de checkpoints
                tracking_checkpoints: List[Dict[str, Any]] = []

                for checkpoint_doc in checkpoints_snapshot:
                    try:
                        checkpoint_data = checkpoint_doc.to_dict()
                        if checkpoint_data is None:
                            continue

                        # Construir objeto CheckpointsTracking
                        checkpoint_tracking = {
                            "id": checkpoint_doc.id,
                            "name": checkpoint_data.get("name", ""),
                            "checkpointType": checkpoint_data.get("checkpointType", "pass"),
                            "statusCompetitor": checkpoint_data.get(
                                "statusCompetitor", "none"
                            ),
                            "checkpointDisable": (
                                checkpoint_data.get("checkpointDisable") or ""
                            ),
                            "checkpointDisableName": (
                                checkpoint_data.get("checkpointDisableName") or ""
                            ),
                            "passTime": convert_firestore_value(
                                checkpoint_data.get("passTime")
                            ),
                            "order": checkpoint_data.get("order", 0),
                            "note": checkpoint_data.get("note"),
                        }

                        tracking_checkpoints.append(checkpoint_tracking)

                    except (ValueError, AttributeError, RuntimeError, TypeError) as e:
                        logging.warning(
                            "all_competitor_tracking: Error procesando checkpoint %s del competidor %s: %s",
                            checkpoint_doc.id,
                            competitor_id,
                            e,
                        )
                        continue

                # Construir objeto CompetitorTracking con todos sus checkpoints
                competitor_tracking = {
                    "id": competitor_id,
                    "name": competitor_data.get("name", ""),
                    "order": competitor_data.get("order", 0),
                    "category": competitor_data.get("category", ""),
                    "number": (
                        str(competitor_data.get("number", ""))
                        if competitor_data.get("number") is not None
                        else ""
                    ),
                    "timeToStart": convert_firestore_value(
                        competitor_data.get("timeToStart")
                    ),
                    "createdAt": convert_firestore_value(
                        competitor_data.get("createdAt")
                    ),
                    "updatedAt": convert_firestore_value(
                        competitor_data.get("updatedAt")
                    ),
                    "trackingCheckpoints": tracking_checkpoints,
                }

                competitor_tracking_list.append(competitor_tracking)

            except (ValueError, AttributeError, RuntimeError, TypeError) as e:
                logging.warning(
                    "all_competitor_tracking: Error procesando competidor %s: %s",
                    competitor_doc.id,
                    e,
                )
                continue

        # Retornar respuesta exitosa
        return https_fn.Response(
            json.dumps(
                {"success": True},
                ensure_ascii=False,
            ),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("all_competitor_tracking: Error de validación: %s", e)
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
        logging.error("all_competitor_tracking: Error interno: %s", e, exc_info=True)
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
