"""
Tests para handlers del catálogo checkpoint-type (list, create, delete).
"""

import json
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, ".")


@pytest.fixture
def mock_db():
    return MagicMock()


def _empty_groups():
    return [
        {"type": "zones", "items": []},
        {"type": "symbols", "items": []},
        {"type": "waypoints", "items": []},
        {"type": "safety", "items": []},
        {"type": "dunes_sand", "items": []},
    ]


def test_handle_list_empty_catalog_returns_five_empty_groups(mock_db):
    from catalogs.checkpoint_type.list_checkpoint_type import handle_list

    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = iter(
        []
    )

    response = handle_list(mock_db)
    assert response.status_code == 200
    body = json.loads(response.get_data(as_text=True))
    assert body == _empty_groups()


def test_handle_list_groups_by_category_and_sorts_by_type(mock_db):
    from catalogs.checkpoint_type.list_checkpoint_type import handle_list

    d1 = MagicMock()
    d1.id = "b"
    d1.to_dict.return_value = {
        "category": "zones",
        "name": "B",
        "type": "beta",
        "icon": "ib",
        "description": "db",
        "abbreviation": "BB",
    }
    d2 = MagicMock()
    d2.id = "a"
    d2.to_dict.return_value = {
        "category": "zones",
        "name": "A",
        "type": "alpha",
        "icon": "ia",
        "description": "da",
        "abbreviation": None,
    }
    d3 = MagicMock()
    d3.id = "s1"
    d3.to_dict.return_value = {
        "category": "symbols",
        "name": "Fence",
        "type": "fence",
        "icon": "fence",
        "description": "A fence.",
    }

    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = iter(
        [d1, d2, d3]
    )

    response = handle_list(mock_db)
    body = json.loads(response.get_data(as_text=True))
    assert len(body) == 5
    zones = next(g for g in body if g["type"] == "zones")
    assert [x["type"] for x in zones["items"]] == ["alpha", "beta"]
    assert zones["items"][0] == {
        "id": "a",
        "name": "A",
        "type": "alpha",
        "icon": "ia",
        "abbreviation": None,
        "description": "da",
    }
    assert zones["items"][1]["abbreviation"] == "BB"
    sym = next(g for g in body if g["type"] == "symbols")
    assert len(sym["items"]) == 1


def test_handle_list_ignores_doc_without_valid_category(mock_db):
    from catalogs.checkpoint_type.list_checkpoint_type import handle_list

    bad = MagicMock()
    bad.id = "x"
    bad.to_dict.return_value = {
        "name": "orphan",
        "type": "t",
        "icon": "i",
        "description": "d",
    }
    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = iter(
        [bad]
    )

    response = handle_list(mock_db)
    body = json.loads(response.get_data(as_text=True))
    for g in body:
        assert g["items"] == []


def test_handle_create_returns_201_with_ids(mock_db):
    from catalogs.checkpoint_type.create_checkpoint_type import handle_create

    ref = MagicMock()
    doc_ref = MagicMock()
    doc_ref.id = "newid1"
    ref.document.return_value = doc_ref
    mock_db.collection.return_value.document.return_value.collection.return_value = ref

    req = MagicMock()
    req.get_json = lambda silent=True: [
        {
            "type": "zones",
            "items": [
                {
                    "name": "Start",
                    "type": "start_speed_limit_zone",
                    "icon": "speed_zone_start",
                    "abbreviation": "DZ",
                    "description": "Marks the beginning.",
                },
            ],
        },
    ]

    response = handle_create(req, mock_db)
    assert response.status_code == 201
    body = json.loads(response.get_data(as_text=True))
    assert body == ["newid1"]
    doc_ref.set.assert_called_once_with(
        {
            "category": "zones",
            "name": "Start",
            "type": "start_speed_limit_zone",
            "icon": "speed_zone_start",
            "description": "Marks the beginning.",
            "abbreviation": "DZ",
        }
    )


def test_handle_create_abbreviation_null_omits_field(mock_db):
    from catalogs.checkpoint_type.create_checkpoint_type import handle_create

    ref = MagicMock()
    doc_ref = MagicMock()
    doc_ref.id = "id2"
    ref.document.return_value = doc_ref
    mock_db.collection.return_value.document.return_value.collection.return_value = ref

    req = MagicMock()
    req.get_json = lambda silent=True: [
        {
            "type": "symbols",
            "items": [
                {
                    "name": "Fence",
                    "type": "fence",
                    "icon": "fence",
                    "abbreviation": None,
                    "description": "Fence.",
                },
            ],
        },
    ]

    response = handle_create(req, mock_db)
    assert response.status_code == 201
    doc_ref.set.assert_called_once_with(
        {
            "category": "symbols",
            "name": "Fence",
            "type": "fence",
            "icon": "fence",
            "description": "Fence.",
        }
    )


def test_handle_create_empty_groups_201_empty_ids(mock_db):
    from catalogs.checkpoint_type.create_checkpoint_type import handle_create

    ref = MagicMock()
    mock_db.collection.return_value.document.return_value.collection.return_value = ref

    req = MagicMock()
    req.get_json = lambda silent=True: []

    response = handle_create(req, mock_db)
    assert response.status_code == 201
    assert json.loads(response.get_data(as_text=True)) == []
    ref.document.assert_not_called()


