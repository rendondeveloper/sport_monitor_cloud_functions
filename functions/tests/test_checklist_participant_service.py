"""Tests unitarios para checklist_participant_service (SPRTMNTRPP-124)."""

import sys
from unittest.mock import MagicMock, call

sys.path.insert(0, ".")


def _make_helper(existing_ids=None, existing_doc=None):
    helper = MagicMock()
    helper.list_document_ids.return_value = list(existing_ids or [])
    helper.get_document.return_value = existing_doc
    helper.query_documents.return_value = []
    return helper


def test_sync_participants_creates_new_and_deletes_removed():
    from checklists.checklist_participant_service import sync_participants_for_assigned_ids
    from checklists.checklist_paths import participants_collection_path

    helper = _make_helper(existing_ids=["user-old", "user-keep"])
    path = participants_collection_path("evt-1", "chk-1")

    sync_participants_for_assigned_ids(
        helper, "evt-1", "chk-1", ["user-keep", "user-new"], ["item-1"]
    )

    helper.delete_document.assert_called_once_with(path, "user-old")
    helper.create_document_with_id.assert_called_once()
    create_args = helper.create_document_with_id.call_args[0]
    assert create_args[0] == path
    assert create_args[1] == "user-new"
    helper.update_document.assert_called_once()


def test_sync_participants_preserves_check_and_update_date_on_existing_items():
    from checklists.checklist_participant_service import sync_participants_for_assigned_ids

    helper = _make_helper(
        existing_ids=["user-1"],
        existing_doc={
            "itemProgress": {
                "item-1": {"check": True, "updateDate": "2026-01-15T10:00:00+00:00"},
            }
        },
    )

    sync_participants_for_assigned_ids(
        helper, "evt-1", "chk-1", ["user-1"], ["item-1", "item-2"]
    )

    update_payload = helper.update_document.call_args[0][2]
    item_progress = update_payload["itemProgress"]
    assert item_progress["item-1"]["check"] is True
    assert item_progress["item-1"]["updateDate"] == "2026-01-15T10:00:00+00:00"
    assert item_progress["item-2"] == {"check": False, "updateDate": None}
    assert update_payload["isCompleted"] is False


def test_create_participant_doc_denormalizes_fields():
    from checklists.checklist_participant_service import create_participant_doc
    from models.firestore_collections import FirestoreCollections

    helper = MagicMock()
    helper.get_document.side_effect = lambda collection, doc_id: {
        (FirestoreCollections.USERS, "user-1"): {"email": "ana@test.com"},
        ("events/evt-1/participants", "user-1"): {
            "competitionCategory": {"pilotNumber": "42"}
        },
    }.get((collection, doc_id))
    helper.query_documents.return_value = [
        ("pd-1", {"firstName": "Ana", "lastName": "Lopez"})
    ]

    create_participant_doc(helper, "evt-1", "chk-1", "user-1", ["item-1"])

    payload = helper.create_document_with_id.call_args[0][2]
    assert payload["participantName"] == "Ana Lopez"
    assert payload["pilotNumber"] == "42"
    assert payload["email"] == "ana@test.com"
    assert payload["itemProgress"] == {"item-1": {"check": False, "updateDate": None}}


def test_required_ids_from_items_filters_optional():
    from checklists.checklist_participant_service import required_ids_from_items

    items = [
        {"id": "req-1", "isRequired": True},
        {"id": "opt-1", "isRequired": False},
        {"id": "req-2", "isRequired": True},
    ]
    assert required_ids_from_items(items) == ["req-1", "req-2"]
