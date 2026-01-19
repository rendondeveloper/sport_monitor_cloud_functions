import json
import logging

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value


@https_fn.on_request()
def checkpoint(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene un checkpoint específico de un evento desde Firestore

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Path Parameters:
    - checkpointId: ID del checkpoint (requerido, viene en la URL)
    - eventId: ID del evento (requerido, viene en la URL)

    Query Parameters (alternativa):
    - checkpointId: ID del checkpoint (si no viene en path)
    - eventId: ID del evento (si no viene en path)

    Returns:
    - 200: Objeto Checkpoint completo en formato JSON
    - 400: Bad Request (sin respuesta JSON, solo código HTTP) - parámetros faltantes
    - 401: Unauthorized (sin respuesta JSON, solo código HTTP) - token inválido o faltante
    - 404: Not Found (sin respuesta JSON, solo código HTTP) - checkpoint no encontrado
    - 500: Internal Server Error (sin respuesta JSON, solo código HTTP)

    Nota: Consulta la subcolección events/{eventId}/checkpoints/{checkpointId}
    """
    # Validar CORS y método HTTP
    validation_response = validate_request(
        req, ["GET"], "get_checkpoint", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token (solo para autenticación)
        if not verify_bearer_token(req, "get_checkpoint"):
            logging.warning("get_checkpoint: Token inválido o faltante")
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Obtener checkpointId y eventId de query parameters primero
        checkpoint_id = req.args.get("checkpointId")
        event_id = req.args.get("eventId")

        # Si no vienen en query params, intentar extraerlos del path
        # La URL será: /api/checkpoint/{checkpointId}/event/{eventId}
        if not checkpoint_id or not event_id:
            path = req.path
            logging.info("get_checkpoint: Path recibido: %s", path)
            path_parts = [p for p in path.split("/") if p]  # Filtrar strings vacíos
            logging.info("get_checkpoint: Path parts: %s", path_parts)

            # Buscar el índice de "checkpoint" y tomar el siguiente elemento como checkpointId
            # Luego buscar "event" y tomar el siguiente como eventId
            try:
                if "checkpoint" in path_parts:
                    checkpoint_index = path_parts.index("checkpoint")
                    if checkpoint_index + 1 < len(path_parts) and not checkpoint_id:
                        checkpoint_id = path_parts[checkpoint_index + 1]
                        logging.info(
                            "get_checkpoint: checkpointId extraído del path: %s",
                            checkpoint_id,
                        )

                if "event" in path_parts:
                    event_index = path_parts.index("event")
                    if event_index + 1 < len(path_parts) and not event_id:
                        event_id = path_parts[event_index + 1]
                        logging.info(
                            "get_checkpoint: eventId extraído del path: %s", event_id
                        )
            except (ValueError, IndexError) as e:
                logging.warning(
                    "get_checkpoint: Error extrayendo parámetros del path: %s", e
                )

        # Validar que ambos parámetros estén presentes
        if not checkpoint_id or checkpoint_id.strip() == "":
            logging.warning("get_checkpoint: checkpointId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if not event_id or event_id.strip() == "":
            logging.warning("get_checkpoint: eventId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Inicializar Firestore
        db = firestore.client()

        # Construir ruta: events/{eventId}/checkpoints/{checkpointId}
        # Consultar el documento específico del checkpoint
        event_ref = db.collection(FirestoreCollections.EVENTS).document(event_id)
        checkpoint_ref = event_ref.collection(
            FirestoreCollections.EVENT_CHECKPOINTS
        ).document(checkpoint_id)

        # Obtener el documento
        checkpoint_doc = checkpoint_ref.get()

        if not checkpoint_doc.exists:
            logging.info(
                "get_checkpoint: Checkpoint %s no encontrado para evento %s",
                checkpoint_id,
                event_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Obtener los datos del documento
        checkpoint_data = checkpoint_doc.to_dict()

        if checkpoint_data is None:
            logging.warning(
                "get_checkpoint: Datos vacíos para checkpoint %s del evento %s",
                checkpoint_id,
                event_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Construir respuesta con el checkpoint
        checkpoint_response = {
            "id": checkpoint_doc.id,
        }

        # Copiar todos los campos del documento, convirtiendo valores
        for key, value in checkpoint_data.items():
            checkpoint_response[key] = convert_firestore_value(value)

        # Retornar respuesta HTTP 200 con el objeto Checkpoint completo
        return https_fn.Response(
            json.dumps(checkpoint_response, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("get_checkpoint: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("get_checkpoint: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
