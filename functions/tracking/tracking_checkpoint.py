from firebase_functions import https_fn
from firebase_admin import firestore
from datetime import datetime
from models.event_document import EventDocument, EventStatus
from models.checkpoint_tracking import (
    TrackingCheckpoint,
    Checkpoint,
    CheckpointType,
    CompetitorsTrackingStatus,
)


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
            current_time = datetime.utcnow()
            basic_checkpoints = [
                Checkpoint(
                    id=f"{event_id}_start_1",
                    name="Inicio",
                    order=1,
                    checkpoint_type=CheckpointType.START,
                    status_competitor=CompetitorsTrackingStatus.NONE,
                    checkpoint_disable="",
                    checkpoint_disable_name="",
                    pass_time=current_time,
                    note=None,
                ),
                Checkpoint(
                    id=f"{event_id}_finish_2",
                    name="Meta",
                    order=2,
                    checkpoint_type=CheckpointType.FINISH,
                    status_competitor=CompetitorsTrackingStatus.NONE,
                    checkpoint_disable="",
                    checkpoint_disable_name="",
                    pass_time=current_time,
                    note=None,
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

