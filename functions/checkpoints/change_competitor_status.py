import json
import logging
from datetime import datetime
from typing import Any, Dict

from firebase_admin import firestore
from firebase_functions import https_fn
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request

# Constantes
OUT_STATUSES = ["out", "outStart", "outLast"]
VALID_STATUSES = [
    "none",
    "noneStart",
    "noneLast",
    "check",
    "checkStart",
    "checkLast",
    "out",
    "outStart",
    "outLast",
]


@https_fn.on_request()
def change_competitor_status(req: https_fn.Request) -> https_fn.Response:
    """
    Cambia el estado de un competidor y actualiza todos sus checkpoints relacionados.

    Headers:
    - Authorization: Bearer {Firebase Auth Token} (requerido)
    - Content-Type: application/json (requerido)

    Request Body:
    {
        "eventId": "string (requerido)",
        "dayOfRaceId": "string (requerido)",
        "checkpointId": "string (requerido)",
        "orderCheckpoint": "integer (requerido)",
        "competitorId": "string (requerido)",
        "status": "string (requerido)",
        "lastStatusCompetitor": "string (requerido)",
        "checkpointName": "string (requerido)",
        "note": "string (opcional)"
    }

    Returns:
    - 200: {"success": True} - Operación exitosa
    - 400: Bad Request - parámetros faltantes o inválidos
    - 401: Unauthorized - token inválido o faltante
    - 404: Not Found - competidor o checkpoint no encontrado
    - 500: Internal Server Error

    Nota: Esta función consolida tres operaciones:
          1. Actualiza el checkpoint específico
          2. Limpia checkpoints superiores si el status anterior era 'out'
          3. Actualiza checkpoints superiores si el nuevo status es 'out'
    """
    # Validar CORS y método HTTP
    validation_response = validate_request(
        req, ["PUT"], "change_competitor_status", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        # Validar Bearer token
        if not verify_bearer_token(req, "change_competitor_status"):
            logging.warning("change_competitor_status: Token inválido o faltante")
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

        # Parsear request body
        try:
            request_data = req.get_json(silent=True)
            if request_data is None:
                logging.warning(
                    "change_competitor_status: Request body inválido o faltante"
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
            logging.warning("change_competitor_status: Error parseando JSON: %s", e)
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

        # Validar parámetros requeridos
        required_params = [
            "eventId",
            "dayOfRaceId",
            "checkpointId",
            "orderCheckpoint",
            "competitorId",
            "status",
            "lastStatusCompetitor",
            "checkpointName",
        ]

        missing_params = [
            param for param in required_params if param not in request_data
        ]
        if missing_params:
            logging.warning(
                "change_competitor_status: Parámetros faltantes: %s", missing_params
            )
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": f"Faltan los siguientes parámetros: {', '.join(missing_params)}",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # Extraer y validar parámetros
        event_id = request_data.get("eventId", "").strip()
        day_of_race_id = request_data.get("dayOfRaceId", "").strip()
        checkpoint_id = request_data.get("checkpointId", "").strip()
        competitor_id = request_data.get("competitorId", "").strip()
        status = request_data.get("status", "").strip()
        last_status = request_data.get("lastStatusCompetitor", "").strip()
        checkpoint_name = request_data.get("checkpointName", "").strip()
        note = request_data.get("note")

        # Validar que los parámetros no estén vacíos
        if not all(
            [
                event_id,
                day_of_race_id,
                checkpoint_id,
                competitor_id,
                status,
                last_status,
                checkpoint_name,
            ]
        ):
            logging.warning("change_competitor_status: Parámetros vacíos")
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": "Los parámetros requeridos no pueden estar vacíos",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # Validar orderCheckpoint
        try:
            order_checkpoint = int(request_data.get("orderCheckpoint"))
            if order_checkpoint < 0:
                raise ValueError("orderCheckpoint debe ser un número positivo")
        except (ValueError, TypeError) as e:
            logging.warning("change_competitor_status: orderCheckpoint inválido: %s", e)
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": "El campo 'orderCheckpoint' debe ser un número entero positivo",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # Validar valores de status
        if status not in VALID_STATUSES:
            logging.warning("change_competitor_status: Status inválido: %s", status)
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": f"El campo 'status' debe ser uno de: {', '.join(VALID_STATUSES)}",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        if last_status not in VALID_STATUSES:
            logging.warning(
                "change_competitor_status: lastStatusCompetitor inválido: %s",
                last_status,
            )
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": f"El campo 'lastStatusCompetitor' debe ser uno de: {', '.join(VALID_STATUSES)}",
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

        # Construir referencias
        competitor_ref = (
            db.collection(FirestoreCollections.EVENT_TRACKING)
            .document(event_id)
            .collection(FirestoreCollections.EVENT_TRACKING_COMPETITOR_TRACKING)
            .document(tracking_id)
            .collection(FirestoreCollections.EVENT_TRACKING_COMPETITOR)
            .document(competitor_id)
        )

        checkpoints_ref = competitor_ref.collection(
            FirestoreCollections.EVENT_TRACKING_CHECKPOINTS
        )
        checkpoint_ref = checkpoints_ref.document(checkpoint_id)

        # Verificar que el competidor existe
        competitor_doc = competitor_ref.get()
        if not competitor_doc.exists:
            logging.warning(
                "change_competitor_status: Competidor no encontrado: %s", competitor_id
            )
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Not Found",
                        "error": f"Competidor con ID '{competitor_id}' no encontrado",
                    },
                    ensure_ascii=False,
                ),
                status=404,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # Verificar que el checkpoint existe
        checkpoint_doc = checkpoint_ref.get()
        if not checkpoint_doc.exists:
            logging.warning(
                "change_competitor_status: Checkpoint no encontrado: %s", checkpoint_id
            )
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Not Found",
                        "error": f"Checkpoint con ID '{checkpoint_id}' no encontrado",
                    },
                    ensure_ascii=False,
                ),
                status=404,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # Verificar que el order coincide
        checkpoint_data = checkpoint_doc.to_dict()
        checkpoint_order = checkpoint_data.get("order") if checkpoint_data else None
        if checkpoint_order is not None and checkpoint_order != order_checkpoint:
            logging.warning(
                "change_competitor_status: Order no coincide - esperado: %s, recibido: %s",
                checkpoint_order,
                order_checkpoint,
            )
            return https_fn.Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Bad Request",
                        "error": f"El order del checkpoint ({checkpoint_order}) no coincide con el proporcionado ({order_checkpoint})",
                    },
                    ensure_ascii=False,
                ),
                status=400,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # ============================================
        # PASO 1: Actualizar checkpoint específico
        # ============================================
        now = datetime.utcnow()
        update_data: Dict[str, Any] = {
            "statusCompetitor": status,
            "passTime": now,
            "updatedAt": now,
        }

        # Manejar checkpointDisable según el status
        if status in OUT_STATUSES:
            update_data["checkpointDisable"] = checkpoint_id
            update_data["checkpointDisableName"] = checkpoint_name
        else:
            update_data["checkpointDisable"] = None
            update_data["checkpointDisableName"] = None

        # Agregar note si está presente
        if note is not None:
            update_data["note"] = note

        logging.info(
            "change_competitor_status: Actualizando checkpoint %s con datos: %s",
            checkpoint_id,
            update_data,
        )
        checkpoint_ref.update(update_data)

        # ============================================
        # PASO 2: Limpiar checkpoints superiores (si el status anterior era 'out')
        # ============================================
        if last_status in OUT_STATUSES:
            try:
                logging.info(
                    "change_competitor_status: Limpiando checkpoints superiores (order > %s)",
                    order_checkpoint,
                )
                # Obtener todos los checkpoints
                all_checkpoints = checkpoints_ref.stream()

                # Filtrar y actualizar checkpoints con order superior
                checkpoints_cleared = 0
                for cp_doc in all_checkpoints:
                    cp_data = cp_doc.to_dict()
                    if cp_data is None:
                        continue

                    cp_order = cp_data.get("order")
                    if cp_order is not None and cp_order > order_checkpoint:
                        clear_data = {
                            "statusCompetitor": "none",
                            "checkpointDisable": None,
                            "checkpointDisableName": None,
                            "updatedAt": now,
                        }
                        checkpoints_ref.document(cp_doc.id).update(clear_data)
                        checkpoints_cleared += 1

                logging.info(
                    "change_competitor_status: %d checkpoints superiores limpiados",
                    checkpoints_cleared,
                )
            except Exception as e:
                # Log error pero continuar (el checkpoint específico ya se actualizó)
                logging.error(
                    "change_competitor_status: Error limpiando checkpoints superiores: %s",
                    e,
                    exc_info=True,
                )

        # ============================================
        # PASO 3: Actualizar todos los checkpoints superiores (si el nuevo status es 'out')
        # ============================================
        if status in OUT_STATUSES:
            try:
                logging.info(
                    "change_competitor_status: Actualizando checkpoints superiores (order > %s) a status '%s'",
                    order_checkpoint,
                    status,
                )
                # Obtener todos los checkpoints
                all_checkpoints = checkpoints_ref.stream()

                # Filtrar y actualizar checkpoints con order superior
                checkpoints_updated = 0
                for cp_doc in all_checkpoints:
                    cp_data = cp_doc.to_dict()
                    if cp_data is None:
                        continue

                    cp_order = cp_data.get("order")
                    if cp_order is not None and cp_order > order_checkpoint:
                        update_all_data: Dict[str, Any] = {
                            "statusCompetitor": status,
                            "checkpointDisable": checkpoint_id,
                            "checkpointDisableName": checkpoint_name,
                            "updatedAt": now,
                        }
                        if note is not None:
                            update_all_data["note"] = note

                        checkpoints_ref.document(cp_doc.id).update(update_all_data)
                        checkpoints_updated += 1

                logging.info(
                    "change_competitor_status: %d checkpoints superiores actualizados",
                    checkpoints_updated,
                )
            except Exception as e:
                # Log error pero continuar (el checkpoint específico ya se actualizó)
                logging.error(
                    "change_competitor_status: Error actualizando checkpoints superiores: %s",
                    e,
                    exc_info=True,
                )

        # Retornar respuesta exitosa
        return https_fn.Response(
            json.dumps({"success": True}, ensure_ascii=False),
            status=200,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "PUT, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    except ValueError as e:
        logging.error("change_competitor_status: Error de validación: %s", e)
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
        logging.error("change_competitor_status: Error interno: %s", e, exc_info=True)
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
