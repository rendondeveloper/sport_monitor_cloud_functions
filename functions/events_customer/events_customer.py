from firebase_functions import https_fn
from firebase_admin import firestore
from typing import Dict, Any
import logging
from .event_short_document import EventShortDocument
from models.firestore_collections import FirestoreCollections
from models.paginated_response import PaginatedResponse


@https_fn.on_call()
def get_events(req: https_fn.CallableRequest) -> Dict[str, Any]:
    """
    Función optimizada que obtiene eventos de Firestore con soporte de paginación.
    Retorna eventos usando el modelo EventShortDocument.
    
    Parámetros opcionales en req.data:
    - limit: Número de eventos por página (default: 50, max: 100)
    - page: Número de página (default: 1, basado en 1)
    - lastDocId: ID del último documento de la página anterior (para cursor-based pagination)
    
    Optimizaciones aplicadas:
    - Paginación para mejorar rendimiento
    - Eliminado logging innecesario en el loop (solo errores)
    - Procesamiento más eficiente evitando conversiones redundantes
    - Uso directo de to_dict() del modelo
    """
    try:
        # Obtener datos de la petición
        data = req.data or {}
        
        # Parámetros de paginación
        limit = min(int(data.get("limit", 50)), 100)  # Default 50, máximo 100
        page = int(data.get("page", 1))  # Default página 1
        last_doc_id = data.get("lastDocId")  # Para cursor-based pagination
        
        # Validar parámetros
        if limit < 1:
            limit = 50
        if page < 1:
            page = 1

        # Inicializar Firestore
        db = firestore.client()

        # Consultar eventos usando la constante
        events_ref = db.collection(FirestoreCollections.EVENTS)
        
        # Aplicar paginación
        # Ordenar por createdAt descendente (más recientes primero)
        try:
            query = events_ref.order_by("createdAt", direction=firestore.Query.DESCENDING)
        except Exception as e:
            # Si falla por falta de índice, usar sin ordenamiento
            logging.warning(f"get_events: Error con order_by, usando sin orden: {str(e)}")
            query = events_ref
        
        # Si se proporciona lastDocId, usar cursor-based pagination (más eficiente)
        if last_doc_id:
            try:
                last_doc_ref = events_ref.document(last_doc_id)
                last_doc = last_doc_ref.get()
                if last_doc.exists:
                    query = query.start_after(last_doc)
            except Exception as e:
                logging.warning(f"get_events: Error con lastDocId {last_doc_id}: {str(e)}")
        # Si no hay lastDocId pero hay page > 1, usar offset (menos eficiente)
        # Nota: Para mejor rendimiento, se recomienda usar lastDocId
        elif page > 1:
            # Calcular cuántos documentos saltar
            offset = (page - 1) * limit
            # Obtener documentos hasta el offset para usar como cursor
            # Esto es menos eficiente pero funcional
            try:
                offset_docs = query.limit(offset).get()
                if len(offset_docs) > 0:
                    query = query.start_after(offset_docs[-1])
                else:
                    # Si no hay documentos en el offset, retornar vacío usando el modelo
                    empty_response = PaginatedResponse.create(
                        items=[],
                        limit=limit,
                        page=page,
                        has_more=False,
                        last_doc_id=None,
                    )
                    return empty_response.to_dict()
            except Exception as e:
                logging.warning(f"get_events: Error calculando offset para página {page}: {str(e)}")
        
        # Aplicar límite (agregar 1 para verificar si hay más páginas)
        query = query.limit(limit + 1)
        
        # Ejecutar query
        events_docs = query.get()

        # Determinar si hay más páginas
        has_more = len(events_docs) > limit
        if has_more:
            events_docs = events_docs[:limit]  # Remover el documento extra

        # Procesar documentos
        events_data = []
        last_document_id = None
        
        for doc in events_docs:
            try:
                event_data = doc.to_dict()
                if event_data is None:
                    continue
                
                # Convertir usando el modelo EventShortDocument con mapeo automático
                event = EventShortDocument.from_firestore_data(event_data, doc.id)
                # Convertir directamente a dict usando el método del modelo
                events_data.append(event.to_dict())
                last_document_id = doc.id
            except Exception as e:
                # Solo loggear errores, no cada evento procesado
                logging.warning(
                    f"get_events: Error procesando evento {doc.id}: {str(e)}"
                )
                continue

        # Crear respuesta paginada usando el modelo genérico
        paginated_response = PaginatedResponse.create(
            items=events_data,
            limit=limit,
            page=page,
            has_more=has_more,
            last_doc_id=last_document_id if has_more else None,
        )

        # Retornar usando el método to_dict() del modelo
        return paginated_response.to_dict()

    except ValueError as e:
        logging.error(f"get_events: Error de validación: {str(e)}")
        raise https_fn.HttpsError(
            code="invalid-argument",
            message=f"Parámetros inválidos: {str(e)}"
        )
    except Exception as e:
        logging.error(f"get_events: Error interno: {str(e)}", exc_info=True)
        raise https_fn.HttpsError(
            code="internal", message=f"Error interno del servidor: {str(e)}"
        )

