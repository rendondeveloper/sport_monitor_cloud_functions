from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app, firestore
import json
from datetime import datetime

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

            # Crear la colección tracking_checkpoint dentro del evento
            tracking_ref = event_ref.collection("tracking_checkpoint")

            # Crear un documento inicial en tracking_checkpoint
            initial_checkpoint = {
                "created_at": datetime.utcnow(),
                "status": "inProgress",
                "event_id": event_id,
                "checkpoint_data": {
                    "start_time": datetime.utcnow(),
                    "status": "active",
                },
            }

            # Agregar el documento inicial
            tracking_ref.add(initial_checkpoint)

            return {
                "success": True,
                "message": f"Colección 'tracking_checkpoint' creada para el evento {event_id}",
                "event_id": event_id,
                "status": status,
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
