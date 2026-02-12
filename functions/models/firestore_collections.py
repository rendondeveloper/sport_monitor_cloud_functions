"""
Constantes para nombres de colecciones de Firestore
"""


class FirestoreCollections:
    """Constantes para nombres de colecciones de Firestore"""

    # Colecciones principales
    EVENTS = "events"
    USERS = "users"
    EVENT_TRACKING = "events_tracking"

    # Catálogos (documento fijo "default", subcolecciones)
    CATALOGS = "catalogs"
    CATALOGS_DEFAULT_DOC_ID = "default"
    CATALOGS_VEHICLES = "vehicles"
    CATALOGS_YEARS = "years"
    CATALOGS_COLORS = "colors"

    # Colecciones de usuarios relacionados (subcolecciones bajo users)
    USER_VEHICLES = "vehicles"

    # Colecciones de eventos relacionados
    EVENT_CHECKPOINTS = "checkpoints"
    DAY_OF_RACES = "day_of_races"
    EVENT_CATEGORIES = "event_categories"
    EVENT_PARTICIPANTS = "participants"
    EVENT_STAFF = "staff_users"
    EVENT_ROUTES = "routes"
    EVENT_CONTENT = "event_content"

    # Colecciones de tracking
    EVENT_TRACKING_COMPETITOR_TRACKING = "competitor_tracking"
    EVENT_TRACKING_COMPETITOR = "competitors"
    EVENT_TRACKING_CHECKPOINTS = "checkpoints"
