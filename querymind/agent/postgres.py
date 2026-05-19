import os
from typing import Any, Dict, Iterable, Optional

from querymind.agent.sql_guard import wrap_with_limit


def pg_config_from_env() -> Dict[str, Any]:
    return {
        "host": os.getenv("QUERYMIND_PG_HOST", "localhost"),
        "port": int(os.getenv("QUERYMIND_PG_PORT", "5432")),
        "dbname": os.getenv("QUERYMIND_PG_DATABASE", "postgres"),
        "user": os.getenv("QUERYMIND_PG_USER", "postgres"),
        "password": os.getenv("QUERYMIND_PG_PASSWORD", ""),
        "connect_timeout": int(os.getenv("QUERYMIND_PG_CONNECT_TIMEOUT", "5")),
    }


def execute_readonly_sql(
    sql: str,
    limit: Optional[int] = 50,
    allowed_tables: Optional[Iterable[str]] = None,
    pg_config: Optional[Dict[str, Any]] = None,
    statement_timeout_ms: int = 5000,
) -> Dict[str, Any]:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL dependency is not installed. "
            "Run: python3 -m pip install -r requirements-agent.txt"
        ) from exc

    wrapped_sql, safe_limit = wrap_with_limit(sql, limit, allowed_tables=allowed_tables)
    config = pg_config or pg_config_from_env()
    with psycopg2.connect(**config) as conn:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("set statement_timeout = %s", (statement_timeout_ms,))
            cursor.execute(wrapped_sql, (safe_limit,))
            rows = [dict(row) for row in cursor.fetchall()]

    return {
        "sql": sql,
        "wrapped_sql": wrapped_sql,
        "limit": safe_limit,
        "row_count": len(rows),
        "rows": rows,
    }
