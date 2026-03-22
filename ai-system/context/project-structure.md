# Project Structure — Sport Monitor Cloud Functions

## Estructura completa de functions/

```
functions/
├── main.py                          # Entry point — importa y registra TODAS las funciones
│
├── catalogs/                        # Catálogos del sistema (vehículos, años, colores, etc.)
│   ├── __init__.py
│   └── <catalog_function>.py
│
├── checkpoints/                     # Gestión de checkpoints de carrera
│   ├── __init__.py
│   ├── all_competitor_tracking.py
│   ├── change_competitor_status.py
│   ├── checkpoint.py
│   ├── competitor_tracking.py
│   ├── day_of_race_active.py
│   ├── days_of_race.py
│   └── update_competitor_status.py
│
├── competitors/                     # Competidores — CRUD principal
│   ├── __init__.py
│   ├── competitor_route.py
│   ├── create_competitor.py
│   ├── create_competitor_user.py    # Flujo A (nuevo) + Flujo B (existente)
│   ├── delete_competitor.py
│   ├── delete_competitor_user.py
│   ├── get_competitor_by_email.py
│   ├── get_competitor_by_id.py
│   ├── get_competitors_by_event.py
│   ├── get_event_competitor_by_email.py
│   ├── get_event_competitor_by_id.py
│   └── list_competitors_by_event.py
│
├── events/                          # Eventos deportivos
│   ├── __init__.py
│   ├── event_categories.py
│   ├── event_short_document.py
│   ├── events_customer.py
│   └── events_detail_customer.py
│
├── monitor/                         # Monitoreo en tiempo real
│   └── ...
│
├── staff/                           # Personal del evento
│   ├── __init__.py
│   └── create_staff_user.py
│
├── tracking/                        # Tracking de posición y checkpoints
│   ├── track_competitor_position.py
│   ├── tracking_checkpoint.py
│   └── tracking_competitors.py
│
├── users/                           # Gestión de usuarios
│   ├── __init__.py
│   ├── create.py
│   ├── delete_section_item.py
│   ├── read.py
│   ├── read_sections.py
│   ├── subscribed_events.py
│   ├── update.py
│   └── user_route.py               # Dispatcher — despacha por path a create/read/update
│
├── vehicles/                        # Vehículos de usuarios
│   ├── __init__.py
│   ├── delete_vehicle.py
│   ├── get_vehicles.py
│   ├── search_vehicle.py
│   └── update_vehicle.py
│
├── models/
│   ├── firestore_collections.py     # FirestoreCollections — SIEMPRE usar
│   ├── checkpoint_tracking.py
│   ├── competitor_tracking.py
│   ├── event_document.py
│   ├── events_response.py
│   └── paginated_response.py
│
├── utils/
│   ├── firestore_helper.py          # FirestoreHelper — CRUD centralizado
│   ├── helper_http.py               # verify_bearer_token()
│   ├── helper_http_verb.py          # validate_request()
│   ├── auth_helper.py               # Firebase Auth CRUD
│   ├── validation_helper.py         # Email, phone, password, required fields
│   ├── datetime_helper.py           # get_current_timestamp()
│   └── helpers.py                   # convert_firestore_value(), format_utc_to_local_datetime()
│
└── tests/
    ├── __init__.py
    ├── test_catalog_relationship_type.py
    ├── test_create_competitor_user.py
    ├── test_create_competitor.py
    ├── test_create_staff_user.py
    ├── test_create_user.py
    ├── test_delete_section_item.py
    ├── test_delete_vehicle.py
    ├── test_get_competitor_by_email.py
    ├── test_get_competitor_by_id.py
    ├── test_get_competitors_by_event.py
    ├── test_get_event_competitor_by_email.py
    ├── test_get_event_competitor_by_id.py
    ├── test_list_competitors_by_event.py
    ├── test_read_sections.py
    ├── test_search_vehicle.py
    ├── test_subscribed_events.py
    ├── test_track_competitor_position.py
    └── test_update_user.py
```

---

## Cómo registrar una función nueva en main.py

Toda función nueva debe registrarse en `functions/main.py` para que Firebase la exponga.

### Paso 1 — Crear el archivo

```
functions/competitors/get_competitor_stats.py
```

### Paso 2 — Exportar desde `__init__.py` del módulo

```python
# functions/competitors/__init__.py
from competitors.get_competitor_stats import get_competitor_stats
```

### Paso 3 — Importar en main.py

```python
# functions/main.py — añadir al bloque del módulo correspondiente
from competitors import (
    # ... funciones existentes ...
    get_competitor_stats,   # nueva función
)
```

### Paso 4 — Verificar con firebase emulator

```bash
firebase emulators:start --only functions
```

---

## FirestoreCollections — todas las constantes

```python
class FirestoreCollections:
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
    CATALOGS_RELATIONSHIP_TYPES = "relationship_types"

    # Subcolecciones de users
    USER_VEHICLES = "vehicles"
    USER_MEMBERSHIP = "membership"
    USER_EMERGENCY_CONTACT = "emergencyContacts"
    USER_HEALTH_DATA = "healthData"
    USER_PERSONAL_DATA = "personalData"

    # Subcolecciones de eventos
    EVENT_CHECKPOINTS = "checkpoints"
    DAY_OF_RACES = "day_of_races"
    EVENT_CATEGORIES = "event_categories"
    EVENT_PARTICIPANTS = "participants"        # events/{eventId}/participants
    EVENT_STAFF = "staff_users"
    EVENT_ROUTES = "routes"
    EVENT_CONTENT = "event_content"

    # Subcolecciones de participantes
    PARTICIPANT_EMERGENCY_CONTACTS = "emergencyContacts"
    PARTICIPANT_VEHICLE = "vehicle"

    # Tracking
    EVENT_TRACKING_COMPETITOR_TRACKING = "competitor_tracking"
    EVENT_TRACKING_COMPETITOR = "competitors"
    EVENT_TRACKING_CHECKPOINTS = "checkpoints"
```

