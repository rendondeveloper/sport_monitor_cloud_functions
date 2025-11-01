from datetime import datetime
from typing import List, Optional
import json


class CheckpointsTracking:
    """Modelo para CheckpointsTracking (siguiendo el modelo Dart)"""

    def __init__(
        self,
        id: str,
        name: str,
        status_competitor: str,
        pass_time: datetime,
        note: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.status_competitor = status_competitor
        self.pass_time = pass_time
        self.note = note

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para Firestore"""
        return {
            "id": self.id,
            "name": self.name,
            "statusCompetitor": self.status_competitor,
            "passTime": self.pass_time.isoformat(),
            "note": self.note,
        }

    def to_json(self) -> str:
        """Convierte el objeto a JSON string para Firestore"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointsTracking":
        """Crea un objeto desde un diccionario de Firestore"""
        return cls(
            id=data["id"],
            name=data["name"],
            status_competitor=data["statusCompetitor"],
            pass_time=datetime.fromisoformat(data["passTime"]),
            note=data.get("note"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "CheckpointsTracking":
        """Crea un objeto desde un JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __eq__(self, other):
        if not isinstance(other, CheckpointsTracking):
            return False
        return (
            self.id == other.id
            and self.name == other.name
            and self.status_competitor == other.status_competitor
            and self.pass_time == other.pass_time
            and self.note == other.note
        )

    def __repr__(self):
        return f"CheckpointsTracking(id='{self.id}', name='{self.name}', status_competitor='{self.status_competitor}', pass_time={self.pass_time}, note='{self.note}')"


class CompetitorTracking:
    """Modelo para CompetitorTracking (siguiendo el modelo Dart)"""

    def __init__(
        self,
        id: str,
        name: str,
        order: int,
        category: str,
        number: str,
        tracking_chakpoints: List[CheckpointsTracking],
    ):
        self.id = id
        self.name = name
        self.order = order
        self.category = category
        self.number = number
        self.tracking_chakpoints = tracking_chakpoints

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para Firestore"""
        return {
            "id": self.id,
            "name": self.name,
            "order": self.order,
            "category": self.category,
            "number": self.number,
            "trackingChakpoints": [tc.to_dict() for tc in self.tracking_chakpoints],
        }

    def to_json(self) -> str:
        """Convierte el objeto a JSON string para Firestore"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "CompetitorTracking":
        """Crea un objeto desde un diccionario de Firestore"""
        tracking_chakpoints: List[CheckpointsTracking] = []
        if "trackingChakpoints" in data and data["trackingChakpoints"]:
            tracking_chakpoints = [
                CheckpointsTracking.from_dict(tc) for tc in data["trackingChakpoints"]
            ]

        return cls(
            id=data["id"],
            name=data["name"],
            order=data["order"],
            category=data["category"],
            number=data["number"],
            tracking_chakpoints=tracking_chakpoints,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "CompetitorTracking":
        """Crea un objeto desde un JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def add_tracking_checkpoint(self, tracking_checkpoint: CheckpointsTracking):
        """Agrega un tracking checkpoint al competidor"""
        self.tracking_chakpoints.append(tracking_checkpoint)

    def __eq__(self, other):
        if not isinstance(other, CompetitorTracking):
            return False
        return (
            self.id == other.id
            and self.name == other.name
            and self.order == other.order
            and self.category == other.category
            and self.number == other.number
            and self.tracking_chakpoints == other.tracking_chakpoints
        )

    def __repr__(self):
        return f"CompetitorTracking(id='{self.id}', name='{self.name}', order={self.order}, category='{self.category}', number='{self.number}', tracking_chakpoints={len(self.tracking_chakpoints)})"


class CompetitorTrackingDocument:
    """Documento de Firestore para CompetitorTrackingDocument (siguiendo el modelo Dart)"""

    def __init__(
        self,
        id: str,
        event_id: str,
        day_id: str,
        name: str,
        created_at: datetime,
        updated_at: datetime,
        competitors_tracking: Optional[List[CompetitorTracking]] = None,
        is_active: bool = True,
    ):
        self.id = id
        self.event_id = event_id
        self.day_id = day_id
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at
        self.competitors_tracking = competitors_tracking or []
        self.is_active = is_active

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para Firestore"""
        return {
            "eventId": self.event_id,
            "dayId": self.day_id,
            "competitorsTracking": [ct.to_dict() for ct in self.competitors_tracking],
            "isActive": self.is_active,
            "name": self.name,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }

    def to_json(self) -> str:
        """Convierte el objeto a JSON string para Firestore"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict, doc_id: str) -> "CompetitorTrackingDocument":
        """Crea un objeto desde un diccionario de Firestore"""
        competitors_tracking: List[CompetitorTracking] = []
        if "competitorsTracking" in data and data["competitorsTracking"]:
            competitors_tracking = [
                CompetitorTracking.from_dict(ct) for ct in data["competitorsTracking"]
            ]

        created_at = datetime.fromisoformat(
            data.get("createdAt", datetime.utcnow().isoformat())
        )
        updated_at = datetime.fromisoformat(
            data.get("updatedAt", datetime.utcnow().isoformat())
        )

        return cls(
            id=doc_id,
            event_id=data["eventId"],
            day_id=data["dayId"],
            name=data["name"],
            created_at=created_at,
            updated_at=updated_at,
            competitors_tracking=competitors_tracking,
            is_active=data.get("isActive", True),
        )

    @classmethod
    def from_json(cls, json_str: str, doc_id: str) -> "CompetitorTrackingDocument":
        """Crea un objeto desde un JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data, doc_id)

    def add_competitor_tracking(self, competitor_tracking: CompetitorTracking):
        """Agrega un competitor tracking al documento"""
        self.competitors_tracking.append(competitor_tracking)

    def copy_with(self, **kwargs) -> "CompetitorTrackingDocument":
        """Crea una copia del objeto con los campos especificados actualizados"""
        return CompetitorTrackingDocument(
            id=kwargs.get("id", self.id),
            event_id=kwargs.get("event_id", self.event_id),
            day_id=kwargs.get("day_id", self.day_id),
            name=kwargs.get("name", self.name),
            created_at=kwargs.get("created_at", self.created_at),
            updated_at=kwargs.get("updated_at", self.updated_at),
            competitors_tracking=kwargs.get(
                "competitors_tracking", self.competitors_tracking
            ),
            is_active=kwargs.get("is_active", self.is_active),
        )

    def __eq__(self, other):
        if not isinstance(other, CompetitorTrackingDocument):
            return False
        return (
            self.id == other.id
            and self.event_id == other.event_id
            and self.day_id == other.day_id
            and self.name == other.name
            and self.competitors_tracking == other.competitors_tracking
            and self.is_active == other.is_active
        )

    def __repr__(self):
        return (
            f"CompetitorTrackingDocument(id='{self.id}', event_id='{self.event_id}', day_id='{self.day_id}', "
            f"competitors_tracking={len(self.competitors_tracking)}, is_active={self.is_active})"
            f"name='{self.name}')"
        )
