import json
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

from models.firestore_collections import FirestoreCollections


class _FakeDoc:
    def __init__(self, exists: bool, data: dict):
        self.exists = exists
        self._data = data

    def to_dict(self):
        return dict(self._data)


def test_get_registration_prefers_competition_category_nested():
    from competitors.competitor_route import (
        _get_registration_category_and_pilot_number,
    )

    reg, pilot = _get_registration_category_and_pilot_number(
        {
            "pilotNumber": "root-ignored-when-nested-key-exists",
            "registrationCategory": "root-reg-ignored",
            "competitionCategory": {
                "registrationCategory": "skWQ3ZPgLjMGsKOcv28J",
                "pilotNumber": "",
            },
        }
    )
    assert reg == "skWQ3ZPgLjMGsKOcv28J"
    assert pilot == ""

    reg2, pilot2 = _get_registration_category_and_pilot_number(
        {
            "pilotNumber": "99",
            "competitionCategory": {"registrationCategory": "catX"},
        }
    )
    assert reg2 == "catX"
    assert pilot2 == "99"


def _make_req(user_id="uid1", auth_header="Bearer valid"):
    req = MagicMock()
    req.method = "GET"
    req.path = ""
    req.args = {"userId": user_id}
    req.headers = {"Authorization": auth_header}
    req.get_json = lambda silent=True: None
    return req


def _build_firestore_mock(
    *,
    membership_event_ids,
    events_meta,
    participant_by_event,
    category_ids_by_event,
    visible_routes_by_event,
    checkpoints_by_route=None,
    category_display_names=None,
):
    """
    events_meta: { event_id: { "exists": bool, "name": str } }
    participant_by_event: { event_id: { "exists", "data": dict } }
    category_ids_by_event: { event_id: str | None } doc id en event_categories;
        truthy => .document(id).get() existe; falsy (None) => doc no existe
    category_display_names: { event_id: str } campo name del doc categoría (tests)
    visible_routes_by_event: { event_id: [ dict route fields + categoryIds list ] }
    checkpoints_by_route: { (event_id, route_id): [ checkpoint docs mocks ] }
    """
    category_display_names = category_display_names or {}
    checkpoints_by_route = checkpoints_by_route or {}
    db = MagicMock()

    # --- users/{uid}/membership ---
    m_docs = []
    for eid in membership_event_ids:
        md = MagicMock()
        md.id = eid
        m_docs.append(md)
    mem = MagicMock()
    mem.stream.return_value = m_docs
    usr = MagicMock()

    def usr_sub(name):
        if name == FirestoreCollections.USER_MEMBERSHIP:
            return mem
        return MagicMock()

    usr.collection.side_effect = usr_sub
    users_chain = MagicMock()
    users_chain.document.return_value = usr

    def route_doc_maker(event_id):
        route_ids_seen = {}

        def document(route_id):
            rref = MagicMock()
            chk_col = MagicMock()
            chk_col.get.return_value = checkpoints_by_route.get(
                (event_id, route_id), []
            )
            rref.collection.return_value = chk_col
            return rref

        return document

    def events_document(eid):
        ev_root = MagicMock()
        meta = events_meta.get(eid, {"exists": False, "name": ""})
        ev_snap = _FakeDoc(
            meta.get("exists", False), {"name": meta.get("name", "")}
        )
        ev_root.get.return_value = ev_snap

        p_meta = participant_by_event.get(
            eid, {"exists": False, "data": {}}
        )
        p_snap = _FakeDoc(p_meta["exists"], p_meta.get("data", {}))

        p_participant_doc_ref = MagicMock()
        p_participant_doc_ref.get.return_value = p_snap
        p_col = MagicMock()
        p_col.document.return_value = p_participant_doc_ref

        cat_rid = category_ids_by_event.get(eid)
        cats_col = MagicMock()
        cat_doc_ref = MagicMock()
        display = category_display_names.get(eid, "")
        if cat_rid:
            cat_doc_ref.get.return_value = _FakeDoc(
                True, {"name": display} if display else {}
            )
        else:
            cat_doc_ref.get.return_value = _FakeDoc(False, {})
        cats_col.document.return_value = cat_doc_ref

        routes_payload = visible_routes_by_event.get(eid, [])
        route_snapshots = []
        routes_document_side = route_doc_maker(eid)

        for i, rdata in enumerate(routes_payload):
            rdoc = MagicMock()
            rdoc.id = rdata.get("_id", f"r{i}")
            rdoc.to_dict.return_value = {
                k: v for k, v in rdata.items() if k != "_id"
            }
            route_snapshots.append(rdoc)

        r_col = MagicMock()
        r_where = MagicMock()
        r_where.get.return_value = route_snapshots

        def r_document(rid):
            return routes_document_side(rid)

        r_col.where.return_value = r_where
        r_col.document.side_effect = r_document

        def ev_sub(name):
            if name == FirestoreCollections.EVENT_PARTICIPANTS:
                return p_col
            if name == FirestoreCollections.EVENT_CATEGORIES:
                return cats_col
            if name == FirestoreCollections.EVENT_ROUTES:
                return r_col
            return MagicMock()

        ev_root.collection.side_effect = ev_sub
        return ev_root

    events_root = MagicMock()
    events_root.document.side_effect = events_document

    def db_collection(name, *a, **kw):
        if name == FirestoreCollections.USERS:
            return users_chain
        if name == FirestoreCollections.EVENTS:
            return events_root
        return MagicMock()

    db.collection.side_effect = db_collection
    return db


