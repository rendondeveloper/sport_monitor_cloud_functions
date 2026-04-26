"""
Tests para event_management/get_event_info.py

Casos obligatorios:
1. Happy path — retorna documento info con id
2. Retorna {} cuando no existe info
3. eventId faltante -> 400
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
    with patch("event_management.get_event_info.get_event_if_owner") as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("event_management.get_event_info.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


def _make_request(event_id=None, method="GET"):
    req = MagicMock()
    req.method = method
    req.args = {}
    if event_id is not None:
        req.args["eventId"] = event_id
    req.path = "/api/event-management/get-info"
    req.headers = {"Authorization": "Bearer test_token"}
    return req


# ============================================================================
# TESTS
# ============================================================================


class TestGetEventInfoHappyPath:
    def test_returns_info_with_id(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event_info import handle_get_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.return_value = [
            ("info1", {"description": "Info del evento", "updatedAt": "2026-01-01"})
        ]

        req = _make_request(event_id="ev1")
        response = handle_get_info(req, "user1")

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "info1"
        assert data["description"] == "Info del evento"

    def test_returns_empty_dict_when_no_info_exists(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event_info import handle_get_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(event_id="ev1")
        response = handle_get_info(req, "user1")

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data == {}

    def test_queries_with_limit_1(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event_info import handle_get_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(event_id="ev1")
        handle_get_info(req, "user1")

        call_args = mock_firestore_helper.query_documents.call_args
        limit = call_args.kwargs.get("limit") or call_args[1].get("limit")
        assert limit == 1


class TestGetEventInfoMissingParams:
    def test_missing_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event_info import handle_get_info

        req = _make_request()
        response = handle_get_info(req, "user1")
        assert response.status_code == 400

    def test_empty_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event_info import handle_get_info

        req = _make_request(event_id="   ")
        response = handle_get_info(req, "user1")
        assert response.status_code == 400


class TestGetEventInfoOwnership:
    def test_ownership_failure_returns_404(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event_info import handle_get_info

        mock_get_event_if_owner.return_value = None

        req = _make_request(event_id="ev1")
        response = handle_get_info(req, "user1")
        assert response.status_code == 404


class TestGetEventInfoInternalError:
    def test_runtime_error_returns_500(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event_info import handle_get_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.side_effect = RuntimeError("DB crash")

        req = _make_request(event_id="ev1")
        response = handle_get_info(req, "user1")
        assert response.status_code == 500


class TestGetEventInfoMultipleCalls:
    def test_multiple_calls_are_stable(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.get_event_info import handle_get_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.return_value = [
            ("info1", {"description": "Info"})
        ]

        for _ in range(3):
            req = _make_request(event_id="ev1")
            response = handle_get_info(req, "user1")
            assert response.status_code == 200
            data = json.loads(response.response[0])
            assert data["id"] == "info1"
