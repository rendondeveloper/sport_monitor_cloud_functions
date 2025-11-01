from datetime import datetime
from enum import Enum
from typing import List, Optional
import json


class CheckpointType(Enum):
    """Enum para los tipos de checkpoint"""

    START = "start"
    PASS = "pass"
    TIMER = "timer"
    START_TIMER = "startTimer"
    END_TIMER = "endTimer"
    FINISH = "finish"

    @property
    def display_name(self) -> str:
        """Nombre en español para mostrar"""
        display_names = {
            CheckpointType.START: "Inicio",
            CheckpointType.PASS: "Paso",
            CheckpointType.TIMER: "Temporizador",
            CheckpointType.START_TIMER: "Inicio Temporizador",
            CheckpointType.END_TIMER: "Fin Temporizador",
            CheckpointType.FINISH: "Meta",
        }
        return display_names[self]


class CompetitorsTrackingStatus(Enum):
    """Enum para el estado del tracking de competidores"""

    NONE = "none"
    NONE_START = "noneStart"
    NONE_LAST = "noneLast"
    CHECK = "check"
    CHECK_START = "checkStart"
    CHECK_LAST = "checkLast"
    OUT = "out"
    OUT_START = "outStart"
    OUT_LAST = "outLast"


class CheckpointStatus(Enum):
    """Enum para el estado del checkpoint"""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"

    @property
    def display_name(self) -> str:
        """Nombre en español para mostrar"""
        display_names = {
            CheckpointStatus.DRAFT: "Borrador",
            CheckpointStatus.ACTIVE: "Activo",
            CheckpointStatus.COMPLETED: "Completado",
        }
        return display_names[self]


class Checkpoint:
    """Modelo para Checkpoint (siguiendo el modelo Dart)"""

    def __init__(
        self,
        id: str,
        name: str,
        order: int,
        checkpoint_type: CheckpointType,
        status_competitor: CompetitorsTrackingStatus,
        checkpoint_disable: str,
        checkpoint_disable_name: str,
        pass_time: datetime,
        note: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.order = order
        self.checkpoint_type = checkpoint_type
        self.status_competitor = status_competitor
        self.checkpoint_disable = checkpoint_disable
        self.checkpoint_disable_name = checkpoint_disable_name
        self.pass_time = pass_time
        self.note = note

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para Firestore"""
        return {
            "id": self.id,
            "name": self.name,
            "order": self.order,
            "checkpointType": self.checkpoint_type.value,
            "statusCompetitor": self.status_competitor.value,
            "checkpointDisable": self.checkpoint_disable,
            "checkpointDisableName": self.checkpoint_disable_name,
            "passTime": self.pass_time.isoformat(),
            "note": self.note,
        }

    def to_json(self) -> str:
        """Convierte el objeto a JSON string para Firestore"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        """Crea un objeto desde un diccionario de Firestore"""
        return cls(
            id=data["id"],
            name=data["name"],
            order=data["order"],
            checkpoint_type=CheckpointType(data["checkpointType"]),
            status_competitor=CompetitorsTrackingStatus(data["statusCompetitor"]),
            checkpoint_disable=data.get("checkpointDisable", ""),
            checkpoint_disable_name=data.get("checkpointDisableName", ""),
            pass_time=datetime.fromisoformat(data["passTime"]),
            note=data.get("note"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Checkpoint":
        """Crea un objeto desde un JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __eq__(self, other):
        if not isinstance(other, Checkpoint):
            return False
        return (
            self.id == other.id
            and self.name == other.name
            and self.order == other.order
            and self.checkpoint_type == other.checkpoint_type
            and self.status_competitor == other.status_competitor
            and self.checkpoint_disable == other.checkpoint_disable
            and self.checkpoint_disable_name == other.checkpoint_disable_name
            and self.pass_time == other.pass_time
            and self.note == other.note
        )

    def __repr__(self):
        return (
            f"Checkpoint(id='{self.id}', name='{self.name}', order={self.order}, "
            f"checkpoint_type={self.checkpoint_type.value}, status_competitor={self.status_competitor.value}, "
            f"pass_time={self.pass_time}, note='{self.note}')"
        )


class Competitor:
    """Modelo simplificado para Competitor"""

    def __init__(
        self,
        id: str,
        category: Optional[str] = None,
        pilot_number: Optional[str] = None,
        status: Optional[str] = None,
    ):
        self.id = id
        self.category = category
        self.pilot_number = pilot_number
        self.status = status

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para Firestore"""
        return {
            "id": self.id,
            "category": self.category,
            "pilotNumber": self.pilot_number,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Competitor":
        """Crea un objeto desde un diccionario de Firestore"""
        return cls(
            id=data["id"],
            category=data.get("category"),
            pilot_number=data.get("pilotNumber"),
            status=data.get("status"),
        )

    def __eq__(self, other):
        if not isinstance(other, Competitor):
            return False
        return (
            self.id == other.id
            and self.category == other.category
            and self.pilot_number == other.pilot_number
            and self.status == other.status
        )

    def __repr__(self):
        return f"Competitor(id='{self.id}', category='{self.category}', pilot_number='{self.pilot_number}', status='{self.status}')"


class TrackingCheckpoint:
    """Modelo principal para el tracking checkpoint"""

    def __init__(
        self,
        event_id: str,
        checkpoints: List[Checkpoint],
        competitors: List[Competitor],
        created_at: Optional[datetime] = None,
        status: str = "inProgress",
    ):
        self.event_id = event_id
        self.checkpoints = checkpoints
        self.competitors = competitors
        self.created_at = created_at or datetime.utcnow()
        self.status = status

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para Firestore"""
        return {
            "eventId": self.event_id,
            "checkpoints": [checkpoint.to_dict() for checkpoint in self.checkpoints],
            "competitors": [competitor.to_dict() for competitor in self.competitors],
            "createdAt": self.created_at.isoformat(),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrackingCheckpoint":
        """Crea un objeto desde un diccionario de Firestore"""
        checkpoints = []
        if "checkpoints" in data and data["checkpoints"]:
            checkpoints = [Checkpoint.from_dict(cp) for cp in data["checkpoints"]]

        competitors = []
        if "competitors" in data and data["competitors"]:
            competitors = [Competitor.from_dict(comp) for comp in data["competitors"]]

        created_at = datetime.fromisoformat(
            data.get("createdAt", datetime.utcnow().isoformat())
        )

        return cls(
            event_id=data["eventId"],
            checkpoints=checkpoints,
            competitors=competitors,
            created_at=created_at,
            status=data.get("status", "inProgress"),
        )

    def add_checkpoint(self, checkpoint: Checkpoint):
        """Agrega un checkpoint a la lista"""
        self.checkpoints.append(checkpoint)

    def add_competitor(self, competitor: Competitor):
        """Agrega un competidor a la lista"""
        self.competitors.append(competitor)

    def __eq__(self, other):
        if not isinstance(other, TrackingCheckpoint):
            return False
        return (
            self.event_id == other.event_id
            and self.checkpoints == other.checkpoints
            and self.competitors == other.competitors
            and self.status == other.status
        )

    def __repr__(self):
        return f"TrackingCheckpoint(event_id='{self.event_id}', checkpoints={len(self.checkpoints)}, competitors={len(self.competitors)}, status='{self.status}')"