def test_competitor_payload_without_pilot_uses_category_name_not_id():
    """Sin dorsal, competitor.category debe ser el nombre de event_categories, no el id."""
    from competitors.competitor_route import _competitor_payload

    out = _competitor_payload(
        {
            "competitionCategory": {
                "registrationCategory": "docIdCat",
                "pilotNumber": "",
            }
        },
        category_display_name="  Prototipo  ",
    )
    assert out["category"] == "Prototipo"
    assert out["nombre"] == "Prototipo"


def test_competitor_payload_with_pilot_keeps_dorsal_in_category():
    from competitors.competitor_route import _competitor_payload

    out = _competitor_payload(
        {
            "competitionCategory": {
                "registrationCategory": "x",
                "pilotNumber": "7",
            }
        },
        category_display_name="Oro",
    )
    assert out["category"] == "7"
    assert out["nombre"] == "Oro"


@patch("competitors.competitor_route.validate_request", return_value=None)
@patch("competitors.competitor_route.verify_bearer_token", return_value=True)
def test_competitor_route_missing_user_id(_mock_vbt, _vr):
    from competitors.competitor_route import competitor_route

    req = MagicMock()
    req.method = "GET"
    req.args = {}
    req.headers = {"Authorization": "Bearer x"}
    req.get_json = lambda silent=True: None
    resp = competitor_route(req)
    assert resp.status_code == 400


@patch("competitors.competitor_route.validate_request", return_value=None)
@patch("competitors.competitor_route.verify_bearer_token", return_value=False)
def test_competitor_route_unauthorized(_mock_vbt, _vr):
    from competitors.competitor_route import competitor_route

    resp = competitor_route(_make_req())
    assert resp.status_code == 401


@patch("competitors.competitor_route.validate_request", return_value=None)
@patch("competitors.competitor_route.firestore.client")
@patch("competitors.competitor_route.verify_bearer_token", return_value=True)
def test_competitor_route_empty_membership(_mock_vbt, mock_fs, _vr):
    from competitors.competitor_route import competitor_route

    mock_fs.return_value = _build_firestore_mock(
        membership_event_ids=[],
        events_meta={},
        participant_by_event={},
        category_ids_by_event={},
        visible_routes_by_event={},
    )
    resp = competitor_route(_make_req())
    assert resp.status_code == 404


@patch("competitors.competitor_route.validate_request", return_value=None)
@patch("competitors.competitor_route.firestore.client")
@patch("competitors.competitor_route.verify_bearer_token", return_value=True)
def test_competitor_route_happy_path_with_checkpoints(_mock_vbt, mock_fs, _vr):
    from competitors.competitor_route import competitor_route

    class _CpDoc:
        id = "cp1"

        def to_dict(self):
            return {
                "checkpointTypeId": "t1",
                "coordinates": "1,2",
                "order": 1,
                "name": "CP1",
            }

    cp = _CpDoc()
    route_row = {
        "_id": "routeA",
        "name": "R1",
        "routeUrl": "https://x/r.gpx",
        "totalDistance": 10,
        "typedistance": "km",
        "visibleForPilots": True,
        "categoryIds": ["cat1"],
        "updatedAt": datetime(2026, 1, 1, 12, 0, 0),
    }

    db = _build_firestore_mock(
        membership_event_ids=["ev1"],
        events_meta={"ev1": {"exists": True, "name": "Rally Uno"}},
        participant_by_event={
            "ev1": {
                "exists": True,
                "data": {
                    "competitionCategory": {
                        "registrationCategory": "cat1",
                        "pilotNumber": "4",
                    }
                },
            }
        },
        category_ids_by_event={"ev1": "cat1"},
        category_display_names={"ev1": "Oro"},
        visible_routes_by_event={"ev1": [route_row]},
        checkpoints_by_route={("ev1", "routeA"): [cp]},
    )
    mock_fs.return_value = db

    resp = competitor_route(_make_req())
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert len(data) == 1
    assert data[0]["eventId"] == "ev1"
    assert data[0]["eventName"] == "Rally Uno"
    assert data[0]["routes"] is not None
    assert len(data[0]["routes"]) == 1
    item = data[0]["routes"][0]
    assert item["competitor"]["category"] == "4"
    assert item["competitor"]["nombre"] == "Oro"
    assert item["route"]["name"] == "R1"
    assert item["updatedAt"]
    assert len(item["checkpoints"]) == 1
    assert item["checkpoints"][0]["name"] == "CP1"


