"""
Pruebas unitarias para vehicles.search (handle).
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
    """Construye un mock de Request para GET search."""
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


@patch("vehicles.search.FirestoreHelper")
def test_search_vehicle_found(mock_fs_cls):
    """Happy path: vehiculo coincide en branch, model y year -> 200 con datos."""
    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.return_value = {"name": "Test User"}
    fs_instance.query_documents.return_value = [("veh-abc", VEHICLE_DATA)]

    from vehicles.search import handle

    req = _make_request()
    response = handle(req)

    assert response.status_code == 200
    body = json.loads(response.response[0])
    assert body["id"] == "veh-abc"
    assert body["branch"] == "Honda"
    assert body["model"] == "CRF450R"
    assert body["year"] == 2024
    assert body["color"] == "Rojo"


# --- Not found ---


@patch("vehicles.search.FirestoreHelper")
def test_search_vehicle_not_found(mock_fs_cls):
    """No hay coincidencia -> 404."""
    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.return_value = {"name": "Test User"}
    fs_instance.query_documents.return_value = []

    from vehicles.search import handle

    req = _make_request()
    response = handle(req)

    assert response.status_code == 404


# --- Parametros faltantes ---


def test_search_vehicle_missing_user_id():
    """userId faltante -> 400."""
    from vehicles.search import handle

    req = _make_request(user_id="")
    response = handle(req)

    assert response.status_code == 400


def test_search_vehicle_missing_branch():
    """branch faltante -> 400."""
    from vehicles.search import handle

    req = _make_request(branch="")
    response = handle(req)

    assert response.status_code == 400


def test_search_vehicle_missing_model():
    """model faltante -> 400."""
    from vehicles.search import handle

    req = _make_request(model="")
    response = handle(req)

    assert response.status_code == 400


def test_search_vehicle_missing_year():
    """year faltante -> 400."""
    from vehicles.search import handle

    req = _make_request(year="")
    response = handle(req)

    assert response.status_code == 400


# --- year invalido ---


def test_search_vehicle_year_not_numeric():
    """year no numerico -> 400."""
    from vehicles.search import handle

    req = _make_request(year="abc")
    response = handle(req)

    assert response.status_code == 400


def test_search_vehicle_year_out_of_range():
    """year fuera de rango (< 1900 o > 2100) -> 400."""
    from vehicles.search import handle

    req = _make_request(year="1800")
    response = handle(req)

    assert response.status_code == 400


# --- Usuario no encontrado ---


@patch("vehicles.search.FirestoreHelper")
def test_search_vehicle_user_not_found(mock_fs_cls):
    """Usuario no existe -> 404."""
    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.return_value = None

    from vehicles.search import handle

    req = _make_request()
    response = handle(req)

    assert response.status_code == 404


# --- Multiples llamadas ---


@patch("vehicles.search.FirestoreHelper")
def test_search_vehicle_multiple_calls(mock_fs_cls):
    """Dos llamadas seguidas: comportamiento estable."""
    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.return_value = {"name": "Test User"}
    fs_instance.query_documents.return_value = [("veh-abc", VEHICLE_DATA)]

    from vehicles.search import handle

    req1 = _make_request()
    r1 = handle(req1)
    assert r1.status_code == 200

    req2 = _make_request()
    r2 = handle(req2)
    assert r2.status_code == 200

    body1 = json.loads(r1.response[0])
    body2 = json.loads(r2.response[0])
    assert body1["id"] == body2["id"]


# --- Error interno (excepcion en FirestoreHelper) ---


@patch("vehicles.search.FirestoreHelper")
def test_search_vehicle_internal_error(mock_fs_cls):
    """Excepcion interna -> 500."""
    fs_instance = MagicMock()
    mock_fs_cls.return_value = fs_instance
    fs_instance.get_document.side_effect = RuntimeError("Firestore down")

    from vehicles.search import handle

    req = _make_request()
    response = handle(req)

    assert response.status_code == 500
