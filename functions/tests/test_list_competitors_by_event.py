"""
Tests para list_competitors_by_event Cloud Function.

Casos obligatorios según cloud_functions_rules.mdc:
1. Happy path - lista paginada con category name resuelto
2. Parámetros faltantes -> 400
3. Token inválido -> 401
4. Método no permitido -> 405
5. Paginación (limit, cursor)
6. Resolución de nombre de categoría desde event_categories
7. Múltiples llamadas estables
"""

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FIXTURES
# ============================================================================

_MOD = "competitors.list_competitors_by_event"


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


def _make_request(event_id="", limit=None, cursor=None, method="GET"):
    req = MagicMock()
    req.method = method
    req.args = {}
    req.path = ""
    req.headers = {"Authorization": "Bearer test_token"}
    if event_id:
        req.args["eventId"] = event_id
    if limit is not None:
        req.args["limit"] = str(limit)
    if cursor:
        req.args["cursor"] = cursor
    return req


def _make_participant(pilot_number="1", registration_category="cat-id-1", team="Team A"):
    return {
        "competitionCategory": {
            "pilotNumber": pilot_number,
            "registrationCategory": registration_category,
        },
        "team": team,
        "registrationDate": "2026-01-01T00:00:00",
    }


def _setup_helper(mock_helper, participants, categories=None, names=None):
    """
    Configura side_effect de query_documents:
    1ª llamada: event_categories (category_map)
    2ª llamada: participants
    get_document + list_document_ids + get_document x N para los nombres
    """
    # category map call
    cat_docs = categories or []
    # participants call
    participant_docs = participants

    mock_helper.query_documents.side_effect = [cat_docs, participant_docs]

    # name resolution: list_document_ids + get_document por participante
    names = names or ["" for _ in participants]
    ids_side = [["pd1"] if name else [] for name in names]
    docs_side = [{"fullName": name} if name else None for name in names]

    mock_helper.list_document_ids.side_effect = ids_side
    mock_helper.get_document.side_effect = [d for d in docs_side if d is not None]


# ============================================================================
# TESTS
# ============================================================================


