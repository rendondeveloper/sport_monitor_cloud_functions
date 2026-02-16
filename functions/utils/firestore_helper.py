"""
Firestore Helper - Utilidades para interactuar con Firestore.

Clase centralizada para operaciones CRUD sobre Firestore.
DEBE SER USADA por todas las APIs que necesiten acceder a Firestore.
NO duplicar lógica de Firestore en cada Cloud Function.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

LOG = logging.getLogger(__name__)


class FirestoreHelper:
    """Helper centralizado para operaciones de Firestore."""

    def __init__(self):
        """Inicializa el cliente de Firestore (ya inicializado en main.py)."""
        self.db = firestore.client()

    def get_document(
        self,
        collection_path: str,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene un documento por ID.

        Args:
            collection_path: Ruta de la colección (puede incluir subcolecciones,
                             ej: "events/abc/participants").
            document_id: ID del documento.

        Returns:
            Diccionario con datos del documento o None si no existe.
        """
        try:
            doc_ref = self.db.collection(collection_path).document(document_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            LOG.error("FirestoreHelper.get_document error: %s", e, exc_info=True)
            raise

    def create_document(
        self,
        collection_path: str,
        data: Dict[str, Any],
    ) -> str:
        """
        Crea un documento con ID autogenerado por Firestore.

        Args:
            collection_path: Ruta de la colección.
            data: Datos del documento.

        Returns:
            ID del documento creado.
        """
        try:
            doc_ref = self.db.collection(collection_path).document()
            doc_ref.set(data)
            return doc_ref.id
        except Exception as e:
            LOG.error("FirestoreHelper.create_document error: %s", e, exc_info=True)
            raise

    def create_document_with_id(
        self,
        collection_path: str,
        document_id: str,
        data: Dict[str, Any],
    ) -> str:
        """
        Crea un documento con ID específico.

        Útil para la subcolección membership donde el ID es el eventId.

        Args:
            collection_path: Ruta de la colección.
            document_id: ID deseado para el documento.
            data: Datos del documento.

        Returns:
            ID del documento creado.
        """
        try:
            doc_ref = self.db.collection(collection_path).document(document_id)
            doc_ref.set(data)
            return doc_ref.id
        except Exception as e:
            LOG.error(
                "FirestoreHelper.create_document_with_id error: %s", e, exc_info=True
            )
            raise

    def update_document(
        self,
        collection_path: str,
        document_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """
        Actualiza un documento existente.

        Args:
            collection_path: Ruta de la colección.
            document_id: ID del documento.
            data: Datos a actualizar (merge parcial).

        Returns:
            True si se actualizó correctamente.
        """
        try:
            doc_ref = self.db.collection(collection_path).document(document_id)
            doc_ref.update(data)
            return True
        except Exception as e:
            LOG.error("FirestoreHelper.update_document error: %s", e, exc_info=True)
            raise

    def delete_document(
        self,
        collection_path: str,
        document_id: str,
    ) -> bool:
        """
        Elimina un documento.

        Args:
            collection_path: Ruta de la colección.
            document_id: ID del documento.

        Returns:
            True si se eliminó correctamente.
        """
        try:
            doc_ref = self.db.collection(collection_path).document(document_id)
            doc_ref.delete()
            return True
        except Exception as e:
            LOG.error("FirestoreHelper.delete_document error: %s", e, exc_info=True)
            raise

    def list_document_ids(self, collection_path: str) -> List[str]:
        """
        Lista los IDs de todos los documentos de una colección (o subcolección).

        Args:
            collection_path: Ruta de la colección (ej: "users/abc/emergencyContact").

        Returns:
            Lista de IDs de documentos.
        """
        try:
            docs = self.db.collection(collection_path).stream()
            return [doc.id for doc in docs]
        except Exception as e:
            LOG.error("FirestoreHelper.list_document_ids error: %s", e, exc_info=True)
            raise

    def query_documents(
        self,
        collection_path: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        order_by: Optional[List[Tuple[str, str]]] = None,
        limit: Optional[int] = None,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Ejecuta una query en una colección.

        Args:
            collection_path: Ruta de la colección.
            filters: Lista de filtros [{"field": ..., "operator": ..., "value": ...}].
            order_by: Lista de ordenamiento [("field", "asc"|"desc")].
            limit: Límite de resultados.

        Returns:
            Lista de tuplas (document_id, document_data).
        """
        try:
            query = self.db.collection(collection_path)

            if filters:
                for f in filters:
                    query = query.where(
                        filter=FieldFilter(f["field"], f["operator"], f["value"])
                    )

            if order_by:
                for field, direction in order_by:
                    dir_enum = (
                        firestore.Query.DESCENDING
                        if direction == "desc"
                        else firestore.Query.ASCENDING
                    )
                    query = query.order_by(field, direction=dir_enum)

            if limit:
                query = query.limit(limit)

            docs = query.stream()
            return [(doc.id, doc.to_dict()) for doc in docs]

        except Exception as e:
            LOG.error("FirestoreHelper.query_documents error: %s", e, exc_info=True)
            raise

    def batch_update(
        self,
        updates: List[Tuple[str, str, Dict[str, Any]]],
    ) -> bool:
        """
        Actualiza múltiples documentos en una transacción batch.

        Args:
            updates: Lista de tuplas (collection_path, document_id, data).

        Returns:
            True si todas las actualizaciones fueron exitosas.
        """
        try:
            batch = self.db.batch()
            for collection_path, document_id, data in updates:
                doc_ref = self.db.collection(collection_path).document(document_id)
                batch.update(doc_ref, data)
            batch.commit()
            return True
        except Exception as e:
            LOG.error("FirestoreHelper.batch_update error: %s", e, exc_info=True)
            raise
