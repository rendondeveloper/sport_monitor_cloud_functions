import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


def _make_request(event_id="ev1", user_id=None):
    req = MagicMock()
    req.method = "GET"
    args = {}
    if event_id is not None:
        args["eventId"] = event_id
    if user_id is not None:
        args["userId"] = user_id
    req.args = args
    req.get_json = lambda silent=True: None
    return req


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_includes_routes_checkpoints_name_type(
    _mock_firestore_client, _mock_helper_cls, _mock_validate
):
    from events.events_detail_customer import event_detail

    # ---- Arrange: mocks ----
    db = MagicMock()
    _mock_firestore_client.return_value = db
    _mock_helper_cls.return_value = MagicMock()

    from models.firestore_collections import FirestoreCollections

    # event_content/{...}
    event_content_ref = MagicMock()
    event_content_doc = MagicMock()
    event_content_doc.to_dict.return_value = {
        "name": "Evento 1",
        "descriptionShort": "Desc short",
        "description": "Desc",
        "photoMain": "https://example.com/main.jpg",
        "startEvent": "2025-01-01T10:00:00Z",
        "endEvent": "2025-01-02T18:00:00Z",
        "address": "Some address",
        "historia": "Historia",
        "photoUrls": ["https://example.com/1.jpg"],
        "website": "https://example.com",
        # Campo extra para cubrir el branch "if key not in event_info"
        "foo": "bar",
    }
    event_content_ref.limit.return_value.get.return_value = [event_content_doc]

    # participants
    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = [MagicMock(), MagicMock()]

    # routes
    ts = MagicMock()
    ts.isoformat.return_value = "2026-03-25T00:00:00"

    route_doc = MagicMock()
    route_doc.id = "route1"
    route_doc.to_dict.return_value = {
        "name": "Ruta 4",
        "routeUrl": "https://example.com/track",
        "colorTrack": 123,
        "updatedAt": ts,
        "trackPoints": [1, 2, 3],
    }

    routes_ref = MagicMock()
    routes_query = MagicMock()
    routes_query.get.return_value = [route_doc]
    routes_ref.where.return_value = routes_query

    # checkpoints subcollection under route1
    cp_doc_1 = MagicMock()
    cp_doc_1.to_dict.return_value = {
        "checkpointTypeId": "type1",
        "coordinates": {"latitude": 19.0, "longitude": 18.0},
        "iconCustom": "icon1",
        "name": "Checkpoint A",
        "order": 1,
    }
    cp_doc_2 = MagicMock()
    cp_doc_2.to_dict.return_value = {
        "checkpointTypeId": "type2",
        "coordinates": {"latitude": 20.0, "longitude": 21.0},
        "iconCustom": "icon2",
        "name": "Checkpoint B",
        "order": 2,
    }
    checkpoint_docs = [cp_doc_1, cp_doc_2]

    route_doc_ref = MagicMock()
    route_doc_ref.collection.return_value.get.return_value = checkpoint_docs
    routes_ref.document.return_value = route_doc_ref

    # Build events/{eventId} doc ref
    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    # catalogs/default/checkpoint_types/{id}
    catalogs_col_ref = MagicMock()
    catalogs_default_ref = MagicMock()
    catalogs_col_ref.document.return_value = catalogs_default_ref

    checkpoint_types_col_ref = MagicMock()
    catalogs_default_ref.collection.return_value = checkpoint_types_col_ref

    snapshot_type_1 = MagicMock()
    snapshot_type_1.exists = True
    snapshot_type_1.to_dict.return_value = {"abbreviation": "AB", "name": "Type 1"}

    snapshot_type_2 = MagicMock()
    snapshot_type_2.exists = True
    snapshot_type_2.to_dict.return_value = {"abbreviation": None, "name": "Type 2"}

    doc_ref_type_1 = MagicMock()
    doc_ref_type_1.get.return_value = snapshot_type_1
    doc_ref_type_2 = MagicMock()
    doc_ref_type_2.get.return_value = snapshot_type_2

    def checkpoint_type_doc_side_effect(checkpoint_type_id):
        if checkpoint_type_id == "type1":
            return doc_ref_type_1
        return doc_ref_type_2

    checkpoint_types_col_ref.document.side_effect = checkpoint_type_doc_side_effect

    def db_collection_side_effect(col_name):
        if col_name == FirestoreCollections.EVENTS:
            return events_col_ref
        if col_name == FirestoreCollections.CATALOGS:
            return catalogs_col_ref
        return MagicMock()

    db.collection.side_effect = db_collection_side_effect

    # ---- Act ----
    req = _make_request(event_id="ev1")
    response = event_detail(req)

    # ---- Assert ----
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data["name"] == "Evento 1"
    assert data["descriptionShort"] == "Desc short"
    assert data["description"] == "Desc"
    assert data["photoMain"] == "https://example.com/main.jpg"
    assert data["startEvent"] == "2025-01-01T10:00:00Z"
    assert data["endEvent"] == "2025-01-02T18:00:00Z"
    assert data["address"] == "Some address"
    assert data["historia"] == "Historia"
    assert data["photoUrls"] == ["https://example.com/1.jpg"]
    assert data["website"] == "https://example.com"
    assert data["foo"] == "bar"

    assert "routes" in data
    assert len(data["routes"]) == 1
    route_out = data["routes"][0]

    assert "checkpoint" not in route_out
    assert "checkpoints" in route_out
    assert "trackPoints" not in route_out
    assert len(route_out["checkpoints"]) == 2

    cp_out_1 = route_out["checkpoints"][0]
    assert cp_out_1["checkpointTypeId"] == "type1"
    assert cp_out_1["nameType"] == "AB - Type 1"
    assert cp_out_1["coordinates"] == {"latitude": 19.0, "longitude": 18.0}
    assert cp_out_1["iconCustom"] == "icon1"
    assert cp_out_1["name"] == "Checkpoint A"
    assert cp_out_1["order"] == 1

    cp_out_2 = route_out["checkpoints"][1]
    assert cp_out_2["checkpointTypeId"] == "type2"
    assert cp_out_2["nameType"] == "Type 2"
    assert cp_out_2["coordinates"] == {"latitude": 20.0, "longitude": 21.0}
    assert cp_out_2["iconCustom"] == "icon2"
    assert cp_out_2["name"] == "Checkpoint B"
    assert cp_out_2["order"] == 2


