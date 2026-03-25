"""
Helpers compartidos para el catálogo checkpoint_types (tipos de checkpoint).

Respuesta GET y cuerpo POST: lista de grupos
`{ "type": "<categoría>", "items": [...] }`.
Cada ítem: name, type (slug), icon, abbreviation (null o string), description.
En Firestore: campo `category` = categoría del grupo; `type` = slug del ítem.
"""

from typing import Any, Dict, List, Tuple

from google.cloud.firestore import Client
from models.firestore_collections import FirestoreCollections

_CATALOG_DOC_ID = FirestoreCollections.CATALOGS_DEFAULT_DOC_ID

# Orden fijo de grupos en GET (aunque no haya documentos).
CHECKPOINT_GROUP_ORDER: Tuple[str, ...] = (
    "zones",
    "symbols",
    "waypoints",
    "safety",
    "dunes_sand",
)
CHECKPOINT_GROUP_TYPES = frozenset(CHECKPOINT_GROUP_ORDER)

_REQUIRED_ITEM_FIELDS = ("name", "type", "icon", "description")


def checkpoint_types_ref(db: Client):
    """Referencia a la subcolección checkpoint_types del catálogo default."""
    return (
        db.collection(FirestoreCollections.CATALOGS)
        .document(_CATALOG_DOC_ID)
        .collection(FirestoreCollections.CATALOGS_CHECKPOINT_TYPES)
    )


def _abbreviation_from_data(data: Dict[str, Any]) -> str | None:
    v = data.get("abbreviation")
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def build_checkpoint_type_item(doc) -> Dict[str, Any]:
    """Un ítem para JSON (incluye id de Firestore)."""
    data = doc.to_dict() or {}
    item: Dict[str, Any] = {
        "id": doc.id,
        "name": data.get("name", "") or "",
        "type": data.get("type", "") or "",
        "icon": data.get("icon", "") or "",
        "description": data.get("description", "") or "",
    }
    abbr = _abbreviation_from_data(data)
    item["abbreviation"] = abbr if abbr is not None else None
    return item


def build_grouped_checkpoint_types_response(docs) -> List[Dict[str, Any]]:
    """
    Agrupa documentos por `category` y devuelve la lista ordenada de grupos.
    Siempre incluye las cinco categorías; `items` vacío si no hay docs.
    """
    buckets: Dict[str, List[Dict[str, Any]]] = {g: [] for g in CHECKPOINT_GROUP_ORDER}
    for doc in docs:
        data = doc.to_dict() or {}
        cat = data.get("category")
        if not isinstance(cat, str) or cat not in CHECKPOINT_GROUP_TYPES:
            continue
        buckets[cat].append(build_checkpoint_type_item(doc))
    for cat in CHECKPOINT_GROUP_ORDER:
        buckets[cat].sort(key=lambda x: x.get("type") or "")
    return [{"type": g, "items": buckets[g]} for g in CHECKPOINT_GROUP_ORDER]


def validate_checkpoint_item(item: Any) -> str | None:
    """Valida un ítem dentro de `items`. None si es válido."""
    if not item or not isinstance(item, dict):
        return "item inválido"
    for field in _REQUIRED_ITEM_FIELDS:
        val = item.get(field)
        if not val or not isinstance(val, str) or not str(val).strip():
            return f"{field} es requerido y debe ser string no vacío"
    if "abbreviation" in item:
        ab = item["abbreviation"]
        if ab is None:
            pass
        elif isinstance(ab, str):
            if not ab.strip():
                return "abbreviation no puede ser string vacío; use null u omita el campo"
        else:
            return "abbreviation debe ser string no vacío o null"
    return None


def validate_checkpoint_groups_body(body: Any) -> str | None:
    """Valida el body POST: lista de { type: categoría, items: [...] }."""
    if not isinstance(body, list):
        return "body debe ser un array"
    for i, group in enumerate(body):
        if not group or not isinstance(group, dict):
            return f"grupo [{i}] inválido"
        gtype = group.get("type")
        if not isinstance(gtype, str) or gtype.strip() == "":
            return f"grupo [{i}]: type es requerido"
        if gtype.strip() not in CHECKPOINT_GROUP_TYPES:
            return f"grupo [{i}]: type debe ser una categoría conocida"
        items = group.get("items")
        if not isinstance(items, list):
            return f"grupo [{i}]: items debe ser un array"
        for j, it in enumerate(items):
            err = validate_checkpoint_item(it)
            if err:
                return f"grupo [{i}] item [{j}]: {err}"
    return None


def cors_headers() -> Dict[str, str]:
    """Headers CORS para respuestas."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
