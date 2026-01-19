import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value


def is_competitor_visible(status: str, checkpoint_type: str) -> bool:
    """
    Determina si un competidor debe mostrarse según su status y el tipo de checkpoint.

    Reglas:
    - Si status es 'out': visible para todos los tipos de checkpoints
    - Si status es 'outStart': solo visible para checkpoints tipo 'start' o 'finish'
    - Para cualquier otro status: siempre visible

    Args:
        status: Status del competidor (none, check, out, outStart, outLast, disqualified)
        checkpoint_type: Tipo de checkpoint (start, pass, timer, startTimer, endTimer, finish)

    Returns:
        bool: True si el competidor es visible, False en caso contrario
    """
    # Si el status es 'out', es visible para todos los tipos de checkpoints
    if status == "out":
        return True

    # Si el status es 'outStart', solo es visible para checkpoints tipo start y finish
    if status == "outStart":
        return checkpoint_type == "start" or checkpoint_type == "finish"

    # Para cualquier otro status, siempre es visible
    return True


@https_fn.on_request()
def competitor_tracking(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene la lista de competidores con su checkpoint específico y el nombre de la ruta asociada.
    Retorna un JSON mapeable a la clase CompetitorTrackingWithRoute, filtrando competidores visibles
    según su status y el tipo de checkpoint.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Path Parameters:
    - eventId: ID del evento (requerido, viene en la URL)
    - dayOfRaceId: ID del día de carrera (requerido, viene en la URL)
    - checkpointId: ID del checkpoint para filtrar (requerido, viene en la URL)

    Query Parameters (alternativa):
    - eventId: ID del evento (si no viene en path)
    - dayOfRaceId: ID del día de carrera (si no viene en path)
    - checkpointId: ID del checkpoint (si no viene en path)

    Returns:
    - 200: Objeto CompetitorTrackingWithRoute en formato JSON
    - 400: Bad Request (sin respuesta JSON, solo código HTTP) - parámetros faltantes
    - 401: Unauthorized (sin respuesta JSON, solo código HTTP) - token inválido o faltante
    - 500: Internal Server Error (sin respuesta JSON, solo código HTTP)

    Nota: Consulta events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/
          y filtra competidores visibles según isCompetitorVisible.
          Los campos createdAt y updatedAt se generan en el momento de la consulta (DateTime.now()),
          no se usan los valores de Firestore.
    """
    # Validar CORS y método HTTP
    validation_response = validate_request(
        req, ["GET"], "competitor_tracking", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token (solo para autenticación)
        if not verify_bearer_token(req, "competitor_tracking"):
            logging.warning("competitor_tracking: Token inválido o faltante")
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Obtener parámetros de query parameters primero
        event_id = req.args.get("eventId")
        day_of_race_id = req.args.get("dayOfRaceId")
        checkpoint_id = req.args.get("checkpointId")

        # Si no vienen en query params, intentar extraerlos del path
        # La URL será: /api/checkpoint/competitor-tracking/{eventId}/{dayOfRaceId}/{checkpointId}
        if (
            not event_id
            or event_id.strip() == ""
            or not day_of_race_id
            or day_of_race_id.strip() == ""
            or not checkpoint_id
            or checkpoint_id.strip() == ""
        ):
            path = req.path
            logging.warning("competitor_tracking: Path recibido: %s", path)
            path_parts = [p for p in path.split("/") if p]  # Filtrar strings vacíos
            logging.warning("competitor_tracking: Path parts: %s", path_parts)

            try:
                # Buscar el patrón /competitor-tracking/{eventId}/{dayOfRaceId}/{checkpointId}
                if "competitor-tracking" in path_parts:
                    tracking_index = path_parts.index("competitor-tracking")
                    if tracking_index + 3 < len(path_parts):
                        if not event_id or event_id.strip() == "":
                            event_id = path_parts[tracking_index + 1]
                        if not day_of_race_id or day_of_race_id.strip() == "":
                            day_of_race_id = path_parts[tracking_index + 2]
                        if not checkpoint_id or checkpoint_id.strip() == "":
                            checkpoint_id = path_parts[tracking_index + 3]
                        logging.warning(
                            "competitor_tracking: Parámetros extraídos - eventId: %s, dayOfRaceId: %s, checkpointId: %s",
                            event_id,
                            day_of_race_id,
                            checkpoint_id,
                        )
            except (ValueError, IndexError) as e:
                logging.warning(
                    "competitor_tracking: Error extrayendo parámetros del path: %s",
                    e,
                )

        # Validar que todos los parámetros estén presentes
        if not event_id or event_id.strip() == "":
            logging.warning("competitor_tracking: eventId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        if not day_of_race_id or day_of_race_id.strip() == "":
            logging.warning("competitor_tracking: dayOfRaceId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        if not checkpoint_id or checkpoint_id.strip() == "":
            logging.warning("competitor_tracking: checkpointId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Inicializar Firestore
        db = firestore.client()

        # Construir ruta base para tracking
        tracking_id = f"{event_id}_{day_of_race_id}"

        # 1. Obtener todos los competidores
        # events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors
        logging.warning(
            "competitor_tracking: Obteniendo competidores para eventId=%s, dayOfRaceId=%s, trackingId=%s",
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
            # Si no hay competidores, retornar lista vacía
            response_data = {
                "competitors": [],
                "routeName": None,
            }
            return https_fn.Response(
                json.dumps(response_data, ensure_ascii=False),
                status=200,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                },
            )

        # 2. Para cada competidor, obtener su checkpoint específico
        competitor_tracking_list: List[Dict[str, Any]] = []
        checkpoint_type: Optional[str] = None

        for competitor_doc in competitors_snapshot:
            try:
                competitor_data = competitor_doc.to_dict()
                if competitor_data is None:
                    continue

                competitor_id = competitor_doc.id

                # Construir ruta al checkpoint específico del competidor
                # events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/competitors/{competitorId}/checkpoints/{checkpointId}
                checkpoint_ref = (
                    db.collection(FirestoreCollections.EVENT_TRACKING)
                    .document(event_id)
                    .collection(FirestoreCollections.EVENT_TRACKING_COMPETITOR_TRACKING)
                    .document(tracking_id)
                    .collection(FirestoreCollections.EVENT_TRACKING_COMPETITOR)
                    .document(competitor_id)
                    .collection(FirestoreCollections.EVENT_TRACKING_CHECKPOINTS)
                    .document(checkpoint_id)
                )

                checkpoint_doc = checkpoint_ref.get()

                if not checkpoint_doc.exists:
                    # Si el checkpoint no existe para este competidor, omitirlo
                    continue

                checkpoint_data = checkpoint_doc.to_dict()
                if checkpoint_data is None:
                    continue

                # Guardar checkpointType del primer competidor (todos tienen el mismo tipo)
                if checkpoint_type is None:
                    checkpoint_type = checkpoint_data.get("checkpointType", "pass")

                # Generar createdAt y updatedAt en el momento de la consulta (DateTime.now())
                current_time = datetime.utcnow().isoformat() + "Z"

                # Construir objeto del competidor con su checkpoint
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
                    "createdAt": current_time,  # DateTime.now() - no de Firestore
                    "updatedAt": current_time,  # DateTime.now() - no de Firestore
                    "trackingCheckpoints": [
                        {
                            "id": checkpoint_id,
                            "name": checkpoint_data.get("name", ""),
                            "order": checkpoint_data.get("order", 0),
                            "checkpointType": checkpoint_data.get(
                                "checkpointType", "pass"
                            ),
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
                            "note": checkpoint_data.get("note"),
                        }
                    ],
                }

                competitor_tracking_list.append(competitor_tracking)

            except (ValueError, AttributeError, RuntimeError, TypeError) as e:
                logging.warning(
                    "competitor_tracking: Error procesando competidor %s: %s",
                    competitor_doc.id,
                    e,
                )
                continue

        # Si no hay competidores con checkpoint, retornar lista vacía
        if not competitor_tracking_list:
            response_data = {
                "competitors": [],
                "routeName": None,
            }
            return https_fn.Response(
                json.dumps(response_data, ensure_ascii=False),
                status=200,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                },
            )

        # 3. Obtener todas las rutas
        # events_tracking/{eventId}/competitor_tracking/{eventId}_{dayOfRaceId}/routes
        logging.warning(
            "competitor_tracking: Obteniendo rutas para eventId=%s, trackingId=%s",
            event_id,
            tracking_id,
        )
        routes_ref = (
            db.collection(FirestoreCollections.EVENT_TRACKING)
            .document(event_id)
            .collection(FirestoreCollections.EVENT_TRACKING_COMPETITOR_TRACKING)
            .document(tracking_id)
            .collection(FirestoreCollections.EVENT_ROUTES)
        )
        routes_snapshot = routes_ref.get()

        # 4. Buscar ruta que contiene checkpointId
        route_name: Optional[str] = None

        if routes_snapshot:
            for route_doc in routes_snapshot:
                try:
                    route_data = route_doc.to_dict()
                    if route_data is None:
                        continue

                    checkpoint_ids = route_data.get("checkpointIds")
                    if checkpoint_ids and isinstance(checkpoint_ids, list):
                        if checkpoint_id in checkpoint_ids:
                            route_name = route_data.get("name")
                            logging.warning(
                                "competitor_tracking: Ruta encontrada: %s", route_name
                            )
                            break
                except (ValueError, AttributeError, RuntimeError, TypeError) as e:
                    logging.warning(
                        "competitor_tracking: Error procesando ruta %s: %s",
                        route_doc.id,
                        e,
                    )
                    continue

        # 5. Filtrar competidores visibles usando isCompetitorVisible
        if checkpoint_type is None:
            # Si no hay checkpointType, usar el del primer competidor
            if competitor_tracking_list:
                first_checkpoint = competitor_tracking_list[0].get(
                    "trackingCheckpoints", []
                )
                if first_checkpoint and len(first_checkpoint) > 0:
                    checkpoint_type = first_checkpoint[0].get("checkpointType", "pass")

        visible_competitors: List[Dict[str, Any]] = []

        for competitor in competitor_tracking_list:
            try:
                status = competitor["trackingCheckpoints"][0].get(
                    "statusCompetitor", "none"
                )
                if is_competitor_visible(status, checkpoint_type):
                    visible_competitors.append(competitor)
            except (KeyError, IndexError, TypeError) as e:
                logging.warning(
                    "competitor_tracking: Error filtrando competidor %s: %s",
                    competitor.get("id", "unknown"),
                    e,
                )
                continue

        # 6. Construir respuesta final
        response_data = {
            "competitors": visible_competitors,
            "routeName": route_name,
        }

        # Retornar respuesta HTTP 200
        return https_fn.Response(
            json.dumps(response_data, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("competitor_tracking: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("competitor_tracking: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
