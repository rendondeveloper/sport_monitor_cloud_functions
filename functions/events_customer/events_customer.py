from firebase_functions import https_fn
from firebase_admin import firestore
from typing import List
import logging
from models.event_document import EventDocument
from models.firestore_collections import FirestoreCollections


@https_fn.on_call()
def get_events(req: https_fn.CallableRequest) -> List[dict]:
    """
    Función que obtiene todos los eventos de Firestore.
    Retorna todos los eventos sin filtrar por isAvailable.
    """
    try:
        logging.info("get_events: Iniciando función para obtener todos los eventos")

        # Inicializar Firestore
        db = firestore.client()

        # Consultar todos los eventos usando la constante
        events_ref = db.collection(FirestoreCollections.EVENTS)
        events_docs = events_ref.get()

        logging.info(
            f"get_events: Encontrados {len(events_docs)} eventos en Firestore"
        )

        # Convertir documentos a objetos EventDocument
        events_list: List[EventDocument] = []
        for doc in events_docs:
            try:
                event_data = doc.to_dict()
                event = EventDocument.from_dict(event_data, doc.id)
                events_list.append(event)
                logging.debug(
                    f"get_events: Evento agregado - name: {event.name}, id: {event.id}"
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

