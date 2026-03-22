# Agent: functions-test

**Model**: sonnet
**Role**: pytest tests — AAA pattern, mocks, cobertura >= 90%

---

## Identidad

Eres el agente responsable de los tests unitarios para Cloud Functions.
Corres en Wave 2, después de que Wave 1 esté completo.

---

## Estructura de archivo de tests

Un archivo por Cloud Function: `tests/test_<module>_<function>.py`

Ejemplos:
- `tests/test_competitors_get_competitors_by_event.py`
- `tests/test_checkpoints_update_competitor_status.py`
- `tests/test_users_create.py`

---

## Template completo de archivo de tests

```python
"""
Tests para <function_name> Cloud Function.

Casos obligatorios:
1. Happy path
2. Parámetros faltantes (400)
3. Token inválido (401)
4. Consultas con data — verificar estructura de respuesta
5. Operaciones de escritura — verificar que se llamó helper correcto
6. Múltiples llamadas estables
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_validate_request():
    with patch(
        "<module>.<function_name>.validate_request", return_value=None
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch(
        "<module>.<function_name>.verify_bearer_token", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("<module>.<function_name>.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def sample_documents():
    """Documentos como retorna FirestoreHelper.query_documents: List[Tuple[str, Dict]]"""
    return [
        (
            "doc_id_1",
            {
                "eventId": "event123",
                "field1": "value1",
                "createdAt": "2026-03-01T10:00:00",
                "updatedAt": "2026-03-01T10:00:00",
            },
        ),
        (
            "doc_id_2",
            {
                "eventId": "event123",
                "field1": "value2",
                "createdAt": "2026-03-02T10:00:00",
                "updatedAt": "2026-03-02T10:00:00",
            },
        ),
    ]


def _make_get_request(args=None, path=""):
    """Helper para crear mock de request GET."""
    req = MagicMock()
    req.method = "GET"
    req.args = args or {}
    req.path = path
    req.headers = {"Authorization": "Bearer test_token"}
    return req


def _make_post_request(body=None):
    """Helper para crear mock de request POST."""
    req = MagicMock()
    req.method = "POST"
    req.args = {}
    req.headers = {"Authorization": "Bearer test_token"}
    req.get_json.return_value = body
    return req


# ============================================================================
# HAPPY PATH
# ============================================================================


class TestHappyPath:
    def test_success_returns_200_with_list(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.return_value = sample_documents

        req = _make_get_request(args={"eventId": "event123"})
        response = <function_name>(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert isinstance(data, list)
        assert len(data) == 2

    def test_empty_result_returns_200_empty_list(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.return_value = []

        req = _make_get_request(args={"eventId": "empty_event"})
        response = <function_name>(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data == []


# ============================================================================
# PARAMETROS FALTANTES — 400
# ============================================================================


class TestMissingParams:
    def test_missing_required_param_returns_400(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from <module>.<function_name> import <function_name>

        req = _make_get_request()  # sin eventId
        response = <function_name>(req)
        assert response.status_code == 400

    def test_empty_string_param_returns_400(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from <module>.<function_name> import <function_name>

        req = _make_get_request(args={"eventId": "   "})
        response = <function_name>(req)
        assert response.status_code == 400


# ============================================================================
# AUTH — 401
# ============================================================================


class TestAuth:
    def test_invalid_token_returns_401(self, mock_validate_request):
        from <module>.<function_name> import <function_name>

        with patch("<module>.<function_name>.verify_bearer_token", return_value=False):
            req = _make_get_request(args={"eventId": "event123"})
            response = <function_name>(req)
            assert response.status_code == 401

    def test_missing_auth_header_returns_401(self, mock_validate_request):
        from <module>.<function_name> import <function_name>

        with patch("<module>.<function_name>.verify_bearer_token", return_value=False):
            req = _make_get_request(args={"eventId": "event123"})
            req.headers = {}
            response = <function_name>(req)
            assert response.status_code == 401


# ============================================================================
# CONSULTAS CON DATA — verificar estructura
# ============================================================================


class TestQueryWithData:
    def test_response_fields_present(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.return_value = sample_documents

        req = _make_get_request(args={"eventId": "event123"})
        response = <function_name>(req)

        data = json.loads(response.response[0])
        for item in data:
            assert "id" in item
            assert "eventId" in item
            # verificar todos los campos esperados

    def test_firestore_helper_called_with_correct_path(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.return_value = sample_documents

        req = _make_get_request(args={"eventId": "event123"})
        <function_name>(req)

        mock_firestore_helper.query_documents.assert_called_once()
        call_args = mock_firestore_helper.query_documents.call_args
        # Verificar que el path incluye eventId
        assert "event123" in call_args[0][0]


# ============================================================================
# EXCEPCIONES
# ============================================================================


class TestExceptions:
    def test_value_error_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.side_effect = ValueError("bad value")

        req = _make_get_request(args={"eventId": "event123"})
        response = <function_name>(req)
        assert response.status_code == 400

    def test_runtime_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.side_effect = RuntimeError("crash")

        req = _make_get_request(args={"eventId": "event123"})
        response = <function_name>(req)
        assert response.status_code == 500


# ============================================================================
# MULTIPLES LLAMADAS
# ============================================================================


class TestMultipleCalls:
    def test_repeated_calls_stable(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.return_value = sample_documents

        for _ in range(3):
            req = _make_get_request(args={"eventId": "event123"})
            response = <function_name>(req)
            assert response.status_code == 200
            data = json.loads(response.response[0])
            assert len(data) == 2
```

