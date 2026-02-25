"""
Tests para create_competitor Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path
2. Parámetros faltantes
3. Valor/tipo incorrecto
4. Consultas con data (mock Firestore)
5. Escrituras exitosas
6. Múltiples llamadas al mismo API
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_validate_request():
    """Mock validate_request que siempre retorna None (válido)."""
    with patch(
        "competitors.create_competitor.validate_request", return_value=None
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    """Mock verify_bearer_token que siempre retorna True."""
    with patch(
        "competitors.create_competitor.verify_bearer_token", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    """Mock FirestoreHelper."""
    with patch("competitors.create_competitor.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def valid_request_body():
    """Body válido para crear un competidor."""
    return {
        "userId": "user_abc",
        "eventId": "event123",
        "competitionCategory": {
            "pilotNumber": "42",
            "registrationCategory": "Pro",
        },
        "team": "Team Red Bull",
    }


def _make_request(body=None, method="POST"):
    """Crea un mock de Request."""
    req = MagicMock()
    req.method = method
    req.get_json.return_value = body
    req.args = {}
    req.path = ""
    req.headers = {"Authorization": "Bearer test_token"}
    return req


# ============================================================================
# TESTS
# ============================================================================


class TestCreateCompetitorHappyPath:
    """Happy path: request válido con todos los parámetros correctos."""

    def test_create_competitor_success(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor import create_competitor

        # Mock: usuario existe, evento existe, participante no existe
        mock_firestore_helper.get_document.side_effect = [
            {"email": "test@example.com"},
            {"name": "Test Event"},
            None,
        ]
        # Mock: no hay duplicados
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(body=valid_request_body)
        response = create_competitor(req)

        assert response.status_code == 201
        data = json.loads(response.response[0])
        assert data["id"] == "user_abc"

    def test_create_competitor_without_pilot_number(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.create_competitor import create_competitor

        body = {
            "userId": "user_no_pilot",
            "eventId": "event123",
            "competitionCategory": {
                "pilotNumber": "",
                "registrationCategory": "Amateur",
            },
        }

        # Mock: usuario existe, evento existe, participante no existe
        mock_firestore_helper.get_document.side_effect = [
            {"email": "test@example.com"},
            {"name": "Event"},
            None,
        ]

        req = _make_request(body=body)
        response = create_competitor(req)

        assert response.status_code == 201
        mock_firestore_helper.query_documents.assert_not_called()


class TestCreateCompetitorMissingParams:
    """Parámetros faltantes: body o campos faltantes -> 400."""

    def test_missing_body(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
    ):
        from competitors.create_competitor import create_competitor

        req = _make_request(body=None)
        response = create_competitor(req)

        assert response.status_code == 400

    def test_missing_user_id(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
    ):
        from competitors.create_competitor import create_competitor

        req = _make_request(body={"eventId": "event123"})
        response = create_competitor(req)

        assert response.status_code == 400

    def test_missing_event_id(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
    ):
        from competitors.create_competitor import create_competitor

        req = _make_request(body={"userId": "user_abc", "competitionCategory": {}})
        response = create_competitor(req)

        assert response.status_code == 400

    def test_empty_event_id(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
    ):
        from competitors.create_competitor import create_competitor

        req = _make_request(body={"userId": "user_abc", "eventId": "  "})
        response = create_competitor(req)

        assert response.status_code == 400


class TestCreateCompetitorInvalidType:
    """Valor/tipo incorrecto -> 400."""

    def test_event_id_not_string(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
    ):
        from competitors.create_competitor import create_competitor

        req = _make_request(body={"userId": "user_abc", "eventId": 12345})
        response = create_competitor(req)

        assert response.status_code == 400


class TestCreateCompetitorAuth:
    """Token inválido -> 401."""

    def test_invalid_token(self, mock_validate_request):
        from competitors.create_competitor import create_competitor

        with patch(
            "competitors.create_competitor.verify_bearer_token", return_value=False
        ):
            req = _make_request(body={"eventId": "event123"})
            response = create_competitor(req)

            assert response.status_code == 401


class TestCreateCompetitorNotFound:
    """Evento o usuario no encontrado -> 404."""

    def test_user_not_found(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.create_competitor import create_competitor

        mock_firestore_helper.get_document.return_value = None

        req = _make_request(body={"userId": "nonexistent", "eventId": "event123"})
        response = create_competitor(req)

        assert response.status_code == 404

    def test_event_not_found(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.create_competitor import create_competitor

        # Usuario existe pero evento no
        mock_firestore_helper.get_document.side_effect = [
            {"email": "test@example.com"},
            None,
        ]

        req = _make_request(body={"userId": "user_abc", "eventId": "nonexistent"})
        response = create_competitor(req)

        assert response.status_code == 404


class TestCreateCompetitorDuplicate:
    """Número de piloto duplicado o participante existente -> 409."""

    def test_duplicate_pilot_number(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor import create_competitor

        # Usuario existe, evento existe, participante no existe
        mock_firestore_helper.get_document.side_effect = [
            {"email": "test@example.com"},
            {"name": "Event"},
            None,
        ]
        mock_firestore_helper.query_documents.return_value = [
            ("existing_id", {"competitionCategory": {"pilotNumber": "42"}})
        ]

        req = _make_request(body=valid_request_body)
        response = create_competitor(req)

        assert response.status_code == 409


class TestCreateCompetitorJsonParseError:
    """Error al parsear JSON."""

    def test_json_parse_error(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
    ):
        from competitors.create_competitor import create_competitor

        req = _make_request(body=None)
        req.get_json.side_effect = ValueError("bad json")
        response = create_competitor(req)
        assert response.status_code == 400


class TestCreateCompetitorExceptions:
    """Excepciones internas -> 500."""

    def test_value_error_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.create_competitor import create_competitor

        mock_firestore_helper.get_document.side_effect = ValueError("bad value")

        req = _make_request(body={"userId": "user_abc", "eventId": "event123"})
        response = create_competitor(req)
        assert response.status_code == 400

    def test_runtime_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.create_competitor import create_competitor

        mock_firestore_helper.get_document.side_effect = RuntimeError("db crash")

        req = _make_request(body={"userId": "user_abc", "eventId": "event123"})
        response = create_competitor(req)
        assert response.status_code == 500


class TestCreateCompetitorMultipleCalls:
    """Múltiples llamadas al mismo API sin efectos colaterales."""

    def test_multiple_calls_stable(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        valid_request_body,
    ):
        from competitors.create_competitor import create_competitor

        # Cada llamada: usuario existe, evento existe, participante no existe
        mock_firestore_helper.get_document.side_effect = [
            {"email": "t@e.com"}, {"name": "Event"}, None,
            {"email": "t@e.com"}, {"name": "Event"}, None,
            {"email": "t@e.com"}, {"name": "Event"}, None,
        ]
        mock_firestore_helper.query_documents.return_value = []

        for i in range(3):
            req = _make_request(body=valid_request_body)
            response = create_competitor(req)
            assert response.status_code == 201
            data = json.loads(response.response[0])
            assert data["id"] == "user_abc"
