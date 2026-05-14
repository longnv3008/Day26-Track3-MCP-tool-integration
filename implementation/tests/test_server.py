import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import SQLiteAdapter, ValidationError
from init_db import create_database


@pytest.fixture
def adapter(tmp_path):
    db_path = str(tmp_path / "test.db")
    create_database(db_path)
    return SQLiteAdapter(db_path)


def test_list_tables(adapter):
    tables = adapter.list_tables()
    assert set(tables) == {"students", "courses", "enrollments"}


def test_get_table_schema(adapter):
    schema = adapter.get_table_schema("students")
    col_names = {c["name"] for c in schema}
    assert col_names == {"id", "name", "cohort", "score"}


def test_search_valid(adapter):
    result = adapter.search("students")
    assert "rows" in result
    assert len(result["rows"]) == 5
    assert result["table"] == "students"


def test_search_with_filter(adapter):
    result = adapter.search("students", filters={"cohort": {"eq": "A1"}})
    assert len(result["rows"]) == 3
    assert all(r["cohort"] == "A1" for r in result["rows"])


def test_search_with_columns(adapter):
    result = adapter.search("students", columns=["name", "score"])
    assert set(result["rows"][0].keys()) == {"name", "score"}


def test_search_with_order(adapter):
    result = adapter.search("students", order_by="score", descending=True)
    scores = [r["score"] for r in result["rows"]]
    assert scores == sorted(scores, reverse=True)


def test_search_invalid_table(adapter):
    with pytest.raises(ValidationError, match="Unknown table"):
        adapter.search("nonexistent")


def test_search_invalid_column(adapter):
    with pytest.raises(ValidationError, match="Unknown column"):
        adapter.search("students", columns=["invalid_col"])


def test_search_invalid_operator(adapter):
    with pytest.raises(ValidationError, match="Unsupported operator"):
        adapter.search("students", filters={"name": {"contains": "Alice"}})


def test_insert_valid(adapter):
    result = adapter.insert("students", {"name": "Frank", "cohort": "A2", "score": 80.0})
    assert "id" in result
    assert result["inserted"]["name"] == "Frank"
    assert result["inserted"]["cohort"] == "A2"


def test_insert_empty_values(adapter):
    with pytest.raises(ValidationError, match="must not be empty"):
        adapter.insert("students", {})


def test_insert_invalid_column(adapter):
    with pytest.raises(ValidationError, match="Unknown column"):
        adapter.insert("students", {"bad_col": "value"})


def test_aggregate_count(adapter):
    result = adapter.aggregate("students", "count")
    assert result[0]["value"] == 5


def test_aggregate_avg(adapter):
    result = adapter.aggregate("students", "avg", "score")
    assert isinstance(result[0]["value"], float)
    assert 70 < result[0]["value"] < 100


def test_aggregate_sum(adapter):
    result = adapter.aggregate("students", "sum", "score")
    assert result[0]["value"] == pytest.approx(92.5 + 78.0 + 88.5 + 65.0 + 95.0)


def test_aggregate_group_by(adapter):
    result = adapter.aggregate("students", "count", group_by="cohort")
    groups = {r["group"] for r in result}
    assert "A1" in groups and "A2" in groups


def test_aggregate_invalid_metric(adapter):
    with pytest.raises(ValidationError, match="Unsupported metric"):
        adapter.aggregate("students", "variance", "score")


def test_aggregate_missing_column(adapter):
    with pytest.raises(ValidationError, match="column is required"):
        adapter.aggregate("students", "avg")