Para añadir una colección nueva, agregarla en `models/firestore_collections.py` antes de usarla.

---

## FirestoreHelper — métodos disponibles

```python
from utils.firestore_helper import FirestoreHelper

helper = FirestoreHelper()

# Leer documento por ID
doc_data = helper.get_document(collection_path, document_id)
# Retorna: Dict[str, Any] | None

# Crear documento (ID autogenerado)
new_id = helper.create_document(collection_path, data)
# Retorna: str (ID del documento)

# Crear documento con ID específico
doc_id = helper.create_document_with_id(collection_path, document_id, data)
# Útil para membership donde el ID = eventId

# Actualizar documento (merge parcial)
success = helper.update_document(collection_path, document_id, {"field": "value"})
# Retorna: bool

# Eliminar documento
success = helper.delete_document(collection_path, document_id)
# Retorna: bool

# Listar IDs de documentos en una colección
ids = helper.list_document_ids(collection_path)
# Retorna: List[str]

# Query con filtros, ordenamiento y paginación
results = helper.query_documents(
    collection_path,
    filters=[
        {"field": "eventId", "operator": "==", "value": "abc123"},
        {"field": "status", "operator": "in", "value": ["active", "pending"]},
    ],
    order_by=[("createdAt", "desc")],
    limit=50,
    start_after_doc_id="last_doc_id",  # para paginación
)
# Retorna: List[Tuple[str, Dict[str, Any]]]  →  [(doc_id, doc_data), ...]

# Batch update (múltiples documentos en una transacción)
success = helper.batch_update([
    (collection_path_1, doc_id_1, {"field": "value1"}),
    (collection_path_2, doc_id_2, {"field": "value2"}),
])
# Retorna: bool
```

### Operadores soportados en query_documents filters

- `"=="` — igualdad exacta
- `"!="` — diferente
- `"<"`, `"<="`, `">"`, `">="` — comparación
- `"in"` — valor en lista
- `"not-in"` — valor no en lista
- `"array-contains"` — elemento en array
- `"array-contains-any"` — algún elemento de lista en array

---

## Utils disponibles

### helper_http.py — verify_bearer_token

```python
from utils.helper_http import verify_bearer_token

# Verifica Bearer token contra Firebase Auth
is_valid = verify_bearer_token(req, "function_name")
# Retorna: bool — True si válido, False si inválido o faltante
```

### helper_http_verb.py — validate_request

```python
from utils.helper_http_verb import validate_request

# Maneja OPTIONS preflight (204) y valida método HTTP (405)
response = validate_request(req, ["GET"], "function_name", return_json_error=False)
# Retorna: Response (para retornar) | None (continuar)
```

### datetime_helper.py — get_current_timestamp

```python
from utils.datetime_helper import get_current_timestamp

timestamp = get_current_timestamp()
# Retorna: datetime UTC actual — usar para createdAt y updatedAt
```

### helpers.py — convert_firestore_value

```python
from utils.helpers import convert_firestore_value, format_utc_to_local_datetime

# Convierte Firestore Timestamp a string ISO 8601
date_str = convert_firestore_value(doc_data.get("createdAt"))
# Retorna: str | None

# Formatea UTC a datetime local
local_dt = format_utc_to_local_datetime(utc_datetime, "America/Mexico_City")
```

### validation_helper.py

```python
from utils.validation_helper import (
    validate_email,
    validate_phone,
    validate_required_fields,
    validate_password,
)

validate_email("user@example.com")      # bool
validate_phone("+521234567890")          # bool
validate_required_fields(body, ["email", "name", "eventId"])  # lista de campos faltantes
validate_password("Pass123!")           # bool
```

### auth_helper.py

```python
from utils.auth_helper import (
    create_firebase_auth_user,
    delete_firebase_auth_user,
    update_firebase_auth_email,
    update_firebase_auth_password,
)

uid = create_firebase_auth_user("email@example.com", "password123", "Nombre Completo")
delete_firebase_auth_user(uid)
```

---

## Estructura de tests

Convención de nombres: `tests/test_<module>_<function>.py`

```python
# tests/test_competitors_get_competitors_by_event.py
import json
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_validate_request():
    with patch("competitors.get_competitors_by_event.validate_request", return_value=None) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch("competitors.get_competitors_by_event.verify_bearer_token", return_value=True) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("competitors.get_competitors_by_event.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


def _make_request(method="GET", args=None, body=None, path=""):
    req = MagicMock()
    req.method = method
    req.args = args or {}
    req.path = path
    req.headers = {"Authorization": "Bearer test_token"}
    if body is not None:
        req.get_json.return_value = body
    return req
```

---

## Módulos y sus responsabilidades

| Módulo | Responsabilidad | Region |
|--------|----------------|--------|
| `competitors/` | CRUD competidores, registro en eventos | us-east4 |
| `events/` | Consulta de eventos, categorías, detalle | us-central1 |
| `users/` | CRUD usuarios, secciones, eventos suscritos | us-central1 |
| `checkpoints/` | Estado de competidores, días de carrera | us-east4 |
| `tracking/` | Posición GPS, checkpoints en tiempo real | us-east4 |
| `catalogs/` | Catálogos de vehículos, años, colores, tipos | us-east4 |
| `vehicles/` | Vehículos de usuarios | us-east4 |
| `staff/` | Personal del evento | us-central1 |
| `monitor/` | Monitoreo en tiempo real | us-central1 |
