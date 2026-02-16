"""
Pruebas unitarias para search_vehicle.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


def _make_request(
    method: str = "GET",
    user_id: str = "user-1",
    branch: str = "Honda",
    model: str = "CRF450R",
    year: str = "2024",
):
    """Construye un mock de Request para GET search_vehicle."""
    req = MagicMock()
    req.method = method

    params = {
        "userId": user_id,
        "branch": branch,
        "model": model,
        "year": year,
    }

    def _get_arg(k, default=None):
        return params.get(k, default)

    req.args.get.side_effect = _get_arg
    return req


VEHICLE_DATA = {
    "branch": "Honda",
    "model": "CRF450R",
    "year": 2024,
    "color": "Rojo",
    "createdAt": "2026-01-15T10:00:00Z",
    "updatedAt": "2026-01-15T10:00:00Z",
}


# --- Happy path ---


@patch("vehicles.search_vehicle.FirestoreHelper")
@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_found(mock_validate, mock_verify, mock_fs_cls):
    """Happy path: vehículo coincide en branch, model y year → 200 con datos."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.return_value = {"name": "Test User"}
    fs_instance.query_documents.return_value = [("veh-abc", VEHICLE_DATA)]

    from vehicles.search_vehicle import search_vehicle

    req = _make_request()
    response = search_vehicle(req)

    assert response.status_code == 200
    body = json.loads(response.response[0])
    assert body["id"] == "veh-abc"
    assert body["branch"] == "Honda"
    assert body["model"] == "CRF450R"
    assert body["year"] == 2024
    assert body["color"] == "Rojo"


# --- Not found ---


@patch("vehicles.search_vehicle.FirestoreHelper")
@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_not_found(mock_validate, mock_verify, mock_fs_cls):
    """No hay coincidencia → 404."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.return_value = {"name": "Test User"}
    fs_instance.query_documents.return_value = []

    from vehicles.search_vehicle import search_vehicle

    req = _make_request()
    response = search_vehicle(req)

    assert response.status_code == 404


# --- Validación de request ---


@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_validation_fails(mock_validate, mock_verify):
    """validate_request retorna respuesta → se devuelve esa respuesta (ej: 405)."""
    mock_verify.return_value = True
    mock_validate.return_value = MagicMock(status_code=405)

    from vehicles.search_vehicle import search_vehicle

    req = _make_request()
    response = search_vehicle(req)

    assert response.status_code == 405


# --- Token inválido ---


@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_unauthorized(mock_validate, mock_verify):
    """Token inválido o faltante → 401."""
    mock_validate.return_value = None
    mock_verify.return_value = False

    from vehicles.search_vehicle import search_vehicle

    req = _make_request()
    response = search_vehicle(req)

    assert response.status_code == 401


# --- Parámetros faltantes ---


@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_missing_user_id(mock_validate, mock_verify):
    """userId faltante → 400."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    from vehicles.search_vehicle import search_vehicle

    req = _make_request(user_id="")
    response = search_vehicle(req)

    assert response.status_code == 400


@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_missing_branch(mock_validate, mock_verify):
    """branch faltante → 400."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    from vehicles.search_vehicle import search_vehicle

    req = _make_request(branch="")
    response = search_vehicle(req)

    assert response.status_code == 400


@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_missing_model(mock_validate, mock_verify):
    """model faltante → 400."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    from vehicles.search_vehicle import search_vehicle

    req = _make_request(model="")
    response = search_vehicle(req)

    assert response.status_code == 400


@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_missing_year(mock_validate, mock_verify):
    """year faltante → 400."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    from vehicles.search_vehicle import search_vehicle

    req = _make_request(year="")
    response = search_vehicle(req)

    assert response.status_code == 400


# --- year inválido ---


@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_year_not_numeric(mock_validate, mock_verify):
    """year no numérico → 400."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    from vehicles.search_vehicle import search_vehicle

    req = _make_request(year="abc")
    response = search_vehicle(req)

    assert response.status_code == 400


@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_year_out_of_range(mock_validate, mock_verify):
    """year fuera de rango (< 1900 o > 2100) → 400."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    from vehicles.search_vehicle import search_vehicle

    req = _make_request(year="1800")
    response = search_vehicle(req)

    assert response.status_code == 400


# --- Usuario no encontrado ---


@patch("vehicles.search_vehicle.FirestoreHelper")
@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_user_not_found(mock_validate, mock_verify, mock_fs_cls):
    """Usuario no existe → 404."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.return_value = None

    from vehicles.search_vehicle import search_vehicle

    req = _make_request()
    response = search_vehicle(req)

    assert response.status_code == 404


# --- Múltiples llamadas ---


@patch("vehicles.search_vehicle.FirestoreHelper")
@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_multiple_calls(mock_validate, mock_verify, mock_fs_cls):
    """Dos llamadas seguidas: comportamiento estable."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.return_value = {"name": "Test User"}
    fs_instance.query_documents.return_value = [("veh-abc", VEHICLE_DATA)]

    from vehicles.search_vehicle import search_vehicle

    req1 = _make_request()
    r1 = search_vehicle(req1)
    assert r1.status_code == 200

    req2 = _make_request()
    r2 = search_vehicle(req2)
    assert r2.status_code == 200

    body1 = json.loads(r1.response[0])
    body2 = json.loads(r2.response[0])
    assert body1["id"] == body2["id"]


# --- Error interno (excepción en FirestoreHelper) ---


@patch("vehicles.search_vehicle.FirestoreHelper")
@patch("vehicles.search_vehicle.verify_bearer_token")
@patch("vehicles.search_vehicle.validate_request")
def test_search_vehicle_internal_error(mock_validate, mock_verify, mock_fs_cls):
    """Excepción interna → 500."""
    mock_validate.return_value = None
    mock_verify.return_value = True

    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.side_effect = RuntimeError("Firestore down")

    from vehicles.search_vehicle import search_vehicle

    req = _make_request()
    response = search_vehicle(req)

    assert response.status_code == 500