def test_build_name_type_variants():
    from events.events_detail_customer import _build_name_type

    assert _build_name_type(None) == ""
    assert _build_name_type({}) == ""
    assert _build_name_type({"abbreviation": "  AB  ", "name": "Type 1"}) == "AB - Type 1"
    assert _build_name_type({"abbreviation": None, "name": "Type 2"}) == "Type 2"


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_missing_event_id_returns_400(
    _mock_firestore_client, _mock_helper_cls, _mock_validate
):
    from events.events_detail_customer import event_detail

    req = _make_request(event_id=None)
    response = event_detail(req)
    assert response.status_code == 400
    assert response.get_data(as_text=True) == ""


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_event_content_empty_returns_404(
    _mock_firestore_client, _mock_helper_cls, _mock_validate
):
    from events.events_detail_customer import event_detail

    db = MagicMock()
    _mock_firestore_client.return_value = db
    _mock_helper_cls.return_value = MagicMock()

    from models.firestore_collections import FirestoreCollections

    event_content_ref = MagicMock()
    event_content_ref.limit.return_value.get.return_value = []

    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = []

    routes_ref = MagicMock()

    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    db.collection.side_effect = lambda col_name: (
        events_col_ref
        if col_name == FirestoreCollections.EVENTS
        else MagicMock()
    )

    req = _make_request(event_id="ev1")
    response = event_detail(req)
    assert response.status_code == 404
    assert response.get_data(as_text=True) == ""


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_route_without_id_returns_empty_checkpoints(
    _mock_firestore_client, _mock_helper_cls, _mock_validate
):
    from events.events_detail_customer import event_detail

    db = MagicMock()
    _mock_firestore_client.return_value = db
    _mock_helper_cls.return_value = MagicMock()

    from models.firestore_collections import FirestoreCollections

    event_content_ref = MagicMock()
    event_content_doc = MagicMock()
    event_content_doc.to_dict.return_value = {"name": "Evento 1"}
    event_content_ref.limit.return_value.get.return_value = [event_content_doc]

    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = []

    ts = MagicMock()
    ts.isoformat.return_value = "2026-03-25T00:00:00"

    route_doc = MagicMock()
    route_doc.id = None
    route_doc.to_dict.return_value = {
        "name": "Ruta 4",
        "routeUrl": "url",
        "colorTrack": 1,
        "updatedAt": ts,
        "trackPoints": [],
    }

    routes_ref = MagicMock()
    routes_query = MagicMock()
    routes_query.get.return_value = [route_doc]
    routes_ref.where.return_value = routes_query

    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    db.collection.side_effect = lambda col_name: (
        events_col_ref
        if col_name == FirestoreCollections.EVENTS
        else MagicMock()
    )

    req = _make_request(event_id="ev1")
    response = event_detail(req)
    assert response.status_code == 200

    data = json.loads(response.get_data(as_text=True))
    assert len(data["routes"]) == 1
    assert data["routes"][0]["checkpoints"] == []


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_checkpoint_type_missing_uses_id_as_name_type(
    _mock_firestore_client, _mock_helper_cls, _mock_validate
):
    from events.events_detail_customer import event_detail

    db = MagicMock()
    _mock_firestore_client.return_value = db
    _mock_helper_cls.return_value = MagicMock()

    from models.firestore_collections import FirestoreCollections

    event_content_ref = MagicMock()
    event_content_doc = MagicMock()
    event_content_doc.to_dict.return_value = {"name": "Evento 1"}
    event_content_ref.limit.return_value.get.return_value = [event_content_doc]

    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = []

    ts = MagicMock()
    ts.isoformat.return_value = "2026-03-25T00:00:00"

    route_doc = MagicMock()
    route_doc.id = "route1"
    route_doc.to_dict.return_value = {
        "name": "Ruta 4",
        "routeUrl": None,
        "colorTrack": None,
        "updatedAt": ts,
        "trackPoints": [],
    }

    routes_ref = MagicMock()
    routes_query = MagicMock()
    routes_query.get.return_value = [route_doc]
    routes_ref.where.return_value = routes_query

    cp_doc = MagicMock()
    cp_doc.to_dict.return_value = {
        "checkpointTypeId": "missing_type",
        "coordinates": {"latitude": 19.0, "longitude": 18.0},
        "iconCustom": "icon1",
        "name": "Checkpoint A",
        "order": 1,
    }

    route_doc_ref = MagicMock()
    route_doc_ref.collection.return_value.get.return_value = [cp_doc]
    routes_ref.document.return_value = route_doc_ref

    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    catalogs_col_ref = MagicMock()
    catalogs_default_ref = MagicMock()
    catalogs_col_ref.document.return_value = catalogs_default_ref

    checkpoint_types_col_ref = MagicMock()
    catalogs_default_ref.collection.return_value = checkpoint_types_col_ref

    snapshot_missing = MagicMock()
    snapshot_missing.exists = False
    snapshot_missing.to_dict.return_value = {}

    doc_ref_missing = MagicMock()
    doc_ref_missing.get.return_value = snapshot_missing
    checkpoint_types_col_ref.document.return_value = doc_ref_missing

    def db_collection_side_effect(col_name):
        if col_name == FirestoreCollections.EVENTS:
            return events_col_ref
        if col_name == FirestoreCollections.CATALOGS:
            return catalogs_col_ref
        return MagicMock()

    db.collection.side_effect = db_collection_side_effect

    req = _make_request(event_id="ev1")
    response = event_detail(req)
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    cp_out = data["routes"][0]["checkpoints"][0]
    assert cp_out["checkpointTypeId"] == "missing_type"
    assert cp_out["nameType"] == "missing_type"


