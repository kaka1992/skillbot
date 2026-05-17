"""SQL completion for %%sql cells — keywords + table/column cache."""

import re

SQL_KEYWORDS = sorted([
    "SELECT", "FROM", "WHERE", "JOIN", "INNER JOIN", "LEFT JOIN",
    "RIGHT JOIN", "FULL JOIN", "CROSS JOIN", "ON", "AND", "OR",
    "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "OFFSET",
    "INSERT INTO", "UPDATE", "DELETE FROM", "CREATE TABLE",
    "ALTER TABLE", "DROP TABLE", "TRUNCATE TABLE",
    "SET", "VALUES", "INTO", "DISTINCT",
    "COUNT", "SUM", "AVG", "MAX", "MIN", "COALESCE", "CAST",
    "AS", "IN", "NOT", "NULL", "IS", "LIKE", "BETWEEN", "EXISTS",
    "UNION", "UNION ALL", "INTERSECT", "EXCEPT",
    "CASE", "WHEN", "THEN", "ELSE", "END",
    "OVER", "PARTITION BY", "ROW_NUMBER", "RANK", "DENSE_RANK",
    "LAG", "LEAD", "FIRST_VALUE", "LAST_VALUE",
    "ASC", "DESC", "NULLS FIRST", "NULLS LAST",
    "TRUE", "FALSE",
    "INT", "BIGINT", "STRING", "DOUBLE", "FLOAT", "BOOLEAN",
    "DATE", "TIMESTAMP", "DECIMAL", "ARRAY", "MAP", "STRUCT",
], key=str.lower)


def load_sql_completer(ipython) -> None:
    """Register SQL completer for %%sql cells."""
    from . import get_table_columns

    def _sql_complete(event):
        # only active in %%sql cells
        cell = getattr(ipython, "_current_cell_raw", "") or ""
        if not cell.lstrip().startswith("%%sql"):
            return None

        line = (event.line or "").strip()
        symbol = (event.symbol or "").strip()

        if not symbol:
            return None

        prefix_lower = symbol.lower()

        # SQL keywords
        matches = [kw for kw in SQL_KEYWORDS if kw.lower().startswith(prefix_lower)]

        # table names from cache
        for table, cols in get_table_columns().items():
            if table.startswith(prefix_lower):
                matches.append(table)

        # column completion: after "table." pattern
        dot_match = re.search(r'(\w+)\.\s*$', line[:event.end])
        if dot_match:
            tbl = dot_match.group(1).lower()
            cached_cols = get_table_columns().get(tbl, [])
            col_prefix = symbol.lower()
            col_matches = [f"{tbl}.{c}" for c in cached_cols if c.startswith(col_prefix)]
            if col_matches:
                return sorted(col_matches)

        if matches:
            return sorted(set(matches), key=str.lower)
        return None

    ipython.set_hook("complete_command", _sql_complete, str_key="%sql")
