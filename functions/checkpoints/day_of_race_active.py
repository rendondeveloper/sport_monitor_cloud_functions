import json
import logging

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value


@https_fn.on_request()
def day_of_race_active(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene el día de carrera activo para un evento desde Firestore

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Path Parameters:
    - eventId: ID del evento (requerido, viene en la URL)

    Returns:
    - 200: Objeto DayOfRace activo en formato JSON con campos: id, createdAt, updatedAt, day, isActivate
    - 400: Bad Request (sin respuesta JSON, solo código HTTP) - eventId faltante
    - 401: Unauthorized (sin respuesta JSON, solo código HTTP) - token inválido o faltante
    - 404: Not Found (sin respuesta JSON, solo código HTTP) - día de carrera activo no encontrado
    - 500: Internal Server Error (sin respuesta JSON, solo código HTTP)

    Nota: Consulta la subcolección events/{eventId}/dayOfRaces filtrando por isActivate: true
    """
    # Validar CORS y método HTTP
    validation_response = validate_request(
        req, ["GET"], "day_of_race_active", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token (solo para autenticación)
        if not verify_bearer_token(req, "day_of_race_active"):
            logging.warning("day_of_race_active: Token inválido o faltante")
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Obtener eventId del path o query parameters
        # La URL será: /api/checkpoint/dayofrace/active/{eventId}
        # O también puede venir como query parameter: ?eventId=xxx
        event_id = req.args.get("eventId")

        # Si no viene en query params, intentar extraerlo del path
        if not event_id or event_id.strip() == "":
            path = req.path
            logging.info("day_of_race_active: Path recibido: %s", path)
            path_parts = [p for p in path.split("/") if p]  # Filtrar strings vacíos
            logging.info("day_of_race_active: Path parts: %s", path_parts)

            # Buscar el índice de "active" y tomar el siguiente elemento como eventId
            try:
                active_index = path_parts.index("active")
                if active_index + 1 < len(path_parts):
                    event_id = path_parts[active_index + 1]
                    logging.info(
                        "day_of_race_active: eventId extraído del path: %s", event_id
                    )
            except ValueError:
                # Si no se encuentra "active" en el path, event_id seguirá siendo None
                logging.warning(
                    "day_of_race_active: No se encontró 'active' en el path"
                )
                pass

        # Validar que eventId esté presente
        if not event_id or event_id.strip() == "":
            logging.warning("day_of_race_active: eventId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Inicializar Firestore
        db = firestore.client()

        # Construir ruta: events/{eventId}/dayOfRaces
        # Consultar la subcolección dayOfRaces dentro del documento del evento
        event_ref = db.collection(FirestoreCollections.EVENTS).document(event_id)
        day_of_races_ref = event_ref.collection(FirestoreCollections.DAY_OF_RACES)

        # Filtrar documentos donde isActivate sea true
        # Obtener el primer documento que cumpla la condición
        query = day_of_races_ref.where("isActivate", "==", True).limit(1)
        query_snapshot = query.get()

        if not query_snapshot or len(query_snapshot) == 0:
            logging.info(
                "day_of_race_active: No se encontró día de carrera activo para evento %s",
                event_id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Obtener el primer documento del resultado
        day_of_race_doc = query_snapshot[0]
        day_of_race_data = day_of_race_doc.to_dict()

        if day_of_race_data is None:
            logging.warning(
                "day_of_race_active: Datos vacíos para día de carrera del evento %s (docId: %s)",
                event_id,
                day_of_race_doc.id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Construir respuesta con los campos requeridos
        day_of_race_response = {
            "id": day_of_race_doc.id,
        }

        # Copiar todos los campos del documento, convirtiendo valores
        for key, value in day_of_race_data.items():
            day_of_race_response[key] = convert_firestore_value(value)

        # Asegurar que los campos requeridos estén presentes
        # id ya está incluido arriba
        # createdAt, updatedAt, day, isActivate deben venir del documento

        # Retornar respuesta HTTP 200 con el objeto DayOfRace activo
        return https_fn.Response(
            json.dumps(day_of_race_response, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("day_of_race_active: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("day_of_race_active: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