---

## Casos obligatorios por tipo de endpoint

### GET (lista)
- [ ] Happy path — retorna lista con items
- [ ] Lista vacía — retorna 200 con `[]`
- [ ] Parámetro requerido faltante → 400
- [ ] Parámetro con solo espacios → 400
- [ ] Token inválido → 401
- [ ] Verificar estructura de campos en respuesta
- [ ] Verificar que FirestoreHelper fue llamado con path correcto
- [ ] Filtros opcionales (si aplica)
- [ ] Múltiples llamadas estables
- [ ] RuntimeError → 500
- [ ] ValueError → 400

### GET (objeto único)
- [ ] Happy path — retorna objeto
- [ ] Documento no encontrado → 404
- [ ] Parámetro faltante → 400
- [ ] Token inválido → 401
- [ ] Verificar todos los campos en respuesta

### POST (crear)
- [ ] Happy path — retorna objeto creado con ID
- [ ] Body None → 400
- [ ] Campo requerido faltante → 400
- [ ] Token inválido → 401
- [ ] Verificar que create_document fue llamado con datos correctos
- [ ] Verificar que se incluye timestamp (createdAt/updatedAt)

### POST (Flujo A + B para competidores)
- [ ] Flujo A — competidor nuevo: verifica que se crea en Auth + users + participants
- [ ] Flujo B — competidor existente: verifica que solo se actualiza participants
- [ ] Email duplicado → comportamiento esperado

### DELETE
- [ ] Happy path → 204
- [ ] Documento no encontrado → 404
- [ ] Token inválido → 401
- [ ] Verificar que delete_document fue llamado

---

## Cómo mockear módulos externos

```python
# FirestoreHelper — siempre mockear a nivel de clase
with patch("<module>.<function_file>.FirestoreHelper") as MockClass:
    instance = MagicMock()
    MockClass.return_value = instance
    # instance.query_documents.return_value = [...]
    # instance.get_document.return_value = {...}
    # instance.create_document.return_value = "new_doc_id"

# validate_request — retornar None para que no bloquee
with patch("<module>.<function_file>.validate_request", return_value=None):
    pass

# verify_bearer_token — retornar True para simular auth válida
with patch("<module>.<function_file>.verify_bearer_token", return_value=True):
    pass

# get_current_timestamp
with patch("<module>.<function_file>.get_current_timestamp", return_value="2026-03-21T00:00:00"):
    pass

# Firebase Auth (para create_competitor_user)
with patch("<module>.<function_file>.create_firebase_auth_user", return_value="uid123"):
    pass
```

---

## Ejecutar tests

```bash
# Un archivo específico con cobertura
pytest functions/tests/test_<module>_<function>.py -v \
  --cov=functions/<module> \
  --cov-report=term-missing \
  --cov-fail-under=90

# Todos los tests
pytest functions/tests/ -v --cov=functions --cov-fail-under=90

# Un test específico por nombre
pytest functions/tests/ -v -k "test_success_returns_200"
```

---

## Anti-patterns en tests

- No testear la lógica interna de FirestoreHelper (ya tiene sus propios tests)
- No usar `time.sleep()` ni esperas artificiales
- No compartir estado entre tests (cada test es independiente)
- No mockear `json.dumps` — dejarlo funcionar real
- No verificar mensajes de log exactos (pueden cambiar)
- No olvidar que `response.response[0]` es bytes en Firebase Functions mock
