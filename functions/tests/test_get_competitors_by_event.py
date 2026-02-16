"""
Tests para get_competitors_by_event Cloud Function.

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
        "competitors.get_competitors_by_event.validate_request", return_value=None
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch(
        "competitors.get_competitors_by_event.verify_bearer_token", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("competitors.get_competitors_by_event.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def sample_documents():
    """Lista de documentos como retorna FirestoreHelper.query_documents."""
    return [
        (
            "comp1",
            {
                "eventId": "event123",
                "competitionCategory": {
                    "pilotNumber": "1",
                    "registrationCategory": "Pro",
                },
                "registrationDate": "2026-02-15T10:00:00",
                "team": "Team A",
                "score": 10,
                "timesToStart": [],
                "createdAt": "2026-02-15T08:00:00",
                "updatedAt": "2026-02-15T09:00:00",
            },
        ),
        (
            "comp2",
            {
                "eventId": "event123",
                "competitionCategory": {
                    "pilotNumber": "2",
                    "registrationCategory": "Amateur",
                },
                "registrationDate": "2026-02-14T10:00:00",
                "team": "Team B",
                "score": 5,
                "timesToStart": [],
                "createdAt": "2026-02-14T08:00:00",
                "updatedAt": "2026-02-14T09:00:00",
            },
        ),
    ]


def _make_request(event_id="", category="", team="", method="GET"):
    req = MagicMock()
    req.method = method
    req.args = {}
    req.path = ""
    req.headers = {"Authorization": "Bearer test_token"}

    if event_id:
        req.args["eventId"] = event_id
    if category:
        req.args["category"] = category
    if team:
        req.args["team"] = team

    return req


# ============================================================================
# TESTS
# ============================================================================


class TestGetCompetitorsByEventHappyPath:
    """Happy path: lista de competidores retornada correctamente."""

    def test_get_competitors_success(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        mock_firestore_helper.query_documents.return_value = sample_documents

        req = _make_request(event_id="event123")
        response = get_competitors_by_event(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == "comp1"
        assert data[1]["id"] == "comp2"

    def test_get_competitors_empty(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(event_id="event_empty")
        response = get_competitors_by_event(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data == []


class TestGetCompetitorsByEventWithFilters:
    """Filtros opcionales (category, team)."""

    def test_filter_by_category(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        mock_firestore_helper.query_documents.return_value = [sample_documents[0]]

        req = _make_request(event_id="event123", category="Pro")
        response = get_competitors_by_event(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert len(data) == 1
        assert data[0]["competitionCategory"]["registrationCategory"] == "Pro"

        # Verificar que se pasaron los filtros al helper
        call_args = mock_firestore_helper.query_documents.call_args
        filters = call_args.kwargs.get("filters") or call_args[1].get("filters")
        assert any(f["field"] == "competitionCategory.registrationCategory" for f in filters)

    def test_filter_by_team(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        mock_firestore_helper.query_documents.return_value = [sample_documents[1]]

        req = _make_request(event_id="event123", team="Team B")
        response = get_competitors_by_event(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert len(data) == 1
        assert data[0]["team"] == "Team B"


class TestGetCompetitorsByEventMissingParams:
    """Parámetros faltantes -> 400."""

    def test_missing_event_id(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        req = _make_request()
        response = get_competitors_by_event(req)
        assert response.status_code == 400


class TestGetCompetitorsByEventAuth:
    """Token inválido -> 401."""

    def test_invalid_token(self, mock_validate_request):
        from competitors.get_competitors_by_event import get_competitors_by_event

        with patch(
            "competitors.get_competitors_by_event.verify_bearer_token",
            return_value=False,
        ):
            req = _make_request(event_id="event123")
            response = get_competitors_by_event(req)
            assert response.status_code == 401


class TestGetCompetitorsByEventQueryWithData:
    """Consultas con data: verificar estructura de cada competidor."""

    def test_competitor_fields_present(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        mock_firestore_helper.query_documents.return_value = sample_documents

        req = _make_request(event_id="event123")
        response = get_competitors_by_event(req)

        data = json.loads(response.response[0])
        for competitor in data:
            assert "id" in competitor
            assert "eventId" in competitor
            assert "competitionCategory" in competitor
            assert "registrationDate" in competitor
            assert "team" in competitor
            assert "score" in competitor
            assert "timesToStart" in competitor
            assert "createdAt" in competitor
            assert "updatedAt" in competitor


class TestGetCompetitorsByEventPathParams:
    """Parámetros extraídos del path."""

    def test_event_id_from_path(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        mock_firestore_helper.query_documents.return_value = sample_documents

        req = MagicMock()
        req.method = "GET"
        req.args = {}
        req.path = "/api/competitors/get-competitors-by-event/event123"
        req.headers = {"Authorization": "Bearer test_token"}

        response = get_competitors_by_event(req)
        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert len(data) == 2


class TestGetCompetitorsByEventExceptions:
    """Excepciones -> códigos apropiados."""

    def test_value_error_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        mock_firestore_helper.query_documents.side_effect = ValueError("bad")

        req = _make_request(event_id="ev1")
        response = get_competitors_by_event(req)
        assert response.status_code == 400

    def test_runtime_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        mock_firestore_helper.query_documents.side_effect = RuntimeError("crash")

        req = _make_request(event_id="ev1")
        response = get_competitors_by_event(req)
        assert response.status_code == 500


class TestGetCompetitorsByEventMultipleCalls:
    """Múltiples llamadas estables."""

    def test_multiple_calls(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_documents,
    ):
        from competitors.get_competitors_by_event import get_competitors_by_event

        mock_firestore_helper.query_documents.return_value = sample_documents

        for _ in range(3):
            req = _make_request(event_id="event123")
            response = get_competitors_by_event(req)
            assert response.status_code == 200
            data = json.loads(response.response[0])
            assert len(data) == 2
