import json
import logging

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.firestore_helper import FirestoreHelper
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value


def _build_name_type(checkpoint_type_data: dict) -> str:
    """
    Construye nameType con:
    - Si abbreviation existe y es string no vacío: "{abbreviation} - {name}"
    - Si abbreviation es null: "{name}"
    """
    if not isinstance(checkpoint_type_data, dict):
        return ""

    abbreviation = checkpoint_type_data.get("abbreviation")
    name = checkpoint_type_data.get("name") or ""

    if isinstance(abbreviation, str) and abbreviation.strip():
        return f"{abbreviation.strip()} - {name}"
    return name


def _get_checkpoint_name_type(
    db: firestore.Client,
    checkpoint_type_id: str,
    cache: dict,
) -> str:
    """Resuelve el nameType por checkpointTypeId (con cache en memoria)."""
    if not checkpoint_type_id:
        return ""

    if checkpoint_type_id in cache:
        return cache[checkpoint_type_id]

    checkpoint_type_doc = (
        db.collection(FirestoreCollections.CATALOGS)
        .document(FirestoreCollections.CATALOGS_DEFAULT_DOC_ID)
        .collection(FirestoreCollections.CATALOGS_CHECKPOINT_TYPES)
        .document(checkpoint_type_id)
        .get()
    )

    if not checkpoint_type_doc.exists:
        cache[checkpoint_type_id] = checkpoint_type_id
        return cache[checkpoint_type_id]

    data = checkpoint_type_doc.to_dict() or {}
    cache[checkpoint_type_id] = _build_name_type(data)
    return cache[checkpoint_type_id]


def _map_checkpoint(
    checkpoint_doc,
    db: firestore.Client,
    checkpoint_type_cache: dict,
) -> dict:
    checkpoint_data = checkpoint_doc.to_dict() or {}
    checkpoint_type_id = checkpoint_data.get("checkpointTypeId")

    return {
        "nameType": _get_checkpoint_name_type(
            db=db,
            checkpoint_type_id=checkpoint_type_id,
            cache=checkpoint_type_cache,
        ),
        "checkpointTypeId": checkpoint_type_id,
        "coordinates": convert_firestore_value(checkpoint_data.get("coordinates")),
        "iconCustom": convert_firestore_value(checkpoint_data.get("iconCustom")),
        "name": checkpoint_data.get("name"),
        "order": checkpoint_data.get("order", 0),
    }


@https_fn.on_request()
def event_detail(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene el detalle de un evento desde Firestore

    Query Parameters:
    - eventId: ID del evento (requerido)
    - userId: ID del usuario autenticado (opcional) — determina isEnrolled

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
        # Obtener parámetros de query string
        event_id = req.args.get("eventId")
        user_id = req.args.get("userId", "").strip() or None

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
        helper = FirestoreHelper()

        # Validar que el userId existe en Firestore; si no, ignorar inscripción
        if user_id:
            user_doc = helper.get_document(FirestoreCollections.USERS, user_id)
            if user_doc is None:
                user_id = None

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

        # Verificar inscripción del usuario en el evento
        if user_id:
            participant_ref = (
                db.collection(FirestoreCollections.EVENTS)
                .document(event_id)
                .collection(FirestoreCollections.EVENT_PARTICIPANTS)
                .document(user_id)
            )
            event_info["isEnrolled"] = participant_ref.get().exists
        else:
            event_info["isEnrolled"] = None

        # Contar participantes registrados en el evento
        participants_ref = (
            db.collection(FirestoreCollections.EVENTS)
            .document(event_id)
            .collection(FirestoreCollections.EVENT_PARTICIPANTS)
        )
        participants_docs = participants_ref.select([]).get()
        event_info["registeredCount"] = len(participants_docs)

        # Buscar rutas visibles para pilotos (puede haber múltiples)
        visible_routes = (
            db.collection(FirestoreCollections.EVENTS)
            .document(event_id)
            .collection(FirestoreCollections.EVENT_ROUTES)
            .where("visibleForPilots", "==", True)
            .get()
        )
        if visible_routes:
            checkpoint_type_cache: dict[str, str] = {}
            routes_list = []
            for r in visible_routes:
                rd = r.to_dict() or {}
                ts = rd.get("updatedAt")
                route_id = getattr(r, "id", None)

                checkpoints_docs = []
                if route_id:
                    checkpoints_ref = (
                        db.collection(FirestoreCollections.EVENTS)
                        .document(event_id)
                        .collection(FirestoreCollections.EVENT_ROUTES)
                        .document(route_id)
                        .collection(FirestoreCollections.EVENT_CHECKPOINTS)
                    )
                    checkpoints_docs = checkpoints_ref.get() or []

                # Asegura orden estable por `order` sin depender del orden de Firestore.
                def _cp_order(cp_doc):
                    cp_data = cp_doc.to_dict() or {}
                    return cp_data.get("order", 0) or 0

                checkpoints_docs = sorted(checkpoints_docs, key=_cp_order)

                checkpoints_list = [
                    _map_checkpoint(
                        checkpoint_doc=cp_doc,
                        db=db,
                        checkpoint_type_cache=checkpoint_type_cache,
                    )
                    for cp_doc in checkpoints_docs
                ]

                routes_list.append(
                    {
                        "name": rd.get("name", ""),
                        "routeUrl": rd.get("routeUrl"),
                        "colorTrack": rd.get("colorTrack"),
                        "updatedAt": ts.isoformat() if hasattr(ts, "isoformat") else None,
                        "checkpoints": checkpoints_list,
                    }
                )

            event_info["routes"] = routes_list
        # Si no hay rutas visibles, NO se añade "routes" al response

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
