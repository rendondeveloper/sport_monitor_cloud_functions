"""
Tests para catalog_relationship_type Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path GET — lista con items, respuesta 200 con estructura [{id, label, order}]
2. GET retorna array vacío si no hay datos — respuesta 200 con []
3. Múltiples llamadas consecutivas al GET — comportamiento estable
4. Token inválido — retorna 401
5. Método no permitido (POST, PUT, DELETE) — retorna 405
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
        "catalogs.relationship_type.validate_request", return_value=None
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch(
        "catalogs.relationship_type.verify_bearer_token", return_value=True
    ) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token_fail():
    with patch(
        "catalogs.relationship_type.verify_bearer_token", return_value=False
    ) as m:
        yield m


@pytest.fixture
def mock_firestore_client():
    with patch("catalogs.relationship_type.firestore") as mock_fs:
        db = MagicMock()
        mock_fs.client.return_value = db
        yield db


def _make_doc(doc_id: str, label: str, order: int):
    """Helper: crea un mock de documento Firestore."""
    doc = MagicMock()
    doc.id = doc_id
    doc.to_dict.return_value = {"label": label, "order": order}
    return doc


def _make_request(method: str = "GET"):
    req = MagicMock()
    req.method = method
    return req


# ============================================================================
# TESTS
# ============================================================================


def test_get_returns_200_with_items(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    """Happy path: GET retorna lista ordenada con estructura correcta."""
    from catalogs.relationship_type import catalog_relationship_type

    docs = [
        _make_doc("id3", "Hermano", 6),
        _make_doc("id1", "Padre", 1),
        _make_doc("id2", "Madre", 2),
    ]
    (
        mock_firestore_client.collection.return_value
        .document.return_value
        .collection.return_value
        .stream.return_value
    ) = iter(docs)

    req = _make_request("GET")
    response = catalog_relationship_type(req)

    assert response.status_code == 200
    body = json.loads(response.get_data(as_text=True))
    assert isinstance(body, list)
    assert len(body) == 3
    # Debe estar ordenado por order
    assert body[0]["order"] == 1
    assert body[0]["label"] == "Padre"
    assert body[1]["order"] == 2
    assert body[2]["order"] == 6
    # Estructura correcta
    assert "id" in body[0]
    assert "label" in body[0]
    assert "order" in body[0]


def test_get_returns_empty_list_when_no_data(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    """GET retorna [] si no hay documentos en Firestore."""
    from catalogs.relationship_type import catalog_relationship_type

    (
        mock_firestore_client.collection.return_value
        .document.return_value
        .collection.return_value
        .stream.return_value
    ) = iter([])

    req = _make_request("GET")
    response = catalog_relationship_type(req)

    assert response.status_code == 200
    body = json.loads(response.get_data(as_text=True))
    assert body == []


def test_get_called_twice_is_stable(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    """Múltiples llamadas GET devuelven el mismo resultado."""
    from catalogs.relationship_type import catalog_relationship_type

    docs = [_make_doc("id1", "Padre", 1), _make_doc("id2", "Madre", 2)]

    (
        mock_firestore_client.collection.return_value
        .document.return_value
        .collection.return_value
        .stream
    ).side_effect = [iter(docs), iter(docs)]

    req = _make_request("GET")
    response1 = catalog_relationship_type(req)
    response2 = catalog_relationship_type(req)

    assert response1.status_code == 200
    assert response2.status_code == 200
    body1 = json.loads(response1.get_data(as_text=True))
    body2 = json.loads(response2.get_data(as_text=True))
    assert body1 == body2


def test_invalid_token_returns_401(mock_validate_request, mock_verify_bearer_token_fail):
    """Token inválido o faltante retorna 401."""
    from catalogs.relationship_type import catalog_relationship_type

    req = _make_request("GET")
    response = catalog_relationship_type(req)

    assert response.status_code == 401


def test_post_method_returns_405(mock_validate_request):
    """Método no permitido retorna 405."""
    from catalogs.relationship_type import catalog_relationship_type

    mock_validate_request.return_value = MagicMock(status_code=405)

    req = _make_request("POST")
    # validate_request retorna el response directamente cuando el método no es válido
    with patch(
        "catalogs.relationship_type.validate_request",
        return_value=MagicMock(status_code=405),
    ):
        response = catalog_relationship_type(req)
        assert response.status_code == 405


def test_response_content_type_is_json(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    """La respuesta tiene Content-Type application/json."""
    from catalogs.relationship_type import catalog_relationship_type

    (
        mock_firestore_client.collection.return_value
        .document.return_value
        .collection.return_value
        .stream.return_value
    ) = iter([_make_doc("id1", "Padre", 1)])

    req = _make_request("GET")
    response = catalog_relationship_type(req)

    assert response.status_code == 200
    assert "application/json" in response.content_type


def test_items_sorted_by_order_field(
    mock_validate_request, mock_verify_bearer_token, mock_firestore_client
):
    """Los items se devuelven ordenados ascendentemente por el campo `order`."""
    from catalogs.relationship_type import catalog_relationship_type

    docs = [
        _make_doc("id20", "Otro", 20),
        _make_doc("id5", "Hija", 5),
        _make_doc("id1", "Padre", 1),
    ]
    (
        mock_firestore_client.collection.return_value
        .document.return_value
        .collection.return_value
        .stream.return_value
    ) = iter(docs)

    req = _make_request("GET")
    response = catalog_relationship_type(req)

    body = json.loads(response.get_data(as_text=True))
    orders = [item["order"] for item in body]
    assert orders == sorted(orders)
