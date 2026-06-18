"""
Pruebas unitarias para FirestoreHelper.query_documents.

Verifican principalmente que los `filters` SÍ se apliquen sobre la query
mediante `.where(filter=FieldFilter(field, operator, value))`. Firestore se
mockea con unittest.mock para no depender de servicios reales.
"""

import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")


def _make_doc(doc_id: str, data: dict):
    doc = MagicMock()
    doc.id = doc_id
    doc.to_dict.return_value = data
    return doc


def _make_query(docs):
    """Crea un mock de query que se devuelve a sí mismo en cada encadenamiento."""
    query = MagicMock()
    query.where.return_value = query
    query.order_by.return_value = query
    query.start_after.return_value = query
    query.limit.return_value = query
    query.stream.return_value = iter(docs)
    return query


def _make_helper(query):
    """Instancia FirestoreHelper con firestore.client() mockeado y collection -> query."""
    with patch("utils.firestore_helper.firestore") as mock_firestore:
        db = MagicMock()
        db.collection.return_value = query
        mock_firestore.client.return_value = db
        from utils.firestore_helper import FirestoreHelper

        helper = FirestoreHelper()
    return helper, db


class _FakeFieldFilter:
    """Captura los argumentos con los que se construye FieldFilter."""

    def __init__(self, field, operator, value):
        self.field = field
        self.operator = operator
        self.value = value

    def __eq__(self, other):
        return (
            isinstance(other, _FakeFieldFilter)
            and self.field == other.field
            and self.operator == other.operator
            and self.value == other.value
        )


def test_query_documents_single_filter_applies_where():
    docs = [_make_doc("u1", {"email": "a@b.com"})]
    query = _make_query(docs)
    helper, _ = _make_helper(query)

    with patch("utils.firestore_helper.FieldFilter", _FakeFieldFilter):
        result = helper.query_documents(
            "users",
            filters=[{"field": "email", "operator": "==", "value": "a@b.com"}],
        )

    assert result == [("u1", {"email": "a@b.com"})]
    query.where.assert_called_once()
    applied = query.where.call_args.kwargs["filter"]
    assert applied.field == "email"
    assert applied.operator == "=="
    assert applied.value == "a@b.com"


def test_query_documents_multiple_filters_chain_where():
    docs = [_make_doc("u2", {"email": "x@y.com", "isActive": True})]
    query = _make_query(docs)
    helper, _ = _make_helper(query)

    filters = [
        {"field": "email", "operator": "==", "value": "x@y.com"},
        {"field": "isActive", "operator": "==", "value": True},
    ]
    with patch("utils.firestore_helper.FieldFilter", _FakeFieldFilter):
        result = helper.query_documents("users", filters=filters)

    assert result == [("u2", {"email": "x@y.com", "isActive": True})]
    assert query.where.call_count == 2
    applied = [c.kwargs["filter"] for c in query.where.call_args_list]
    assert applied[0].field == "email" and applied[0].value == "x@y.com"
    assert applied[1].field == "isActive" and applied[1].value is True


def test_query_documents_filter_and_limit():
    docs = [_make_doc("u3", {"riderNumber": 7})]
    query = _make_query(docs)
    helper, _ = _make_helper(query)

    with patch("utils.firestore_helper.FieldFilter", _FakeFieldFilter):
        result = helper.query_documents(
            "competitors",
            filters=[{"field": "riderNumber", "operator": "==", "value": 7}],
            limit=5,
        )

    assert result == [("u3", {"riderNumber": 7})]
    query.where.assert_called_once()
    query.limit.assert_called_once_with(5)


def test_query_documents_in_operator():
    docs = [_make_doc("u4", {"status": "a"})]
    query = _make_query(docs)
    helper, _ = _make_helper(query)

    with patch("utils.firestore_helper.FieldFilter", _FakeFieldFilter):
        helper.query_documents(
            "events",
            filters=[{"field": "status", "operator": "in", "value": ["a", "b"]}],
        )

    applied = query.where.call_args.kwargs["filter"]
    assert applied.field == "status"
    assert applied.operator == "in"
    assert applied.value == ["a", "b"]


def test_query_documents_no_results_returns_empty():
    query = _make_query([])
    helper, _ = _make_helper(query)

    with patch("utils.firestore_helper.FieldFilter", _FakeFieldFilter):
        result = helper.query_documents(
            "users",
            filters=[{"field": "email", "operator": "==", "value": "none@x.com"}],
        )

    assert result == []
    query.where.assert_called_once()


def test_query_documents_no_filters_does_not_call_where():
    docs = [_make_doc("u5", {"name": "n"})]
    query = _make_query(docs)
    helper, _ = _make_helper(query)

    result = helper.query_documents("users", filters=None)

    assert result == [("u5", {"name": "n"})]
    query.where.assert_not_called()
