from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app, firestore
import json
import logging
from datetime import datetime
from models.event_document import EventDocument, EventStatus
from models.tracking_checkpoint import (
    TrackingCheckpoint,
    Checkpoint,
    CheckpointType,
    CheckpointStatus,
    Competitor,
)
from models.competitor_tracking_models import (
    CompetitorTrackingDocument,
    CompetitorTracking,
    TrackingChakpoints,
)

# For cost control, you can set the maximum number of containers that can be
# running at the same time. This helps mitigate the impact of unexpected
# traffic spikes by instead downgrading performance. This limit is a per-function
# limit. You can override the limit for each function using the max_instances
# parameter in the decorator, e.g. @https_fn.on_request(max_instances=5).
set_global_options(max_instances=10)

# Initialize Firebase Admin
initialize_app()


@https_fn.on_call()
def track_event_checkpoint(req: https_fn.CallableRequest) -> dict:
    """
    Función que recibe un eventId y un status.
    Si el status es 'inProgress', busca la colección en Firestore y crea
    una nueva colección llamada 'tracking_checkpoint'.
    """
    try:
        # Obtener datos de la petición callable
        data = req.data

        # Validar parámetros requeridos
        if not data or "eventId" not in data or "status" not in data:
            raise https_fn.HttpsError(
                code="invalid-argument",
                message="Se requieren los parámetros 'eventId' y 'status'",
            )

        event_id = data["eventId"]
        status = data["status"]
        day = data["day"]

        # Inicializar Firestore
        db = firestore.client()

        # Si el status es 'inProgress', crear la colección tracking_checkpoint
        if status == "inProgress":
            # Buscar la colección del evento
            event_ref = db.collection("events").document(event_id)
            event_doc = event_ref.get()

            if not event_doc.exists:
                raise https_fn.HttpsError(
                    code="not-found", message=f"Evento con ID {event_id} no encontrado"
                )

            # Mapear el documento del evento al modelo
            event_data = event_doc.to_dict()
            event = EventDocument.from_dict(event_data, event_id)

            # Verificar que el evento esté en estado válido para tracking
            if event.status not in [
                EventStatus.IN_PROGRESS,
                EventStatus.OPEN_REGISTRATION,
                EventStatus.CLOSED_REGISTRATION,
            ]:
                raise https_fn.HttpsError(
                    code="failed-precondition",
                    message=f"El evento {event.name} no está en un estado válido para tracking. Estado actual: {event.status.display_name}",
                )

            # Crear la colección tracking_checkpoint dentro del evento
            tracking_ref = event_ref.collection("tracking_checkpoint")

            # Crear checkpoints básicos para el evento
            basic_checkpoints = [
                Checkpoint(
                    event_id=event_id,
                    name="Inicio",
                    order=1,
                    type=CheckpointType.START,
                    status=CheckpointStatus.ACTIVE,
                ),
                Checkpoint(
                    event_id=event_id,
                    name="Meta",
                    order=2,
                    type=CheckpointType.FINISH,
                    status=CheckpointStatus.DRAFT,
                ),
            ]

            # Crear el tracking checkpoint con estructura simplificada
            tracking_checkpoint = TrackingCheckpoint(
                event_id=event_id,
                checkpoints=basic_checkpoints,
                competitors=[],  # Lista vacía inicialmente
                status="inProgress",
            )

            # Agregar el documento inicial
            tracking_ref.add(tracking_checkpoint.to_dict())

            return {
                "success": True,
                "message": f"Colección 'tracking_checkpoint' creada para el evento '{event.name}' ({event_id})",
                "event_id": event_id,
                "event_name": event.name,
                "event_status": event.status.value,
                "status": status,
                "tracking_data": {
                    "checkpoints_count": len(tracking_checkpoint.checkpoints),
                    "competitors_count": len(tracking_checkpoint.competitors),
                    "checkpoints": [
                        cp.to_dict() for cp in tracking_checkpoint.checkpoints
                    ],
                },
            }

        else:
            return {
                "success": True,
                "message": f"Status '{status}' recibido para el evento {event_id}. No se requiere acción adicional.",
                "event_id": event_id,
                "status": status,
            }

    except https_fn.HttpsError:
        # Re-lanzar errores de Firebase Functions
        raise
    except Exception as e:
        # Convertir otros errores a HttpsError
        raise https_fn.HttpsError(
            code="internal", message=f"Error interno del servidor: {str(e)}"
        )


