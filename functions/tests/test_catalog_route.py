"""
Tests para catalog_route: router central de catálogos.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


def _make_request(method="GET", path="/api/catalogs/color", headers=None):
    req = MagicMock()
    req.method = method
    req.path = path
    req.headers = dict(headers) if headers else {}
    req.args = {}
    req.get_json = lambda silent=True: None
    return req


@patch("catalogs.catalog_route.verify_bearer_token", return_value=False)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_catalog_route_invalid_token_returns_401(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    req = _make_request(path="/api/catalogs/vehicle", headers={"Authorization": "Bearer bad"})
    response = catalog_route(req)
    assert response.status_code == 401


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_catalog_route_unknown_path_returns_404(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    req = _make_request(path="/api/catalogs/unknown", method="GET")
    response = catalog_route(req)
    assert response.status_code == 404


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_catalog_route_single_segment_color_fallback(_mock_validate, _mock_verify):
    """Path solo 'color' (rewrite) despacha al catálogo color."""
    from catalogs.catalog_route import catalog_route

    mock_list = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_list.return_value = mock_resp

    with (
        patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()),
        patch("catalogs.catalog_route._color_list", mock_list),
    ):
        req = _make_request(path="/color", method="GET")
        response = catalog_route(req)
    assert response.status_code == 200
    mock_list.assert_called_once()


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_relationship_post_returns_405(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    with patch("catalogs.catalog_route.firestore.client"):
        req = _make_request(path="/api/catalogs/relationship-type", method="POST")
        response = catalog_route(req)
    assert response.status_code == 405
    assert "Allow" in dict(response.headers)


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_relationship_get_returns_200_with_data(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    docs = []
    doc1 = MagicMock()
    doc1.id = "id1"
    doc1.to_dict.return_value = {"label": "Padre", "order": 1}
    doc2 = MagicMock()
    doc2.id = "id2"
    doc2.to_dict.return_value = {"label": "Madre", "order": 2}

    db = MagicMock()
    (
        db.collection.return_value.document.return_value.collection.return_value.stream.return_value
    ) = iter([doc2, doc1])

    with patch("catalogs.catalog_route.firestore.client", return_value=db):
        req = _make_request(path="/api/catalogs/relationship-type", method="GET")
        response = catalog_route(req)

    assert response.status_code == 200
    body = json.loads(response.get_data(as_text=True))
    assert len(body) == 2
    assert body[0]["order"] == 1


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_vehicle_get_dispatches_to_list(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    mock_list = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_list.return_value = mock_resp

    with (
        patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()),
        patch("catalogs.catalog_route._vehicle_list", mock_list),
    ):
        req = _make_request(path="/api/catalogs/vehicle", method="GET")
        response = catalog_route(req)
    assert response.status_code == 200
    mock_list.assert_called_once()


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_year_put_dispatches_to_update(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    mock_update = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_update.return_value = mock_resp

    db = MagicMock()
    with (
        patch("catalogs.catalog_route.firestore.client", return_value=db),
        patch("catalogs.catalog_route._year_update", mock_update),
    ):
        req = _make_request(path="/api/catalogs/year", method="PUT")
        response = catalog_route(req)
    assert response.status_code == 200
    mock_update.assert_called_once_with(req, db)


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_color_delete_dispatches_to_delete(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    mock_delete = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 204
    mock_delete.return_value = mock_resp

    db = MagicMock()
    with (
        patch("catalogs.catalog_route.firestore.client", return_value=db),
        patch("catalogs.catalog_route._color_delete", mock_delete),
    ):
        req = _make_request(path="/api/catalogs/color", method="DELETE")
        response = catalog_route(req)
    assert response.status_code == 204
    mock_delete.assert_called_once_with(req, db)


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_vehicle_two_gets_stable(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    mock_list = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_list.return_value = mock_resp

    with (
        patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()),
        patch("catalogs.catalog_route._vehicle_list", mock_list),
    ):
        req = _make_request(path="/api/catalogs/vehicle", method="GET")
        r1 = catalog_route(req)
        r2 = catalog_route(req)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert mock_list.call_count == 2


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request")
def test_validate_request_early_return(mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    early = MagicMock()
    early.status_code = 204
    mock_validate.return_value = early

    req = _make_request(path="/api/catalogs/vehicle", method="OPTIONS")
    response = catalog_route(req)
    assert response.status_code == 204


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_internal_error_returns_500(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    with patch(
        "catalogs.catalog_route.firestore.client",
        side_effect=RuntimeError("db down"),
    ):
        req = _make_request(path="/api/catalogs/year", method="GET")
        response = catalog_route(req)
    assert response.status_code == 500


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_empty_path_returns_404(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    req = _make_request(path="", method="GET")
    response = catalog_route(req)
    assert response.status_code == 404


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_catalogs_without_segment_returns_404(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    req = _make_request(path="/api/catalogs", method="GET")
    response = catalog_route(req)
    assert response.status_code == 404


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_invalid_segment_after_catalogs_returns_404(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    req = _make_request(path="/api/catalogs/not-a-catalog", method="GET")
    response = catalog_route(req)
    assert response.status_code == 404


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_vehicle_unsupported_method_returns_405(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    with patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()):
        req = _make_request(path="/api/catalogs/vehicle", method="PATCH")
        response = catalog_route(req)
    assert response.status_code == 405


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_year_unsupported_method_returns_405(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    with patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()):
        req = _make_request(path="/api/catalogs/year", method="PATCH")
        response = catalog_route(req)
    assert response.status_code == 405


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_color_unsupported_method_returns_405(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    with patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()):
        req = _make_request(path="/api/catalogs/color", method="PATCH")
        response = catalog_route(req)
    assert response.status_code == 405


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_checkpoint_type_get_dispatches_to_list(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    mock_list = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_list.return_value = mock_resp

    with (
        patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()),
        patch("catalogs.catalog_route._checkpoint_type_list", mock_list),
    ):
        req = _make_request(path="/api/catalogs/checkpoint-type", method="GET")
        response = catalog_route(req)
    assert response.status_code == 200
    mock_list.assert_called_once()


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_checkpoint_type_put_returns_405(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    with patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()):
        req = _make_request(path="/api/catalogs/checkpoint-type", method="PUT")
        response = catalog_route(req)
    assert response.status_code == 405
    assert response.headers.get("Allow") == "GET, POST, DELETE"


@patch("catalogs.catalog_route.verify_bearer_token", return_value=True)
@patch("catalogs.catalog_route.validate_request", return_value=None)
def test_checkpoint_type_single_segment_fallback(_mock_validate, _mock_verify):
    from catalogs.catalog_route import catalog_route

    mock_list = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_list.return_value = mock_resp

    with (
        patch("catalogs.catalog_route.firestore.client", return_value=MagicMock()),
        patch("catalogs.catalog_route._checkpoint_type_list", mock_list),
    ):
        req = _make_request(path="/checkpoint-type", method="GET")
        response = catalog_route(req)
    assert response.status_code == 200
    mock_list.assert_called_once()
