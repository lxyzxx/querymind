import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PYTHON_ROOT = ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


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


def _validate_readonly_sql(sql: str) -> str:
    normalized = sql.strip().rstrip(";")
    if ";" in normalized:
        raise ValueError("Only one SQL statement is allowed.")
    if not re.match(r"^(select|with)\b", normalized, re.IGNORECASE):
        raise ValueError("Only read-only SELECT/WITH queries are allowed.")
    blocked = re.search(
        r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|merge)\b",
        normalized,
        re.IGNORECASE,
    )
    if blocked:
        raise ValueError(f"SQL keyword is not allowed: {blocked.group(1)}")
    return normalized


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
    client: Any,
    session_id: str,
    model: str,
    enable_pg: bool,
    print_trace: bool,
    model_timeout: float,
    semantic_layer: Any = None,
):
    try:
        from langchain.agents import create_agent
        from langchain.tools import tool
        from langchain_deepseek import ChatDeepSeek
    except ImportError as exc:
        raise RuntimeError(
            "LangChain agent dependencies are not installed. "
            "Run: python -m pip install -r python/requirements-agent.txt"
        ) from exc

    @tool
    def execute_python(code: str) -> str:
        """Execute Python code in the persistent QueryMind runtime session and return stdout or errors."""
        _log(f"\n[tool:execute_python] request\n{code}", print_trace)
        output = client.execute(session_id, code, raise_on_error=False)
        _log(f"[tool:execute_python] response\n{output or '(no stdout)'}", print_trace)
        return output or "(no stdout)"

    @tool
    def get_variable(name: str) -> str:
        """Read a variable from the current QueryMind runtime session and return a JSON description."""
        _log(f"\n[tool:get_variable] request\n{name}", print_trace)
        value = client.get_variable(session_id, name, raise_on_error=False)
        payload = json.dumps(value, ensure_ascii=False, default=_json_default)
        _log(f"[tool:get_variable] response\n{payload}", print_trace)
        return payload

    tools = [execute_python, get_variable]

    if enable_pg:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL agent dependency is not installed. "
                "Run: python -m pip install -r python/requirements-agent.txt"
            ) from exc

        def run_readonly_sql(sql: str, limit: int) -> str:
            safe_sql = _validate_readonly_sql(sql)
            safe_limit = max(1, min(int(limit), 200))
            wrapped_sql = f"select * from ({safe_sql}) as agent_query limit %s"
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

        if semantic_layer is not None:
            try:
                from querymind.agent.semantic_layer import parse_filters, parse_name_list
            except ImportError as exc:
                raise RuntimeError("Failed to import QueryMind semantic layer utilities.") from exc

            @tool
            def describe_semantic_layer() -> str:
                """Return the governed business metrics, dimensions, filters, and table mappings."""
                payload = semantic_layer.prompt_context()
                _log(f"\n[tool:describe_semantic_layer] response\n{payload}", print_trace)
                return payload

            @tool
            def query_metric(
                metric: str,
                dimensions: str = "",
                filters_json: str = "{}",
                named_filters: str = "",
                limit: int = 50,
            ) -> str:
                """
                Query a governed semantic metric.

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

            tools.extend([describe_semantic_layer, query_metric])

        @tool
        def execute_sql(sql: str, limit: int = 50) -> str:
            """Execute a read-only PostgreSQL SELECT query and return rows as JSON."""
            _log(f"\n[tool:execute_sql] request\nsql={sql}\nlimit={limit}", print_trace)
            payload = run_readonly_sql(sql, limit)
            _log(f"[tool:execute_sql] response\n{payload}", print_trace)
            return payload

        tools.append(execute_sql)

    prompt_parts = [
        "You are a data analysis agent.",
        "Use execute_python for calculations or Python data analysis.",
        "Use get_variable when you need to inspect a variable that was created earlier.",
        "Keep code short, print useful results, and do not install packages or access the network.",
    ]
    if enable_pg:
        prompt_parts.append("Use execute_sql only for read-only PostgreSQL ad-hoc exploration.")
    if semantic_layer is not None:
        prompt_parts.append(
            "A governed semantic layer is available. Prefer query_metric for business metric questions. "
            "Call describe_semantic_layer when you need the metric, dimension, or filter catalog. "
            "Only fall back to execute_sql when the semantic layer cannot express the request."
        )

    system_prompt = " ".join(prompt_parts)

    llm = ChatDeepSeek(
        model=model,
        temperature=0,
        timeout=model_timeout,
        max_retries=2,
    )

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )


def main():
    parser = argparse.ArgumentParser(description="LangChain MVP over QueryMind Runtime")
    parser.add_argument(
        "question",
        nargs="?",
        default=(
            "Use Python to create numbers 1 through 10, calculate their squares, "
            "store the result in a variable named result, and tell me the sum."
        ),
        help="User question for the agent.",
    )
    parser.add_argument("--host", default=os.getenv("QUERYMIND_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("QUERYMIND_PORT", "50051")))
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
        help="Enable the PostgreSQL execute_sql tool.",
    )
    parser.add_argument(
        "--print-trace",
        action="store_true",
        default=os.getenv("QUERYMIND_PRINT_TRACE", "").lower() in {"1", "true", "yes"},
        help="Print model messages, tool calls, and tool results after the final answer.",
    )
    parser.add_argument(
        "--semantic-layer",
        default=os.getenv("QUERYMIND_SEMANTIC_LAYER", ""),
        help="Optional YAML semantic layer file for governed metric queries.",
    )
    args = parser.parse_args()

    try:
        from querymind.client import QueryMindClient
    except ImportError as exc:
        raise RuntimeError(
            "QueryMind client imports failed. Generate the gRPC stubs first: "
            "python -m grpc_tools.protoc -I protobuf --python_out=python/querymind/generated "
            "--grpc_python_out=python/querymind/generated protobuf/cli.proto"
        ) from exc

    client = QueryMindClient(args.host, args.port)
    session_id = client.open_session()
    try:
        semantic_layer = None
        if args.semantic_layer:
            from querymind.agent.semantic_layer import SemanticLayer

            semantic_layer = SemanticLayer.from_file(args.semantic_layer)
            if not args.enable_pg:
                raise RuntimeError("--semantic-layer requires --enable-pg because metric queries execute on PostgreSQL.")

        agent = build_agent(
            client,
            session_id,
            args.model,
            args.enable_pg,
            args.print_trace,
            args.model_timeout,
            semantic_layer,
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
    finally:
        client.close_session(session_id)
        client.close()


if __name__ == "__main__":
    main()
