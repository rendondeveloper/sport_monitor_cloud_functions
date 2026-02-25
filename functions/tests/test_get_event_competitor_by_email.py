"""
Tests para get_event_competitor_by_email Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path
2. Parámetros faltantes
3. Valor/tipo incorrecto (email inválido)
4. Consultas con data (mock Firestore)
5. Escrituras exitosas (N/A para GET)
6. Múltiples llamadas al mismo API
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================

_MOD = "competitors.get_event_competitor_by_email"


@pytest.fixture
def mock_validate_request():
    with patch(f"{_MOD}.validate_request", return_value=None) as m:
        yield m


@pytest.fixture
def mock_verify_bearer_token():
    with patch(f"{_MOD}.verify_bearer_token", return_value=True) as m:
        yield m


@pytest.fixture
def mock_firestore_helper():
    with patch(f"{_MOD}.FirestoreHelper") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


@pytest.fixture
def mock_validate_email_ok():
    with patch(f"{_MOD}.validate_email", return_value=True) as m:
        yield m


@pytest.fixture
def sample_user_doc():
    return {
        "email": "pilot@example.com",
        "username": "pilot42",
        "authUserId": None,
        "avatarUrl": None,
        "isActive": False,
        "createdAt": "2026-02-15T08:00:00",
        "updatedAt": "2026-02-15T09:00:00",
    }


@pytest.fixture
def sample_participant_doc():
    return {
        "userId": "user123",
        "eventId": "event123",
        "competitionCategory": {
            "pilotNumber": "42",
            "registrationCategory": "Pro",
        },
        "registrationDate": "2026-02-15T10:00:00",
        "team": "Team Red Bull",
        "score": 10,
        "timesToStart": [],
        "createdAt": "2026-02-15T08:00:00",
        "updatedAt": "2026-02-15T09:00:00",
    }


def _make_request(event_id="", email="", method="GET"):
    req = MagicMock()
    req.method = method
    req.args = {}
    req.path = ""
    req.headers = {"Authorization": "Bearer test_token"}

    if event_id:
        req.args["eventId"] = event_id
    if email:
        req.args["email"] = email

    return req


def _setup_full_response(mock_helper, sample_user_doc, sample_participant_doc):
    """Configura mocks para una respuesta exitosa completa."""
    mock_helper.query_documents.side_effect = [
        [("user123", sample_user_doc)],
        [("pd1", {"fullName": "Juan", "phone": "+521234567890", "createdAt": "t", "updatedAt": "t"})],
        [("hd1", {"bloodType": "O+", "createdAt": "t", "updatedAt": "t"})],
        [("ec1", {"fullName": "María", "phone": "+529876543210", "relationship": "Spouse", "createdAt": "t", "updatedAt": "t"})],
        [("v1", {"branch": "Honda", "year": 2024, "model": "CRF450R", "color": "Red", "createdAt": "t", "updatedAt": "t"})],
        [("event123", {"userId": "user123", "eventId": "event123", "createdAt": "t", "updatedAt": "t"})],
    ]
    mock_helper.get_document.return_value = sample_participant_doc


# ============================================================================
# TESTS
# ============================================================================


class TestHappyPath:
    """Happy path: usuario encontrado, participante en evento, register dentro de membership."""

    def test_success_with_all_data(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)

        req = _make_request(event_id="event123", email="pilot@example.com")
        response = get_event_competitor_by_email(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["id"] == "user123"
        assert data["email"] == "pilot@example.com"
        assert len(data["personalData"]) == 1
        assert len(data["healthData"]) == 1
        assert len(data["emergencyContacts"]) == 1
        assert len(data["vehicles"]) == 1
        assert len(data["membership"]) == 1
        register = data["membership"][0]["register"]
        assert register["number"] == "42"
        assert register["category"] == "Pro"
        assert register["team"] == "Team Red Bull"
        assert "competition" not in data

    def test_no_created_at_updated_at_in_subcollections(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)

        req = _make_request(event_id="event123", email="pilot@example.com")
        response = get_event_competitor_by_email(req)

        data = json.loads(response.response[0])
        for key in ("personalData", "healthData", "emergencyContacts", "vehicles", "membership"):
            for doc in data[key]:
                assert "createdAt" not in doc, f"{key} doc should not have createdAt"
                assert "updatedAt" not in doc, f"{key} doc should not have updatedAt"


class TestMissingParams:
    """Parámetros faltantes -> 400."""

    def test_missing_event_id(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        req = _make_request(email="pilot@example.com")
        response = get_event_competitor_by_email(req)
        assert response.status_code == 400

    def test_missing_email(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        req = _make_request(event_id="event123")
        response = get_event_competitor_by_email(req)
        assert response.status_code == 400

    def test_missing_both(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        req = _make_request()
        response = get_event_competitor_by_email(req)
        assert response.status_code == 400

    def test_empty_event_id(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        req = _make_request(email="pilot@example.com")
        req.args["eventId"] = "   "
        response = get_event_competitor_by_email(req)
        assert response.status_code == 400

    def test_empty_email(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        req = _make_request(event_id="event123")
        req.args["email"] = "   "
        response = get_event_competitor_by_email(req)
        assert response.status_code == 400


class TestInvalidEmail:
    """Email con formato inválido -> 400."""

    def test_invalid_email_format(
        self, mock_validate_request, mock_verify_bearer_token
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        with patch(f"{_MOD}.validate_email", return_value=False):
            req = _make_request(event_id="event123", email="not-an-email")
            response = get_event_competitor_by_email(req)
            assert response.status_code == 400


class TestAuth:
    """Token inválido -> 401."""

    def test_invalid_token(self, mock_validate_request):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        with patch(f"{_MOD}.verify_bearer_token", return_value=False):
            req = _make_request(event_id="ev1", email="pilot@example.com")
            response = get_event_competitor_by_email(req)
            assert response.status_code == 401


class TestNotFound:
    """Usuario o participante no encontrado -> 404."""

    def test_user_not_found_by_email(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        mock_firestore_helper.query_documents.return_value = []

        req = _make_request(event_id="event123", email="unknown@example.com")
        response = get_event_competitor_by_email(req)
        assert response.status_code == 404

    def test_user_exists_but_not_participant(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
        sample_user_doc,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        mock_firestore_helper.query_documents.return_value = [
            ("user123", sample_user_doc)
        ]
        mock_firestore_helper.get_document.return_value = None

        req = _make_request(event_id="event123", email="pilot@example.com")
        response = get_event_competitor_by_email(req)
        assert response.status_code == 404


class TestQueryWithData:
    """Consultas con data: verificar estructura completa."""

    def test_register_fields_inside_membership(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
        sample_user_doc,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        participant = {
            "competitionCategory": {
                "pilotNumber": "99",
                "registrationCategory": "Amateur",
            },
            "team": "Solo Rider",
        }
        mock_firestore_helper.query_documents.side_effect = [
            [("user99", sample_user_doc)],
            [], [], [], [],
            [("ev1", {"userId": "user99", "eventId": "ev1"})],
        ]
        mock_firestore_helper.get_document.return_value = participant

        req = _make_request(event_id="ev1", email="pilot@example.com")
        response = get_event_competitor_by_email(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        register = data["membership"][0]["register"]
        assert register["number"] == "99"
        assert register["category"] == "Amateur"
        assert register["team"] == "Solo Rider"

    def test_register_only_on_matching_membership(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = [
            [("user123", sample_user_doc)],
            [], [], [], [],
            [
                ("event123", {"userId": "user123", "eventId": "event123"}),
                ("otherEvent", {"userId": "user123", "eventId": "otherEvent"}),
            ],
        ]
        mock_firestore_helper.get_document.return_value = sample_participant_doc

        req = _make_request(event_id="event123", email="pilot@example.com")
        response = get_event_competitor_by_email(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert len(data["membership"]) == 2
        assert "register" in data["membership"][0]
        assert "register" not in data["membership"][1]

    def test_empty_subcollections_with_participant(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = [
            [("user123", sample_user_doc)],
            [], [], [], [],
            [("event123", {"userId": "user123", "eventId": "event123"})],
        ]
        mock_firestore_helper.get_document.return_value = sample_participant_doc

        req = _make_request(event_id="event123", email="pilot@example.com")
        response = get_event_competitor_by_email(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["personalData"] == []
        assert data["vehicles"] == []
        assert data["membership"][0]["register"]["number"] == "42"

    def test_subcollection_docs_include_id(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)

        req = _make_request(event_id="event123", email="pilot@example.com")
        response = get_event_competitor_by_email(req)

        data = json.loads(response.response[0])
        assert data["personalData"][0]["id"] == "pd1"
        assert data["healthData"][0]["id"] == "hd1"
        assert data["emergencyContacts"][0]["id"] == "ec1"
        assert data["vehicles"][0]["id"] == "v1"
        assert data["membership"][0]["id"] == "event123"


class TestExceptions:
    """Excepciones -> códigos apropiados."""

    def test_value_error_returns_400(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = ValueError("bad")

        req = _make_request(event_id="ev1", email="pilot@example.com")
        response = get_event_competitor_by_email(req)
        assert response.status_code == 400

    def test_runtime_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        mock_firestore_helper.query_documents.side_effect = RuntimeError("crash")

        req = _make_request(event_id="ev1", email="pilot@example.com")
        response = get_event_competitor_by_email(req)
        assert response.status_code == 500


class TestValidateRequestBlocks:
    """validate_request bloquea -> retorna su respuesta."""

    def test_validate_request_blocks(self):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        blocked = MagicMock()
        with patch(f"{_MOD}.validate_request", return_value=blocked):
            req = _make_request(event_id="ev1", email="pilot@example.com")
            response = get_event_competitor_by_email(req)
            assert response is blocked


class TestMultipleCalls:
    """Múltiples llamadas estables sin efectos colaterales."""

    def test_multiple_calls_stable(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        for _ in range(3):
            _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)
            req = _make_request(event_id="event123", email="pilot@example.com")
            response = get_event_competitor_by_email(req)
            assert response.status_code == 200
            data = json.loads(response.response[0])
            assert data["id"] == "user123"
            assert data["membership"][0]["register"]["number"] == "42"

    def test_found_then_not_found(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        mock_validate_email_ok,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_email import get_event_competitor_by_email

        _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)
        req1 = _make_request(event_id="event123", email="pilot@example.com")
        resp1 = get_event_competitor_by_email(req1)
        assert resp1.status_code == 200

        mock_firestore_helper.query_documents.side_effect = [[]]
        req2 = _make_request(event_id="event123", email="notfound@example.com")
        resp2 = get_event_competitor_by_email(req2)
        assert resp2.status_code == 404
