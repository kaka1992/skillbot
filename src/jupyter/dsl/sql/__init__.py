"""dsl/sql — %%sql magic backend: runner, formatter, table registry."""

from .sql_runner import SqlRunner  # noqa: F401

try:
    import sqlparse
    _HAS_SQLPARSE = True
except ImportError:
    _HAS_SQLPARSE = False

# table/column cache for completion (populated externally)
_table_columns: dict[str, list[str]] = {}


def register_table(name: str, columns: list[str]) -> None:
    """Register table columns for SQL completion. Called by tools/spark."""
    _table_columns[name.lower()] = [c.lower() for c in columns]


def get_table_columns() -> dict[str, list[str]]:
    """Return current table/column cache."""
    return dict(_table_columns)


def format_sql(sql: str) -> str:
    """Format SQL using sqlparse. Returns original if sqlparse unavailable."""
    if _HAS_SQLPARSE:
        return sqlparse.format(sql, reindent=True, keyword_case='upper')
    return sql