class TestHappyPath:
    """Happy path: lista paginada con datos correctos."""

    def test_returns_200_with_list(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        from competitors.list_competitors_by_event import list_competitors_by_event

        cat_docs = [("cat-id-1", {"name": "Pro"})]
        participants = [("user1", _make_participant("42", "cat-id-1", "Team A"))]
        mock_firestore_helper.query_documents.side_effect = [cat_docs, participants]
        mock_firestore_helper.list_document_ids.return_value = ["pd1"]
        mock_firestore_helper.get_document.return_value = {"fullName": "Juan Pérez"}

        req = _make_request(event_id="ev1")
        response = list_competitors_by_event(req)

        assert response.status_code == 200
        body = json.loads(response.response[0])
        assert "result" in body
        assert "pagination" in body
        data = body["result"]
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "user1"
        assert data[0]["name"] == "Juan Pérez"
        assert data[0]["category"] == "Pro"
        assert data[0]["number"] == "42"
        assert data[0]["team"] == "Team A"
        pag = body["pagination"]
        assert "hasMore" in pag
        assert "count" in pag
        assert "limit" in pag

    def test_category_id_resolved_to_name(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        """registrationCategory (ID) se resuelve al nombre de la categoría."""
        from competitors.list_competitors_by_event import list_competitors_by_event

        cat_docs = [
            ("cat-pro", {"name": "Profesional"}),
            ("cat-am", {"name": "Amateur"}),
        ]
        participants = [
            ("u1", _make_participant("1", "cat-pro", "A")),
            ("u2", _make_participant("2", "cat-am", "B")),
        ]
        mock_firestore_helper.query_documents.side_effect = [cat_docs, participants]
        mock_firestore_helper.list_document_ids.return_value = []

        req = _make_request(event_id="ev1")
        response = list_competitors_by_event(req)

        body = json.loads(response.response[0])
        data = body["result"]
        assert data[0]["category"] == "Profesional"
        assert data[1]["category"] == "Amateur"

    def test_category_fallback_to_raw_if_not_in_map(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        """Si el ID no está en el mapa, devuelve el valor raw."""
        from competitors.list_competitors_by_event import list_competitors_by_event

        cat_docs = []  # no categories loaded
        participants = [("u1", _make_participant("1", "some-unknown-id", "T"))]
        mock_firestore_helper.query_documents.side_effect = [cat_docs, participants]
        mock_firestore_helper.list_document_ids.return_value = []

        req = _make_request(event_id="ev1")
        response = list_competitors_by_event(req)

        body = json.loads(response.response[0])
        data = body["result"]
        assert data[0]["category"] == "some-unknown-id"

    def test_content_type_is_json(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        from competitors.list_competitors_by_event import list_competitors_by_event

        mock_firestore_helper.query_documents.side_effect = [[], []]
        req = _make_request(event_id="ev1")
        response = list_competitors_by_event(req)

        assert "application/json" in response.content_type

    def test_empty_participants_returns_empty_list(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        from competitors.list_competitors_by_event import list_competitors_by_event

        mock_firestore_helper.query_documents.side_effect = [[], []]
        req = _make_request(event_id="ev1")
        response = list_competitors_by_event(req)

        body = json.loads(response.response[0])
        assert body["result"] == []
        assert body["pagination"]["count"] == 0


class TestPagination:
    """Paginación: limit y cursor."""

    def test_default_limit_is_20(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        """Sin limit, solicita 21 docs (limit+1) para detectar hasMore."""
        from competitors.list_competitors_by_event import list_competitors_by_event

        mock_firestore_helper.query_documents.side_effect = [[], []]
        req = _make_request(event_id="ev1")
        list_competitors_by_event(req)

        calls = mock_firestore_helper.query_documents.call_args_list
        # Segunda llamada es la de participantes — verificar limit=21
        participants_call = calls[1]
        assert participants_call.kwargs.get("limit") == 21

    def test_custom_limit_is_respected(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        from competitors.list_competitors_by_event import list_competitors_by_event

        mock_firestore_helper.query_documents.side_effect = [[], []]
        req = _make_request(event_id="ev1", limit=5)
        list_competitors_by_event(req)

        calls = mock_firestore_helper.query_documents.call_args_list
        participants_call = calls[1]
        assert participants_call.kwargs.get("limit") == 6  # limit+1

    def test_limit_capped_at_100(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        from competitors.list_competitors_by_event import list_competitors_by_event

        mock_firestore_helper.query_documents.side_effect = [[], []]
        req = _make_request(event_id="ev1", limit=999)
        list_competitors_by_event(req)

        calls = mock_firestore_helper.query_documents.call_args_list
        participants_call = calls[1]
        assert participants_call.kwargs.get("limit") == 101  # max 100 + 1

    def test_cursor_passed_to_query(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        from competitors.list_competitors_by_event import list_competitors_by_event

        mock_firestore_helper.query_documents.side_effect = [[], []]
        req = _make_request(event_id="ev1", cursor="lastDocId123")
        list_competitors_by_event(req)

        calls = mock_firestore_helper.query_documents.call_args_list
        participants_call = calls[1]
        assert participants_call.kwargs.get("start_after_doc_id") == "lastDocId123"

    def test_result_truncated_to_limit(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        """Cuando llegan limit+1 docs, la respuesta solo tiene limit."""
        from competitors.list_competitors_by_event import list_competitors_by_event

        participants = [
            (f"u{i}", _make_participant(str(i), "", ""))
            for i in range(6)  # limit+1 when limit=5
        ]
        mock_firestore_helper.query_documents.side_effect = [[], participants]
        mock_firestore_helper.list_document_ids.return_value = []

        req = _make_request(event_id="ev1", limit=5)
        response = list_competitors_by_event(req)

        body = json.loads(response.response[0])
        data = body["result"]
        assert len(data) == 5
        assert body["pagination"]["hasMore"] is True
        assert body["pagination"]["limit"] == 5


class TestMissingParams:
    """Parámetros faltantes -> 400."""

    def test_missing_event_id(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.list_competitors_by_event import list_competitors_by_event

        req = _make_request()
        response = list_competitors_by_event(req)
        assert response.status_code == 400

    def test_empty_event_id(self, mock_validate_request, mock_verify_bearer_token):
        from competitors.list_competitors_by_event import list_competitors_by_event

        req = _make_request()
        req.args["eventId"] = "   "
        response = list_competitors_by_event(req)
        assert response.status_code == 400


class TestAuth:
    """Token inválido -> 401."""

    def test_invalid_token(self, mock_validate_request):
        from competitors.list_competitors_by_event import list_competitors_by_event

        with patch(f"{_MOD}.verify_bearer_token", return_value=False):
            req = _make_request(event_id="ev1")
            response = list_competitors_by_event(req)
            assert response.status_code == 401


class TestValidateRequestBlocks:
    """validate_request bloquea -> retorna su respuesta."""

    def test_validate_request_blocks(self):
        from competitors.list_competitors_by_event import list_competitors_by_event

        blocked = MagicMock()
        with patch(f"{_MOD}.validate_request", return_value=blocked):
            req = _make_request(event_id="ev1")
            response = list_competitors_by_event(req)
            assert response is blocked


class TestExceptions:
    """Excepciones -> 500."""

    def test_runtime_error_returns_500(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        from competitors.list_competitors_by_event import list_competitors_by_event

        mock_firestore_helper.query_documents.side_effect = RuntimeError("crash")

        req = _make_request(event_id="ev1")
        response = list_competitors_by_event(req)
        assert response.status_code == 500


class TestMultipleCalls:
    """Múltiples llamadas estables."""

    def test_multiple_calls_stable(
        self, mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
    ):
        from competitors.list_competitors_by_event import list_competitors_by_event

        for _ in range(3):
            cat_docs = [("cat-1", {"name": "Pro"})]
            participants = [("u1", _make_participant("1", "cat-1", "T"))]
            mock_firestore_helper.query_documents.side_effect = [cat_docs, participants]
            mock_firestore_helper.list_document_ids.return_value = []

            req = _make_request(event_id="ev1")
            response = list_competitors_by_event(req)
            assert response.status_code == 200
            body = json.loads(response.response[0])
            assert body["result"][0]["category"] == "Pro"
