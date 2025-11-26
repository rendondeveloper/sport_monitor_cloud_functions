from typing import Optional


class EventsResponse:
    """Modelo para la respuesta de eventos disponibles"""

    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        url: Optional[str] = None,
        is_available: bool = False,
    ):
        self.title = title
        self.description = description
        self.image_url = image_url
        self.url = url
        self.is_available = is_available

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para Firestore"""
        return {
            "title": self.title,
            "description": self.description,
            "imageUrl": self.image_url,
            "url": self.url,
            "isAvailable": self.is_available,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventsResponse":
        """Crea un objeto desde un diccionario de Firestore"""
        return cls(
            title=data.get("title"),
            description=data.get("description"),
            image_url=data.get("imageUrl"),
            url=data.get("url"),
            is_available=data.get("isAvailable", False),
        )

    @classmethod
    def from_firestore(cls, snapshot) -> "EventsResponse":
        """Crea un objeto desde un DocumentSnapshot de Firestore"""
        data = snapshot.to_dict()
        if data is None:
            data = {}

        return cls(
            title=data.get("title"),
            description=data.get("description"),
            image_url=data.get("imageUrl"),
            url=data.get("url"),
            is_available=data.get("isAvailable", False),
        )

    def __eq__(self, other):
        if not isinstance(other, EventsResponse):
            return False
        return (
            self.title == other.title
            and self.description == other.description
            and self.image_url == other.image_url
            and self.url == other.url
            and self.is_available == other.is_available
        )

    def __repr__(self):
        return (
            f"EventsResponse(title='{self.title}', "
            f"is_available={self.is_available})"
        )

