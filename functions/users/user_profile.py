import json
import logging
from datetime import datetime
from typing import Any

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request


@https_fn.on_request()
def user_profile(req: https_fn.Request) -> https_fn.Response:
    """
    Obtiene el perfil completo de un usuario desde Firestore

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)

    Query Parameters:
    - userId: authUserId del usuario (ID de autenticación de Firebase) (requerido)
             NOTA: Este parámetro se llama "userId" pero es el authUserId, no el ID del documento

    Returns:
    - 200: Objeto UserProfile completo en formato JSON (mapeando TODOS los campos)
    - 400: Bad Request (sin respuesta JSON, solo código HTTP) - authUserId faltante
    - 401: Unauthorized (sin respuesta JSON, solo código HTTP) - token inválido o faltante
    - 404: Not Found (sin respuesta JSON, solo código HTTP) - usuario no encontrado
    - 500: Internal Server Error (sin respuesta JSON, solo código HTTP)

    Nota: La búsqueda se realiza por el campo 'authUserId' en la colección, no por el ID del documento.
    """
    # Validar CORS y método HTTP
    validation_response = validate_request(
        req, ["GET"], "user_profile", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token (solo para autenticación)
        if not verify_bearer_token(req, "user_profile"):
            logging.warning("user_profile: Token inválido o faltante")
            return https_fn.Response(
                "",
                status=401,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Obtener authUserId de query parameters (el parámetro se llama userId pero es el authUserId)
        auth_user_id = req.args.get("userId")

        # Validar que authUserId esté presente
        if not auth_user_id or auth_user_id.strip() == "":
            logging.warning("user_profile: authUserId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Inicializar Firestore
        db = firestore.client()

        # Buscar usuario por authUserId usando query (no por ID del documento)
        users_query = (
            db.collection(FirestoreCollections.USERS)
            .where("authUserId", "==", auth_user_id)
            .limit(1)
        )
        query_snapshot = users_query.get()

        if not query_snapshot or len(query_snapshot) == 0:
            logging.info(
                "user_profile: Usuario no encontrado con authUserId: %s", auth_user_id
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Obtener el primer documento del resultado
        user_doc = query_snapshot[0]
        user_data = user_doc.to_dict()

        if user_data is None:
            logging.warning(
                "user_profile: Datos vacíos para usuario con authUserId %s (docId: %s)",
                auth_user_id,
                user_doc.id,
            )
            return https_fn.Response(
                "",
                status=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Log temporal para debug - ver estructura real de los datos
        logging.info(
            "user_profile: Estructura de datos del usuario %s: %s",
            user_doc.id,
            json.dumps(user_data, default=str, ensure_ascii=False),
        )

        # Obtener eventos asignados
        assigned_events = []
        event_staff_relations = user_data.get("eventStaffRelations", [])

        if event_staff_relations:
            for relation in event_staff_relations:
                event_id = relation.get("eventId")
                checkpoint_ids = relation.get("checkpointIds", [])

                if not event_id:
                    continue

                try:
                    # Obtener evento
                    event_ref = db.collection(FirestoreCollections.EVENTS).document(
                        event_id
                    )
                    event_doc = event_ref.get()

                    if not event_doc.exists:
                        logging.warning(
                            "user_profile: Evento %s no encontrado", event_id
                        )
                        continue

                    event_data = event_doc.to_dict()
                    if event_data is None:
                        continue

                    # Construir objeto de evento
                    event_obj = {
                        "id": event_id,
                        "name": event_data.get("name"),
                        "rallySystemId": event_data.get("rallySystemId"),
                        "status": event_data.get("status"),
                        # Incluir todos los campos del evento
                    }

                    # Copiar todos los campos del evento
                    for key, value in event_data.items():
                        if key not in event_obj:
                            event_obj[key] = value

                    # Obtener checkpoints si hay checkpointIds
                    checkpoints = []
                    if checkpoint_ids:
                        try:
                            checkpoints_ref = event_ref.collection(
                                FirestoreCollections.EVENT_CHECKPOINTS
                            )
                            checkpoints_docs = checkpoints_ref.get()

                            # Filtrar checkpoints por checkpointIds
                            for cp_doc in checkpoints_docs:
                                if cp_doc.id in checkpoint_ids:
                                    cp_data = cp_doc.to_dict()
                                    if cp_data:
                                        checkpoint_obj = {
                                            "id": cp_doc.id,
                                            "name": cp_data.get("name"),
                                            "type": cp_data.get("type"),
                                            "status": cp_data.get("status"),
                                        }
                                        # Copiar todos los campos del checkpoint
                                        for key, value in cp_data.items():
                                            if key not in checkpoint_obj:
                                                checkpoint_obj[key] = value
                                        checkpoints.append(checkpoint_obj)
                        except (ValueError, AttributeError, RuntimeError) as e:
                            logging.warning(
                                "user_profile: Error obteniendo checkpoints para evento %s: %s",
                                event_id,
                                e,
                            )

                    event_obj["checkpoints"] = checkpoints
                    assigned_events.append(event_obj)

                except (ValueError, AttributeError, RuntimeError) as e:
                    logging.warning(
                        "user_profile: Error procesando evento %s: %s", event_id, e
                    )
                    continue

        # Función helper para convertir valores de Firestore a JSON serializable
        def convert_firestore_value(value: Any) -> Any:
            """Convierte valores de Firestore a tipos JSON serializables"""
            if value is None:
                return None
            # Timestamp de Firestore (verificar por tipo o método)
            if hasattr(value, "timestamp") and hasattr(value, "to_datetime"):
                # Es un Timestamp de Firestore
                dt = value.to_datetime()
                return dt.isoformat() + "Z" if dt.tzinfo is None else dt.isoformat()
            # datetime de Python
            if isinstance(value, datetime):
                return (
                    value.isoformat() + "Z"
                    if value.tzinfo is None
                    else value.isoformat()
                )
            # dict - recursivo
            if isinstance(value, dict):
                return {k: convert_firestore_value(v) for k, v in value.items()}
            # list - recursivo
            if isinstance(value, list):
                return [convert_firestore_value(item) for item in value]
            # Otros tipos (str, int, float, bool) se retornan tal cual
            return value

        # Construir UserProfile - copiar todos los campos del documento primero
        user_profile_data = {
            "id": user_doc.id,
        }

        # Copiar todos los campos del documento directamente, convirtiendo valores
        for key, value in user_data.items():
            user_profile_data[key] = convert_firestore_value(value)

        # Asegurar que los campos anidados estén bien estructurados
        # Si personalData existe pero es None, inicializarlo como dict vacío
        if (
            "personalData" in user_profile_data
            and user_profile_data["personalData"] is None
        ):
            user_profile_data["personalData"] = {}
        elif "personalData" not in user_profile_data:
            user_profile_data["personalData"] = {}

        # Si emergencyContact existe pero es None, inicializarlo como dict vacío
        if (
            "emergencyContact" in user_profile_data
            and user_profile_data["emergencyContact"] is None
        ):
            user_profile_data["emergencyContact"] = {}
        elif "emergencyContact" not in user_profile_data:
            user_profile_data["emergencyContact"] = {}

        # Si userData existe pero es None, inicializarlo como dict vacío
        if "userData" in user_profile_data and user_profile_data["userData"] is None:
            user_profile_data["userData"] = {}
        elif "userData" not in user_profile_data:
            user_profile_data["userData"] = {}

        # Asegurar que appVersion tenga un valor por defecto si no existe
        if (
            "appVersion" not in user_profile_data
            or user_profile_data.get("appVersion") is None
        ):
            user_data_obj = user_profile_data.get("userData", {})
            if isinstance(user_data_obj, dict):
                user_profile_data["appVersion"] = user_data_obj.get(
                    "appVersion", "2.0.0"
                )
            else:
                user_profile_data["appVersion"] = "2.0.0"

        # Actualizar con eventos asignados
        user_profile_data["assignedEvents"] = assigned_events

        # Retornar respuesta HTTP 200 con el objeto UserProfile completo
        return https_fn.Response(
            json.dumps(user_profile_data, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("user_profile: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("user_profile: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
