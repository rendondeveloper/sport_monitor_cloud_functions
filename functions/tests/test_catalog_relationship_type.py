"""
Tests del catálogo relationship-type vía catalog_route (GET /api/catalogs/relationship-type).
"""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_validate_request():
    with patch("catalogs.catalog_route.validate_request", return_value=None) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch("catalogs.catalog_route.verify_bearer_token", return_value=True) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token_fail():
    with patch("catalogs.catalog_route.verify_bearer_token", return_value=False) as m:
        yield m


@pytest.fixture
def mock_firestore_client():
    with patch("catalogs.catalog_route.firestore") as mock_fs:
        db = MagicMock()
        mock_fs.client.return_value = db
        yield db


def _make_doc(doc_id: str, label: str, order: int):
    doc = MagicMock()
    doc.id = doc_id
    doc.to_dict.return_value = {"label": label, "order": order}
    return doc


def _make_request(method: str = "GET"):
    req = MagicMock()
    req.method = method
    req.path = "/api/catalogs/relationship-type"
    req.headers = {}
    req.args = {}
    req.get_json = lambda silent=True: None
    return req


def test_get_returns_200_with_items(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    from catalogs.catalog_route import catalog_route

    docs = [
        _make_doc("id3", "Hermano", 6),
        _make_doc("id1", "Padre", 1),
        _make_doc("id2", "Madre", 2),
    ]
    (
        mock_firestore_client.collection.return_value.document.return_value.collection.return_value.stream.return_value
    ) = iter(docs)

    req = _make_request("GET")
    response = catalog_route(req)

    assert response.status_code == 200
    body = json.loads(response.get_data(as_text=True))
    assert isinstance(body, list)
    assert len(body) == 3
    assert body[0]["order"] == 1
    assert body[0]["label"] == "Padre"
    assert body[1]["order"] == 2
    assert body[2]["order"] == 6
    assert "id" in body[0]
    assert "label" in body[0]
    assert "order" in body[0]


def test_get_returns_empty_list_when_no_data(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    from catalogs.catalog_route import catalog_route

    (
        mock_firestore_client.collection.return_value.document.return_value.collection.return_value.stream.return_value
    ) = iter([])

    req = _make_request("GET")
    response = catalog_route(req)

    assert response.status_code == 200
    body = json.loads(response.get_data(as_text=True))
    assert body == []


def test_get_called_twice_is_stable(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    from catalogs.catalog_route import catalog_route

    docs = [_make_doc("id1", "Padre", 1), _make_doc("id2", "Madre", 2)]

    stream = (
        mock_firestore_client.collection.return_value.document.return_value.collection.return_value.stream
    )
    stream.side_effect = [iter(docs), iter(docs)]

    req = _make_request("GET")
    response1 = catalog_route(req)
    response2 = catalog_route(req)

    assert response1.status_code == 200
    assert response2.status_code == 200
    body1 = json.loads(response1.get_data(as_text=True))
    body2 = json.loads(response2.get_data(as_text=True))
    assert body1 == body2


def test_invalid_token_returns_401(mock_validate_request, mock_verify_bearer_token_fail):
    from catalogs.catalog_route import catalog_route

    req = _make_request("GET")
    response = catalog_route(req)

    assert response.status_code == 401


def test_post_method_returns_405(mock_validate_request, mock_verify_bearer_token):
    from catalogs.catalog_route import catalog_route

    with patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()):
        req = _make_request("POST")
        response = catalog_route(req)

    assert response.status_code == 405


def test_response_content_type_is_json(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    from catalogs.catalog_route import catalog_route

    (
        mock_firestore_client.collection.return_value.document.return_value.collection.return_value.stream.return_value
    ) = iter([_make_doc("id1", "Padre", 1)])

    req = _make_request("GET")
    response = catalog_route(req)

    assert response.status_code == 200
    assert "application/json" in response.content_type


def test_items_sorted_by_order_field(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    from catalogs.catalog_route import catalog_route

    docs = [
        _make_doc("id20", "Otro", 20),
        _make_doc("id5", "Hija", 5),
        _make_doc("id1", "Padre", 1),
    ]
    (
        mock_firestore_client.collection.return_value.document.return_value.collection.return_value.stream.return_value
    ) = iter(docs)

    req = _make_request("GET")
    response = catalog_route(req)

    body = json.loads(response.get_data(as_text=True))
    orders = [item["order"] for item in body]
    assert orders == sorted(orders)
