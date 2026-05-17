"""Tests for dsl/sql: format_sql, register_table, completer."""
import sys

sys.path.insert(0, "src")

import pytest
from jupyter.dsl.sql import format_sql, register_table, get_table_columns
from jupyter.dsl.sql.completer import SQL_KEYWORDS


class TestFormatSql:
    def test_format_keywords_uppercase(self):
        result = format_sql("select * from t where x = 1")
        assert "SELECT" in result
        assert "FROM" in result
        assert "WHERE" in result

    def test_format_reindent(self):
        result = format_sql("select a, b from t where c > 10 order by a")
        # sqlparse reindents and capitalizes
        assert result.strip().upper().startswith("SELECT")

    def test_format_empty(self):
        assert format_sql("") == ""

    def test_format_preserves_comments(self):
        result = format_sql("-- comment\nselect 1")
        assert "-- comment" in result
        assert "SELECT" in result


class TestTableRegistry:
    def test_register_and_get(self):
        register_table("users", ["id", "name", "email"])
        cache = get_table_columns()
        assert "users" in cache
        assert cache["users"] == ["id", "name", "email"]

    def test_register_lowercase(self):
        register_table("Orders", ["OrderID", "Total"])
        cache = get_table_columns()
        assert "orders" in cache
        assert cache["orders"] == ["orderid", "total"]

    def test_multiple_tables(self):
        register_table("a", ["x"])
        register_table("b", ["y"])
        cache = get_table_columns()
        assert len(cache) >= 2


class TestCompleterKeywords:
    def test_select_matches(self):
        matches = [kw for kw in SQL_KEYWORDS if kw.upper().startswith("SEL")]
        assert "SELECT" in matches

    def test_join_matches(self):
        matches = [kw for kw in SQL_KEYWORDS if kw.upper().startswith("LEFT")]
        assert "LEFT JOIN" in matches

    def test_no_match(self):
        matches = [kw for kw in SQL_KEYWORDS if kw.upper().startswith("ZZZ")]
        assert len(matches) == 0

    def test_case_insensitive(self):
        matches_lower = [kw for kw in SQL_KEYWORDS if kw.lower().startswith("sel")]
        matches_upper = [kw for kw in SQL_KEYWORDS if kw.upper().startswith("SEL")]
        assert len(matches_lower) == len(matches_upper)


class TestCompleterTableColumns:
    def test_table_name_matches(self):
        register_table("users", ["id", "name"])
        tables = [t for t in get_table_columns() if t.startswith("us")]
        assert "users" in tables

    def test_column_completion(self):
        register_table("orders", ["order_id", "amount", "date"])
        cache = get_table_columns()
        cols = cache.get("orders", [])
        assert "order_id" in cols
        assert "amount" in cols
