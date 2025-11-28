from datetime import datetime
from enum import Enum
from typing import List, Optional

class EventStatus(Enum):
    """Enum para los estados del evento"""

    DRAFT = "draft"
    PUBLISHED = "published"
    OPEN_REGISTRATION = "openRegistration"
    CLOSED_REGISTRATION = "closedRegistration"
    IN_PROGRESS = "inProgress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @property
    def display_name(self) -> str:
        """Nombre en español para mostrar"""
        display_names = {
            EventStatus.DRAFT: "Borrador",
            EventStatus.PUBLISHED: "Publicado",
            EventStatus.OPEN_REGISTRATION: "Registro Abierto",
            EventStatus.CLOSED_REGISTRATION: "Registro Cerrado",
            EventStatus.IN_PROGRESS: "En Progreso",
            EventStatus.COMPLETED: "Completado",
            EventStatus.CANCELLED: "Cancelado",
        }
        return display_names[self]

    @property
    def color_value(self) -> int:
        """Color en formato hexadecimal asociado al estado del evento"""
        colors = {
            EventStatus.DRAFT: 0xFF6B7280,  # Gray
            EventStatus.PUBLISHED: 0xFF10B981,  # Green
            EventStatus.OPEN_REGISTRATION: 0xFF3B82F6,  # Blue
            EventStatus.CLOSED_REGISTRATION: 0xFFF59E0B,  # Orange
            EventStatus.IN_PROGRESS: 0xFF8B5CF6,  # Purple
            EventStatus.COMPLETED: 0xFF059669,  # Emerald
            EventStatus.CANCELLED: 0xFFEF4444,  # Red
        }
        return colors[self]


class EventDocument:
    """Modelo de ejemplo para eventos deportivos en Firestore"""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        status: EventStatus,
        created_at: datetime,
        updated_at: datetime,
        subtitle: Optional[str] = None,
        rally_system_id: Optional[str] = None,
        created_by: Optional[str] = None,
        location: Optional[str] = None,
        date: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.subtitle = subtitle
        self.rally_system_id = rally_system_id
        self.description = description
        self.status = status
        self.created_by = created_by
        self.location = location
        self.date = date
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para Firestore"""
        return {
            "name": self.name,
            "subtitle": self.subtitle,
            "rallySystemId": self.rally_system_id,
            "description": self.description,
            "status": self.status.value,
            "createdBy": self.created_by,
            "location": self.location,
            "date": self.date,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict, doc_id: str) -> "EventDocument":
        """Crea un objeto desde un diccionario de Firestore"""      
        # Parsear fechas
        created_at = datetime.fromisoformat(
            data.get("createdAt", datetime.now().isoformat())
        )
        updated_at = datetime.fromisoformat(
            data.get("updatedAt", datetime.now().isoformat())
        )

        return cls(
            id=doc_id,
            name=data.get("name", ""),
            subtitle=data.get("subtitle"),
            rally_system_id=data.get("rallySystemId"),
            description=data.get("description", ""),
            status=EventStatus(data.get("status", "draft")),
            created_by=data.get("createdBy"),
            location=data.get("location"),
            date=data.get("date"),
            created_at=created_at,
            updated_at=updated_at,
        )

    def copy_with(self, **kwargs) -> "EventDocument":
        """Crea una copia del objeto con los campos especificados actualizados"""
        return EventDocument(
            id=kwargs.get("id", self.id),
            name=kwargs.get("name", self.name),
            subtitle=kwargs.get("subtitle", self.subtitle),
            rally_system_id=kwargs.get("rally_system_id", self.rally_system_id),
            description=kwargs.get("description", self.description),
            status=kwargs.get("status", self.status),
            created_by=kwargs.get("created_by", self.created_by),
            location=kwargs.get("location", self.location),
            date=kwargs.get("date", self.date),
            created_at=kwargs.get("created_at", self.created_at),
            updated_at=kwargs.get("updated_at", self.updated_at),
        )

    def __eq__(self, other):
        if not isinstance(other, EventDocument):
            return False
        return (
            self.id == other.id
            and self.name == other.name
            and self.description == other.description
            and self.status == other.status
        )

    def __repr__(self):
        return (
            f"EventDocument(id='{self.id}', name='{self.name}', status={self.status})"
        )
