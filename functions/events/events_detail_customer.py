import json
import logging

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http_verb import validate_request


@https_fn.on_request()
def event_detail(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene el detalle de un evento desde Firestore

    Query Parameters:
    - eventId: ID del evento (requerido)

    Returns:
    - 200: Objeto EventInfo completo en formato JSON (mapeando TODOS los campos)
    - 400: Bad Request (sin respuesta JSON, solo código HTTP)
    - 404: Not Found (sin respuesta JSON, solo código HTTP)
    - 500: Internal Server Error (sin respuesta JSON, solo código HTTP)
    """
    # Validar CORS y método HTTP
    validation_response = validate_request(
        req, ["GET"], "event_detail", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Obtener parámetro eventId de query string
        event_id = req.args.get("eventId")

        # Validar que eventId esté presente
        if not event_id or event_id.strip() == "":
            logging.warning("event_detail: eventId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Inicializar Firestore
        db = firestore.client()

        # Construir ruta: events/{eventId}/event_content
        # La subcolección event_content puede tener múltiples documentos
        # Según la tarea, necesitamos obtener el documento de event_content
        event_ref = db.collection(FirestoreCollections.EVENTS).document(event_id)
        event_content_ref = event_ref.collection(FirestoreCollections.EVENT_CONTENT)

        # Obtener todos los documentos de la subcolección event_content
        # Normalmente hay un solo documento, pero manejamos el caso de múltiples
        event_content_docs = event_content_ref.limit(1).get()

        # Si no hay documentos, retornar 404
        if not event_content_docs or len(event_content_docs) == 0:
            logging.info(
                f"event_detail: Evento {event_id} no encontrado en event_content"
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Obtener el primer documento (normalmente solo hay uno)
        event_content_doc = event_content_docs[0]
        event_data = event_content_doc.to_dict()

        if event_data is None:
            logging.warning(f"event_detail: Datos vacíos para evento {event_id}")
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Mapear todos los campos del modelo EventInfo
        # La tarea menciona: name, photoMain, startEvent, endEvent, address,
        # historia, photoUrls, descriptionShort, website, description, etc.
        # Mapeamos todos los campos que existan en el documento
        event_info = {}

        # Campos básicos
        if "name" in event_data:
            event_info["name"] = event_data["name"]
        if "descriptionShort" in event_data:
            event_info["descriptionShort"] = event_data["descriptionShort"]
        if "description" in event_data:
            event_info["description"] = event_data["description"]
        if "photoMain" in event_data:
            event_info["photoMain"] = event_data["photoMain"]
        if "startEvent" in event_data:
            event_info["startEvent"] = event_data["startEvent"]
        if "endEvent" in event_data:
            event_info["endEvent"] = event_data["endEvent"]
        if "address" in event_data:
            event_info["address"] = event_data["address"]
        if "historia" in event_data:
            event_info["historia"] = event_data["historia"]
        if "photoUrls" in event_data:
            event_info["photoUrls"] = event_data["photoUrls"]
        if "website" in event_data:
            event_info["website"] = event_data["website"]

        # Incluir cualquier otro campo que pueda existir en el documento
        # para asegurar que TODOS los campos se mapeen
        for key, value in event_data.items():
            if key not in event_info:
                event_info[key] = value

        # Retornar respuesta HTTP 200 con el objeto EventInfo completo
        return https_fn.Response(
            json.dumps(event_info, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error(f"event_detail: Error de validación: {str(e)}")
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        logging.error(f"event_detail: Error interno: {str(e)}", exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