def test_handle_create_invalid_body_not_list_400(mock_db):
    from catalogs.checkpoint_type.create_checkpoint_type import handle_create

    req = MagicMock()
    req.get_json = lambda silent=True: {}

    response = handle_create(req, mock_db)
    assert response.status_code == 400


def test_handle_create_unknown_category_400(mock_db):
    from catalogs.checkpoint_type.create_checkpoint_type import handle_create

    req = MagicMock()
    req.get_json = lambda silent=True: [
        {"type": "unknown", "items": []},
    ]

    response = handle_create(req, mock_db)
    assert response.status_code == 400


def test_handle_create_missing_item_field_400(mock_db):
    from catalogs.checkpoint_type.create_checkpoint_type import handle_create

    req = MagicMock()
    req.get_json = lambda silent=True: [
        {
            "type": "zones",
            "items": [{"name": "A", "type": "t", "icon": "i"}],
        },
    ]

    response = handle_create(req, mock_db)
    assert response.status_code == 400


def test_handle_delete_204(mock_db):
    from catalogs.checkpoint_type.delete_checkpoint_type import handle_delete

    ref = MagicMock()
    mock_db.collection.return_value.document.return_value.collection.return_value = ref

    req = MagicMock()
    req.get_json = lambda silent=True: ["a1"]

    response = handle_delete(req, mock_db)
    assert response.status_code == 204
    ref.document.assert_called_with("a1")
    ref.document.return_value.delete.assert_called_once()


def test_handle_delete_invalid_body_400(mock_db):
    from catalogs.checkpoint_type.delete_checkpoint_type import handle_delete

    req = MagicMock()
    req.get_json = lambda silent=True: {}

    response = handle_delete(req, mock_db)
    assert response.status_code == 400


def test_handle_list_twice_stable(mock_db):
    from catalogs.checkpoint_type.list_checkpoint_type import handle_list

    doc = MagicMock()
    doc.id = "x"
    doc.to_dict.return_value = {
        "category": "waypoints",
        "name": "n",
        "type": "waypoint_visible",
        "icon": "i",
        "description": "d",
        "abbreviation": "V",
    }
    stream = mock_db.collection.return_value.document.return_value.collection.return_value.stream
    stream.side_effect = [iter([doc]), iter([doc])]

    r1 = handle_list(mock_db)
    r2 = handle_list(mock_db)
    assert json.loads(r1.get_data(as_text=True)) == json.loads(r2.get_data(as_text=True))


def test_handle_create_two_groups_multiple_calls(mock_db):
    from catalogs.checkpoint_type.create_checkpoint_type import handle_create

    ref = MagicMock()
    _counter = [0]

    def _doc():
        dr = MagicMock()
        _counter[0] += 1
        dr.id = f"id{_counter[0]}"
        return dr

    ref.document.side_effect = _doc
    mock_db.collection.return_value.document.return_value.collection.return_value = ref

    body = [
        {
            "type": "zones",
            "items": [
                {
                    "name": "A",
                    "type": "a1",
                    "icon": "i1",
                    "description": "d1",
                },
            ],
        },
        {
            "type": "safety",
            "items": [
                {
                    "name": "B",
                    "type": "b1",
                    "icon": "i2",
                    "description": "d2",
                },
            ],
        },
    ]
    req = MagicMock()
    req.get_json = lambda silent=True: body

    r1 = handle_create(req, mock_db)
    r2 = handle_create(req, mock_db)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert json.loads(r1.get_data(as_text=True)) == ["id1", "id2"]
    assert json.loads(r2.get_data(as_text=True)) == ["id3", "id4"]
    assert ref.document.call_count == 4


def test_validate_checkpoint_item_and_groups():
    from catalogs.checkpoint_type._common import (
        validate_checkpoint_groups_body,
        validate_checkpoint_item,
    )

    assert validate_checkpoint_item(None) is not None
    assert validate_checkpoint_item({"name": "", "type": "t", "icon": "i", "description": "d"}) is not None
    full = {
        "name": "a",
        "type": "b",
        "icon": "c",
        "description": "d",
    }
    assert validate_checkpoint_item(full) is None
    assert validate_checkpoint_item({**full, "abbreviation": "x"}) is None
    assert validate_checkpoint_item({**full, "abbreviation": None}) is None
    assert validate_checkpoint_item({**full, "abbreviation": ""}) is not None
    assert validate_checkpoint_item({**full, "abbreviation": 1}) is not None

    assert validate_checkpoint_groups_body([]) is None
    assert validate_checkpoint_groups_body({}) is not None
    assert (
        validate_checkpoint_groups_body(
            [{"type": "zones", "items": [full]}],
        )
        is None
    )
    assert validate_checkpoint_groups_body([{"type": "zones", "items": "bad"}]) is not None
    assert validate_checkpoint_groups_body([None]) is not None
    assert validate_checkpoint_groups_body([{"type": "", "items": []}]) is not None


def test_handle_delete_json_parse_error_400(mock_db):
    from catalogs.checkpoint_type.delete_checkpoint_type import handle_delete

    req = MagicMock()

    def _raise(*_a, **_k):
        raise ValueError("bad json")

    req.get_json = _raise
    response = handle_delete(req, mock_db)
    assert response.status_code == 400


def test_handle_create_json_parse_error_400(mock_db):
    from catalogs.checkpoint_type.create_checkpoint_type import handle_create

    req = MagicMock()

    def _raise(*_a, **_k):
        raise ValueError("bad json")

    req.get_json = _raise
    response = handle_create(req, mock_db)
    assert response.status_code == 400
