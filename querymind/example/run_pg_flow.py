import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEMO_ORDERS_TABLE = "public.querymind_demo_orders"
DEMO_USERS_TABLE = "public.querymind_demo_users"


def _json_default(value: Any) -> str:
    return str(value)


def _pg_config_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    from querymind.agent.postgres import pg_config_from_env

    config = pg_config_from_env()
    for key in ("host", "port", "dbname", "user", "password", "connect_timeout"):
        value = getattr(args, f"pg_{key}", None)
        if value is not None:
            config[key] = value
    return config


def setup_demo_data(pg_config: Dict[str, Any]) -> None:
    try:
        import psycopg2
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL dependency is not installed. "
            "Run: python3 -m pip install -r requirements-agent.txt"
        ) from exc

    user_rows = [
        (1, "active", "2026-05-01 10:00:00"),
        (2, "active", "2026-05-01 11:00:00"),
        (3, "active", "2026-05-02 09:30:00"),
        (4, "inactive", "2026-05-02 12:00:00"),
        (5, "trial", "2026-05-03 08:15:00"),
    ]
    order_rows = [
        (1, 2000, "paid", "organic", "2026-03-05 10:00:00"),
        (2, 1800, "paid", "ads", "2026-03-12 11:00:00"),
        (3, 700, "paid", "referral", "2026-03-20 09:30:00"),
        (4, 1800, "paid", "organic", "2026-04-03 10:00:00"),
        (5, 700, "paid", "ads", "2026-04-10 11:00:00"),
        (6, 500, "paid", "referral", "2026-04-22 09:30:00"),
    ]
    with psycopg2.connect(**pg_config) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                create table if not exists {DEMO_USERS_TABLE} (
                    id integer primary key,
                    status text not null,
                    created_at timestamp not null
                )
                """
            )
            cursor.execute(f"delete from {DEMO_USERS_TABLE}")
            cursor.executemany(
                f"""
                insert into {DEMO_USERS_TABLE} (id, status, created_at)
                values (%s, %s, %s)
                on conflict (id) do update
                set status = excluded.status,
                    created_at = excluded.created_at
                """,
                user_rows,
            )
            cursor.execute(
                f"""
                create table if not exists {DEMO_ORDERS_TABLE} (
                    id integer primary key,
                    amount integer not null,
                    status text not null,
                    channel text not null,
                    created_at timestamp not null
                )
                """
            )
            cursor.execute(f"delete from {DEMO_ORDERS_TABLE}")
            cursor.executemany(
                f"""
                insert into {DEMO_ORDERS_TABLE} (id, amount, status, channel, created_at)
                values (%s, %s, %s, %s, %s)
                on conflict (id) do update
                set amount = excluded.amount,
                    status = excluded.status,
                    channel = excluded.channel,
                    created_at = excluded.created_at
                """,
                order_rows,
            )


def run_flow(args: argparse.Namespace) -> Dict[str, Any]:
    from querymind.agent.postgres import execute_readonly_sql
    from querymind.agent.semantic_layer import SemanticLayer
    from querymind.core import (
        BasicQueryPlanner,
        QueryResult,
        build_month_over_month_sql,
        can_build_comparison_query,
        generate_basic_insight,
        generate_comparison_insight,
    )

    pg_config = _pg_config_from_args(args)
    if args.setup_demo_data:
        setup_demo_data(pg_config)

    layer = SemanticLayer.from_file(args.semantic_layer)
    planner = BasicQueryPlanner(layer)
    plan = planner.plan(args.question, limit=args.limit)
    if plan.needs_clarification:
        return {
            "plan": plan.to_dict(),
            "sql": "",
            "result": {"sql": "", "row_count": 0, "rows": [], "source": "none"},
            "insight": {
                "answer": plan.clarification_question or "需要补充查询条件。",
                "observations": [],
                "possible_causes": [],
                "recommended_actions": [],
                "evidence": [],
            },
        }

    if can_build_comparison_query(plan):
        sql = build_month_over_month_sql(layer, plan)
    else:
        sql = layer.build_metric_query(
            metric_name=plan.metric,
            dimensions=plan.dimensions,
            filters=plan.filters,
            named_filters=plan.named_filters,
            limit=plan.limit,
        )
    pg_result = execute_readonly_sql(
        sql,
        plan.limit,
        allowed_tables=[table.physical_name for table in layer.tables],
        pg_config=pg_config,
    )
    result = QueryResult(sql=sql, rows=pg_result["rows"], row_count=pg_result["row_count"])
    insight = (
        generate_comparison_insight(plan, result)
        if can_build_comparison_query(plan)
        else generate_basic_insight(plan, result)
    )
    return {
        "plan": plan.to_dict(),
        "sql": sql,
        "result": {**result.to_dict(), "source": "postgres"},
        "insight": insight.to_dict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run QueryMind's PostgreSQL end-to-end flow.")
    parser.add_argument("question", nargs="?", default="按用户状态统计活跃用户数")
    parser.add_argument("--semantic-layer", default="querymind/example/semantic_layer.yaml")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--setup-demo-data", action="store_true")
    parser.add_argument("--pg-host")
    parser.add_argument("--pg-port", type=int)
    parser.add_argument("--pg-dbname")
    parser.add_argument("--pg-user")
    parser.add_argument("--pg-password")
    parser.add_argument("--pg-connect-timeout", type=int)
    args = parser.parse_args()

    print(json.dumps(run_flow(args), ensure_ascii=False, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
