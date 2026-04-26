"""
Tests para event_management/save_event_info.py

Casos obligatorios:
1. Happy path — crea info si no existe
2. Happy path — actualiza info si ya existe
3. Body faltante -> 400
4. eventId faltante en body -> 400
5. Ownership fallido -> 404
6. createdAt solo al crear (no al actualizar)
7. Error interno -> 500
8. Múltiples llamadas al mismo API
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_get_event_if_owner():
    with patch("event_management.save_event_info.get_event_if_owner") as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("event_management.save_event_info.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def mock_get_current_timestamp():
    with patch("event_management.save_event_info.get_current_timestamp", return_value="2026-01-01T00:00:00") as m:
        yield m


def _make_request(body=None, method="POST"):
    req = MagicMock()
    req.method = method
    req.args = {}
    req.path = "/api/event-management/save-info"
    req.headers = {"Authorization": "Bearer test_token"}
    req.get_json.return_value = body
    return req


_SAVED_INFO = {"description": "Info guardada", "updatedAt": "2026-01-01T00:00:00"}


# ============================================================================
# TESTS
# ============================================================================


class TestSaveEventInfoCreate:
    def test_creates_info_when_none_exists(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.save_event_info import handle_save_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.return_value = "new_info_id"
        mock_firestore_helper.get_document.return_value = _SAVED_INFO

        req = _make_request(body={"eventId": "ev1", "description": "Info"})
        response = handle_save_info(req, "user1")

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "new_info_id"

        mock_firestore_helper.create_document.assert_called_once()
        mock_firestore_helper.update_document.assert_not_called()

    def test_new_info_has_created_at(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.save_event_info import handle_save_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.return_value = []
        mock_firestore_helper.create_document.return_value = "info1"
        mock_firestore_helper.get_document.return_value = {}

        req = _make_request(body={"eventId": "ev1"})
        handle_save_info(req, "user1")

        call_args = mock_firestore_helper.create_document.call_args
        payload = call_args[0][1]
        assert "createdAt" in payload


class TestSaveEventInfoUpdate:
    def test_updates_info_when_exists(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.save_event_info import handle_save_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.return_value = [("existing_info", {})]
        mock_firestore_helper.get_document.return_value = _SAVED_INFO

        req = _make_request(body={"eventId": "ev1", "description": "Actualizado"})
        response = handle_save_info(req, "user1")

        assert response.status_code == 200
        mock_firestore_helper.update_document.assert_called_once()
        mock_firestore_helper.create_document.assert_not_called()

    def test_update_removes_event_id_from_payload(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.save_event_info import handle_save_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.return_value = [("info1", {})]
        mock_firestore_helper.get_document.return_value = {}

        req = _make_request(body={"eventId": "ev1", "description": "X"})
        handle_save_info(req, "user1")

        call_args = mock_firestore_helper.update_document.call_args
        updates = call_args[0][2]
        assert "eventId" not in updates
        assert "updatedAt" in updates


class TestSaveEventInfoBadRequest:
    def test_none_body_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.save_event_info import handle_save_info

        req = _make_request(body=None)
        response = handle_save_info(req, "user1")
        assert response.status_code == 400

    def test_missing_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.save_event_info import handle_save_info

        req = _make_request(body={"description": "Sin eventId"})
        response = handle_save_info(req, "user1")
        assert response.status_code == 400

    def test_empty_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.save_event_info import handle_save_info

        req = _make_request(body={"eventId": "  "})
        response = handle_save_info(req, "user1")
        assert response.status_code == 400


class TestSaveEventInfoOwnership:
    def test_ownership_failure_returns_404(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.save_event_info import handle_save_info

        mock_get_event_if_owner.return_value = None

        req = _make_request(body={"eventId": "ev1"})
        response = handle_save_info(req, "user1")
        assert response.status_code == 404


class TestSaveEventInfoInternalError:
    def test_runtime_error_returns_500(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.save_event_info import handle_save_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.side_effect = RuntimeError("DB crash")

        req = _make_request(body={"eventId": "ev1"})
        response = handle_save_info(req, "user1")
        assert response.status_code == 500


class TestSaveEventInfoMultipleCalls:
    def test_multiple_saves_are_stable(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.save_event_info import handle_save_info

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.query_documents.return_value = [("info1", {})]
        mock_firestore_helper.get_document.return_value = _SAVED_INFO

        for _ in range(3):
            req = _make_request(body={"eventId": "ev1", "description": "Info"})
            response = handle_save_info(req, "user1")
            assert response.status_code == 200
