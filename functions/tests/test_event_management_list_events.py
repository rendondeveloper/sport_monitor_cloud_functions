"""
Tests para event_management/list_events.py

Casos obligatorios:
1. Happy path — retorna lista de eventos del usuario
2. Lista vacía — retorna []
3. Filtro por status opcional
4. Siempre filtra por creator == user_id
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
def mock_firestore_helper():
    with patch("event_management.list_events.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


def _make_request(status=None, method="GET"):
    req = MagicMock()
    req.method = method
    req.args = {}
    if status is not None:
        req.args["status"] = status
    req.path = "/api/event-management/list"
    req.headers = {"Authorization": "Bearer test_token"}
    return req


_SAMPLE_EVENTS = [
    ("ev1", {"name": "Rally 2026", "creator": "user1", "status": "draft", "createdAt": "2026-01-02"}),
    ("ev2", {"name": "Rally 2025", "creator": "user1", "status": "published", "createdAt": "2026-01-01"}),
]


# ============================================================================
# TESTS
# ============================================================================


class TestListEventsHappyPath:
    def test_returns_list_with_ids(self, mock_firestore_helper):
        from event_management.list_events import handle_list

        mock_firestore_helper.query_documents.return_value = _SAMPLE_EVENTS

        req = _make_request()
        response = handle_list(req, "user1")

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == "ev1"
        assert data[1]["id"] == "ev2"

    def test_returns_empty_list_when_no_events(self, mock_firestore_helper):
        from event_management.list_events import handle_list

        mock_firestore_helper.query_documents.return_value = []

        req = _make_request()
        response = handle_list(req, "user1")

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data == []


class TestListEventsFilters:
    def test_always_filters_by_creator(self, mock_firestore_helper):
        from event_management.list_events import handle_list

        mock_firestore_helper.query_documents.return_value = []

        req = _make_request()
        handle_list(req, "my_user_id")

        call_args = mock_firestore_helper.query_documents.call_args
        filters = call_args.kwargs.get("filters") or call_args[1].get("filters")
        creator_filter = next((f for f in filters if f["field"] == "creator"), None)
        assert creator_filter is not None
        assert creator_filter["value"] == "my_user_id"

    def test_status_filter_added_when_provided(self, mock_firestore_helper):
        from event_management.list_events import handle_list

        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(status="published")
        handle_list(req, "user1")

        call_args = mock_firestore_helper.query_documents.call_args
        filters = call_args.kwargs.get("filters") or call_args[1].get("filters")
        status_filter = next((f for f in filters if f["field"] == "status"), None)
        assert status_filter is not None
        assert status_filter["value"] == "published"

    def test_no_status_filter_when_not_provided(self, mock_firestore_helper):
        from event_management.list_events import handle_list

        mock_firestore_helper.query_documents.return_value = []

        req = _make_request()
        handle_list(req, "user1")

        call_args = mock_firestore_helper.query_documents.call_args
        filters = call_args.kwargs.get("filters") or call_args[1].get("filters")
        status_filter = next((f for f in filters if f["field"] == "status"), None)
        assert status_filter is None

    def test_orders_by_created_at_desc(self, mock_firestore_helper):
        from event_management.list_events import handle_list

        mock_firestore_helper.query_documents.return_value = []

        req = _make_request()
        handle_list(req, "user1")

        call_args = mock_firestore_helper.query_documents.call_args
        order_by = call_args.kwargs.get("order_by") or call_args[1].get("order_by")
        assert order_by is not None
        assert ("createdAt", "desc") in order_by


class TestListEventsInternalError:
    def test_runtime_error_returns_500(self, mock_firestore_helper):
        from event_management.list_events import handle_list

        mock_firestore_helper.query_documents.side_effect = RuntimeError("DB crash")

        req = _make_request()
        response = handle_list(req, "user1")
        assert response.status_code == 500


class TestListEventsMultipleCalls:
    def test_multiple_calls_are_stable(self, mock_firestore_helper):
        from event_management.list_events import handle_list

        mock_firestore_helper.query_documents.return_value = _SAMPLE_EVENTS

        for _ in range(3):
            req = _make_request()
            response = handle_list(req, "user1")
            assert response.status_code == 200
            data = json.loads(response.response[0])
            assert len(data) == 2
