from firebase_functions import https_fn
from firebase_admin import firestore
from typing import List
import logging
from models.event_document import EventDocument
from models.firestore_collections import FirestoreCollections


@https_fn.on_call()
def get_events(req: https_fn.CallableRequest) -> List[dict]:
    """
    Función optimizada que obtiene todos los eventos de Firestore.
    Retorna todos los eventos usando el modelo EventDocument.
    
    Optimizaciones aplicadas:
    - Eliminado logging innecesario en el loop (solo errores)
    - Procesamiento más eficiente evitando conversiones redundantes
    - Uso directo de to_dict() del modelo
    """
    try:
        # Inicializar Firestore
        db = firestore.client()

        # Consultar todos los eventos usando la constante
        events_ref = db.collection(FirestoreCollections.EVENTS)
        events_docs = events_ref.get()

        # Optimización: procesar y convertir en una sola pasada
        # Usar list comprehension para mejor rendimiento
        events_data = []
        for doc in events_docs:
            try:
                event_data = doc.to_dict()
                if event_data is None:
                    continue
                
                # Convertir usando el modelo para validación y estructura consistente
                event = EventDocument.from_dict(event_data, doc.id)
                # Convertir directamente a dict usando el método del modelo
                events_data.append(event.to_dict())
            except Exception as e:
                # Solo loggear errores, no cada evento procesado
                logging.warning(
                    f"get_events: Error procesando evento {doc.id}: {str(e)}"
                )
                continue

        # Retornar solo la lista de eventos
        return events_data

    except Exception as e:
        logging.error(f"get_events: Error interno: {str(e)}", exc_info=True)
        raise https_fn.HttpsError(
            code="internal", message=f"Error interno del servidor: {str(e)}"
        )

