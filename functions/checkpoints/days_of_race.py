import json
import logging
from typing import Any, Dict, List

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value


@https_fn.on_request()
def days_of_race(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene todos los días de carrera de un evento específico desde Firestore.
    Retorna un array directo de días de carrera mapeable a List<DayOfRaces>.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Path Parameters:
    - eventId: ID del evento (requerido, viene en la URL)

    Query Parameters (alternativa):
    - eventId: ID del evento (si no viene en path)

    Returns:
    - 200: Array de objetos DayOfRace en formato JSON (array directo)
    - 400: Bad Request (sin respuesta JSON, solo código HTTP) - eventId faltante
    - 401: Unauthorized (sin respuesta JSON, solo código HTTP) - token inválido o faltante
    - 500: Internal Server Error (sin respuesta JSON, solo código HTTP)

    Nota: Consulta la subcolección events/{eventId}/dayOfRaces sin filtros.
          Retorna todos los días de carrera, activos e inactivos.
    """
    # Validar CORS y método HTTP
    validation_response = validate_request(
        req, ["GET"], "days_of_race", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token (solo para autenticación)
        if not verify_bearer_token(req, "days_of_race"):
            logging.warning("days_of_race: Token inválido o faltante")
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Obtener eventId de query parameters primero
        event_id = req.args.get("eventId")

        # Si no viene en query params, intentar extraerlo del path
        # La URL será: /api/days-of-race/{eventId}
        if not event_id or event_id.strip() == "":
            path = req.path
            logging.info("days_of_race: Path recibido: %s", path)
            path_parts = [p for p in path.split("/") if p]  # Filtrar strings vacíos
            logging.info("days_of_race: Path parts: %s", path_parts)

            try:
                # Buscar el índice de "days-of-race" y tomar el siguiente elemento como eventId
                if "days-of-race" in path_parts:
                    days_index = path_parts.index("days-of-race")
                    if days_index + 1 < len(path_parts) and not event_id:
                        event_id = path_parts[days_index + 1]
                        logging.info(
                            "days_of_race: eventId extraído del path: %s", event_id
                        )
            except (ValueError, IndexError) as e:
                logging.warning(
                    "days_of_race: Error extrayendo parámetros del path: %s", e
                )

        # Validar que eventId esté presente
        if not event_id or event_id.strip() == "":
            logging.warning("days_of_race: eventId faltante o vacío")
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
        days_of_race_ref = event_ref.collection(FirestoreCollections.DAY_OF_RACES)

        # Obtener todos los documentos sin filtros
        logging.info(
            "days_of_race: Obteniendo días de carrera para evento %s", event_id
        )
        days_of_race_snapshot = days_of_race_ref.get()

        # Mapear documentos a DayOfRaces
        days_of_race_list: List[Dict[str, Any]] = []

        for day_doc in days_of_race_snapshot:
            try:
                day_data = day_doc.to_dict()
                if day_data is None:
                    continue

                # Construir objeto DayOfRace
                day_of_race = {
                    "id": day_doc.id,
                }

                # Copiar todos los campos del documento, convirtiendo valores
                for key, value in day_data.items():
                    day_of_race[key] = convert_firestore_value(value)

                days_of_race_list.append(day_of_race)

            except (ValueError, AttributeError, RuntimeError, TypeError) as e:
                logging.warning(
                    "days_of_race: Error procesando día de carrera %s: %s",
                    day_doc.id,
                    e,
                )
                continue

        # Retornar respuesta HTTP 200 con array directo (sin wrapper)
        # Esto facilita el mapeo a List<DayOfRaces> en Flutter
        return https_fn.Response(
            json.dumps(days_of_race_list, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("days_of_race: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("days_of_race: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
