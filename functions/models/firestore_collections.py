"""
Constantes para nombres de colecciones de Firestore
"""


class FirestoreCollections:
    """Constantes para nombres de colecciones de Firestore"""

    # Colecciones principales
    EVENTS = "events"
    USERS = "users"
    EVENT_TRACKING = "events_tracking"

    # Colecciones de eventos relacionados
    EVENT_CHECKPOINTS = "checkpoints"
    DAY_OF_RACES = "day_of_races"
    EVENT_CATEGORIES = "event_categories"
    EVENT_PARTICIPANTS = "participants"
    EVENT_STAFF = "staff_users"
    EVENT_ROUTES = "routes"

    # Colecciones de tracking
    EVENT_TRACKING_COMPETITOR_TRACKING = "competitor_tracking"
    EVENT_TRACKING_COMPETITOR = "competitor"
    EVENT_TRACKING_CHECKPOINTS = "checkpoints"