@https_fn.on_call()
def track_competitors(req: https_fn.CallableRequest) -> dict:
    """
    Función que recibe eventId, dayId y status.
    Si el status es 'inProgress', toma los datos del evento y crea
    la estructura de tracking de competidores.
    """
    try:
        # Obtener datos de la petición callable
        data = req.data
        logging.info(f"track_competitors: Iniciando función con datos: {data}")

        # Validar parámetros requeridos
        if (
            not data
            or "eventId" not in data
            or "dayId" not in data
            or "status" not in data
        ):
            logging.error("track_competitors: Parámetros requeridos faltantes")
            raise https_fn.HttpsError(
                code="invalid-argument",
                message="Se requieren los parámetros 'eventId', 'dayId' y 'status'",
            )

        event_id = data["eventId"]
        day_id = data["dayId"]
        day_status = data["status"]
        day_name = data["dayName"]

        logging.info(
            f"track_competitors: Procesando evento {event_id}, día {day_id}, status {day_status}, nombre del día {day_name}"
        )

        # Inicializar Firestore
        db = firestore.client()

        # Buscar el evento
        logging.info(f"track_competitors: Buscando evento {event_id} en Firestore")
        event_ref = db.collection("events").document(event_id)
        event_doc = event_ref.get()

        if not event_doc.exists:
            logging.error(
                f"track_competitors: Evento {event_id} no encontrado en Firestore"
            )
            raise https_fn.HttpsError(
                code="not-found", message=f"Evento con ID {event_id} no encontrado"
            )

        logging.info(f"track_competitors: Evento {event_id} encontrado en Firestore")

        # Mapear el documento del evento al modelo
        event_data = event_doc.to_dict()
        event = EventDocument.from_dict(event_data, event_id)
        logging.info(
            f"track_competitors: Evento mapeado - Nombre: {event.name}, Estado: {event.status.value}"
        )

        # Validar: solo continuar si el evento está en progreso
        if event.status != EventStatus.IN_PROGRESS:
            logging.warning(
                f"track_competitors: Evento {event.name} no está en progreso. Estado actual: {event.status.display_name}"
            )
            return {
                "success": False,
                "message": f"El evento '{event.name}' no está en progreso (estado actual: {event.status.display_name}).",
                "event_id": event_id,
                "day_id": day_id,
                "event_status": event.status.value,
            }

        # Obtener checkpoints desde la subcolección events/{eventId}/checkpoints
        logging.info(
            f"track_competitors: Buscando checkpoints en events/{event_id}/checkpoints"
        )
        checkpoints_ref = db.collection(f"events/{event_id}/checkpoints")
        checkpoints_docs = checkpoints_ref.get()

        logging.info(
            f"track_competitors: Encontrados {len(checkpoints_docs)} checkpoints en la subcolección"
        )

        # Obtener participantes desde la subcolección events/{eventId}/participants
        logging.info(
            f"track_competitors: Buscando participantes en events/{event_id}/participants"
        )
        participants_ref = db.collection(f"events/{event_id}/participants")
        participants_docs = participants_ref.get()

        logging.info(
            f"track_competitors: Encontrados {len(participants_docs)} participantes en la subcolección"
        )

        # Crear lista de CompetitorTracking
        competitors_tracking = []
        logging.info(
            f"track_competitors: Creando {len(participants_docs)} CompetitorTracking"
        )

        for i, participant_doc in enumerate(participants_docs):
            participant_data = participant_doc.to_dict()

            # Extraer datos del participante usando la estructura del CompetitorDocument
            personal_data = participant_data.get("personalData", {})
            competition_category = participant_data.get("competitionCategory", {})

            # Crear tracking_chakpoints para este competidor
            tracking_chakpoints = []
            for checkpoint_doc in checkpoints_docs:
                checkpoint_data = checkpoint_doc.to_dict()

                # Crear TrackingChakpoints para cada checkpoint
                tracking_chakpoint = TrackingChakpoints(
                    id=checkpoint_doc.id,
                    name=checkpoint_data.get("name", "Checkpoint"),
                    status_competitor="",  # Estado inicial para el competidor
                    pass_time=datetime.utcnow(),  # Se actualizará cuando pase por el checkpoint
                )
                tracking_chakpoints.append(tracking_chakpoint)

            # Crear CompetitorTracking con datos del participante y sus checkpoints
            competitor_tracking = CompetitorTracking(
                id=participant_doc.id,
                name=personal_data.get("fullName", "Competidor"),
                order=i + 1,
                category=competition_category.get(
                    "registrationCategory", "Sin categoría"
                ),
                number=competition_category.get("pilotNumber", "Sin número"),
                tracking_chakpoints=tracking_chakpoints,
            )

            competitors_tracking.append(competitor_tracking)
            logging.debug(
                f"track_competitors: Competidor {i+1} creado: {competitor_tracking.name} (ID: {competitor_tracking.id}) con {len(tracking_chakpoints)} checkpoints"
            )

        logging.info(
            f"track_competitors: {len(competitors_tracking)} competidores procesados con {len(checkpoints_docs)} checkpoints cada uno"
        )

        # Crear el documento de tracking de competidores
        tracking_doc_id = f"{event_id}_{day_id}"
        logging.info(
            f"track_competitors: Creando CompetitorTrackingDocument con ID: {tracking_doc_id}"
        )

        tracking_doc = CompetitorTrackingDocument(
            id=tracking_doc_id,
            event_id=event_id,
            day_id=day_id,
            name=day_name,  # Usar el nombre del día obtenido de la lista de días
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            competitors_tracking=competitors_tracking,
            is_active=day_status,
        )

        logging.info(
            f"track_competitors: Documento creado - Nombre: {day_name}, Competidores: {len(competitors_tracking)}, Activo: {day_status}"
        )

        # Guardar en la colección competitor_tracking
        collection_path = f"events_tracking/{event_id}/competitor_tracking"
        logging.info(f"track_competitors: Guardando en colección: {collection_path}")

        competitor_tracking_ref = db.collection(collection_path).document(
            tracking_doc_id
        )
        competitor_tracking_ref.set(tracking_doc.to_dict())

        logging.info(f"track_competitors: Documento guardado exitosamente en Firestore")

        result = {
            "success": True,
            "message": f"Tracking de competidores creado para el evento '{event.name}' día {day_id}",
            "event_id": event_id,
            "day_id": day_id,
            "event_name": event.name,
            "competitors_count": len(competitors_tracking),
            "tracking_id": tracking_doc.id,
            "competitors": [ct.to_dict() for ct in competitors_tracking],
        }

        logging.info(
            f"track_competitors: Función completada exitosamente. Resultado: {result}"
        )
        return result

        # Nota: si se llegó aquí, ya se retornó con éxito o por estado inválido.

    except https_fn.HttpsError as e:
        # Re-lanzar errores de Firebase Functions
        logging.error(
            f"track_competitors: Error de Firebase Functions: {e.code} - {e.message}"
        )
        raise
    except Exception as e:
        # Convertir otros errores a HttpsError
        logging.error(f"track_competitors: Error interno: {str(e)}", exc_info=True)
        raise https_fn.HttpsError(
            code="internal", message=f"Error interno del servidor: {str(e)}"
        )