@patch("events.events_detail_customer.validate_request", return_value=None)
def test_event_detail_returns_500_on_unexpected_exception(_mock_validate):
    from events.events_detail_customer import event_detail

    req = _make_request(event_id="ev1")
    with patch("events.events_detail_customer.firestore.client", side_effect=RuntimeError("db down")):
        response = event_detail(req)
        assert response.status_code == 500
        assert response.get_data(as_text=True) == ""


@patch("events.events_detail_customer.validate_request")
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_validate_request_early_return_passthrough(
    _mock_firestore_client, _mock_helper_cls, _mock_validate_request
):
    from events.events_detail_customer import event_detail

    early = MagicMock()
    early.status_code = 204
    early.get_data.return_value = b""
    _mock_validate_request.return_value = early

    req = _make_request(event_id="ev1")
    response = event_detail(req)
    assert response.status_code == 204


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.firestore.client")
@patch("events.events_detail_customer.FirestoreHelper")
def test_event_detail_user_id_user_not_found_sets_is_enrolled_none(
    _mock_helper_cls, _mock_firestore_client, _mock_validate
):
    from events.events_detail_customer import event_detail

    db = MagicMock()
    _mock_firestore_client.return_value = db

    helper = MagicMock()
    helper.get_document.return_value = None  # user not found
    _mock_helper_cls.return_value = helper

    from models.firestore_collections import FirestoreCollections

    event_content_ref = MagicMock()
    event_content_doc = MagicMock()
    event_content_doc.to_dict.return_value = {"name": "Evento 1"}
    event_content_ref.limit.return_value.get.return_value = [event_content_doc]

    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = []

    routes_ref = MagicMock()
    routes_ref.where.return_value.get.return_value = []

    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    db.collection.side_effect = lambda col_name: events_col_ref if col_name == FirestoreCollections.EVENTS else MagicMock()

    req = _make_request(event_id="ev1", user_id="u1")
    response = event_detail(req)
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data["isEnrolled"] is None


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.firestore.client")
@patch("events.events_detail_customer.FirestoreHelper")
def test_event_detail_user_id_enrolled_true(
    _mock_helper_cls, _mock_firestore_client, _mock_validate
):
    from events.events_detail_customer import event_detail

    db = MagicMock()
    _mock_firestore_client.return_value = db

    helper = MagicMock()
    helper.get_document.return_value = {"id": "u1"}  # user exists
    _mock_helper_cls.return_value = helper

    from models.firestore_collections import FirestoreCollections

    event_content_ref = MagicMock()
    event_content_doc = MagicMock()
    event_content_doc.to_dict.return_value = {"name": "Evento 1"}
    event_content_ref.limit.return_value.get.return_value = [event_content_doc]

    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = []

    routes_ref = MagicMock()
    routes_ref.where.return_value.get.return_value = []

    # participant_ref used only when user_id exists
    participant_doc_ref = MagicMock()
    participant_doc_ref.get.return_value.exists = True

    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    def events_document_side_effect(event_id):
        # events/{eventId}/participants/{userId}
        doc_ref = MagicMock()
        doc_ref.collection.side_effect = lambda col_name: {
            FirestoreCollections.EVENT_CONTENT: event_content_ref,
            FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
            FirestoreCollections.EVENT_ROUTES: routes_ref,
        }.get(col_name, MagicMock())
        return doc_ref

    # Root events collection must return proper document refs and also support
    # the participants/{userId} lookup chain.
    events_col_ref.document.side_effect = lambda event_id: event_ref

    # Fix: the chain at line 195 uses:
    # db.collection(EVENTS).document(event_id).collection(PARTICIPANTS).document(user_id).get().exists
    participants_subcollection_ref = MagicMock()
    participants_subcollection_ref.document.return_value.get.return_value.exists = True
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_subcollection_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    db.collection.side_effect = lambda col_name: events_col_ref if col_name == FirestoreCollections.EVENTS else MagicMock()

    req = _make_request(event_id="ev1", user_id="u1")
    response = event_detail(req)
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data["isEnrolled"] is True


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.firestore.client", side_effect=ValueError("bad"))
def test_event_detail_value_error_returns_400(_mock_firestore_client, _mock_validate_request):
    from events.events_detail_customer import event_detail

    req = _make_request(event_id="ev1")
    response = event_detail(req)
    assert response.status_code == 400
    assert response.get_data(as_text=True) == ""


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_event_content_doc_to_dict_none_returns_404(
    _mock_firestore_client, _mock_helper_cls, _mock_validate
):
    from events.events_detail_customer import event_detail

    db = MagicMock()
    _mock_firestore_client.return_value = db
    _mock_helper_cls.return_value = MagicMock()

    from models.firestore_collections import FirestoreCollections

    event_content_ref = MagicMock()
    event_content_doc = MagicMock()
    event_content_doc.to_dict.return_value = None
    event_content_ref.limit.return_value.get.return_value = [event_content_doc]

    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = []

    routes_ref = MagicMock()

    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    db.collection.side_effect = lambda col_name: (
        events_col_ref if col_name == FirestoreCollections.EVENTS else MagicMock()
    )

    req = _make_request(event_id="ev1")
    response = event_detail(req)
    assert response.status_code == 404
    assert response.get_data(as_text=True) == ""


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_checkpoint_type_id_empty_returns_empty_name_type(
    _mock_firestore_client, _mock_helper_cls, _mock_validate
):
    from events.events_detail_customer import event_detail

    db = MagicMock()
    _mock_firestore_client.return_value = db
    _mock_helper_cls.return_value = MagicMock()

    from models.firestore_collections import FirestoreCollections

    event_content_ref = MagicMock()
    event_content_doc = MagicMock()
    event_content_doc.to_dict.return_value = {"name": "Evento 1"}
    event_content_ref.limit.return_value.get.return_value = [event_content_doc]

    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = []

    ts = MagicMock()
    ts.isoformat.return_value = "2026-03-25T00:00:00"

    route_doc = MagicMock()
    route_doc.id = "route1"
    route_doc.to_dict.return_value = {
        "name": "Ruta 4",
        "routeUrl": None,
        "colorTrack": None,
        "updatedAt": ts,
        "trackPoints": [],
    }

    routes_ref = MagicMock()
    routes_query = MagicMock()
    routes_query.get.return_value = [route_doc]
    routes_ref.where.return_value = routes_query

    cp_doc = MagicMock()
    cp_doc.to_dict.return_value = {
        "coordinates": {"latitude": 19.0, "longitude": 18.0},
        "iconCustom": "icon1",
        "name": "Checkpoint A",
        "order": 1,
        # sin checkpointTypeId
    }

    route_doc_ref = MagicMock()
    route_doc_ref.collection.return_value.get.return_value = [cp_doc]
    routes_ref.document.return_value = route_doc_ref

    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    catalogs_col_ref = MagicMock()
    catalogs_default_ref = MagicMock()
    catalogs_col_ref.document.return_value = catalogs_default_ref
    checkpoint_types_col_ref = MagicMock()
    catalogs_default_ref.collection.return_value = checkpoint_types_col_ref

    # Si checkpointTypeId es vacío, no debería consultar; igual dejamos mocks.
    db.collection.side_effect = lambda col_name: (
        events_col_ref if col_name == FirestoreCollections.EVENTS else catalogs_col_ref
    )

    req = _make_request(event_id="ev1")
    response = event_detail(req)
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    cp_out = data["routes"][0]["checkpoints"][0]
    assert cp_out["checkpointTypeId"] is None
    assert cp_out["nameType"] == ""


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_checkpoint_type_cache_hit(
    _mock_firestore_client, _mock_helper_cls, _mock_validate
):
    from events.events_detail_customer import event_detail

    db = MagicMock()
    _mock_firestore_client.return_value = db
    _mock_helper_cls.return_value = MagicMock()

    from models.firestore_collections import FirestoreCollections

    event_content_ref = MagicMock()
    event_content_doc = MagicMock()
    event_content_doc.to_dict.return_value = {"name": "Evento 1"}
    event_content_ref.limit.return_value.get.return_value = [event_content_doc]

    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = []

    ts = MagicMock()
    ts.isoformat.return_value = "2026-03-25T00:00:00"

    route_doc = MagicMock()
    route_doc.id = "route1"
    route_doc.to_dict.return_value = {
        "name": "Ruta 4",
        "routeUrl": None,
        "colorTrack": None,
        "updatedAt": ts,
        "trackPoints": [],
    }

    routes_ref = MagicMock()
    routes_query = MagicMock()
    routes_query.get.return_value = [route_doc]
    routes_ref.where.return_value = routes_query

    cp_doc_1 = MagicMock()
    cp_doc_1.to_dict.return_value = {
        "checkpointTypeId": "type1",
        "coordinates": {"latitude": 19.0, "longitude": 18.0},
        "iconCustom": "icon1",
        "name": "Checkpoint A",
        "order": 1,
    }
    cp_doc_2 = MagicMock()
    cp_doc_2.to_dict.return_value = {
        "checkpointTypeId": "type1",
        "coordinates": {"latitude": 20.0, "longitude": 21.0},
        "iconCustom": "icon2",
        "name": "Checkpoint B",
        "order": 2,
    }
    route_doc_ref = MagicMock()
    route_doc_ref.collection.return_value.get.return_value = [cp_doc_1, cp_doc_2]
    routes_ref.document.return_value = route_doc_ref

    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    catalogs_col_ref = MagicMock()
    catalogs_default_ref = MagicMock()
    catalogs_col_ref.document.return_value = catalogs_default_ref
    checkpoint_types_col_ref = MagicMock()
    catalogs_default_ref.collection.return_value = checkpoint_types_col_ref

    snapshot_type_1 = MagicMock()
    snapshot_type_1.exists = True
    snapshot_type_1.to_dict.return_value = {"abbreviation": "AB", "name": "Type 1"}

    doc_ref_type_1 = MagicMock()
    doc_ref_type_1.get.return_value = snapshot_type_1

    checkpoint_types_col_ref.document.return_value = doc_ref_type_1

    db.collection.side_effect = lambda col_name: (
        events_col_ref if col_name == FirestoreCollections.EVENTS else catalogs_col_ref
    )

    req = _make_request(event_id="ev1")
    response = event_detail(req)
    assert response.status_code == 200

    # Si cache funciona: solo debería consultar 1 vez el doc del checkpoint type.
    assert checkpoint_types_col_ref.document.call_count == 1


