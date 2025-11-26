from firebase_functions import https_fn
from firebase_admin import firestore
from typing import List
import logging
from models.events_response import EventsResponse


@https_fn.on_call(allow_unauthenticated=True)
def get_events(req: https_fn.CallableRequest) -> List[dict]:
    """
    Función que obtiene todos los eventos disponibles de Firestore.
    Retorna solo los eventos donde isAvailable es True.
    """
    try:
        logging.info("get_events: Iniciando función para obtener eventos disponibles")

        # Inicializar Firestore
        db = firestore.client()

        # Consultar directamente los eventos donde isAvailable es True
        events_ref = db.collection("events")
        events_query = events_ref.where("isAvailable", "==", True)
        events_docs = events_query.get()

        logging.info(
            f"get_events: Encontrados {len(events_docs)} eventos disponibles en Firestore"
        )

        # Convertir documentos a objetos EventsResponse
        events_list: List[EventsResponse] = []
        for doc in events_docs:
            try:
                event = EventsResponse.from_firestore(doc)
                events_list.append(event)
                logging.debug(
                    f"get_events: Evento disponible agregado - title: {event.title}"
                )
            except Exception as e:
                logging.warning(
                    f"get_events: Error al procesar evento {doc.id}: {str(e)}"
                )
                continue

        # Convertir a lista de diccionarios para la respuesta
        events_data = [event.to_dict() for event in events_list]

        # Retornar solo la lista de eventos
        return events_data

    except Exception as e:
        logging.error(f"get_events: Error interno: {str(e)}", exc_info=True)
        raise https_fn.HttpsError(
            code="internal", message=f"Error interno del servidor: {str(e)}"
        )

