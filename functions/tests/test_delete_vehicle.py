"""
Pruebas unitarias para vehicles.delete (handle) (SPRTMNTRPP-73).
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


def _make_request(
    method: str = "DELETE",
    path: str = "/api/vehicles/veh-123",
    user_id: str = "user-1",
    auth_user_id: str = "auth-1",
    vehicle_id_query: str | None = "veh-123",
):
    """Construye un mock de Request para DELETE."""
    req = MagicMock()
    req.method = method
    req.path = path

    def _get_arg(k, default=None):
        if k == "userId":
            return user_id or default
        if k == "authUserId":
            return auth_user_id or default
        if k == "vehicleId":
            return vehicle_id_query if vehicle_id_query is not None else default
        return default

    req.args.get.side_effect = _get_arg
    return req


@patch("vehicles.delete.firestore")
def test_delete_vehicle_happy_path(mock_firestore_module):
    """Happy path: DELETE con parametros validos y vehiculo existente -> 204."""
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"authUserId": "auth-1"}
    vehicle_doc = MagicMock()
    vehicle_doc.exists = True
    vehicle_ref = MagicMock()
    vehicle_ref.get.return_value = vehicle_doc
    vehicle_ref.delete = MagicMock()
    sub_collection = MagicMock()
    sub_collection.document.return_value = vehicle_ref
    user_ref = MagicMock()
    user_ref.get.return_value = user_doc
    user_ref.collection.return_value = sub_collection
    users_col = MagicMock()
    users_col.document.return_value = user_ref
    client = MagicMock()
    client.collection.return_value = users_col
    mock_firestore_module.client.return_value = client

    from vehicles.delete import handle

    req = _make_request()
    response = handle(req)

    assert response.status_code == 204
    assert response.get_data(as_text=True) == ""
    vehicle_ref.delete.assert_called_once()


def test_delete_vehicle_missing_vehicle_id():
    """vehicleId faltante (path sin segmento y query vacio) -> 400."""
    from vehicles.delete import handle

    req = _make_request(path="/api/vehicles/", vehicle_id_query=None)
    req.args.get.side_effect = lambda k, default=None: {"userId": "u1", "authUserId": "a1"}.get(k, default or "")
    response = handle(req)

    assert response.status_code == 400


def test_delete_vehicle_missing_user_id():
    """userId faltante o vacio -> 400."""
    from vehicles.delete import handle

    req = _make_request(user_id="")
    response = handle(req)

    assert response.status_code == 400


def test_delete_vehicle_missing_auth_user_id():
    """authUserId faltante o vacio -> 400."""
    from vehicles.delete import handle

    req = _make_request(auth_user_id="")
    response = handle(req)

    assert response.status_code == 400


@patch("vehicles.delete.firestore")
def test_delete_vehicle_user_not_found(mock_firestore_module):
    """Usuario no existe -> 404."""
    user_doc = MagicMock()
    user_doc.exists = False
    user_ref = MagicMock()
    user_ref.get.return_value = user_doc
    users_col = MagicMock()
    users_col.document.return_value = user_ref
    client = MagicMock()
    client.collection.return_value = users_col
    mock_firestore_module.client.return_value = client

    from vehicles.delete import handle

    req = _make_request()
    response = handle(req)

    assert response.status_code == 404


@patch("vehicles.delete.firestore")
def test_delete_vehicle_auth_user_id_mismatch(mock_firestore_module):
    """authUserId no coincide con el usuario -> 404."""
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"authUserId": "other-auth"}
    user_ref = MagicMock()
    user_ref.get.return_value = user_doc
    users_col = MagicMock()
    users_col.document.return_value = user_ref
    client = MagicMock()
    client.collection.return_value = users_col
    mock_firestore_module.client.return_value = client

    from vehicles.delete import handle

    req = _make_request()
    response = handle(req)

    assert response.status_code == 404


@patch("vehicles.delete.firestore")
def test_delete_vehicle_not_found(mock_firestore_module):
    """Vehiculo no existe -> 404."""
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"authUserId": "auth-1"}
    vehicle_doc = MagicMock()
    vehicle_doc.exists = False
    vehicle_ref = MagicMock()
    vehicle_ref.get.return_value = vehicle_doc
    sub_collection = MagicMock()
    sub_collection.document.return_value = vehicle_ref
    user_ref = MagicMock()
    user_ref.get.return_value = user_doc
    user_ref.collection.return_value = sub_collection
    users_col = MagicMock()
    users_col.document.return_value = user_ref
    client = MagicMock()
    client.collection.return_value = users_col
    mock_firestore_module.client.return_value = client

    from vehicles.delete import handle

    req = _make_request()
    response = handle(req)

    assert response.status_code == 404
    vehicle_ref.delete.assert_not_called()


@patch("vehicles.delete.firestore")
def test_delete_vehicle_multiple_calls(mock_firestore_module):
    """Dos llamadas seguidas: comportamiento estable."""
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {"authUserId": "auth-1"}
    vehicle_doc = MagicMock()
    vehicle_doc.exists = True
    vehicle_ref = MagicMock()
    vehicle_ref.get.return_value = vehicle_doc
    vehicle_ref.delete = MagicMock()
    sub_collection = MagicMock()
    sub_collection.document.return_value = vehicle_ref
    user_ref = MagicMock()
    user_ref.get.return_value = user_doc
    user_ref.collection.return_value = sub_collection
    users_col = MagicMock()
    users_col.document.return_value = user_ref
    client = MagicMock()
    client.collection.return_value = users_col
    mock_firestore_module.client.return_value = client

    from vehicles.delete import handle

    req1 = _make_request()
    r1 = handle(req1)
    assert r1.status_code == 204
    vehicle_ref.delete.assert_called_once()

    vehicle_ref.delete.reset_mock()
    req2 = _make_request()
    r2 = handle(req2)
    assert r2.status_code == 204
    vehicle_ref.delete.assert_called_once()
