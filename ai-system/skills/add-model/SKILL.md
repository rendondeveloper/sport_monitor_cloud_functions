# Skill: /add-model

**Categoria**: Código
**Agente responsable**: functions-cross

---

## Cuando usar

- El endpoint retorna o recibe estructuras de datos complejas que se repiten en múltiples funciones
- Se necesita un lugar centralizado para las constantes de campos de un documento Firestore
- Los campos del documento requieren validación de tipos en `from_dict`

No crear modelos para estructuras simples de una sola función — usar `_build_dict()` directamente.

---

## Patrón de modelo Firestore

```python
# models/<nombre_modelo>.py

"""
<NombreModelo> — Modelo de datos para <descripción>.

Representa el documento Firestore en la colección
<FirestoreCollections.CONSTANTE> (<path/en/firestore>).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class <NombreModelo>:
    """
    Modelo de documento Firestore para <colección>.

    Constantes de campos para usar en queries y actualizaciones.
    """

    # Constantes de campos — usar en FirestoreHelper queries y updates
    FIELD_EVENT_ID = "eventId"
    FIELD_COMPETITOR_ID = "competitorId"
    FIELD_STATUS = "status"
    FIELD_CREATED_AT = "createdAt"
    FIELD_UPDATED_AT = "updatedAt"

    # Valores permitidos para campos con enum
    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_FINISHED = "finished"
    STATUS_VALUES = [STATUS_ACTIVE, STATUS_INACTIVE, STATUS_FINISHED]

    # Campos del modelo
    event_id: str
    competitor_id: str
    status: str = STATUS_ACTIVE
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "<NombreModelo>":
        """
        Crea instancia desde documento Firestore.

        Args:
            data: Dict retornado por FirestoreHelper.get_document() o query_documents()

        Returns:
            Instancia del modelo con valores del documento.
        """
        return cls(
            event_id=data.get(cls.FIELD_EVENT_ID, ""),
            competitor_id=data.get(cls.FIELD_COMPETITOR_ID, ""),
            status=data.get(cls.FIELD_STATUS, cls.STATUS_ACTIVE),
            created_at=data.get(cls.FIELD_CREATED_AT),
            updated_at=data.get(cls.FIELD_UPDATED_AT),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte a dict para guardar en Firestore.

        Returns:
            Dict listo para FirestoreHelper.create_document() o update_document()
        """
        return {
            self.FIELD_EVENT_ID: self.event_id,
            self.FIELD_COMPETITOR_ID: self.competitor_id,
            self.FIELD_STATUS: self.status,
            self.FIELD_CREATED_AT: self.created_at,
            self.FIELD_UPDATED_AT: self.updated_at,
        }

    def to_response_dict(self, doc_id: str) -> Dict[str, Any]:
        """
        Convierte a dict de respuesta HTTP API (incluye id, excluye campos internos).

        Args:
            doc_id: ID del documento Firestore.

        Returns:
            Dict para retornar en json.dumps() de la respuesta HTTP.
        """
        return {
            "id": doc_id,
            "eventId": self.event_id,
            "competitorId": self.competitor_id,
            "status": self.status,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
```

---

## Modelo para subcolecciones

Cuando el documento tiene subcolecciones embebidas (como `vehicle` bajo `participants`):

```python
@dataclass
class ParticipantVehicle:
    """Subdocumento vehicle bajo events/{id}/participants/{id}/vehicle/{id}."""

    FIELD_MAKE = "make"
    FIELD_MODEL = "model"
    FIELD_YEAR = "year"
    FIELD_COLOR = "color"
    FIELD_PLATE = "licensePlate"

    make: str
    model: str
    year: int
    color: str
    license_plate: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParticipantVehicle":
        return cls(
            make=data.get(cls.FIELD_MAKE, ""),
            model=data.get(cls.FIELD_MODEL, ""),
            year=int(data.get(cls.FIELD_YEAR, 0)),
            color=data.get(cls.FIELD_COLOR, ""),
            license_plate=data.get(cls.FIELD_PLATE, ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            self.FIELD_MAKE: self.make,
            self.FIELD_MODEL: self.model,
            self.FIELD_YEAR: self.year,
            self.FIELD_COLOR: self.color,
            self.FIELD_PLATE: self.license_plate,
        }
```

---

## Uso del modelo en un endpoint

```python
from models.competitor_result import CompetitorResult
from utils.firestore_helper import FirestoreHelper
from models.firestore_collections import FirestoreCollections

helper = FirestoreHelper()

# Leer documento y convertir a modelo
doc_data = helper.get_document(FirestoreCollections.EVENTS, event_id)
if doc_data:
    result = CompetitorResult.from_dict(doc_data)
    response_data = result.to_response_dict(event_id)

# Crear documento desde modelo
new_result = CompetitorResult(
    event_id="event123",
    competitor_id="uid123",
    status=CompetitorResult.STATUS_ACTIVE,
    created_at=get_current_timestamp(),
    updated_at=get_current_timestamp(),
)
new_id = helper.create_document(
    f"{FirestoreCollections.EVENTS}/event123/{FirestoreCollections.EVENT_PARTICIPANTS}",
    new_result.to_dict(),
)

# Query con constantes de campos del modelo
documents = helper.query_documents(
    collection_path,
    filters=[{
        "field": CompetitorResult.FIELD_STATUS,
        "operator": "==",
        "value": CompetitorResult.STATUS_ACTIVE,
    }],
)
```

---

## Reglas de modelos

- Solo crear modelo si se reutiliza en 2+ funciones o si tiene lógica de campos compleja
- Siempre incluir `from_dict` y `to_dict`
- `to_response_dict(doc_id)` solo si el formato HTTP difiere del formato Firestore
- Constantes de campos en UPPER_SNAKE como atributos de clase
- Valores enum como constantes (`STATUS_ACTIVE`, `STATUS_VALUES`)
- No poner lógica de negocio en el modelo — solo conversión de datos
