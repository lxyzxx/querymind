import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _json_default(value: Any) -> str:
    return repr(value)


def _log(message: str, enabled: bool = True) -> None:
    if enabled:
        print(message, file=sys.stderr, flush=True)


def _last_message_text(result: Any) -> str:
    if isinstance(result, dict) and result.get("messages"):
        message = result["messages"][-1]
        content = getattr(message, "content", None)
        if content is not None:
            return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    return str(result)


def _message_type(message: Any) -> str:
    msg_type = getattr(message, "type", None)
    if msg_type:
        return msg_type
    return message.__class__.__name__


def _print_agent_trace(result: Any) -> None:
    messages = result.get("messages") if isinstance(result, dict) else None
    if not messages:
        print("\n[agent-trace]\n" + json.dumps(result, ensure_ascii=False, default=_json_default))
        return

    print("\n[agent-trace]")
    for index, message in enumerate(messages, start=1):
        msg_type = _message_type(message)
        name = getattr(message, "name", "") or ""
        header = f"{index}. {msg_type}"
        if name:
            header += f" name={name}"
        print(header)

        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            print("tool_calls:")
            print(json.dumps(tool_calls, ensure_ascii=False, indent=2, default=_json_default))

        content = getattr(message, "content", None)
        if content:
            if isinstance(content, str):
                print(content)
            else:
                print(json.dumps(content, ensure_ascii=False, indent=2, default=_json_default))


def _pg_config_from_env() -> dict:
    return {
        "host": os.getenv("QUERYMIND_PG_HOST", "localhost"),
        "port": int(os.getenv("QUERYMIND_PG_PORT", "5432")),
        "dbname": os.getenv("QUERYMIND_PG_DATABASE", "postgres"),
        "user": os.getenv("QUERYMIND_PG_USER", "postgres"),
        "password": os.getenv("QUERYMIND_PG_PASSWORD", ""),
        "connect_timeout": int(os.getenv("QUERYMIND_PG_CONNECT_TIMEOUT", "5")),
    }


