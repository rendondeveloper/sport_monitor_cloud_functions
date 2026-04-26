"""
Tests para event_management/create_event.py

Casos obligatorios:
1. Happy path — crea evento y retorna 201 sin body
2. Body faltante o inválido -> 400
3. Error interno -> 500
4. Escritura verificable — create_document llamado con creator correcto
5. Múltiples llamadas al mismo API
"""

from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_firestore_helper():
    with patch("event_management.create_event.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def mock_get_current_timestamp():
    with patch("event_management.create_event.get_current_timestamp", return_value="2026-01-01T00:00:00") as m:
        yield m


def _base_event_fields():
    """Campos raíz obligatorios para create."""
    return {
        "source": "app",
        "typeEvent": "individual",
        "duration": 120,
        "sendNotifications": True,
    }


def _make_request(body=None, method="POST"):
    req = MagicMock()
    req.method = method
    req.args = {}
    req.path = "/api/event-management/create"
    req.headers = {"Authorization": "Bearer test_token"}
    req.get_json.return_value = body
    return req


# ============================================================================
# TESTS
# ============================================================================


class TestCreateEventHappyPath:
    def test_creates_event_and_returns_201(self, mock_firestore_helper, mock_get_current_timestamp):
        from event_management.create_event import handle_create

        mock_firestore_helper.create_document.return_value = "new_event_id"

        req = _make_request(body={**_base_event_fields(), "name": "Rally 2026"})
        response = handle_create(req, "user123")

        assert response.status_code == 201
        assert response.response == [b""]

    def test_sets_creator_from_user_id(self, mock_firestore_helper, mock_get_current_timestamp):
        from event_management.create_event import handle_create

        mock_firestore_helper.create_document.return_value = "ev1"

        req = _make_request(body={**_base_event_fields(), "name": "Evento"})
        handle_create(req, "uid_xyz")

        call_args = mock_firestore_helper.create_document.call_args
        payload = call_args[0][1]
        assert payload["creator"] == "uid_xyz"

    def test_adds_timestamps(self, mock_firestore_helper, mock_get_current_timestamp):
        from event_management.create_event import handle_create

        mock_firestore_helper.create_document.return_value = "ev2"

        req = _make_request(body={**_base_event_fields(), "name": "Evento"})
        handle_create(req, "user1")

        call_args = mock_firestore_helper.create_document.call_args
        payload = call_args[0][1]
        assert "createdAt" in payload
        assert "updatedAt" in payload

    def test_saves_event_content_when_informed(self, mock_firestore_helper, mock_get_current_timestamp):
        from event_management.create_event import handle_create

        mock_batch = MagicMock()
        mock_firestore_helper.db.batch.return_value = mock_batch
        event_ref = MagicMock()
        event_ref.id = "ev3"
        content_ref = MagicMock()
        mock_firestore_helper.db.collection.return_value.document.side_effect = [event_ref, content_ref]

        req = _make_request(
            body={**_base_event_fields(), "name": "Evento", "event_content": {"description": "Info"}}
        )
        response = handle_create(req, "user1")

        assert response.status_code == 201
        assert mock_firestore_helper.create_document.call_count == 0
        assert mock_batch.set.call_count == 2
        assert mock_batch.commit.call_count == 1

    def test_does_not_save_event_content_when_missing(self, mock_firestore_helper, mock_get_current_timestamp):
        from event_management.create_event import handle_create

        mock_firestore_helper.create_document.return_value = "ev4"

        req = _make_request(body={**_base_event_fields(), "name": "Evento sin info"})
        response = handle_create(req, "user1")

        assert response.status_code == 201
        assert mock_firestore_helper.create_document.call_count == 1

    def test_returns_500_when_atomic_commit_fails(self, mock_firestore_helper, mock_get_current_timestamp):
        from event_management.create_event import handle_create

        mock_batch = MagicMock()
        mock_batch.commit.side_effect = RuntimeError("batch failed")
        mock_firestore_helper.db.batch.return_value = mock_batch
        event_ref = MagicMock()
        event_ref.id = "ev3"
        content_ref = MagicMock()
        mock_firestore_helper.db.collection.return_value.document.side_effect = [event_ref, content_ref]

        req = _make_request(
            body={**_base_event_fields(), "name": "Evento", "event_content": {"description": "Info"}}
        )
        response = handle_create(req, "user1")

        assert response.status_code == 500

class TestCreateEventBadRequest:
    def test_none_body_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(body=None)
        response = handle_create(req, "user1")

        assert response.status_code == 400

    def test_non_dict_body_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(body=[1, 2, 3])
        response = handle_create(req, "user1")

        assert response.status_code == 400

    def test_string_body_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(body="invalid")
        response = handle_create(req, "user1")

        assert response.status_code == 400

    def test_missing_source_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(body={"name": "E", "typeEvent": "individual"})
        assert handle_create(req, "user1").status_code == 400

    def test_missing_type_event_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(body={"name": "E", "source": "app"})
        assert handle_create(req, "user1").status_code == 400

    def test_invalid_source_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(
            body={"name": "E", "source": "mobile", "typeEvent": "individual"}
        )
        assert handle_create(req, "user1").status_code == 400

    def test_invalid_type_event_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(
            body={
                "name": "E",
                "source": "web",
                "typeEvent": "team",
                "duration": 120,
                "sendNotifications": True,
            }
        )
        assert handle_create(req, "user1").status_code == 400

    def test_missing_duration_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(
            body={"name": "E", "source": "app", "typeEvent": "individual", "sendNotifications": True}
        )
        assert handle_create(req, "user1").status_code == 400

    def test_missing_send_notifications_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(
            body={"name": "E", "source": "app", "typeEvent": "individual", "duration": 120}
        )
        assert handle_create(req, "user1").status_code == 400

    def test_invalid_duration_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(
            body={
                "name": "E",
                "source": "app",
                "typeEvent": "individual",
                "duration": "120",
                "sendNotifications": True,
            }
        )
        assert handle_create(req, "user1").status_code == 400

    def test_invalid_send_notifications_returns_400(self, mock_firestore_helper):
        from event_management.create_event import handle_create

        req = _make_request(
            body={
                "name": "E",
                "source": "app",
                "typeEvent": "individual",
                "duration": 120,
                "sendNotifications": "true",
            }
        )
        assert handle_create(req, "user1").status_code == 400


class TestCreateEventInternalError:
    def test_runtime_error_returns_500(self, mock_firestore_helper, mock_get_current_timestamp):
        from event_management.create_event import handle_create

        mock_firestore_helper.create_document.side_effect = RuntimeError("DB down")

        req = _make_request(body={**_base_event_fields(), "name": "Evento"})
        response = handle_create(req, "user1")

        assert response.status_code == 500

    def test_type_error_returns_500(self, mock_firestore_helper, mock_get_current_timestamp):
        from event_management.create_event import handle_create

        mock_firestore_helper.create_document.side_effect = TypeError("bad type")

        req = _make_request(body={**_base_event_fields(), "name": "Evento"})
        response = handle_create(req, "user1")

        assert response.status_code == 500


class TestCreateEventMultipleCalls:
    def test_multiple_calls_are_stable(self, mock_firestore_helper, mock_get_current_timestamp):
        from event_management.create_event import handle_create

        mock_firestore_helper.create_document.side_effect = ["id1", "id2", "id3"]

        for i in range(3):
            req = _make_request(body={**_base_event_fields(), "name": f"Evento {i}"})
            response = handle_create(req, "user1")
            assert response.status_code == 201
            assert response.response == [b""]
