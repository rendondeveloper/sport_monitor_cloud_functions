"""
Pruebas unitarias para competitors.delete_competitor.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


def _make_request(body=None):
    req = MagicMock()
    req.method = "DELETE"
    req.path = "/api/competitors/delete-competitor"
    req.get_json = lambda silent=True: body
    return req


@patch("competitors.delete_competitor.verify_bearer_token", return_value=True)
@patch("competitors.delete_competitor.validate_request", return_value=None)
@patch("competitors.delete_competitor.delete_competitor_resources")
@patch("competitors.delete_competitor.FirestoreHelper")
def test_delete_competitor_happy_path(
    mock_helper_cls, mock_delete_resources, mock_validate, mock_verify
):
    helper = MagicMock()
    helper.get_document.return_value = {"id": "user-1"}
    mock_helper_cls.return_value = helper

    from competitors.delete_competitor import delete_competitor

    req = _make_request({"eventId": "event-1", "userId": "user-1"})
    response = delete_competitor(req)

    assert response.status_code == 204
    mock_delete_resources.assert_called_once_with(helper, "user-1", "event-1")


@patch("competitors.delete_competitor.verify_bearer_token", return_value=True)
@patch("competitors.delete_competitor.validate_request", return_value=None)
def test_delete_competitor_missing_body(mock_validate, mock_verify):
    from competitors.delete_competitor import delete_competitor

    req = _make_request(body=None)
    response = delete_competitor(req)

    assert response.status_code == 400


@patch("competitors.delete_competitor.verify_bearer_token", return_value=True)
@patch("competitors.delete_competitor.validate_request", return_value=None)
def test_delete_competitor_missing_user_id(mock_validate, mock_verify):
    from competitors.delete_competitor import delete_competitor

    req = _make_request({"eventId": "event-1"})
    response = delete_competitor(req)

    assert response.status_code == 400


@patch("competitors.delete_competitor.verify_bearer_token", return_value=True)
@patch("competitors.delete_competitor.validate_request", return_value=None)
def test_delete_competitor_rejects_email_only(mock_validate, mock_verify):
    from competitors.delete_competitor import delete_competitor

    req = _make_request({"eventId": "event-1", "email": "user@example.com"})
    response = delete_competitor(req)

    assert response.status_code == 400


@patch("competitors.delete_competitor.verify_bearer_token", return_value=True)
@patch("competitors.delete_competitor.validate_request", return_value=None)
@patch("competitors.delete_competitor.FirestoreHelper")
def test_delete_competitor_participant_not_found(
    mock_helper_cls, mock_validate, mock_verify
):
    helper = MagicMock()
    helper.get_document.return_value = None
    mock_helper_cls.return_value = helper

    from competitors.delete_competitor import delete_competitor

    req = _make_request({"eventId": "event-1", "userId": "user-1"})
    response = delete_competitor(req)

    assert response.status_code == 404


@patch("competitors.delete_competitor.verify_bearer_token", return_value=False)
@patch("competitors.delete_competitor.validate_request", return_value=None)
def test_delete_competitor_unauthorized(mock_validate, mock_verify):
    from competitors.delete_competitor import delete_competitor

    req = _make_request({"eventId": "event-1", "userId": "user-1"})
    response = delete_competitor(req)

    assert response.status_code == 401


@patch("competitors.delete_competitor.validate_request")
def test_delete_competitor_validation_response(mock_validate):
    from competitors.delete_competitor import delete_competitor
    from firebase_functions import https_fn

    early = https_fn.Response("", status=405)
    mock_validate.return_value = early

    req = _make_request({"eventId": "event-1", "userId": "user-1"})
    response = delete_competitor(req)

    assert response is early


@patch("competitors.delete_competitor.verify_bearer_token", return_value=True)
@patch("competitors.delete_competitor.validate_request", return_value=None)
def test_delete_competitor_missing_event_id(mock_validate, mock_verify):
    from competitors.delete_competitor import delete_competitor

    req = _make_request({"userId": "user-1"})
    response = delete_competitor(req)

    assert response.status_code == 400


@patch("competitors.delete_competitor.verify_bearer_token", return_value=True)
@patch("competitors.delete_competitor.validate_request", return_value=None)
def test_delete_competitor_invalid_json_body(mock_validate, mock_verify):
    from competitors.delete_competitor import delete_competitor

    req = _make_request()
    req.get_json = MagicMock(side_effect=ValueError("bad json"))
    response = delete_competitor(req)

    assert response.status_code == 400


@patch("competitors.delete_competitor.verify_bearer_token", return_value=True)
@patch("competitors.delete_competitor.validate_request", return_value=None)
@patch("competitors.delete_competitor.delete_competitor_resources")
@patch("competitors.delete_competitor.FirestoreHelper")
def test_delete_competitor_accepts_snake_case_fields(
    mock_helper_cls, mock_delete_resources, mock_validate, mock_verify
):
    helper = MagicMock()
    helper.get_document.return_value = {"id": "user-1"}
    mock_helper_cls.return_value = helper

    from competitors.delete_competitor import delete_competitor

    req = _make_request({"event_id": "event-1", "user_id": "user-1"})
    response = delete_competitor(req)

    assert response.status_code == 204
    mock_delete_resources.assert_called_once_with(helper, "user-1", "event-1")


@patch("competitors.delete_competitor.verify_bearer_token", return_value=True)
@patch("competitors.delete_competitor.validate_request", return_value=None)
@patch("competitors.delete_competitor.delete_competitor_resources", side_effect=RuntimeError("boom"))
@patch("competitors.delete_competitor.FirestoreHelper")
def test_delete_competitor_internal_error(
    mock_helper_cls, mock_delete_resources, mock_validate, mock_verify
):
    helper = MagicMock()
    helper.get_document.return_value = {"id": "user-1"}
    mock_helper_cls.return_value = helper

    from competitors.delete_competitor import delete_competitor

    req = _make_request({"eventId": "event-1", "userId": "user-1"})
    response = delete_competitor(req)

    assert response.status_code == 500