def build_agent(
    model: str,
    enable_pg: bool,
    print_trace: bool,
    model_timeout: float,
    semantic_layer: Any,
):
    try:
        from langchain.agents import create_agent
        from langchain.tools import tool
        from langchain_deepseek import ChatDeepSeek
    except ImportError as exc:
        raise RuntimeError(
            "LangChain agent dependencies are not installed. "
            "Run: python3 -m pip install -r requirements-agent.txt"
        ) from exc

    from querymind.agent.semantic_layer import parse_filters, parse_name_list
    from querymind.agent.sql_guard import wrap_with_limit

    tools = []

    @tool
    def describe_semantic_layer() -> str:
        """Return the governed business metrics, dimensions, filters, and table mappings."""
        payload = semantic_layer.prompt_context()
        _log(f"\n[tool:describe_semantic_layer] response\n{payload}", print_trace)
        return payload

    @tool
    def compile_metric_sql(
        metric: str,
        dimensions: str = "",
        filters_json: str = "{}",
        named_filters: str = "",
        limit: int = 50,
    ) -> str:
        """
        Compile a governed semantic metric request into SQL without executing it.

        dimensions and named_filters are comma-separated names or JSON arrays.
        filters_json is a JSON object that maps dimension names to exact-match values.
        """
        _log(
            "\n[tool:compile_metric_sql] request\n"
            f"metric={metric}\ndimensions={dimensions}\n"
            f"filters_json={filters_json}\nnamed_filters={named_filters}\nlimit={limit}",
            print_trace,
        )
        sql = semantic_layer.build_metric_query(
            metric_name=metric,
            dimensions=parse_name_list(dimensions),
            filters=parse_filters(filters_json),
            named_filters=parse_name_list(named_filters),
            limit=limit,
        )
        payload = json.dumps({"generated_sql": sql}, ensure_ascii=False)
        _log(f"[tool:compile_metric_sql] response\n{payload}", print_trace)
        return payload

    tools.extend([describe_semantic_layer, compile_metric_sql])

    if enable_pg:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL dependency is not installed. "
                "Run: python3 -m pip install -r requirements-agent.txt"
            ) from exc

        allowed_tables = [table.physical_name for table in semantic_layer.tables]

        def run_readonly_sql(sql: str, limit: int) -> str:
            wrapped_sql, safe_limit = wrap_with_limit(sql, limit, allowed_tables=allowed_tables)
            with psycopg2.connect(**_pg_config_from_env()) as conn:
                conn.set_session(readonly=True, autocommit=True)
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("set statement_timeout = %s", (5000,))
                    cursor.execute(wrapped_sql, (safe_limit,))
                    rows = cursor.fetchall()
            return json.dumps(
                {"row_count": len(rows), "rows": rows},
                ensure_ascii=False,
                default=_json_default,
            )

        @tool
        def query_metric(
            metric: str,
            dimensions: str = "",
            filters_json: str = "{}",
            named_filters: str = "",
            limit: int = 50,
        ) -> str:
            """
            Compile and execute a governed semantic metric query against PostgreSQL.

            dimensions and named_filters are comma-separated names or JSON arrays.
            filters_json is a JSON object that maps dimension names to exact-match values.
            """
            _log(
                "\n[tool:query_metric] request\n"
                f"metric={metric}\ndimensions={dimensions}\n"
                f"filters_json={filters_json}\nnamed_filters={named_filters}\nlimit={limit}",
                print_trace,
            )
            sql = semantic_layer.build_metric_query(
                metric_name=metric,
                dimensions=parse_name_list(dimensions),
                filters=parse_filters(filters_json),
                named_filters=parse_name_list(named_filters),
                limit=limit,
            )
            rows = run_readonly_sql(sql, limit)
            payload = json.dumps(
                {"generated_sql": sql, "result": json.loads(rows)},
                ensure_ascii=False,
                default=_json_default,
            )
            _log(f"[tool:query_metric] response\n{payload}", print_trace)
            return payload

        @tool
        def execute_sql(sql: str, limit: int = 50) -> str:
            """Execute a read-only PostgreSQL SELECT/WITH query for ad-hoc exploration."""
            _log(f"\n[tool:execute_sql] request\nsql={sql}\nlimit={limit}", print_trace)
            payload = run_readonly_sql(sql, limit)
            _log(f"[tool:execute_sql] response\n{payload}", print_trace)
            return payload

        tools.extend([query_metric, execute_sql])

    prompt_parts = [
        "You are a governed AI2SQL assistant.",
        "Use describe_semantic_layer to inspect available business metrics, dimensions, and filters.",
        "Use compile_metric_sql when the user asks for SQL generation only.",
    ]
    if enable_pg:
        prompt_parts.append("Prefer query_metric for business metric questions that should be executed.")
        prompt_parts.append("Use execute_sql only for read-only ad-hoc exploration that the semantic layer cannot express.")
    else:
        prompt_parts.append("PostgreSQL execution is disabled, so do not claim that SQL was executed.")

    llm = ChatDeepSeek(
        model=model,
        temperature=0,
        timeout=model_timeout,
        max_retries=2,
    )

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=" ".join(prompt_parts),
    )


def main():
    parser = argparse.ArgumentParser(description="QueryMind governed AI2SQL agent demo")
    parser.add_argument(
        "question",
        nargs="?",
        default="Generate SQL for active user count by status.",
        help="User question for the agent.",
    )
    parser.add_argument("--model", default=os.getenv("QUERYMIND_AGENT_MODEL", "deepseek-chat"))
    parser.add_argument(
        "--model-timeout",
        type=float,
        default=float(os.getenv("QUERYMIND_MODEL_TIMEOUT", "60")),
        help="DeepSeek request timeout in seconds.",
    )
    parser.add_argument(
        "--enable-pg",
        action="store_true",
        default=os.getenv("QUERYMIND_ENABLE_PG", "").lower() in {"1", "true", "yes"},
        help="Enable PostgreSQL execution tools.",
    )
    parser.add_argument(
        "--print-trace",
        action="store_true",
        default=os.getenv("QUERYMIND_PRINT_TRACE", "").lower() in {"1", "true", "yes"},
        help="Print model messages, tool calls, and tool results after the final answer.",
    )
    parser.add_argument(
        "--semantic-layer",
        default=os.getenv("QUERYMIND_SEMANTIC_LAYER", "querymind/example/semantic_layer.yaml"),
        help="YAML semantic layer file for governed metric queries.",
    )
    args = parser.parse_args()

    from querymind.agent.semantic_layer import SemanticLayer

    semantic_layer = SemanticLayer.from_file(args.semantic_layer)
    agent = build_agent(
        model=args.model,
        enable_pg=args.enable_pg,
        print_trace=args.print_trace,
        model_timeout=args.model_timeout,
        semantic_layer=semantic_layer,
    )
    _log("[agent] invoking model...", args.print_trace)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": args.question}]},
        config={"recursion_limit": 8},
    )
    _log("[agent] invoke completed", args.print_trace)
    print(_last_message_text(result))
    if args.print_trace:
        _print_agent_trace(result)


if __name__ == "__main__":
    main()
