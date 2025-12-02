from datetime import datetime
from typing import Optional
from models.event_document import EventStatus


class EventShortDocument:
    """Modelo para eventos cortos (versión simplificada de EventDocument)"""

    def __init__(
        self,
        id: str,
        title: str,
        status: EventStatus,
        start_date_time_utc: datetime,
        location_name: str,
        subtitle: Optional[str] = None,
        timezone: Optional[str] = None,
        image_url: Optional[str] = None,
    ):
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.status = status
        self.start_date_time_utc = start_date_time_utc
        self.timezone = timezone
        self.location_name = location_name
        self.image_url = image_url

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para JSON/Firestore"""
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "status": self.status.value,
            "startDateTime": self.start_date_time_utc.isoformat(),
            "timezone": self.timezone,
            "locationName": self.location_name,
            "imageUrl": self.image_url,
        }

    @classmethod
    def from_dict(cls, data: dict, doc_id: Optional[str] = None) -> "EventShortDocument":
        """Crea un objeto desde un diccionario (JSON/Firestore)"""
        # Usar doc_id si se proporciona, sino usar el id del diccionario
        event_id = doc_id or data.get("id", "")
        
        # Parsear fecha
        start_date_time_str = data.get("startDateTime", "")
        if isinstance(start_date_time_str, str):
            start_date_time_utc = datetime.fromisoformat(start_date_time_str.replace("Z", "+00:00"))
        elif isinstance(start_date_time_str, datetime):
            start_date_time_utc = start_date_time_str
        else:
            raise ValueError(f"startDateTime inválido: {start_date_time_str}")

        # Parsear status (con fallback a draft como en Dart)
        status_str = data.get("status", "draft")
        try:
            status = EventStatus(status_str)
        except ValueError:
            # Si no se encuentra el status, usar draft como default (como en Dart)
            status = EventStatus.DRAFT

        return cls(
            id=event_id,
            title=data.get("title", ""),
            subtitle=data.get("subtitle"),
            status=status,
            start_date_time_utc=start_date_time_utc,
            timezone=data.get("timezone"),
            location_name=data.get("locationName", ""),
            image_url=data.get("imageUrl"),
        )

    @classmethod
    def from_firestore_data(cls, data: dict, doc_id: str) -> "EventShortDocument":
        """
        Crea un EventShortDocument desde datos de Firestore (EventDocument).
        Maneja el mapeo de campos y el parseo de fechas automáticamente.
        
        Mapea:
        - name -> title
        - location -> locationName
        - date -> startDateTime (con parseo y fallbacks)
        - createdAt -> startDateTime (si date no existe)
        """
        # Mapear campos
        title = data.get("name", "")
        location_name = data.get("location", "")
        subtitle = data.get("subtitle")
        status_str = data.get("status", "draft")
        timezone = data.get("timezone")
        image_url = data.get("imageUrl")
        
        # Parsear status (con fallback a draft como en Dart)
        try:
            status = EventStatus(status_str)
        except ValueError:
            status = EventStatus.DRAFT
        
        # Parsear fecha de inicio con fallbacks
        start_date_time = None
        date_str = data.get("date")
        
        if date_str:
            # Intentar parsear la fecha desde el formato que tenga
            if isinstance(date_str, str):
                try:
                    # Intentar formato ISO primero
                    start_date_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    try:
                        # Intentar otros formatos comunes
                        start_date_time = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        try:
                            start_date_time = datetime.strptime(date_str, "%Y-%m-%d")
                        except ValueError:
                            # Si todos fallan, usar None para activar el fallback
                            start_date_time = None
            elif isinstance(date_str, datetime):
                start_date_time = date_str
        
        # Si no hay fecha válida, usar createdAt como fallback
        if start_date_time is None:
            created_at_str = data.get("createdAt")
            if created_at_str:
                try:
                    if isinstance(created_at_str, str):
                        start_date_time = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    elif isinstance(created_at_str, datetime):
                        start_date_time = created_at_str
                except (ValueError, AttributeError):
                    pass
        
        # Si aún no hay fecha, usar fecha actual como último recurso
        if start_date_time is None:
            start_date_time = datetime.now()
        
        return cls(
            id=doc_id,
            title=title,
            subtitle=subtitle,
            status=status,
            start_date_time_utc=start_date_time,
            timezone=timezone,
            location_name=location_name,
            image_url=image_url,
        )

    def copy_with(self, **kwargs) -> "EventShortDocument":
        """Crea una copia del objeto con los campos especificados actualizados"""
        return EventShortDocument(
            id=kwargs.get("id", self.id),
            title=kwargs.get("title", self.title),
            subtitle=kwargs.get("subtitle", self.subtitle),
            status=kwargs.get("status", self.status),
            start_date_time_utc=kwargs.get("start_date_time_utc", self.start_date_time_utc),
            timezone=kwargs.get("timezone", self.timezone),
            location_name=kwargs.get("location_name", self.location_name),
            image_url=kwargs.get("image_url", self.image_url),
        )

    def __eq__(self, other):
        if not isinstance(other, EventShortDocument):
            return False
        return (
            self.id == other.id
            and self.title == other.title
            and self.status == other.status
            and self.start_date_time_utc == other.start_date_time_utc
        )

    def __repr__(self):
        return (
            f"EventShortDocument(id='{self.id}', title='{self.title}', "
            f"status={self.status}, startDateTimeUtc={self.start_date_time_utc})"
        )

