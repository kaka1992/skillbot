"""Tests for dsl/sql: format_sql, register_table."""
import sys

sys.path.insert(0, "src")

import pytest
from jupyter.dsl.sql import format_sql, register_table, get_table_columns


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