@patch("competitors.competitor_route.validate_request", return_value=None)
@patch("competitors.competitor_route.firestore.client")
@patch("competitors.competitor_route.verify_bearer_token", return_value=True)
def test_competitor_route_routes_null_when_no_category_match(
    _mock_vbt, mock_fs, _vr
):
    from competitors.competitor_route import competitor_route

    route_row = {
        "name": "R1",
        "routeUrl": "u",
        "visibleForPilots": True,
        "categoryIds": ["other"],
        "totalDistance": 0,
    }
    db = _build_firestore_mock(
        membership_event_ids=["ev1"],
        events_meta={"ev1": {"exists": True, "name": "E1"}},
        participant_by_event={
            "ev1": {
                "exists": True,
                "data": {
                    "competitionCategory": {
                        "registrationCategory": "cat1",
                        "pilotNumber": "4",
                    }
                },
            }
        },
        category_ids_by_event={"ev1": "cat1"},
        visible_routes_by_event={"ev1": [route_row]},
    )
    mock_fs.return_value = db

    resp = competitor_route(_make_req())
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data[0]["routes"] is None


@patch("competitors.competitor_route.validate_request", return_value=None)
@patch("competitors.competitor_route.firestore.client")
@patch("competitors.competitor_route.verify_bearer_token", return_value=True)
def test_competitor_route_404_when_event_missing(_mock_vbt, mock_fs, _vr):
    from competitors.competitor_route import competitor_route

    db = _build_firestore_mock(
        membership_event_ids=["ev1"],
        events_meta={"ev1": {"exists": False, "name": ""}},
        participant_by_event={},
        category_ids_by_event={},
        visible_routes_by_event={},
    )
    mock_fs.return_value = db

    resp = competitor_route(_make_req())
    assert resp.status_code == 404


@patch("competitors.competitor_route.validate_request", return_value=None)
@patch("competitors.competitor_route.firestore.client")
@patch("competitors.competitor_route.verify_bearer_token", return_value=True)
def test_competitor_route_empty_registration_category_yields_null_routes(
    _mock_vbt, mock_fs, _vr
):
    from competitors.competitor_route import competitor_route

    db = _build_firestore_mock(
        membership_event_ids=["ev1"],
        events_meta={"ev1": {"exists": True, "name": "E1"}},
        participant_by_event={
            "ev1": {
                "exists": True,
                "data": {
                    "competitionCategory": {
                        "registrationCategory": "",
                        "pilotNumber": "",
                    },
                },
            }
        },
        category_ids_by_event={"ev1": "cat1"},
        visible_routes_by_event={"ev1": []},
    )
    mock_fs.return_value = db

    resp = competitor_route(_make_req())
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data[0]["routes"] is None


@patch("competitors.competitor_route.validate_request", return_value=None)
@patch("competitors.competitor_route.firestore.client")
@patch("competitors.competitor_route.verify_bearer_token", return_value=True)
def test_competitor_route_two_calls_stable(_mock_vbt, mock_fs, _vr):
    from competitors.competitor_route import competitor_route

    route_row = {
        "_id": "r0",
        "name": "R1",
        "routeUrl": "u",
        "visibleForPilots": True,
        "categoryIds": ["cat1"],
        "totalDistance": 0,
        "updatedAt": datetime(2026, 6, 1, 10, 0, 0),
    }
    db = _build_firestore_mock(
        membership_event_ids=["ev1"],
        events_meta={"ev1": {"exists": True, "name": "E1"}},
        participant_by_event={
            "ev1": {
                "exists": True,
                "data": {
                    "competitionCategory": {"registrationCategory": "cat1"},
                },
            }
        },
        category_ids_by_event={"ev1": "cat1"},
        visible_routes_by_event={"ev1": [route_row]},
    )
    mock_fs.return_value = db

    req = _make_req()
    r1 = competitor_route(req)
    r2 = competitor_route(req)
    assert r1.status_code == r2.status_code == 200
    assert r1.get_data() == r2.get_data()


@patch("competitors.competitor_route.validate_request", return_value=None)
@patch("competitors.competitor_route.firestore.client")
@patch("competitors.competitor_route.verify_bearer_token", return_value=True)
def test_competitor_route_no_resolved_category_returns_null_routes(
    _mock_vbt, mock_fs, _vr
):
    from competitors.competitor_route import competitor_route

    route_row = {
        "name": "R1",
        "routeUrl": "u",
        "visibleForPilots": True,
        "categoryIds": ["cat1"],
        "totalDistance": 0,
    }
    db = _build_firestore_mock(
        membership_event_ids=["ev1"],
        events_meta={"ev1": {"exists": True, "name": "E1"}},
        participant_by_event={
            "ev1": {
                "exists": True,
                "data": {
                    "competitionCategory": {"registrationCategory": "cat1"},
                },
            }
        },
        category_ids_by_event={"ev1": None},
        visible_routes_by_event={"ev1": [route_row]},
    )
    mock_fs.return_value = db

    resp = competitor_route(_make_req())
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data[0]["routes"] is None
