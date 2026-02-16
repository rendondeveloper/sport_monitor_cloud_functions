"""
Tests para get_competitor_by_id Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path
2. Parámetros faltantes
3. Valor/tipo incorrecto
4. Consultas con data (mock Firestore)
5. Escrituras exitosas (N/A para GET)
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
    with patch(
        "competitors.get_competitor_by_id.validate_request", return_value=None
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch(
        "competitors.get_competitor_by_id.verify_bearer_token", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("competitors.get_competitor_by_id.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def sample_competitor_doc():
    """Documento de competidor como viene de Firestore."""
    return {
        "eventId": "event123",
        "competitionCategory": {
            "pilotNumber": "42",
            "registrationCategory": "Pro",
        },
        "registrationDate": "2026-02-15T10:00:00",
        "team": "Team Red Bull",
        "score": 10,
        "timesToStart": [],
        "createdAt": "2026-02-15T08:00:00",
        "updatedAt": "2026-02-15T09:00:00",
    }


def _make_request(event_id="", competitor_id="", method="GET"):
    req = MagicMock()
    req.method = method
    req.args = {}
    req.path = ""
    req.headers = {"Authorization": "Bearer test_token"}

    if event_id:
        req.args["eventId"] = event_id
    if competitor_id:
        req.args["competitorId"] = competitor_id

    return req


# ============================================================================
# TESTS
# ============================================================================


class TestGetCompetitorByIdHappyPath:
    """Happy path: competidor encontrado y retornado correctamente."""

    def test_get_competitor_success(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_competitor_doc,
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        mock_firestore_helper.get_document.return_value = sample_competitor_doc

        req = _make_request(event_id="event123", competitor_id="comp456")
        response = get_competitor_by_id(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "comp456"
        assert data["eventId"] == "event123"
        assert data["competitionCategory"]["pilotNumber"] == "42"
        assert data["team"] == "Team Red Bull"
        assert data["score"] == 10


class TestGetCompetitorByIdMissingParams:
    """Parámetros faltantes -> 400."""

    def test_missing_event_id(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        req = _make_request(competitor_id="comp456")
        response = get_competitor_by_id(req)
        assert response.status_code == 400

    def test_missing_competitor_id(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        req = _make_request(event_id="event123")
        response = get_competitor_by_id(req)
        assert response.status_code == 400

    def test_missing_both_params(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        req = _make_request()
        response = get_competitor_by_id(req)
        assert response.status_code == 400


class TestGetCompetitorByIdAuth:
    """Token inválido -> 401."""

    def test_invalid_token(self, mock_validate_request):
        from competitors.get_competitor_by_id import get_competitor_by_id

        with patch(
            "competitors.get_competitor_by_id.verify_bearer_token",
            return_value=False,
        ):
            req = _make_request(event_id="ev1", competitor_id="c1")
            response = get_competitor_by_id(req)
            assert response.status_code == 401


class TestGetCompetitorByIdNotFound:
    """Competidor no encontrado -> 404."""

    def test_competitor_not_found(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        mock_firestore_helper.get_document.return_value = None

        req = _make_request(event_id="event123", competitor_id="nonexistent")
        response = get_competitor_by_id(req)
        assert response.status_code == 404


class TestGetCompetitorByIdQueryWithData:
    """Consultas con data: verificar que la respuesta incluye datos correctos."""

    def test_response_includes_all_fields(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        doc = {
            "eventId": "ev1",
            "competitionCategory": {
                "pilotNumber": "99",
                "registrationCategory": "Amateur",
            },
            "registrationDate": "2026-01-01T00:00:00",
            "team": "Solo",
            "score": 5,
            "timesToStart": [{"time": "08:00"}],
            "createdAt": "2026-01-01T00:00:00",
            "updatedAt": "2026-01-02T00:00:00",
        }
        mock_firestore_helper.get_document.return_value = doc

        req = _make_request(event_id="ev1", competitor_id="c99")
        response = get_competitor_by_id(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["score"] == 5
        assert data["timesToStart"] == [{"time": "08:00"}]
        assert data["competitionCategory"]["registrationCategory"] == "Amateur"


class TestGetCompetitorByIdPathParams:
    """Parámetros extraídos del path."""

    def test_params_from_path(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_competitor_doc,
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        mock_firestore_helper.get_document.return_value = sample_competitor_doc

        req = MagicMock()
        req.method = "GET"
        req.args = {}
        req.path = "/api/competitors/get-competitor-by-id/event123/comp456"
        req.headers = {"Authorization": "Bearer test_token"}

        response = get_competitor_by_id(req)
        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "comp456"


class TestGetCompetitorByIdExceptions:
    """Excepciones -> códigos apropiados."""

    def test_value_error_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        mock_firestore_helper.get_document.side_effect = ValueError("bad")

        req = _make_request(event_id="ev1", competitor_id="c1")
        response = get_competitor_by_id(req)
        assert response.status_code == 400

    def test_runtime_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        mock_firestore_helper.get_document.side_effect = RuntimeError("crash")

        req = _make_request(event_id="ev1", competitor_id="c1")
        response = get_competitor_by_id(req)
        assert response.status_code == 500


class TestGetCompetitorByIdMultipleCalls:
    """Múltiples llamadas estables."""

    def test_multiple_calls(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_competitor_doc,
    ):
        from competitors.get_competitor_by_id import get_competitor_by_id

        mock_firestore_helper.get_document.return_value = sample_competitor_doc

        for _ in range(3):
            req = _make_request(event_id="event123", competitor_id="comp456")
            response = get_competitor_by_id(req)
            assert response.status_code == 200
