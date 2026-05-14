import re
from typing import Iterable, Optional

try:
    import sqlglot
    from sqlglot import exp
except ImportError:  # pragma: no cover - exercised only in incomplete installs.
    sqlglot = None
    exp = None


BLOCKED_SQL_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
    "copy",
    "call",
    "merge",
)


def validate_readonly_sql(
    sql: str,
    allowed_tables: Optional[Iterable[str]] = None,
    dialect: str = "postgres",
) -> str:
    normalized = sql.strip().rstrip(";")
    if not normalized:
        raise ValueError("SQL must not be empty.")
    if ";" in normalized:
        raise ValueError("Only one SQL statement is allowed.")

    expression = _parse_single_statement(normalized, dialect)
    if not isinstance(expression, exp.Select):
        raise ValueError("Only read-only SELECT/WITH queries are allowed.")

    _reject_mutating_expressions(expression)
    _validate_allowed_tables(expression, allowed_tables)

    return normalized


def clamp_limit(limit: Optional[int], default: int = 50, maximum: int = 200) -> int:
    if limit is None:
        limit = default
    return max(1, min(int(limit), maximum))


def wrap_with_limit(
    sql: str,
    limit: Optional[int] = 50,
    maximum: int = 200,
    allowed_tables: Optional[Iterable[str]] = None,
) -> tuple[str, int]:
    safe_sql = validate_readonly_sql(sql, allowed_tables=allowed_tables)
    safe_limit = clamp_limit(limit, maximum=maximum)
    return f"select * from ({safe_sql}) as agent_query limit %s", safe_limit


def _parse_single_statement(sql: str, dialect: str):
    if sqlglot is None:
        return _fallback_validate_readonly_sql(sql)
    try:
        expressions = sqlglot.parse(sql, read=dialect)
    except Exception as exc:
        raise ValueError(f"SQL parse failed: {exc}") from exc
    if len(expressions) != 1:
        raise ValueError("Only one SQL statement is allowed.")
    return expressions[0]


def _fallback_validate_readonly_sql(sql: str):
    if not re.match(r"^(select|with)\b", sql, re.IGNORECASE):
        raise ValueError("Only read-only SELECT/WITH queries are allowed.")
    blocked = re.search(
        rf"\b({'|'.join(BLOCKED_SQL_KEYWORDS)})\b",
        sql,
        re.IGNORECASE,
    )
    if blocked:
        raise ValueError(f"SQL keyword is not allowed: {blocked.group(1)}")
    raise ValueError("sqlglot is required for SQL AST validation. Install project dependencies.")


def _reject_mutating_expressions(expression) -> None:
    mutating_types = tuple(
        getattr(exp, name)
        for name in (
            "Insert",
            "Update",
            "Delete",
            "Drop",
            "Create",
            "Alter",
            "Merge",
            "Command",
        )
        if hasattr(exp, name)
    )
    for node in expression.walk():
        if isinstance(node, mutating_types):
            raise ValueError(f"SQL statement type is not allowed: {node.key.upper()}")


def _validate_allowed_tables(expression, allowed_tables: Optional[Iterable[str]]) -> None:
    if not allowed_tables:
        return

    allowed = {_normalize_table_name(table) for table in allowed_tables}
    cte_names = {
        _normalize_table_name(cte.alias_or_name)
        for cte in expression.find_all(exp.CTE)
        if cte.alias_or_name
    }

    for table in expression.find_all(exp.Table):
        table_name = _table_name(table)
        normalized = _normalize_table_name(table_name)
        if normalized in cte_names:
            continue
        if normalized not in allowed:
            raise ValueError(f"SQL table is not allowed: {table_name}")


def _table_name(table) -> str:
    parts = [part for part in (table.catalog, table.db, table.name) if part]
    return ".".join(parts)


def _normalize_table_name(value: str) -> str:
    return value.replace('"', "").replace("`", "").strip().lower()
