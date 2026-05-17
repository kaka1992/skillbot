"""SQL completion for %%sql cells — keywords + table/column cache."""

import logging
import re

_log = logging.getLogger(__name__)

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

    _log.info("sql completer registered")

    def _sql_complete(event):
        cell = getattr(ipython, "_current_cell_raw", "") or ""

        # only active in %%sql cells
        if not cell.lstrip().startswith("%%sql"):
            _log.debug("completer skip: not a %%sql cell")
            return None

        line = (event.line or "").strip()
        symbol = (event.symbol or "").strip()
        _log.debug("completer: line=%r symbol=%r cell_first_line=%r",
                   line[:80], symbol, cell.split("\n")[0][:80])

        if not symbol:
            _log.debug("completer skip: empty symbol")
            return None

        prefix_lower = symbol.lower()

        # SQL keywords
        kw_matches = [kw for kw in SQL_KEYWORDS if kw.lower().startswith(prefix_lower)]
        _log.debug("completer: keyword matches for %r: %s", symbol, kw_matches[:10])

        # table names from cache
        tbl_cache = get_table_columns()
        tbl_matches = [t for t in tbl_cache if t.startswith(prefix_lower)]
        if tbl_matches:
            _log.debug("completer: table matches for %r: %s (cache size=%d)",
                      symbol, tbl_matches, len(tbl_cache))

        matches = kw_matches + tbl_matches

        # column completion: after "table." pattern
        dot_match = re.search(r'(\w+)\.\s*$', line[:event.end])
        if dot_match:
            tbl = dot_match.group(1).lower()
            cached_cols = tbl_cache.get(tbl, [])
            col_prefix = symbol.lower()
            col_matches = [f"{tbl}.{c}" for c in cached_cols if c.startswith(col_prefix)]
            _log.debug("completer: column completion table=%r prefix=%r matches=%s",
                      tbl, col_prefix, col_matches)
            if col_matches:
                return sorted(col_matches)

        if matches:
            result = sorted(set(matches), key=str.lower)
            _log.debug("completer: returning %d matches for %r: %s", len(result), symbol, result[:10])
            return result

        _log.debug("completer: no matches for %r", symbol)
        return None

    # Try multiple registration paths for IPython 8.x / Jupyter kernel
    completer = getattr(ipython, "Completer", None)
    if completer and hasattr(completer, "matchers"):
        completer.matchers.insert(0, _sql_complete)
        _log.info("sql completer registered via Completer.matchers")
    else:
        # Fallback: register as a general custom completer
        ipython.set_hook("complete_command", _sql_complete, re_key=".*")
        _log.info("sql completer registered via set_hook(re_key=.*)")
