"""
Pruebas unitarias para delete_vehicle (SPRTMNTRPP-73).
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


def _mock_firestore(user_exists: bool = True, auth_matches: bool = True, vehicle_exists: bool = True):
    """Mock de Firestore: usuario existe, auth coincide, vehículo existe."""
    user_doc = MagicMock()
    user_doc.exists = user_exists
    user_doc.to_dict.return_value = {"authUserId": "auth-1"} if auth_matches else {"authUserId": "other"}

    vehicle_doc = MagicMock()
    vehicle_doc.exists = vehicle_exists

    def _get_collection(name):
        col = MagicMock()
        if name == "users":
            def _doc(uid):
                doc_ref = MagicMock()
                doc_ref.get.return_value = user_doc
                if user_exists and auth_matches:
                    sub = MagicMock()
                    sub_ref = MagicMock()
                    sub_ref.get.return_value = vehicle_doc
                    sub_ref.delete = MagicMock()
                    sub.document.return_value = sub_ref
                    doc_ref.collection.return_value = sub
                return doc_ref
                doc_ref.collection.side_effect = lambda c: sub
                return doc_ref
            col.document.side_effect = _doc
        return col

    client = MagicMock()
    client.collection.side_effect = _get_collection
    return client


@patch("vehicles.delete_vehicle.firestore")
@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_happy_path(mock_validate, mock_verify, mock_firestore_module):
    """Happy path: DELETE con parámetros válidos y vehículo existente → 204."""
    mock_validate.return_value = None
    mock_verify.return_value = True

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

    from vehicles.delete_vehicle import delete_vehicle

    req = _make_request()
    response = delete_vehicle(req)

    assert response.status_code == 204
    assert response.get_data(as_text=True) == ""
    vehicle_ref.delete.assert_called_once()


@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_validation_fails(mock_validate, mock_verify):
    """validate_request retorna respuesta → se devuelve esa respuesta."""
    mock_verify.return_value = True
    mock_validate.return_value = MagicMock(status_code=405)

    from vehicles.delete_vehicle import delete_vehicle

    req = _make_request()
    response = delete_vehicle(req)

    assert response.status_code == 405


@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_unauthorized(mock_validate, mock_verify):
    """Token inválido o faltante → 401."""
    mock_validate.return_value = None
    mock_verify.return_value = False

    from vehicles.delete_vehicle import delete_vehicle

    req = _make_request()
    response = delete_vehicle(req)

    assert response.status_code == 401


@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_missing_vehicle_id(mock_validate, mock_verify):
    """vehicleId faltante (path sin segmento y query vacío) → 400."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    from vehicles.delete_vehicle import delete_vehicle

    req = _make_request(path="/api/vehicles/", vehicle_id_query=None)
    req.args.get.side_effect = lambda k, default=None: {"userId": "u1", "authUserId": "a1"}.get(k, default or "")
    response = delete_vehicle(req)

    assert response.status_code == 400


@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_missing_user_id(mock_validate, mock_verify):
    """userId faltante o vacío → 400."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    from vehicles.delete_vehicle import delete_vehicle

    req = _make_request(user_id="")
    response = delete_vehicle(req)

    assert response.status_code == 400


@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_missing_auth_user_id(mock_validate, mock_verify):
    """authUserId faltante o vacío → 400."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    from vehicles.delete_vehicle import delete_vehicle

    req = _make_request(auth_user_id="")
    response = delete_vehicle(req)

    assert response.status_code == 400


@patch("vehicles.delete_vehicle.firestore")
@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_user_not_found(mock_validate, mock_verify, mock_firestore_module):
    """Usuario no existe → 404."""
    mock_validate.return_value = None
    mock_verify.return_value = True
    user_doc = MagicMock()
    user_doc.exists = False
    user_ref = MagicMock()
    user_ref.get.return_value = user_doc
    users_col = MagicMock()
    users_col.document.return_value = user_ref
    client = MagicMock()
    client.collection.return_value = users_col
    mock_firestore_module.client.return_value = client

    from vehicles.delete_vehicle import delete_vehicle

    req = _make_request()
    response = delete_vehicle(req)

    assert response.status_code == 404


@patch("vehicles.delete_vehicle.firestore")
@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_auth_user_id_mismatch(mock_validate, mock_verify, mock_firestore_module):
    """authUserId no coincide con el usuario → 404."""
    mock_validate.return_value = None
    mock_verify.return_value = True
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

    from vehicles.delete_vehicle import delete_vehicle

    req = _make_request()
    response = delete_vehicle(req)

    assert response.status_code == 404


@patch("vehicles.delete_vehicle.firestore")
@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_not_found(mock_validate, mock_verify, mock_firestore_module):
    """Vehículo no existe → 404."""
    mock_validate.return_value = None
    mock_verify.return_value = True
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

    from vehicles.delete_vehicle import delete_vehicle

    req = _make_request()
    response = delete_vehicle(req)

    assert response.status_code == 404
    vehicle_ref.delete.assert_not_called()


@patch("vehicles.delete_vehicle.firestore")
@patch("vehicles.delete_vehicle.verify_bearer_token")
@patch("vehicles.delete_vehicle.validate_request")
def test_delete_vehicle_multiple_calls(mock_validate, mock_verify, mock_firestore_module):
    """Dos llamadas seguidas: comportamiento estable (segunda puede 404 si ya se eliminó)."""
    mock_validate.return_value = None
    mock_verify.return_value = True
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

    from vehicles.delete_vehicle import delete_vehicle

    req1 = _make_request()
    r1 = delete_vehicle(req1)
    assert r1.status_code == 204
    vehicle_ref.delete.assert_called_once()

    # Segunda llamada: mismo mock, delete ya fue llamado; si exists sigue True, elimina de nuevo
    vehicle_ref.delete.reset_mock()
    req2 = _make_request()
    r2 = delete_vehicle(req2)
    assert r2.status_code == 204
    vehicle_ref.delete.assert_called_once()
