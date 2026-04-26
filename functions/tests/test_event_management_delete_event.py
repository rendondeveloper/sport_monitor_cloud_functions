"""
Tests para event_management/delete_event.py

Casos obligatorios:
1. Happy path — elimina evento y retorna 200 vacío
2. eventId faltante -> 400
3. Ownership fallido -> 404
4. Cascade: event_content y routes eliminados
5. Error interno -> 500
6. Múltiples llamadas al mismo API
"""

from unittest.mock import MagicMock, call, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_get_event_if_owner():
    with patch("event_management.delete_event.get_event_if_owner") as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch("event_management.delete_event.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def mock_delete_event_routes():
    with patch("event_management.delete_event._delete_event_routes") as m:
        yield m


def _make_request(event_id=None, method="DELETE"):
    req = MagicMock()
    req.method = method
    req.args = {}
    if event_id is not None:
        req.args["eventId"] = event_id
    req.path = "/api/event-management/delete"
    req.headers = {"Authorization": "Bearer test_token"}
    return req


# ============================================================================
# TESTS
# ============================================================================


class TestDeleteEventHappyPath:
    def test_returns_200_empty(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_delete_event_routes
    ):
        from event_management.delete_event import handle_delete

        mock_get_event_if_owner.return_value = {"name": "Evento", "creator": "user1"}
        mock_firestore_helper.list_document_ids.return_value = []

        req = _make_request(event_id="ev1")
        response = handle_delete(req, "user1")

        assert response.status_code == 200
        assert response.response[0] == b""

    def test_deletes_event_document(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_delete_event_routes
    ):
        from event_management.delete_event import handle_delete

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.list_document_ids.return_value = []

        req = _make_request(event_id="ev1")
        handle_delete(req, "user1")

        mock_firestore_helper.delete_document.assert_called_once()

    def test_deletes_event_content_cascade(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_delete_event_routes
    ):
        from event_management.delete_event import handle_delete

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.list_document_ids.return_value = ["content1", "content2"]

        req = _make_request(event_id="ev1")
        handle_delete(req, "user1")

        assert mock_firestore_helper.delete_document.call_count == 3  # 2 content + 1 event

    def test_calls_delete_event_routes(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_delete_event_routes
    ):
        from event_management.delete_event import handle_delete

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.list_document_ids.return_value = []

        req = _make_request(event_id="ev1")
        handle_delete(req, "user1")

        mock_delete_event_routes.assert_called_once_with("ev1")


class TestDeleteEventMissingParams:
    def test_missing_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.delete_event import handle_delete

        req = _make_request()
        response = handle_delete(req, "user1")
        assert response.status_code == 400

    def test_empty_event_id_returns_400(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.delete_event import handle_delete

        req = _make_request(event_id="   ")
        response = handle_delete(req, "user1")
        assert response.status_code == 400


class TestDeleteEventOwnership:
    def test_ownership_failure_returns_404(self, mock_get_event_if_owner, mock_firestore_helper):
        from event_management.delete_event import handle_delete

        mock_get_event_if_owner.return_value = None

        req = _make_request(event_id="ev1")
        response = handle_delete(req, "user1")
        assert response.status_code == 404


class TestDeleteEventInternalError:
    def test_runtime_error_returns_500(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_delete_event_routes
    ):
        from event_management.delete_event import handle_delete

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.list_document_ids.side_effect = RuntimeError("DB crash")

        req = _make_request(event_id="ev1")
        response = handle_delete(req, "user1")
        assert response.status_code == 500


class TestDeleteEventCascadeHelpers:
    def test_delete_route_checkpoints_iterates_and_deletes(self):
        from event_management.delete_event import _delete_route_checkpoints

        db = MagicMock()
        route_ref = MagicMock()

        checkpoint_doc_1 = MagicMock()
        checkpoint_doc_2 = MagicMock()
        route_ref.collection.return_value.stream.return_value = [checkpoint_doc_1, checkpoint_doc_2]

        _delete_route_checkpoints(db, route_ref)

        checkpoint_doc_1.reference.delete.assert_called_once()
        checkpoint_doc_2.reference.delete.assert_called_once()

    def test_delete_route_checkpoints_empty_collection(self):
        from event_management.delete_event import _delete_route_checkpoints

        db = MagicMock()
        route_ref = MagicMock()
        route_ref.collection.return_value.stream.return_value = []

        _delete_route_checkpoints(db, route_ref)

        route_ref.collection.assert_called_once()

    def test_delete_event_content_uses_correct_path(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_delete_event_routes
    ):
        from event_management.delete_event import handle_delete

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.list_document_ids.return_value = ["c1"]

        req = _make_request(event_id="ev_target")
        handle_delete(req, "user1")

        call_args = mock_firestore_helper.list_document_ids.call_args
        path_arg = call_args[0][0]
        assert "ev_target" in path_arg
        assert "event_content" in path_arg


class TestDeleteEventMultipleCalls:
    def test_multiple_deletes_are_stable(
        self, mock_get_event_if_owner, mock_firestore_helper, mock_delete_event_routes
    ):
        from event_management.delete_event import handle_delete

        mock_get_event_if_owner.return_value = {"creator": "user1"}
        mock_firestore_helper.list_document_ids.return_value = []

        for event_id in ["ev1", "ev2", "ev3"]:
            req = _make_request(event_id=event_id)
            response = handle_delete(req, "user1")
            assert response.status_code == 200
