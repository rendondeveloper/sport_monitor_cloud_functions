"""
Helpers compartidos para el catálogo de años. SPRTMNTRPP-82.
"""

from typing import Any, Dict

from google.cloud.firestore import Client
from models.firestore_collections import FirestoreCollections
from utils.helpers import convert_firestore_value

_CATALOG_DOC_ID = FirestoreCollections.CATALOGS_DEFAULT_DOC_ID


def years_ref(db: Client):
    """Referencia a la subcolección years del catálogo default."""
    return (
        db.collection(FirestoreCollections.CATALOGS)
        .document(_CATALOG_DOC_ID)
        .collection(FirestoreCollections.CATALOGS_YEARS)
    )


def build_year_item(doc) -> Dict[str, Any]:
    """Construye el dict de un year para la respuesta."""
    data = doc.to_dict() or {}
    return {
        "id": doc.id,
        "year": convert_firestore_value(data.get("year")),
    }


def validate_item_year(item: Any) -> str | None:
    """Valida un item de year. Retorna None si es válido, mensaje de error si no."""
    if not item or not isinstance(item, dict):
        return "item inválido"
    year = item.get("year")
    if year is None:
        return "year es requerido"
    try:
        y = int(year)
        if y < 1894 or y > 2100:
            return "year debe estar entre 1894 y 2100"
    except (TypeError, ValueError):
        return "year debe ser número"
    return None


def cors_headers() -> Dict[str, str]:
    """Headers CORS para respuestas."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
