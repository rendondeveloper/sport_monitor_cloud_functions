from typing import List, Optional, Dict, Any, TypeVar, Generic

T = TypeVar('T')


class PaginationInfo:
    """Información de paginación"""

    def __init__(
        self,
        limit: int,
        page: int,
        has_more: bool,
        count: int,
        last_doc_id: Optional[str] = None,
    ):
        self.limit = limit
        self.page = page
        self.has_more = has_more
        self.count = count
        self.last_doc_id = last_doc_id

    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            "limit": self.limit,
            "page": self.page,
            "hasMore": self.has_more,
            "count": self.count,
            "lastDocId": self.last_doc_id,
        }


class PaginatedResponse(Generic[T]):
    """Respuesta genérica paginada"""

    def __init__(
        self,
        items: List[T],
        pagination: PaginationInfo,
    ):
        self.items = items
        self.pagination = pagination

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte a diccionario para la respuesta.
        Retorna directamente result y pagination al mismo nivel.
        Nota: Si Firebase Functions callable envuelve la respuesta en 'result',
        este método retorna la estructura que queremos en la respuesta final.
        """
        # Retornar directamente result y pagination al mismo nivel
        # Si Firebase envuelve en result, esto dará: {"result": {"result": [...], "pagination": {...}}}
        # Si Firebase NO envuelve, esto dará: {"result": [...], "pagination": {...}}
        return {
            "result": self.items,
            "pagination": self.pagination.to_dict(),
        }

    @classmethod
    def create(
        cls,
        items: List[T],
        limit: int,
        page: int,
        has_more: bool,
        last_doc_id: Optional[str] = None,
    ) -> "PaginatedResponse[T]":
        """
        Método de fábrica para crear una respuesta paginada
        
        Args:
            items: Lista de items de la página actual
            limit: Límite de items por página
            page: Número de página actual
            has_more: Indica si hay más páginas
            last_doc_id: ID del último documento (para cursor-based pagination)
        """
        pagination = PaginationInfo(
            limit=limit,
            page=page,
            has_more=has_more,
            count=len(items),
            last_doc_id=last_doc_id,
        )
        return cls(items=items, pagination=pagination)

