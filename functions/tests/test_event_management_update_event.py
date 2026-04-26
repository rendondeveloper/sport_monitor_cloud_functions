"""
Tests para event_management/update_event.py

Casos obligatorios:
1. Happy path — actualiza evento y retorna documento actualizado
2. Body faltante -> 400
3. eventId faltante en body -> 400
4. Ownership fallido (evento no existe o no es propietario) -> 404
5. Error interno -> 500
6. Campos inmutables eliminados del payload
7. Múltiples llamadas al mismo API
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_get_event_if_owner():
    with patch("event_management.update_event.get_event_if_owner") as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("event_management.update_event.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def mock_get_current_timestamp():
    with patch("event_management.update_event.get_current_timestamp", return_value="2026-01-01T00:00:00") as m:
        yield m


def _make_request(body=None, method="PUT"):
    req = MagicMock()
    req.method = method
    req.args = {}
    req.path = "/api/event-management/update"
    req.headers = {"Authorization": "Bearer test_token"}
    req.args = {}
    req.get_json.return_value = body
    return req


# ============================================================================
# TESTS
# ============================================================================


class TestUpdateEventHappyPath:
    def test_uses_event_id_from_query_string(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"name": "Viejo nombre", "creator": "user1"}
        mock_firestore_helper.get_document.return_value = {"name": "Nuevo nombre"}

        req = _make_request(body={"name": "Nuevo nombre"})
        req.args = {"eventId": "ev_query"}
        response = handle_update(req, "user1")

        assert response.status_code == 200
        mock_get_event_if_owner.assert_called_once_with("ev_query", "user1")

    def test_updates_event_and_returns_document(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"name": "Viejo nombre", "creator": "user1"}
        mock_firestore_helper.get_document.return_value = {
            "name": "Nuevo nombre",
            "creator": "user1",
            "updatedAt": "2026-01-01T00:00:00",
        }

        req = _make_request(body={"eventId": "ev1", "name": "Nuevo nombre"})
        response = handle_update(req, "user1")

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "ev1"
        assert data["name"] == "Nuevo nombre"

    def test_calls_update_document(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.get_document.return_value = {}

        req = _make_request(body={"eventId": "ev1", "name": "Nombre"})
        handle_update(req, "user1")

        mock_firestore_helper.update_document.assert_called_once()

    def test_removes_immutable_fields_from_payload(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.get_document.return_value = {}

        req = _make_request(body={
            "eventId": "ev1",
            "id": "ev1",
            "creator": "hacker",
            "name": "Nombre legítimo",
        })
        handle_update(req, "user1")

        call_args = mock_firestore_helper.update_document.call_args
        updates = call_args[0][2]
        assert "eventId" not in updates
        assert "id" not in updates
        assert "creator" not in updates
        assert "name" in updates
        assert "updatedAt" in updates

    def test_event_content_not_written_to_event_root(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.get_document.return_value = {"name": "E"}
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(
            body={
                "eventId": "ev1",
                "name": "E",
                "event_content": {"description": "Info", "address": "Calle 1"},
            }
        )
        handle_update(req, "user1")

        call_args = mock_firestore_helper.update_document.call_args
        updates = call_args[0][2]
        assert "event_content" not in updates
        assert updates.get("name") == "E"

    def test_send_notifications_not_written_and_duration_kept(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.get_document.return_value = {"name": "E"}

        req = _make_request(
            body={
                "eventId": "ev1",
                "name": "E",
                "duration": 90,
                "sendNotifications": False,
            }
        )
        handle_update(req, "user1")

        call_args = mock_firestore_helper.update_document.call_args
        updates = call_args[0][2]
        assert "sendNotifications" not in updates
        assert updates.get("duration") == 90

    def test_upserts_event_content_when_dict_nonempty(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.get_document.return_value = {}
        mock_firestore_helper.query_documents.return_value = [("c1", {"x": 1})]

        req = _make_request(
            body={
                "eventId": "ev1",
                "event_content": {"name": "N", "address": "A"},
            }
        )
        handle_update(req, "user1")

        assert mock_firestore_helper.query_documents.call_count == 1
        content_call = [
            c
            for c in mock_firestore_helper.update_document.call_args_list
            if "event_content" in (c[0][0] or "")
        ]
        assert len(content_call) == 1
        assert content_call[0][0][0].endswith("event_content")
        assert content_call[0][0][1] == "c1"
        assert "name" in content_call[0][0][2]

    def test_creates_event_content_when_subcollection_empty(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.get_document.return_value = {}
        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(
            body={"eventId": "ev1", "event_content": {"description": "D"}}
        )
        handle_update(req, "user1")

        mock_firestore_helper.create_document.assert_called_once()
        create_path = mock_firestore_helper.create_document.call_args[0][0]
        assert "event_content" in create_path

    def test_skips_event_content_upsert_when_empty_dict(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.get_document.return_value = {}

        req = _make_request(
            body={"eventId": "ev1", "name": "X", "event_content": {}}
        )
        handle_update(req, "user1")

        mock_firestore_helper.query_documents.assert_not_called()


class TestUpdateEventBadRequest:
    def test_none_body_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.update_event import handle_update

        req = _make_request(body=None)
        response = handle_update(req, "user1")
        assert response.status_code == 400

    def test_missing_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.update_event import handle_update

        req = _make_request(body={"name": "Sin eventId"})
        response = handle_update(req, "user1")
        assert response.status_code == 400

    def test_empty_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.update_event import handle_update

        req = _make_request(body={"eventId": "  "})
        response = handle_update(req, "user1")
        assert response.status_code == 400

    def test_invalid_source_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.update_event import handle_update

        req = _make_request(
            body={"eventId": "ev1", "source": "mobile", "name": "X"}
        )
        assert handle_update(req, "user1").status_code == 400

    def test_invalid_type_event_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.update_event import handle_update

        req = _make_request(
            body={"eventId": "ev1", "typeEvent": "team", "name": "X"}
        )
        assert handle_update(req, "user1").status_code == 400

    def test_invalid_duration_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.update_event import handle_update

        req = _make_request(body={"eventId": "ev1", "duration": "60", "name": "X"})
        assert handle_update(req, "user1").status_code == 400

    def test_invalid_send_notifications_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.update_event import handle_update

        req = _make_request(body={"eventId": "ev1", "sendNotifications": "true", "name": "X"})
        assert handle_update(req, "user1").status_code == 400


class TestUpdateEventOwnership:
    def test_ownership_failure_returns_404(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = None

        req = _make_request(body={"eventId": "ev1", "name": "X"})
        response = handle_update(req, "user1")
        assert response.status_code == 404


class TestUpdateEventInternalError:
    def test_runtime_error_returns_500(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.update_document.side_effect = RuntimeError("DB error")

        req = _make_request(body={"eventId": "ev1", "name": "X"})
        response = handle_update(req, "user1")
        assert response.status_code == 500


class TestUpdateEventMultipleCalls:
    def test_multiple_updates_are_stable(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_get_current_timestamp
    ):
        from event_management.update_event import handle_update

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.get_document.return_value = {"name": "Updated"}

        for _ in range(3):
            req = _make_request(body={"eventId": "ev1", "name": "Updated"})
            response = handle_update(req, "user1")
            assert response.status_code == 200
