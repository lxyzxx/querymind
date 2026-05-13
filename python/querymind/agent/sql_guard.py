import re
from typing import Optional


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


def validate_readonly_sql(sql: str) -> str:
    normalized = sql.strip().rstrip(";")
    if not normalized:
        raise ValueError("SQL must not be empty.")
    if ";" in normalized:
        raise ValueError("Only one SQL statement is allowed.")
    if not re.match(r"^(select|with)\b", normalized, re.IGNORECASE):
        raise ValueError("Only read-only SELECT/WITH queries are allowed.")

    blocked = re.search(
        rf"\b({'|'.join(BLOCKED_SQL_KEYWORDS)})\b",
        normalized,
        re.IGNORECASE,
    )
    if blocked:
        raise ValueError(f"SQL keyword is not allowed: {blocked.group(1)}")

    return normalized


def clamp_limit(limit: Optional[int], default: int = 50, maximum: int = 200) -> int:
    if limit is None:
        limit = default
    return max(1, min(int(limit), maximum))


def wrap_with_limit(sql: str, limit: Optional[int] = 50, maximum: int = 200) -> tuple[str, int]:
    safe_sql = validate_readonly_sql(sql)
    safe_limit = clamp_limit(limit, maximum=maximum)
    return f"select * from ({safe_sql}) as agent_query limit %s", safe_limit