@patch("events.events_detail_customer.validate_request", return_value=None)
@patch("events.events_detail_customer.FirestoreHelper")
@patch("events.events_detail_customer.firestore.client")
def test_event_detail_multiple_calls_stable(
    _mock_firestore_client, _mock_helper_cls, _mock_validate
):
    from events.events_detail_customer import event_detail

    db = MagicMock()
    _mock_firestore_client.return_value = db
    _mock_helper_cls.return_value = MagicMock()

    from models.firestore_collections import FirestoreCollections

    event_content_ref = MagicMock()
    event_content_doc = MagicMock()
    event_content_doc.to_dict.return_value = {"name": "Evento 1"}
    event_content_ref.limit.return_value.get.return_value = [event_content_doc]

    participants_ref = MagicMock()
    participants_ref.select.return_value.get.return_value = []

    ts = MagicMock()
    ts.isoformat.return_value = "2026-03-25T00:00:00"

    route_doc = MagicMock()
    route_doc.id = "route1"
    route_doc.to_dict.return_value = {
        "name": "Ruta 4",
        "routeUrl": None,
        "colorTrack": None,
        "updatedAt": ts,
        "trackPoints": [],
    }

    routes_ref = MagicMock()
    routes_query = MagicMock()
    routes_query.get.return_value = [route_doc]
    routes_ref.where.return_value = routes_query

    cp_doc = MagicMock()
    cp_doc.to_dict.return_value = {
        "checkpointTypeId": "type1",
        "coordinates": {"latitude": 19.0, "longitude": 18.0},
        "iconCustom": "icon1",
        "name": "Checkpoint A",
        "order": 1,
    }
    checkpoint_docs = [cp_doc]

    route_doc_ref = MagicMock()
    route_doc_ref.collection.return_value.get.return_value = checkpoint_docs
    routes_ref.document.return_value = route_doc_ref

    event_ref = MagicMock()
    event_ref.collection.side_effect = lambda col_name: {
        FirestoreCollections.EVENT_CONTENT: event_content_ref,
        FirestoreCollections.EVENT_PARTICIPANTS: participants_ref,
        FirestoreCollections.EVENT_ROUTES: routes_ref,
    }.get(col_name, MagicMock())

    events_col_ref = MagicMock()
    events_col_ref.document.return_value = event_ref

    catalogs_col_ref = MagicMock()
    catalogs_default_ref = MagicMock()
    catalogs_col_ref.document.return_value = catalogs_default_ref

    checkpoint_types_col_ref = MagicMock()
    catalogs_default_ref.collection.return_value = checkpoint_types_col_ref

    snapshot_type_1 = MagicMock()
    snapshot_type_1.exists = True
    snapshot_type_1.to_dict.return_value = {"abbreviation": "AB", "name": "Type 1"}

    doc_ref_type_1 = MagicMock()
    doc_ref_type_1.get.return_value = snapshot_type_1

    checkpoint_types_col_ref.document.return_value = doc_ref_type_1

    def db_collection_side_effect(col_name):
        if col_name == FirestoreCollections.EVENTS:
            return events_col_ref
        if col_name == FirestoreCollections.CATALOGS:
            return catalogs_col_ref
        return MagicMock()

    db.collection.side_effect = db_collection_side_effect

    req = _make_request(event_id="ev1")
    r1 = event_detail(req)
    r2 = event_detail(req)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.get_data(as_text=True) == r2.get_data(as_text=True)

