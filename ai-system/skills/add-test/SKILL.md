# Skill: /add-test

**Categoria**: Testing
**Agente responsable**: functions-test

---

## Cuando usar

Siempre después de crear o modificar una Cloud Function.
Cobertura mínima: 90%.

---

## Naming convention

| Tipo | Archivo |
|------|---------|
| Cloud Function | `tests/test_<module>_<function>.py` |
| Util/Helper | `tests/test_utils_<helper_name>.py` |
| Modelo | `tests/test_models_<model_name>.py` |

---

## Template completo con todos los casos obligatorios

```python
"""
Tests para <function_name> — <módulo>.

Casos cubiertos:
1. Happy path — respuesta correcta con data
2. Parámetro requerido faltante → 400
3. Parámetro con solo espacios → 400
4. Token inválido → 401
5. Recurso no encontrado → 404 (solo para GET objeto único)
6. Error interno Firestore → 500
7. Estructura completa de campos en respuesta
8. Verificar llamadas correctas a FirestoreHelper
9. Múltiples llamadas estables
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES — reutilizables entre todos los tests del archivo
# ============================================================================


@pytest.fixture
def mock_validate_request():
    """Evita que validate_request bloquee el test — retorna None (sin respuesta)."""
    with patch(
        "<module>.<function_name>.validate_request", return_value=None
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    """Simula token válido."""
    with patch(
        "<module>.<function_name>.verify_bearer_token", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    """Mock de FirestoreHelper — retorna instancia mockeada."""
    with patch("<module>.<function_name>.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def sample_documents():
    """
    Documentos de ejemplo como retorna FirestoreHelper.query_documents.
    Formato: List[Tuple[str, Dict]]
    """
    return [
        (
            "doc_id_1",
            {
                "eventId": "event123",
                "field1": "value1",
                "score": 10,
                "createdAt": "2026-03-01T10:00:00",
                "updatedAt": "2026-03-01T10:00:00",
            },
        ),
        (
            "doc_id_2",
            {
                "eventId": "event123",
                "field1": "value2",
                "score": 5,
                "createdAt": "2026-03-02T10:00:00",
                "updatedAt": "2026-03-02T10:00:00",
            },
        ),
    ]


@pytest.fixture
def sample_doc():
    """Documento único como retorna FirestoreHelper.get_document."""
    return {
        "eventId": "event123",
        "field1": "value1",
        "status": "active",
        "createdAt": "2026-03-01T10:00:00",
        "updatedAt": "2026-03-01T10:00:00",
    }


def _make_get_request(args=None, path=""):
    """Crea mock de HTTP GET request."""
    req = MagicMock()
    req.method = "GET"
    req.args = args or {}
    req.path = path
    req.headers = {"Authorization": "Bearer valid_test_token"}
    return req


def _make_post_request(body=None):
    """Crea mock de HTTP POST request."""
    req = MagicMock()
    req.method = "POST"
    req.args = {}
    req.headers = {"Authorization": "Bearer valid_test_token"}
    req.get_json.return_value = body
    return req


# ============================================================================
# HAPPY PATH
# ============================================================================


class TestHappyPath:
    """Casos de éxito — status 200/201."""

    def test_returns_200_with_list(
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

    def test_empty_list_returns_200_not_404(
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
        assert data == []  # lista vacía, nunca 404


# ============================================================================
# PARAMETROS FALTANTES — 400
# ============================================================================


class TestMissingParams:
    """Parámetros requeridos faltantes → 400."""

    def test_missing_event_id_returns_400(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from <module>.<function_name> import <function_name>

        req = _make_get_request()  # sin eventId
        response = <function_name>(req)
        assert response.status_code == 400

    def test_empty_event_id_returns_400(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from <module>.<function_name> import <function_name>

        req = _make_get_request(args={"eventId": ""})
        response = <function_name>(req)
        assert response.status_code == 400

    def test_whitespace_event_id_returns_400(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from <module>.<function_name> import <function_name>

        req = _make_get_request(args={"eventId": "   "})
        response = <function_name>(req)
        assert response.status_code == 400


# ============================================================================
# AUTH — 401
# ============================================================================


class TestAuthentication:
    """Token inválido o faltante → 401."""

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
# ESTRUCTURA DE RESPUESTA — verificar campos
# ============================================================================


class TestResponseStructure:
    """Verificar shape de la respuesta."""

    def test_response_has_required_fields(
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
            assert "field1" in item
            assert "createdAt" in item
            assert "updatedAt" in item

    def test_response_is_valid_json(
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

        # No debe lanzar excepción
        data = json.loads(response.response[0])
        assert data is not None

    def test_no_wrapper_in_response(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        """Verifica que no hay wrappers success/data/message."""
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.return_value = sample_documents

        req = _make_get_request(args={"eventId": "event123"})
        response = <function_name>(req)

        data = json.loads(response.response[0])
        # Para listas: data es list, no dict
        assert isinstance(data, list)
        # Si fuera objeto: assert "success" not in data


# ============================================================================
# LLAMADAS CORRECTAS A FIRESTORE
# ============================================================================


class TestFirestoreInteraction:
    """Verificar que FirestoreHelper se llama correctamente."""

    def test_query_called_with_correct_collection_path(
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
        collection_path = call_args[0][0]
        assert "event123" in collection_path
        assert "participants" in collection_path

    def test_optional_filter_applied_when_provided(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.return_value = [sample_documents[0]]

        req = _make_get_request(args={"eventId": "event123", "category": "Pro"})
        <function_name>(req)

        call_args = mock_firestore_helper.query_documents.call_args
        kwargs = call_args.kwargs if call_args.kwargs else call_args[1]
        filters = kwargs.get("filters") or []
        assert any("Pro" in str(f.get("value", "")) for f in filters)


# ============================================================================
# EXCEPCIONES
# ============================================================================


class TestExceptions:
    """Manejo de excepciones → códigos apropiados."""

    def test_value_error_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.side_effect = ValueError("invalid data")

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

        mock_firestore_helper.query_documents.side_effect = RuntimeError("db crash")

        req = _make_get_request(args={"eventId": "event123"})
        response = <function_name>(req)
        assert response.status_code == 500

    def test_key_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.side_effect = KeyError("missing_key")

        req = _make_get_request(args={"eventId": "event123"})
        response = <function_name>(req)
        assert response.status_code == 500


# ============================================================================
# MULTIPLES LLAMADAS
# ============================================================================


class TestMultipleCalls:
    """Estabilidad bajo múltiples llamadas."""

    def test_three_sequential_calls_consistent(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.return_value = sample_documents

        for i in range(3):
            req = _make_get_request(args={"eventId": f"event{i}"})
            response = <function_name>(req)
            assert response.status_code == 200
            data = json.loads(response.response[0])
            assert isinstance(data, list)

    def test_different_event_ids_call_firestore_each_time(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from <module>.<function_name> import <function_name>

        mock_firestore_helper.query_documents.return_value = sample_documents
        event_ids = ["event1", "event2", "event3"]

        for event_id in event_ids:
            req = _make_get_request(args={"eventId": event_id})
            <function_name>(req)

        assert mock_firestore_helper.query_documents.call_count == 3
```

---

## Comandos para ejecutar

```bash
# Test individual con cobertura del módulo
pytest functions/tests/test_<module>_<function>.py -v \
  --cov=functions/<module>/<function_name> \
  --cov-report=term-missing \
  --cov-fail-under=90

# Todos los tests del módulo
pytest functions/tests/ -v -k "<module>" --cov=functions/<module> --cov-fail-under=90

# Todos los tests del proyecto
pytest functions/tests/ -v --cov=functions --cov-fail-under=90
```