@https_fn.on_call()
def track_competitors_off(req: https_fn.CallableRequest) -> dict:
    """
    Función que recibe eventId y dayId.
    Busca el documento de tracking en events_tracking/{eventId}/competitor_tracking/{eventId_dayId}
    y cambia el valor de isActive a false.
    """
    try:
        data = req.data
        logging.info(f"track_competitors_off: Iniciando función con datos: {data}")

        if not data or "eventId" not in data or "dayId" not in data:
            logging.error("track_competitors_off: Parámetros requeridos faltantes")
            raise https_fn.HttpsError(
                code="invalid-argument",
                message="Se requieren los parámetros 'eventId' y 'dayId'",
            )

        event_id = data["eventId"]
        day_id = data["dayId"]

        logging.info(
            f"track_competitors_off: Procesando evento {event_id}, día {day_id}"
        )

        db = firestore.client()

        # Construir el ID del documento de tracking
        tracking_doc_id = f"{event_id}_{day_id}"
        collection_path = f"events_tracking/{event_id}/competitor_tracking"

        logging.info(
            f"track_competitors_off: Buscando documento {tracking_doc_id} en {collection_path}"
        )

        # Buscar el documento de tracking
        tracking_ref = db.collection(collection_path).document(tracking_doc_id)
        tracking_doc = tracking_ref.get()

        if not tracking_doc.exists:
            logging.error(
                f"track_competitors_off: Documento de tracking {tracking_doc_id} no encontrado"
            )
            raise https_fn.HttpsError(
                code="not-found",
                message=f"Documento de tracking con ID {tracking_doc_id} no encontrado",
            )

        logging.info(
            f"track_competitors_off: Documento de tracking {tracking_doc_id} encontrado"
        )

        # Obtener datos actuales del documento
        tracking_data = tracking_doc.to_dict()
        current_is_active = tracking_data.get("isActive", True)

        logging.info(
            f"track_competitors_off: Estado actual isActive: {current_is_active}"
        )

        # Actualizar el documento con isActive = false
        tracking_ref.update(
            {"isActive": False, "updatedAt": datetime.utcnow().isoformat()}
        )

        logging.info(
            f"track_competitors_off: Documento actualizado exitosamente. isActive cambiado a False"
        )

        result = {
            "success": True,
            "message": f"Tracking de competidores desactivado para el evento {event_id} día {day_id}",
            "event_id": event_id,
            "day_id": day_id,
            "tracking_id": tracking_doc_id,
            "is_active": False,
            "previous_status": current_is_active,
        }

        logging.info(
            f"track_competitors_off: Función completada exitosamente. Resultado: {result}"
        )
        return result

    except https_fn.HttpsError as e:
        logging.error(
            f"track_competitors_off: Error de Firebase Functions: {e.code} - {e.message}"
        )
        raise
    except Exception as e:
        logging.error(f"track_competitors_off: Error interno: {str(e)}", exc_info=True)
        raise https_fn.HttpsError(
            code="internal", message=f"Error interno del servidor: {str(e)}"
        )
