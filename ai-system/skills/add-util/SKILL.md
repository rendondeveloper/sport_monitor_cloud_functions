# Skill: /add-util

**Categoria**: Código
**Agente responsable**: functions-cross

---

## Cuando usar

- Lógica que se repite en 2+ funciones del mismo módulo o de módulos distintos
- Transformaciones de datos puras (sin side effects)
- Validaciones específicas del dominio no cubiertas por validation_helper.py
- Funciones de formato o conversión

No crear helper para lógica que solo existe en una función — usar `_auxiliar` privada dentro del archivo.

---

## Antes de crear — verificar helpers existentes

```
utils/
├── firestore_helper.py    # CRUD Firestore — NO duplicar
├── helper_http.py         # verify_bearer_token — NO duplicar
├── helper_http_verb.py    # validate_request — NO duplicar
├── auth_helper.py         # Firebase Auth — NO duplicar
├── validation_helper.py   # email, phone, password, required_fields — NO duplicar
├── datetime_helper.py     # get_current_timestamp — NO duplicar
└── helpers.py             # convert_firestore_value, format_utc_to_local_datetime — NO duplicar
```

---

## Template de helper

```python
# utils/<nombre>_helper.py

"""
<Nombre> Helper — <Descripción del propósito>.

Funciones puras para <dominio>. Sin side effects, testeable de forma aislada.
"""

import logging
from typing import Any, Dict, List, Optional

LOG = logging.getLogger(__name__)


def <nombre_funcion>(param1: str, param2: int = 0) -> str:
    """
    <Descripción de una línea>.

    Args:
        param1: <descripción> (requerido)
        param2: <descripción> (default: 0)

    Returns:
        <descripción del valor retornado>

    Raises:
        ValueError: Si param1 está vacío o param2 es negativo.

    Examples:
        >>> <nombre_funcion>("input", 5)
        "resultado"
        >>> <nombre_funcion>("")
        Raises ValueError
    """
    if not param1 or not param1.strip():
        raise ValueError(f"param1 no puede estar vacío")
    if param2 < 0:
        raise ValueError(f"param2 no puede ser negativo: {param2}")

    # Lógica de transformación
    result = param1.strip().lower()
    return result
```

---

## Ejemplos de helpers útiles para este proyecto

### competitor_helper.py — rutas de colecciones

```python
# utils/competitor_helper.py

"""
Competitor Helper — Rutas de colecciones para operaciones de competidores.
"""

from models.firestore_collections import FirestoreCollections


def get_participants_path(event_id: str) -> str:
    """
    Construye la ruta de la subcolección de participantes.

    Args:
        event_id: ID del evento.

    Returns:
        Path: "events/{event_id}/participants"

    Raises:
        ValueError: Si event_id está vacío.
    """
    if not event_id or not event_id.strip():
        raise ValueError("event_id no puede estar vacío")
    return (
        f"{FirestoreCollections.EVENTS}/{event_id.strip()}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}"
    )


def get_participant_vehicle_path(event_id: str, user_id: str) -> str:
    """Ruta de vehículo de participante: events/{eventId}/participants/{userId}/vehicle"""
    if not event_id or not user_id:
        raise ValueError("event_id y user_id son requeridos")
    return (
        f"{FirestoreCollections.EVENTS}/{event_id}"
        f"/{FirestoreCollections.EVENT_PARTICIPANTS}/{user_id}"
        f"/{FirestoreCollections.PARTICIPANT_VEHICLE}"
    )


def build_competitor_response(doc_id: str, data: dict) -> dict:
    """
    Convierte documento Firestore de participante a dict de respuesta API.
    Reutilizable en get_competitor_by_id, get_competitors_by_event, etc.
    """
    from utils.helpers import convert_firestore_value

    competition_category = data.get("competitionCategory", {})
    return {
        "id": doc_id,
        "competitionCategory": {
            "pilotNumber": competition_category.get("pilotNumber", ""),
            "registrationCategory": competition_category.get("registrationCategory", ""),
        },
        "registrationDate": convert_firestore_value(data.get("registrationDate")),
        "team": data.get("team", ""),
        "score": data.get("score", 0),
        "timesToStart": data.get("timesToStart", []),
        "createdAt": convert_firestore_value(data.get("createdAt")),
        "updatedAt": convert_firestore_value(data.get("updatedAt")),
    }
```

### time_helper.py — cálculos de tiempo de carrera

```python
# utils/time_helper.py

"""
Time Helper — Utilidades para calcular tiempos de carrera.
"""

from typing import Optional


def calculate_final_time(
    base_time_seconds: float,
    penalty_count: int,
    penalty_seconds: float = 10.0,
) -> float:
    """
    Calcula el tiempo final de un competidor con penalizaciones.

    Args:
        base_time_seconds: Tiempo base en segundos.
        penalty_count: Número de penalizaciones.
        penalty_seconds: Segundos por penalización (default: 10).

    Returns:
        Tiempo final = base_time + (penalty_count * penalty_seconds)

    Raises:
        ValueError: Si base_time_seconds es negativo o penalty_count es negativo.
    """
    if base_time_seconds < 0:
        raise ValueError(f"base_time_seconds no puede ser negativo: {base_time_seconds}")
    if penalty_count < 0:
        raise ValueError(f"penalty_count no puede ser negativo: {penalty_count}")
    return base_time_seconds + (penalty_count * penalty_seconds)


def seconds_to_hms(total_seconds: float) -> str:
    """
    Convierte segundos totales a formato HH:MM:SS.

    Args:
        total_seconds: Tiempo en segundos.

    Returns:
        String en formato "HH:MM:SS".

    Examples:
        >>> seconds_to_hms(3661)
        "01:01:01"
    """
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
```

---

## Reglas de helpers

1. **Funciones puras** — misma entrada = misma salida, sin side effects
2. **Sin imports de Firebase** — helpers no deben llamar a Firestore directamente
3. **Documentación obligatoria** — docstring con Args, Returns, Raises, Examples
4. **Nombres descriptivos** — `calculate_final_time`, no `calc_time`
5. **Una responsabilidad** — no mezclar dominio en el mismo helper
6. **Testeable de forma aislada** — no requiere mocks para la lógica core

---

## Test del helper

```python
# tests/test_utils_time_helper.py

import pytest
from utils.time_helper import calculate_final_time, seconds_to_hms


class TestCalculateFinalTime:
    def test_no_penalties(self):
        assert calculate_final_time(3600.0, 0) == 3600.0

    def test_with_penalties(self):
        assert calculate_final_time(3600.0, 3, 10.0) == 3630.0

    def test_negative_base_time_raises(self):
        with pytest.raises(ValueError):
            calculate_final_time(-1.0, 0)

    def test_negative_penalty_raises(self):
        with pytest.raises(ValueError):
            calculate_final_time(3600.0, -1)


class TestSecondsToHms:
    def test_exact_hour(self):
        assert seconds_to_hms(3600) == "01:00:00"

    def test_mixed(self):
        assert seconds_to_hms(3661) == "01:01:01"

    def test_zero(self):
        assert seconds_to_hms(0) == "00:00:00"
```
