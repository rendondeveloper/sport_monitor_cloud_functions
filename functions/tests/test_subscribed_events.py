"""
Tests para subscribed_events.handle: eventos en los que el usuario está suscrito (membership), paginados.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")

_PATCH_HELPER = "users.subscribed_events.FirestoreHelper"


def _make_request(args=None):
    req = MagicMock()
    req.method = "GET"
    req.args = dict(args) if args else {}
    req.get_json = lambda silent=True: None
    return req


@patch(_PATCH_HELPER)
def test_subscribed_events_missing_user_id_returns_400(mock_helper_cls):
    from users.subscribed_events import handle as subscribed_events_handle

    req = _make_request(args={})
    response = subscribed_events_handle(req)
    assert response.status_code == 400
    assert response.get_data(as_text=True) == ""


@patch(_PATCH_HELPER)
def test_subscribed_events_user_not_found_returns_404(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = None
    helper.list_document_ids.return_value = []

    from users.subscribed_events import handle as subscribed_events_handle

    req = _make_request(args={"userId": "nonexistent"})
    response = subscribed_events_handle(req)
    assert response.status_code == 404
    assert response.get_data(as_text=True) == ""


@patch(_PATCH_HELPER)
def test_subscribed_events_empty_membership_returns_404(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "u@b.com"}
    helper.list_document_ids.return_value = []

    from users.subscribed_events import handle as subscribed_events_handle

    req = _make_request(args={"userId": "user1"})
    response = subscribed_events_handle(req)
    assert response.status_code == 404
    assert response.get_data(as_text=True) == ""


@patch(_PATCH_HELPER)
def test_subscribed_events_happy_path_returns_200_with_result_and_pagination(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper

    def get_doc(collection_path, doc_id):
        if "users" in collection_path:
            return {"email": "u@b.com"}
        if "events" in collection_path and doc_id == "ev1":
            return {
                "name": "Avandarocks",
                "description": "Avandarocks desc",
                "status": "inProgress",
                "date": "2025-06-01T10:00:00+00:00",
                "location": "Desde doc evento",
                "subtitle": "Subtítulo",
            }
        return None

    helper.get_document.side_effect = get_doc
    helper.list_document_ids.return_value = ["ev1"]
    helper.query_documents.return_value = [
        (
            "ec1",
            {
                "startEvent": "2099-01-01T00:00:00+00:00",
                "photoMain": "https://example.com/photo.jpg",
                "address": "Dirección desde content",
            },
        ),
    ]

    from users.subscribed_events import handle as subscribed_events_handle

    req = _make_request(args={"userId": "user1"})
    response = subscribed_events_handle(req)
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert "result" in data
    assert "pagination" in data
    assert len(data["result"]) == 1
    item = data["result"][0]
    assert item["id"] == "ev1"
    assert item["title"] == "Avandarocks"
    assert item["subtitle"] == "Subtítulo"
    assert item["status"] == "inProgress"
    assert item["startDateTime"] == "2025-06-01T10:00:00+00:00"
    assert item["locationName"] == "Dirección desde content"
    assert item["imageUrl"] == "https://example.com/photo.jpg"
    assert item["isEnrolled"] is True
    pag = data["pagination"]
    assert pag["limit"] == 50
    assert pag["page"] == 1
    assert pag["count"] == 1
    assert pag["hasMore"] is False


@patch(_PATCH_HELPER)
def test_subscribed_events_pagination_has_more(mock_helper_cls):
    helper = MagicMock()
    mock_helper_cls.return_value = helper

    def get_doc(collection_path, doc_id):
        if "users" in collection_path:
            return {"email": "u@b.com"}
        if "events" in collection_path:
            return {
                "name": f"Event {doc_id}",
                "description": "",
                "status": "published",
                "date": "2025-01-01T00:00:00+00:00",
                "location": "",
            }
        return None

    helper.get_document.side_effect = get_doc
    helper.list_document_ids.return_value = ["ev1", "ev2", "ev3"]
    helper.query_documents.return_value = [
        ("ec1", {}),
    ]

    from users.subscribed_events import handle as subscribed_events_handle

    req = _make_request(args={"userId": "u1", "limit": "2", "page": "1"})
    response = subscribed_events_handle(req)
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert len(data["result"]) == 2
    assert data["pagination"]["limit"] == 2
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["hasMore"] is True
    assert data["pagination"]["count"] == 2


@patch(_PATCH_HELPER)
def test_subscribed_events_nonexistent_event_omitted(mock_helper_cls):
    """Si un eventId de membership no existe en events, se omite ese ítem (no falla la petición)."""
    helper = MagicMock()
    mock_helper_cls.return_value = helper

    call_count = [0]

    def get_doc(collection_path, doc_id):
        if "users" in collection_path:
            return {"email": "u@b.com"}
        if "events" in collection_path:
            if doc_id == "ev1":
                return {
                    "name": "Event1",
                    "description": "D1",
                    "status": "published",
                    "date": "2025-03-01T00:00:00+00:00",
                    "location": "L1",
                }
            # ev2 no existe
            return None
        return None

    helper.get_document.side_effect = get_doc
    helper.list_document_ids.return_value = ["ev1", "ev2"]
    helper.query_documents.return_value = [
        ("ec1", {}),
    ]

    from users.subscribed_events import handle as subscribed_events_handle

    req = _make_request(args={"userId": "u1"})
    response = subscribed_events_handle(req)
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert len(data["result"]) == 1
    assert data["result"][0]["id"] == "ev1"


@patch(_PATCH_HELPER)
def test_subscribed_events_multiple_calls_stable(mock_helper_cls):
    """Múltiples llamadas al handler devuelven resultado estable."""
    helper = MagicMock()
    mock_helper_cls.return_value = helper
    helper.get_document.return_value = {"email": "u@b.com"}
    helper.list_document_ids.return_value = ["ev1"]
    helper.query_documents.return_value = [
        ("ec1", {}),
    ]

    def get_doc(collection_path, doc_id):
        if "users" in collection_path:
            return {"email": "u@b.com"}
        if "events" in collection_path:
            return {
                "name": "E1",
                "description": "D1",
                "status": "draft",
                "date": "2025-01-01T00:00:00+00:00",
                "location": "",
            }
        return None

    helper.get_document.side_effect = get_doc

    from users.subscribed_events import handle as subscribed_events_handle

    req = _make_request(args={"userId": "u1"})
    r1 = subscribed_events_handle(req)
    r2 = subscribed_events_handle(req)
    assert r1.status_code == 200
    assert r2.status_code == 200
    d1 = json.loads(r1.get_data(as_text=True))
    d2 = json.loads(r2.get_data(as_text=True))
    assert d1["result"][0]["id"] == d2["result"][0]["id"]
    assert d1["result"][0]["title"] == d2["result"][0]["title"]
    assert d1["pagination"]["count"] == d2["pagination"]["count"]


@patch(_PATCH_HELPER)
def test_subscribed_events_no_event_content_uses_event_doc_only(mock_helper_cls):
    """Sin event_content: mismo mapeo que /api/events (fecha desde doc, sin overrides)."""
    helper = MagicMock()
    mock_helper_cls.return_value = helper

    def get_doc(collection_path, doc_id):
        if "users" in collection_path:
            return {"email": "u@b.com"}
        if "events" in collection_path:
            return {
                "name": "SoloEvento",
                "description": "Sin content",
                "status": "draft",
                "date": "2025-04-10T15:30:00+00:00",
                "location": "Ubicación doc",
                "subtitle": "Sub solo",
            }
        return None

    helper.get_document.side_effect = get_doc
    helper.list_document_ids.return_value = ["ev1"]
    helper.query_documents.return_value = []

    from users.subscribed_events import handle as subscribed_events_handle

    req = _make_request(args={"userId": "u1"})
    response = subscribed_events_handle(req)
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    item = data["result"][0]
    assert item["title"] == "SoloEvento"
    assert item["subtitle"] == "Sub solo"
    assert item["startDateTime"] == "2025-04-10T15:30:00+00:00"
    assert item["locationName"] == "Ubicación doc"
    assert item["imageUrl"] is None
    assert item["isEnrolled"] is True
