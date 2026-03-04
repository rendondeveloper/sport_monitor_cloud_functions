"""
Tests para get_event_competitor_by_id Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path
2. Parámetros faltantes
3. Consultas con data (mock Firestore)
4. Múltiples llamadas al mismo API
5. Token inválido -> 401
6. Método no permitido -> 405
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================

_MOD = "competitors.get_event_competitor_by_id"


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


def _make_request(event_id="", competitor_id="", method="GET"):
    req = MagicMock()
    req.method = method
    req.args = {}
    req.path = ""
    req.headers = {"Authorization": "Bearer test_token"}

    if event_id:
        req.args["eventId"] = event_id
    if competitor_id:
        req.args["competitorId"] = competitor_id

    return req


def _setup_full_response(mock_helper, sample_user_doc, sample_participant_doc):
    """Configura mocks para una respuesta exitosa completa.

    get_document se llama 2 veces: participant (1st) y user (2nd).
    query_documents se llama 5 veces: personalData, healthData, emergencyContacts, vehicles, membership.
    """
    mock_helper.get_document.side_effect = [
        sample_participant_doc,
        sample_user_doc,
    ]
    mock_helper.query_documents.side_effect = [
        [("pd1", {"fullName": "Juan", "phone": "+521234567890", "createdAt": "t", "updatedAt": "t"})],
        [("hd1", {"bloodType": "O+", "createdAt": "t", "updatedAt": "t"})],
        [("ec1", {"fullName": "María", "phone": "+529876543210", "relationship": "Spouse", "createdAt": "t", "updatedAt": "t"})],
        [("v1", {"branch": "Honda", "year": 2024, "model": "CRF450R", "color": "Red", "createdAt": "t", "updatedAt": "t"})],
        [("event123", {"userId": "user123", "eventId": "event123", "createdAt": "t", "updatedAt": "t"})],
    ]


# ============================================================================
# TESTS
# ============================================================================


class TestHappyPath:
    """Happy path: competidor encontrado como participante del evento."""

    def test_success_with_all_data(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)

        req = _make_request(event_id="event123", competitor_id="user123")
        response = get_event_competitor_by_id(req)

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

    def test_no_created_at_updated_at_in_subcollections(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)

        req = _make_request(event_id="event123", competitor_id="user123")
        response = get_event_competitor_by_id(req)

        data = json.loads(response.response[0])
        for key in ("personalData", "healthData", "emergencyContacts", "vehicles", "membership"):
            for doc in data[key]:
                assert "createdAt" not in doc, f"{key} doc should not have createdAt"
                assert "updatedAt" not in doc, f"{key} doc should not have updatedAt"

    def test_content_type_is_json(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)

        req = _make_request(event_id="event123", competitor_id="user123")
        response = get_event_competitor_by_id(req)

        assert "application/json" in response.content_type


class TestMissingParams:
    """Parámetros faltantes -> 400."""

    def test_missing_event_id(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        req = _make_request(competitor_id="user123")
        response = get_event_competitor_by_id(req)
        assert response.status_code == 400

    def test_missing_competitor_id(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        req = _make_request(event_id="event123")
        response = get_event_competitor_by_id(req)
        assert response.status_code == 400

    def test_missing_both(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        req = _make_request()
        response = get_event_competitor_by_id(req)
        assert response.status_code == 400

    def test_empty_event_id(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        req = _make_request(competitor_id="user123")
        req.args["eventId"] = "   "
        response = get_event_competitor_by_id(req)
        assert response.status_code == 400

    def test_empty_competitor_id(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        req = _make_request(event_id="event123")
        req.args["competitorId"] = "   "
        response = get_event_competitor_by_id(req)
        assert response.status_code == 400


class TestAuth:
    """Token inválido -> 401."""

    def test_invalid_token(self, mock_validate_request):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        with patch(f"{_MOD}.verify_bearer_token", return_value=False):
            req = _make_request(event_id="ev1", competitor_id="user123")
            response = get_event_competitor_by_id(req)
            assert response.status_code == 401


class TestNotFound:
    """Competidor o usuario no encontrado -> 404."""

    def test_not_participant(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        mock_firestore_helper.get_document.return_value = None

        req = _make_request(event_id="event123", competitor_id="unknown")
        response = get_event_competitor_by_id(req)
        assert response.status_code == 404

    def test_participant_exists_but_user_not_found(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        mock_firestore_helper.get_document.side_effect = [sample_participant_doc, None]

        req = _make_request(event_id="event123", competitor_id="user123")
        response = get_event_competitor_by_id(req)
        assert response.status_code == 404


class TestQueryWithData:
    """Consultas con data: verificar estructura completa."""

    def test_register_fields_inside_membership(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_user_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        participant = {
            "competitionCategory": {
                "pilotNumber": "99",
                "registrationCategory": "Amateur",
            },
            "team": "Solo Rider",
        }
        mock_firestore_helper.get_document.side_effect = [participant, sample_user_doc]
        mock_firestore_helper.query_documents.side_effect = [
            [], [], [], [],
            [("ev1", {"userId": "user99", "eventId": "ev1"})],
        ]

        req = _make_request(event_id="ev1", competitor_id="user99")
        response = get_event_competitor_by_id(req)

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
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        mock_firestore_helper.get_document.side_effect = [sample_participant_doc, sample_user_doc]
        mock_firestore_helper.query_documents.side_effect = [
            [], [], [], [],
            [
                ("event123", {"userId": "user123", "eventId": "event123"}),
                ("otherEvent", {"userId": "user123", "eventId": "otherEvent"}),
            ],
        ]

        req = _make_request(event_id="event123", competitor_id="user123")
        response = get_event_competitor_by_id(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert len(data["membership"]) == 2
        assert "register" in data["membership"][0]
        assert "register" not in data["membership"][1]

    def test_subcollection_docs_include_id(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)

        req = _make_request(event_id="event123", competitor_id="user123")
        response = get_event_competitor_by_id(req)

        data = json.loads(response.response[0])
        assert data["personalData"][0]["id"] == "pd1"
        assert data["healthData"][0]["id"] == "hd1"
        assert data["emergencyContacts"][0]["id"] == "ec1"
        assert data["vehicles"][0]["id"] == "v1"
        assert data["membership"][0]["id"] == "event123"

    def test_empty_subcollections_with_participant(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        mock_firestore_helper.get_document.side_effect = [sample_participant_doc, sample_user_doc]
        mock_firestore_helper.query_documents.side_effect = [
            [], [], [], [],
            [("event123", {"userId": "user123", "eventId": "event123"})],
        ]

        req = _make_request(event_id="event123", competitor_id="user123")
        response = get_event_competitor_by_id(req)

        assert response.status_code == 200
        data = json.loads(response.response[0])
        assert data["personalData"] == []
        assert data["vehicles"] == []
        assert data["membership"][0]["register"]["number"] == "42"


class TestExceptions:
    """Excepciones -> 500."""

    def test_runtime_error_returns_500(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        mock_firestore_helper.get_document.side_effect = RuntimeError("crash")

        req = _make_request(event_id="ev1", competitor_id="user123")
        response = get_event_competitor_by_id(req)
        assert response.status_code == 500


class TestValidateRequestBlocks:
    """validate_request bloquea -> retorna su respuesta."""

    def test_validate_request_blocks(self):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        blocked = MagicMock()
        with patch(f"{_MOD}.validate_request", return_value=blocked):
            req = _make_request(event_id="ev1", competitor_id="user123")
            response = get_event_competitor_by_id(req)
            assert response is blocked


class TestMultipleCalls:
    """Múltiples llamadas estables sin efectos colaterales."""

    def test_multiple_calls_stable(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        for _ in range(3):
            _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)
            req = _make_request(event_id="event123", competitor_id="user123")
            response = get_event_competitor_by_id(req)
            assert response.status_code == 200
            data = json.loads(response.response[0])
            assert data["id"] == "user123"
            assert data["membership"][0]["register"]["number"] == "42"

    def test_found_then_not_found(
        self,
        mock_validate_request,
        mock_verify_bearer_token,
        mock_firestore_helper,
        sample_user_doc,
        sample_participant_doc,
    ):
        from competitors.get_event_competitor_by_id import get_event_competitor_by_id

        _setup_full_response(mock_firestore_helper, sample_user_doc, sample_participant_doc)
        req1 = _make_request(event_id="event123", competitor_id="user123")
        resp1 = get_event_competitor_by_id(req1)
        assert resp1.status_code == 200

        mock_firestore_helper.get_document.side_effect = [None]
        req2 = _make_request(event_id="event123", competitor_id="unknown")
        resp2 = get_event_competitor_by_id(req2)
        assert resp2.status_code == 404
