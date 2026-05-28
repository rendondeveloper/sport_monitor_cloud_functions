"""Tests unitarios para checklist_participant_service (v3)."""

import sys
from unittest.mock import MagicMock

sys.path.insert(0, ".")


def _make_helper(existing_participant_ids=None, existing_doc=None, event_ids=None):
    helper = MagicMock()
    helper.list_document_ids.side_effect = [
        list(event_ids or ["user-1", "user-2"]),
        list(existing_participant_ids or []),
    ]
    helper.get_document.return_value = existing_doc
    helper.query_documents.return_value = []
    return helper


def test_sync_all_event_participants_creates_docs_for_event_competitors():
    from checklists.checklist_participant_service import sync_all_event_participants
    from checklists.checklist_paths import participants_collection_path

    helper = _make_helper(event_ids=["user-1", "user-2"])
    path = participants_collection_path("evt-1", "chk-1")
    stored_items = [
        {"id": "item-global", "isRequired": True, "participantIds": []},
    ]

    sync_all_event_participants(helper, "evt-1", "chk-1", stored_items)

    assert helper.create_document_with_id.call_count == 2
    for call in helper.create_document_with_id.call_args_list:
        assert call[0][0] == path
        progress = call[0][2]["itemProgress"]
        assert "item-global" in progress


def test_sync_all_event_participants_includes_optional_for_all_and_required_only_for_is_completed():
    from checklists.checklist_participant_service import sync_all_event_participants

    helper = _make_helper(event_ids=["user-a", "user-b"])
    stored_items = [
        # Opcional: aunque venga con participantIds, debe aplicar a TODOS.
        {"id": "item-opt", "isRequired": False, "participantIds": ["user-a"]},
        # Requerido global: para todos.
        {"id": "item-req-global", "isRequired": True, "participantIds": []},
        # Opcional targeted (legacy): ahora aplica a TODOS por ser isRequired=False.
        {"id": "item-req-target", "isRequired": False, "participantIds": ["user-a"]},
    ]

    sync_all_event_participants(helper, "evt-1", "chk-1", stored_items)

    payload_by_user = {
        call[0][1]: call[0][2] for call in helper.create_document_with_id.call_args_list
    }

    # itemProgress: todos los opcionales (aunque vengan con participantIds) + requeridos aplicables.
    assert set(payload_by_user["user-a"]["itemProgress"].keys()) == {
        "item-opt",
        "item-req-global",
        "item-req-target",
    }
    assert set(payload_by_user["user-b"]["itemProgress"].keys()) == {
        "item-opt",
        "item-req-global",
        "item-req-target",
    }

    # isCompleted SOLO considera requeridos: aquí ninguno está checked, así que False en ambos.
    assert payload_by_user["user-a"]["isCompleted"] is False
    assert payload_by_user["user-b"]["isCompleted"] is False


def test_sync_all_event_participants_removes_stale_participant_docs():
    from checklists.checklist_participant_service import sync_all_event_participants
    from checklists.checklist_paths import participants_collection_path

    helper = MagicMock()
    helper.list_document_ids.side_effect = [
        ["user-keep"],
        ["user-keep", "user-gone"],
    ]
    helper.get_document.return_value = {"itemProgress": {}}
    path = participants_collection_path("evt-1", "chk-1")

    sync_all_event_participants(helper, "evt-1", "chk-1", [])

    helper.delete_document.assert_called_once_with(path, "user-gone")


def test_sync_all_event_participants_preserves_check_on_existing():
    from checklists.checklist_participant_service import sync_all_event_participants

    helper = MagicMock()
    helper.list_document_ids.side_effect = [["user-1"], ["user-1"]]
    helper.get_document.return_value = {
        "itemProgress": {
            "item-1": {"check": True, "updateDate": "2026-01-15T10:00:00+00:00"},
        }
    }
    stored_items = [
        {"id": "item-1", "isRequired": True, "participantIds": []},
        {"id": "item-2", "isRequired": True, "participantIds": []},
        {"id": "item-opt", "isRequired": False, "participantIds": []},
    ]

    sync_all_event_participants(helper, "evt-1", "chk-1", stored_items)

    item_progress = helper.update_document.call_args[0][2]["itemProgress"]
    assert item_progress["item-1"]["check"] is True
    assert item_progress["item-2"] == {"check": False, "updateDate": None}
    assert item_progress["item-opt"] == {"check": False, "updateDate": None}


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
        ("pd-1", {"fullName": "Ana Lopez"})
    ]

    create_participant_doc(
        helper,
        "evt-1",
        "chk-1",
        "user-1",
        ["item-1"],
        ["item-1"],
    )

    payload = helper.create_document_with_id.call_args[0][2]
    assert payload["participantName"] == "Ana Lopez"
    assert payload["pilotNumber"] == "42"
    assert payload["email"] == "ana@test.com"
    assert payload["itemProgress"] == {"item-1": {"check": False, "updateDate": None}}


def test_create_participant_doc_denormalizes_legacy_first_last_name():
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

    create_participant_doc(
        helper,
        "evt-1",
        "chk-1",
        "user-1",
        ["item-1"],
        ["item-1"],
    )

    payload = helper.create_document_with_id.call_args[0][2]
    assert payload["participantName"] == "Ana Lopez"


def test_sync_all_event_participants_updates_existing_doc_denormalizes_fields():
    from checklists.checklist_participant_service import sync_all_event_participants
    from checklists.checklist_paths import participants_collection_path
    from models.firestore_collections import FirestoreCollections

    helper = MagicMock()
    helper.list_document_ids.side_effect = [
        ["user-1"],  # event participants
        ["user-1"],  # existing checklist participants
    ]

    path = participants_collection_path("evt-1", "chk-1")

    def _get_document_side_effect(collection, doc_id):
        mapping = {
            (path, "user-1"): {"itemProgress": {}},
            (FirestoreCollections.USERS, "user-1"): {"email": "ana@test.com"},
            ("events/evt-1/participants", "user-1"): {
                "competitionCategory": {"pilotNumber": "42"}
            },
        }
        return mapping.get((collection, doc_id))

    helper.get_document.side_effect = _get_document_side_effect
    helper.query_documents.return_value = [("pd-1", {"fullName": "Ana Lopez"})]

    stored_items = [{"id": "item-1", "isRequired": True, "participantIds": []}]

    sync_all_event_participants(helper, "evt-1", "chk-1", stored_items)

    helper.update_document.assert_called_once()
    update_args = helper.update_document.call_args[0]
    assert update_args[0] == path
    assert update_args[1] == "user-1"
    payload = update_args[2]
    assert payload["participantName"] == "Ana Lopez"
    assert payload["email"] == "ana@test.com"
    assert payload["pilotNumber"] == "42"
    assert payload["itemProgress"] == {"item-1": {"check": False, "updateDate": None}}
    assert payload["isCompleted"] is False
    assert payload["updatedAt"] is not None
