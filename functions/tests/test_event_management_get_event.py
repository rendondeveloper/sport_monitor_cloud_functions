"""
Tests para event_management/get_event.py

Casos obligatorios:
1. Happy path — retorna evento con id + eventContent
2. eventId faltante -> 400
3. eventId vacío -> 400
4. Ownership fallido -> 404
5. Error interno -> 500
6. Múltiples llamadas al mismo API
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_get_event_if_owner():
    with patch("event_management.get_event.get_event_if_owner") as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("event_management.get_event.FirestoreHelper") as helper_class:
        helper_instance = MagicMock()
        helper_class.return_value = helper_instance
        yield helper_instance


def _make_request(event_id=None, method="GET"):
    req = MagicMock()
    req.method = method
    req.args = {}
    if event_id is not None:
        req.args["eventId"] = event_id
    req.path = "/api/event-management/get"
    req.headers = {"Authorization": "Bearer test_token"}
    return req


# ============================================================================
# TESTS
# ============================================================================


class TestGetEventHappyPath:
    def test_returns_event_with_event_content(
        self, mock_get_event_if_owner, mock_firestore_helper
    ):
        from event_management.get_event import handle_get

        mock_get_event_if_owner.return_value = {
            "name": "Rally 2026",
            "creator": "user1",
            "status": "draft",
            "subtitle": "Subtitulo legado",
        }
        mock_firestore_helper.query_documents.return_value = [
            (
                "content1",
                {
                    "address": "Av. Principal 123",
                    "description": "Info evento",
                    "descriptionShort": "Resumen corto del evento",
                    "photoUrls": ["https://img/1.jpg"],
                },
            )
        ]

        req = _make_request(event_id="ev1")
        response = handle_get(req, "user1")

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "ev1"
        assert data["name"] == "Rally 2026"
        assert data["creator"] == "user1"
        assert data["subtitle"] == "Subtitulo legado"
        assert data["eventContent"]["address"] == "Av. Principal 123"
        assert data["eventContent"]["description"] == "Info evento"
        assert data["eventContent"]["descriptionShort"] == "Resumen corto del evento"

    def test_returns_empty_event_content_when_not_found(
        self, mock_get_event_if_owner, mock_firestore_helper
    ):
        from event_management.get_event import handle_get

        mock_get_event_if_owner.return_value = {"name": "Rally 2026", "creator": "user1"}
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(event_id="ev1")
        response = handle_get(req, "user1")

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "ev1"
        assert data["eventContent"] == {}

    def test_queries_with_correct_event_id(
        self, mock_get_event_if_owner, mock_firestore_helper
    ):
        from event_management.get_event import handle_get

        mock_get_event_if_owner.return_value = {"name": "X"}
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(event_id="target_event")
        handle_get(req, "user1")

        mock_get_event_if_owner.assert_called_once_with("target_event", "user1")
        mock_firestore_helper.query_documents.assert_called_once_with(
            "events/target_event/event_content", limit=1
        )


class TestGetEventMissingParams:
    def test_missing_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event import handle_get

        req = _make_request()
        response = handle_get(req, "user1")
        assert response.status_code == 400

    def test_empty_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event import handle_get

        req = _make_request(event_id="  ")
        response = handle_get(req, "user1")
        assert response.status_code == 400


class TestGetEventOwnership:
    def test_ownership_failure_returns_404(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event import handle_get

        mock_get_event_if_owner.return_value = None

        req = _make_request(event_id="ev1")
        response = handle_get(req, "user1")
        assert response.status_code == 404


class TestGetEventInternalError:
    def test_runtime_error_returns_500(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event import handle_get

        mock_get_event_if_owner.side_effect = RuntimeError("DB crash")

        req = _make_request(event_id="ev1")
        response = handle_get(req, "user1")
        assert response.status_code == 500

    def test_attribute_error_returns_500(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event import handle_get

        mock_get_event_if_owner.side_effect = AttributeError("attr error")

        req = _make_request(event_id="ev1")
        response = handle_get(req, "user1")
        assert response.status_code == 500


class TestGetEventMultipleCalls:
    def test_multiple_calls_are_stable(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event import handle_get

        mock_get_event_if_owner.return_value = {"name": "Evento"}
        mock_firestore_helper.query_documents.return_value = []

        for _ in range(3):
            req = _make_request(event_id="ev1")
            response = handle_get(req, "user1")
            assert response.status_code == 200
            data = json.loads(response.response[0])
            assert data["id"] == "ev1"
            assert data["eventContent"] == {}
